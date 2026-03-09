#!/usr/bin/env python
import argparse
import re
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Optional, Tuple

from toyopuc import (
    ToyopucClient,
    ToyopucError,
    encode_bit_address,
    encode_exno_byte_u32,
    encode_fr_word_addr32,
    encode_ext_no_address,
    encode_program_bit_address,
    encode_program_word_address,
    encode_word_address,
    parse_address,
)


BASE_BIT_AREAS = {"P", "K", "V", "T", "C", "L", "X", "Y", "M"}
BASE_WORD_AREAS = {"S", "N", "R", "D", "B"}
EXT_BIT_AREAS = {"EP", "EK", "EV", "ET", "EC", "EL", "EX", "EY", "EM", "GX", "GY", "GM"}
EXT_WORD_AREAS = {"ES", "EN", "H", "U", "EB", "FR"}
PREFIXES = {"P1", "P2", "P3"}
PREFIX_TO_NO = {"P1": 0x01, "P2": 0x02, "P3": 0x03}

EXT_BIT_SPECS = {
    "EP": (0x00, 0x0000),
    "EK": (0x00, 0x0200),
    "EV": (0x00, 0x0400),
    "ET": (0x00, 0x0600),
    "EC": (0x00, 0x0600),
    "EL": (0x00, 0x0700),
    "EX": (0x00, 0x0B00),
    "EY": (0x00, 0x0B00),
    "EM": (0x00, 0x0C00),
    "GX": (0x07, 0x0000),
    "GY": (0x07, 0x0000),
    "GM": (0x07, 0x2000),
}


@dataclass
class Target:
    label: str
    kind: str
    default_value: int
    write: Callable[[ToyopucClient, int], None]
    read: Callable[[ToyopucClient], int]


def _pack_u16_le(value: int) -> bytes:
    return bytes([value & 0xFF, (value >> 8) & 0xFF])


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _write_log(log_f, line: str) -> None:
    if log_f:
        log_f.write(line + "\n")
        log_f.flush()


def _split_area_index(text: str) -> Tuple[str, int]:
    m = re.fullmatch(r"([A-Z]+)([0-9A-F]+)", text.upper())
    if not m:
        raise ValueError(f"Invalid target format: {text}")
    return m.group(1), int(m.group(2), 16)


def _prefixed_bit_addr(prefix: str, area: str, index: int) -> Tuple[int, int, int]:
    parsed = parse_address(f"{area}{index:04X}", "bit")
    bit_no, addr = encode_program_bit_address(parsed)
    return PREFIX_TO_NO[prefix], bit_no, addr


def _prefixed_word_addr(prefix: str, area: str, index: int) -> Tuple[int, int]:
    parsed = parse_address(f"{area}{index:04X}", "word")
    return PREFIX_TO_NO[prefix], encode_program_word_address(parsed)


def _ext_bit_addr(area: str, index: int) -> Tuple[int, int, int]:
    no, byte_base = EXT_BIT_SPECS[area]
    return no, index & 0x07, byte_base + (index >> 3)


def _pc10_u_word_addr32(index: int) -> int:
    if index < 0x08000 or index > 0x1FFFF:
        raise ValueError("U PC10 range is 0x08000-0x1FFFF")
    block = index // 0x8000
    ex_no = 0x03 + block
    byte_addr = (index % 0x8000) * 2
    return encode_exno_byte_u32(ex_no, byte_addr)


def _pc10_eb_word_addr32(index: int) -> int:
    if index < 0x00000 or index > 0x3FFFF:
        raise ValueError("EB PC10 range is 0x00000-0x3FFFF")
    block = index // 0x8000
    ex_no = 0x10 + block
    byte_addr = (index % 0x8000) * 2
    return encode_exno_byte_u32(ex_no, byte_addr)


