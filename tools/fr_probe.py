import argparse
from dataclasses import dataclass
from typing import Iterable, Optional

from toyopuc import ToyopucClient, encode_ext_no_address


def parse_int_auto(value: str) -> int:
    return int(value, 0)


def parse_csv_ints(value: str) -> list[int]:
    return [parse_int_auto(part.strip()) for part in value.split(",") if part.strip()]


def fmt_words(values: Iterable[int]) -> str:
    return "[" + ", ".join(f"0x{value:04X}" for value in values) + "]"


def hex_or_none(data: Optional[bytes]) -> str:
    if data is None:
        return "-"
    return data.hex(" ").upper()


@dataclass
class ProbeResult:
    label: str
    ok: bool
    detail: str
    tx_register: Optional[bytes] = None
    rx_register: Optional[bytes] = None
    tx_read: Optional[bytes] = None
    rx_read: Optional[bytes] = None


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Probe candidate FR access paths and print raw TX/RX for each attempt."
    )
    p.add_argument("--host", required=True)
    p.add_argument("--port", required=True, type=int)
    p.add_argument("--protocol", choices=("tcp", "udp"), default="tcp")
    p.add_argument("--local-port", type=int, default=0)
    p.add_argument("--timeout", type=float, default=5.0)
    p.add_argument("--retries", type=int, default=0)
    p.add_argument(
        "--indexes",
        default="0x0,0x8000",
        help="Comma-separated FR indexes to probe, e.g. 0x0,0x8000",
    )
    p.add_argument(
        "--register-exnos",
        default="0x40,0x41",
        help="Comma-separated FR register Ex No. values for CMD=CA probing (low byte is sent)",
    )
    p.add_argument(
        "--log",
        help="Optional text log path",
    )
    return p


def _print_and_log(line: str, log_f) -> None:
    print(line)
    if log_f is not None:
        log_f.write(line + "\n")
        log_f.flush()


def probe_direct_fr(plc: ToyopucClient, index: int) -> ProbeResult:
    ext = encode_ext_no_address("FR", index, "word")
    label = f"direct-fr-map index=0x{index:06X} no=0x{ext.no:02X} addr=0x{ext.addr:04X}"
    try:
        values = plc.read_ext_words(ext.no, ext.addr, 1)
        return ProbeResult(
            label=label,
            ok=True,
            detail=f"read={fmt_words(values)}",
            tx_read=plc.last_tx,
            rx_read=plc.last_rx,
        )
    except Exception as e:
        return ProbeResult(
            label=label,
            ok=False,
            detail=str(e),
            tx_read=plc.last_tx,
            rx_read=plc.last_rx,
        )


def probe_after_register(plc: ToyopucClient, ex_no: int, no: int, addr: int) -> ProbeResult:
    masked_ex_no = ex_no & 0xFF
    label = f"ca=0x{masked_ex_no:02X} (arg=0x{ex_no:X}) -> read no=0x{no:02X} addr=0x{addr:04X}"
    try:
        plc.fr_register(ex_no)
        tx_register = plc.last_tx
        rx_register = plc.last_rx
    except Exception as e:
        return ProbeResult(
            label=label,
            ok=False,
            detail=f"CA failed: {e}",
            tx_register=plc.last_tx,
            rx_register=plc.last_rx,
        )

    try:
        values = plc.read_ext_words(no, addr, 1)
        return ProbeResult(
            label=label,
            ok=True,
            detail=f"read={fmt_words(values)}",
            tx_register=tx_register,
            rx_register=rx_register,
            tx_read=plc.last_tx,
            rx_read=plc.last_rx,
        )
    except Exception as e:
        return ProbeResult(
            label=label,
            ok=False,
            detail=str(e),
            tx_register=tx_register,
            rx_register=rx_register,
            tx_read=plc.last_tx,
            rx_read=plc.last_rx,
        )


def main() -> int:
    args = build_parser().parse_args()
    indexes = parse_csv_ints(args.indexes)
    register_exnos = parse_csv_ints(args.register_exnos)
    log_f = open(args.log, "w", encoding="utf-8") if args.log else None
    try:
        with ToyopucClient(
            args.host,
            args.port,
            protocol=args.protocol,
            local_port=args.local_port,
            timeout=args.timeout,
            retries=args.retries,
        ) as plc:
            success_count = 0
            total_count = 0
            for index in indexes:
                _print_and_log(f"=== FR index 0x{index:06X} ===", log_f)

                direct = probe_direct_fr(plc, index)
                total_count += 1
                if direct.ok:
                    success_count += 1
                _print_and_log(
                    f"{direct.label}: {'OK' if direct.ok else 'ERR'} {direct.detail}",
                    log_f,
                )
                _print_and_log(f"  TX {hex_or_none(direct.tx_read)}", log_f)
                _print_and_log(f"  RX {hex_or_none(direct.rx_read)}", log_f)

                offset = index & 0x7FFF
                for ex_no in register_exnos:
                    for no in (ex_no, 0x00, 0x08):
                        result = probe_after_register(plc, ex_no, no, offset)
                        total_count += 1
                        if result.ok:
                            success_count += 1
                        _print_and_log(
                            f"{result.label}: {'OK' if result.ok else 'ERR'} {result.detail}",
                            log_f,
                        )
                        _print_and_log(
                            f"  CA TX {hex_or_none(result.tx_register)}",
                            log_f,
                        )
                        _print_and_log(
                            f"  CA RX {hex_or_none(result.rx_register)}",
                            log_f,
                        )
                        _print_and_log(
                            f"  RD TX {hex_or_none(result.tx_read)}",
                            log_f,
                        )
                        _print_and_log(
                            f"  RD RX {hex_or_none(result.rx_read)}",
                            log_f,
                        )
                _print_and_log("", log_f)

            _print_and_log(f"SUMMARY: {success_count}/{total_count} probes succeeded", log_f)
            return 0 if success_count > 0 else 1
    finally:
        if log_f is not None:
            log_f.close()


if __name__ == "__main__":
    raise SystemExit(main())

