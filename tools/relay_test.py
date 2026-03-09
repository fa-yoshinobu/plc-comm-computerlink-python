#!/usr/bin/env python
import argparse
from typing import List, Sequence, Tuple

from toyopuc import (
    ToyopucClient,
    ToyopucProtocolError,
    encode_word_address,
    parse_address,
)
from toyopuc.protocol import (
    build_clock_read,
    build_cpu_status_read,
    build_relay_nested,
    build_word_read,
    parse_clock_data,
    parse_cpu_status_data,
    parse_response,
    unpack_u16_le,
)


def parse_int_auto(text: str) -> int:
    return int(text, 0)


def parse_hex_bytes(text: str) -> bytes:
    cleaned = text.replace(" ", "").replace("-", "").replace(":", "")
    if cleaned.startswith("0x"):
        cleaned = cleaned[2:]
    if len(cleaned) % 2 != 0:
        raise argparse.ArgumentTypeError("hex byte string must contain an even number of hex digits")
    try:
        return bytes.fromhex(cleaned)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc


def parse_hops(text: str) -> List[Tuple[int, int]]:
    hops: List[Tuple[int, int]] = []
    for part in text.split(","):
        item = part.strip()
        if not item:
            continue
        if ":" not in item:
            raise argparse.ArgumentTypeError("each hop must be LINK:STATION, for example 1:1 or 0x01:0x02")
        link_text, station_text = item.split(":", 1)
        hops.append((parse_int_auto(link_text), parse_int_auto(station_text)))
    if not hops:
        raise argparse.ArgumentTypeError("at least one hop is required")
    return hops


def format_frame(resp) -> bytes:
    length = len(resp.data) + 1
    ll = length & 0xFF
    lh = (length >> 8) & 0xFF
    return bytes([resp.ft, resp.rc, ll, lh, resp.cmd]) + resp.data


def build_inner_payload(args) -> bytes:
    if args.inner == "cpu-status":
        return build_cpu_status_read()
    if args.inner == "clock-read":
        return build_clock_read()
    if args.inner == "word-read":
        addr = encode_word_address(parse_address(args.device, "word"))
        return build_word_read(addr, args.count)
    return args.raw_inner


def print_decoded_inner(args, inner_resp) -> None:
    if args.inner == "cpu-status":
        status = parse_cpu_status_data(inner_resp.data)
        print(f"INNER CPU_STATUS raw = {status.raw_bytes_hex}")
        print(f"INNER CPU_STATUS RUN = {status.run}")
        print(f"INNER CPU_STATUS Alarm = {status.alarm}")
        print(f"INNER CPU_STATUS PC10 mode = {status.pc10_mode}")
        print(f"INNER CPU_STATUS Under writing flash register = {status.under_writing_flash_register}")
        print(f"INNER CPU_STATUS Abnormal write flash register = {status.abnormal_write_flash_register}")
        return
    if args.inner == "clock-read":
        clock = parse_clock_data(inner_resp.data)
        print(f"INNER CLOCK raw = {clock}")
        try:
            print(f"INNER CLOCK datetime = {clock.as_datetime().isoformat(sep=' ')}")
        except Exception as exc:
            print(f"INNER CLOCK datetime = unavailable ({exc})")
        return
    if args.inner == "word-read":
        words = unpack_u16_le(inner_resp.data)
        print(f"INNER WORD_READ device = {args.device}")
        print(f"INNER WORD_READ count = {args.count}")
        print("INNER WORD_READ values = " + ", ".join(f"0x{value:04X}" for value in words))


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Real-hardware relay command (`CMD=60`) test helper.")
    p.add_argument("--host", required=True)
    p.add_argument("--port", required=True, type=int)
    p.add_argument("--protocol", choices=("tcp", "udp"), default="tcp")
    p.add_argument("--local-port", type=int, default=0)
    p.add_argument("--timeout", type=float, default=5.0)
    p.add_argument("--retries", type=int, default=0)
    p.add_argument(
        "--hops",
        required=True,
        type=parse_hops,
        help="comma-separated LINK:STATION list, for example 1:1 or 0x01:0x01,0x02:0x03",
    )
    p.add_argument(
        "--inner",
        choices=("cpu-status", "clock-read", "word-read", "raw"),
        default="cpu-status",
        help="inner command to relay; default is safe read-only CPU status",
    )
    p.add_argument("--device", default="D0000", help="word device for --inner word-read")
    p.add_argument("--count", type=parse_int_auto, default=1, help="word count for --inner word-read")
    p.add_argument("--raw-inner", type=parse_hex_bytes, default=b"", help="full inner frame bytes for --inner raw")
    return p


def main() -> int:
    args = build_parser().parse_args()
    if args.inner == "word-read" and args.count < 1:
        raise SystemExit("--count must be >= 1")
    if args.inner == "raw" and not args.raw_inner:
        raise SystemExit("--raw-inner is required when --inner raw is used")

    inner_payload = build_inner_payload(args)

    plc = None
    try:
        with ToyopucClient(
            args.host,
            args.port,
            protocol=args.protocol,
            local_port=args.local_port,
            timeout=args.timeout,
            retries=args.retries,
        ) as plc:
            resp = plc.send_payload(build_relay_nested(args.hops, inner_payload))
            outer_raw = format_frame(resp)
            print("HOPS =", ", ".join(f"{link}:{station}" for link, station in args.hops))
            print("INNER_MODE =", args.inner)
            print("TX =", plc.last_tx.hex(" ").upper() if plc.last_tx else "")
            print("RX =", outer_raw.hex(" ").upper())
            if resp.cmd != 0x60:
                raise ToyopucProtocolError(f"Unexpected outer CMD in relay response: 0x{resp.cmd:02X}")
            if len(resp.data) < 3:
                raise ToyopucProtocolError("Relay response data too short")

            link_no, station_no, ack = resp.data[0], resp.data[1], resp.data[2]
            inner_raw = resp.data[3:]
            print(f"OUTER link = 0x{link_no:02X}")
            print(f"OUTER station = 0x{station_no:02X}")
            print(f"OUTER ack = 0x{ack:02X}")
            print("INNER_RAW =", inner_raw.hex(" ").upper())

            if ack != 0x06:
                print("INNER_PARSE = skipped because outer ACK is not 0x06")
                return 1

            inner_resp = parse_response(inner_raw)
            print(f"INNER FT = 0x{inner_resp.ft:02X}")
            print(f"INNER RC = 0x{inner_resp.rc:02X}")
            print(f"INNER CMD = 0x{inner_resp.cmd:02X}")
            print("INNER DATA =", inner_resp.data.hex(" ").upper())

            if inner_resp.rc != 0x00:
                return 1

            print_decoded_inner(args, inner_resp)
            return 0
    except Exception as e:
        print(f"ERR: {e}")
        if plc is not None and plc.last_tx is not None:
            print(f"LAST_TX {plc.last_tx.hex(' ').upper()}")
        if plc is not None and plc.last_rx is not None:
            print(f"LAST_RX {plc.last_rx.hex(' ').upper()}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