def _resolve_non_prefixed(target_text: str) -> Target:
    area, index = _split_area_index(target_text)
    if area in BASE_BIT_AREAS:
        parsed = parse_address(f"{area}{index:04X}", "bit")
        addr = encode_bit_address(parsed)
        return Target(
            label=f"{area}{index:04X}",
            kind="bit",
            default_value=1,
            write=lambda plc, value, addr=addr: plc.write_bit(addr, bool(value)),
            read=lambda plc, addr=addr: 1 if plc.read_bit(addr) else 0,
        )
    if area in BASE_WORD_AREAS:
        parsed = parse_address(f"{area}{index:04X}", "word")
        addr = encode_word_address(parsed)
        return Target(
            label=f"{area}{index:04X}",
            kind="word",
            default_value=0xFFFF,
            write=lambda plc, value, addr=addr: plc.write_words(addr, [value & 0xFFFF]),
            read=lambda plc, addr=addr: plc.read_words(addr, 1)[0],
        )
    if area in EXT_BIT_AREAS:
        no, bit_no, addr = _ext_bit_addr(area, index)
        return Target(
            label=f"{area}{index:04X}",
            kind="ext-bit",
            default_value=1,
            write=lambda plc, value, no=no, bit_no=bit_no, addr=addr: plc.write_ext_multi(
                [(no, bit_no, addr, value & 0x01)], [], []
            ),
            read=lambda plc, no=no, bit_no=bit_no, addr=addr: (
                plc.read_ext_multi([(no, bit_no, addr)], [], [])[0] & 0x01
            ),
        )
    if area in EXT_WORD_AREAS:
        label = f"{area}{index:0{max(4, len(f'{index:X}'))}X}"
        if area == "U" and index >= 0x08000:
            addr32 = _pc10_u_word_addr32(index)
            return Target(
                label=label,
                kind="pc10-word",
                default_value=0xFFFF,
                write=lambda plc, value, addr32=addr32: plc.pc10_block_write(
                    addr32, _pack_u16_le(value & 0xFFFF)
                ),
                read=lambda plc, addr32=addr32: int.from_bytes(plc.pc10_block_read(addr32, 2), "little"),
            )
        if area == "EB" and index <= 0x3FFFF:
            addr32 = _pc10_eb_word_addr32(index)
            return Target(
                label=label,
                kind="pc10-word",
                default_value=0xFFFF,
                write=lambda plc, value, addr32=addr32: plc.pc10_block_write(
                    addr32, _pack_u16_le(value & 0xFFFF)
                ),
                read=lambda plc, addr32=addr32: int.from_bytes(plc.pc10_block_read(addr32, 2), "little"),
            )
        if area == "FR":
            addr32 = encode_fr_word_addr32(index)
            return Target(
                label=label,
                kind="pc10-word",
                default_value=0xFFFF,
                write=lambda plc, value, addr32=addr32: plc.pc10_block_write(
                    addr32, _pack_u16_le(value & 0xFFFF)
                ),
                read=lambda plc, addr32=addr32: int.from_bytes(plc.pc10_block_read(addr32, 2), "little"),
            )
        ext = encode_ext_no_address(area, index, "word")
        return Target(
            label=label,
            kind="ext-word",
            default_value=0xFFFF,
            write=lambda plc, value, no=ext.no, addr=ext.addr: plc.write_ext_words(
                no, addr, [value & 0xFFFF]
            ),
            read=lambda plc, no=ext.no, addr=ext.addr: plc.read_ext_words(no, addr, 1)[0],
        )
    raise ValueError(f"Unsupported target area: {target_text}")


def resolve_target(target_text: str) -> Target:
    upper = target_text.upper()
    if "-" not in upper:
        return _resolve_non_prefixed(upper)
    prefix, rest = upper.split("-", 1)
    if prefix not in PREFIXES:
        raise ValueError(f"Unsupported prefix: {prefix}")
    area, index = _split_area_index(rest)
    if area in BASE_BIT_AREAS:
        no, bit_no, addr = _prefixed_bit_addr(prefix, area, index)
        return Target(
            label=f"{prefix}-{area}{index:04X}",
            kind="pref-bit",
            default_value=1,
            write=lambda plc, value, no=no, bit_no=bit_no, addr=addr: plc.write_ext_multi(
                [(no, bit_no, addr, value & 0x01)], [], []
            ),
            read=lambda plc, no=no, bit_no=bit_no, addr=addr: (
                plc.read_ext_multi([(no, bit_no, addr)], [], [])[0] & 0x01
            ),
        )
    if area in BASE_WORD_AREAS:
        no, addr = _prefixed_word_addr(prefix, area, index)
        return Target(
            label=f"{prefix}-{area}{index:04X}",
            kind="pref-word",
            default_value=0xFFFF,
            write=lambda plc, value, no=no, addr=addr: plc.write_ext_words(
                no, addr, [value & 0xFFFF]
            ),
            read=lambda plc, no=no, addr=addr: plc.read_ext_words(no, addr, 1)[0],
        )
    raise ValueError(f"Unsupported prefixed target area: {target_text}")


