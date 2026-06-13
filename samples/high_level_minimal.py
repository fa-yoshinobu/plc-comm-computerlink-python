# ruff: noqa: E402
from __future__ import annotations

"""
Smallest high-level TOYOPUC sample.

What this sample shows:
- connect with `ToyopucDeviceClient`
- read one word
- write one word
- read the changed word again

Examples:
    python samples/high_level_minimal.py --host 192.168.250.100 --port 1025
    python samples/high_level_minimal.py --host 192.168.250.100 --port 1035 \
        --protocol udp --local-port 12000
"""

import argparse
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from toyopuc import ToyopucDeviceClient


def main() -> int:
    p = argparse.ArgumentParser(
        description="Minimal high-level Toyopuc client example",
        epilog=(
            "Examples:\n"
            "  python samples/high_level_minimal.py --host 192.168.250.100 --port 1025\n"
            "  python samples/high_level_minimal.py --host 192.168.250.100 --port 1035 "
            "--protocol udp --local-port 12000"
        ),
        formatter_class=argparse.RawTextHelpFormatter,
    )
    p.add_argument("--host", required=True)
    p.add_argument("--port", required=True, type=int)
    p.add_argument("--protocol", choices=["tcp", "udp"], default="tcp")
    p.add_argument("--local-port", type=int, default=0)
    p.add_argument("--timeout", type=float, default=3.0)
    p.add_argument("--retries", type=int, default=0)
    p.add_argument("--plc-profile", default="toyopuc:plus:extended")
    args = p.parse_args()

    # Open a high-level string-address client for the requested transport.
    with ToyopucDeviceClient(
        args.host,
        args.port,
        transport=args.protocol,
        local_port=args.local_port,
        timeout=args.timeout,
        retries=args.retries,
        plc_profile=args.plc_profile,
    ) as plc:
        # Profile selection: --plc-profile controls range validation for your PLC.
        print("scenario: read one word, write one word, read it back")
        # Read a prefixed basic word; see GOTCHAS.md for the required P1-/P2-/P3- prefix.
        print("before:", hex(plc.read("P1-D0000")))
        # Write only to a test word you control.
        plc.write("P1-D0000", 0x1234)
        # Read back the word to confirm the write path.
        print("after :", hex(plc.read("P1-D0000")))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
