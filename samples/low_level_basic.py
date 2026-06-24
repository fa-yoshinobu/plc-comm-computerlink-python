from __future__ import annotations

import argparse
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from toyopuc import ToyopucClient


def main() -> int:
    # Advanced low-level example using explicit numeric addresses.
    # Use this when you want direct control over ToyopucClient behavior
    # instead of the simpler high-level wrapper examples.
    p = argparse.ArgumentParser(description="Basic low-level ToyopucClient example")
    p.add_argument("--host", required=True)
    p.add_argument("--port", required=True, type=int)
    p.add_argument("--protocol", choices=["tcp", "udp"], default="tcp")
    p.add_argument("--local-port", type=int, default=0)
    p.add_argument("--timeout", type=float, default=3.0)
    p.add_argument("--retries", type=int, default=0)
    args = p.parse_args()

    with ToyopucClient(
        args.host,
        args.port,
        transport=args.protocol,
        local_port=args.local_port,
        timeout=args.timeout,
        retries=args.retries,
    ) as plc:
        # D0000 word
        original_words = plc.read_words(0x0000, 1)
        try:
            plc.write_words(0x0000, [0x1234])
            print("D0000 =", [hex(v) for v in plc.read_words(0x0000, 1)])
        finally:
            plc.write_words(0x0000, original_words)

        # D0000L / D0000H bytes
        original_bytes = plc.read_bytes(0x2000, 2)
        try:
            plc.write_bytes(0x2000, [0x12, 0x34])
            print("D0000L/H =", [hex(v) for v in plc.read_bytes(0x2000, 2)])
        finally:
            plc.write_bytes(0x2000, original_bytes)

        # M0000 bit
        original_bit = plc.read_bit(0x1800)
        try:
            plc.write_bit(0x1800, True)
            print("M0000 =", plc.read_bit(0x1800))
        finally:
            plc.write_bit(0x1800, original_bit)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