def main() -> int:
    p = argparse.ArgumentParser(description="Looped write test for cable unplug/replug recovery")
    p.add_argument("--host", required=True)
    p.add_argument("--port", type=int, required=True)
    p.add_argument("--target", required=True, help="e.g. M0000, D0000, EX0000, U08000, P1-M0000")
    p.add_argument("--protocol", choices=["tcp", "udp"], default="tcp")
    p.add_argument("--local-port", type=int, default=0)
    p.add_argument("--timeout", type=float, default=3.0)
    p.add_argument("--retries", type=int, default=0)
    p.add_argument("--mode", choices=["write", "read"], default="write")
    p.add_argument("--interval-ms", type=int, default=200)
    p.add_argument("--count", type=int, default=0, help="0 means infinite")
    p.add_argument("--value", type=lambda s: int(s, 0), default=None, help="override write value")
    p.add_argument("--expect", type=lambda s: int(s, 0), default=None, help="optional expected read value")
    p.add_argument("--log", default="", help="optional log file path")
    args = p.parse_args()

    target = resolve_target(args.target)
    value = target.default_value if args.value is None else args.value
    if target.kind.endswith("bit"):
        value &= 0x01
    else:
        value &= 0xFFFF
    interval_s = max(args.interval_ms, 1) / 1000.0
    log_f = open(args.log, "w", encoding="utf-8") if args.log else None

    success_count = 0
    error_count = 0
    consecutive_errors = 0
    recoveries = 0

    print(f"target: {target.label}")
    print(f"kind: {target.kind}")
    print(f"mode: {args.mode}")
    print(f"value: 0x{value:X}" if not target.kind.endswith("bit") else f"value: {value}")
    if args.expect is not None:
        print(f"expect: 0x{args.expect:X}" if not target.kind.endswith("bit") else f"expect: {args.expect & 0x01}")
    print(f"interval_ms: {args.interval_ms}")
    print("Press Ctrl+C to stop.")

    _write_log(log_f, f"started: {_now()}")
    _write_log(log_f, f"target: {target.label}")
    _write_log(log_f, f"kind: {target.kind}")
    _write_log(log_f, f"mode: {args.mode}")
    _write_log(log_f, f"value: {value}")
    _write_log(log_f, f"expect: {args.expect}")
    _write_log(log_f, f"protocol: {args.protocol}")
    _write_log(log_f, f"local_port: {args.local_port}")
    _write_log(log_f, f"interval_ms: {args.interval_ms}")

    client = ToyopucClient(
        args.host,
        args.port,
        protocol=args.protocol,
        local_port=args.local_port,
        timeout=args.timeout,
        retries=args.retries,
    )

    seq = 0
    try:
        while args.count == 0 or seq < args.count:
            seq += 1
            started = time.monotonic()
            try:
                if args.mode == "write":
                    target.write(client, value)
                    line = f"{_now()} seq={seq} result=OK"
                else:
                    read_value = target.read(client)
                    if args.expect is None:
                        value_text = f"0x{read_value:X}" if not target.kind.endswith("bit") else str(read_value)
                        line = f"{_now()} seq={seq} result=OK value={value_text}"
                    else:
                        expected = (args.expect & 0x01) if target.kind.endswith("bit") else (args.expect & 0xFFFF)
                        if read_value == expected:
                            value_text = f"0x{read_value:X}" if not target.kind.endswith("bit") else str(read_value)
                            line = f"{_now()} seq={seq} result=OK value={value_text}"
                        else:
                            value_text = f"0x{read_value:X}" if not target.kind.endswith("bit") else str(read_value)
                            expected_text = f"0x{expected:X}" if not target.kind.endswith("bit") else str(expected)
                            line = f"{_now()} seq={seq} result=MISMATCH value={value_text} expect={expected_text}"
                success_count += 1
                recovered_line = None
                if consecutive_errors:
                    recoveries += 1
                    recovered_line = f"{_now()} seq={seq} result=RECOVERED after_errors={consecutive_errors}"
                    consecutive_errors = 0
                if recovered_line is not None:
                    print(recovered_line)
                    _write_log(log_f, recovered_line)
                print(line)
                _write_log(log_f, line)
            except (ToyopucError, OSError, ValueError) as e:
                error_count += 1
                consecutive_errors += 1
                line = f"{_now()} seq={seq} result=ERROR detail={type(e).__name__}: {e}"
                print(line)
                _write_log(log_f, line)
                client.close()

            elapsed = time.monotonic() - started
            sleep_s = interval_s - elapsed
            if sleep_s > 0:
                time.sleep(sleep_s)
    except KeyboardInterrupt:
        print("stopped by operator")
        _write_log(log_f, "stopped by operator")
    finally:
        client.close()
        print("Summary")
        print(f"- target: {target.label}")
        print(f"- success: {success_count}")
        print(f"- error: {error_count}")
        print(f"- recoveries: {recoveries}")
        _write_log(log_f, f"summary success={success_count} error={error_count} recoveries={recoveries}")
        _write_log(log_f, f"finished: {_now()}")
        if log_f:
            log_f.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
