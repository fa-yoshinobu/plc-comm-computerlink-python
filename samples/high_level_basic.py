# ruff: noqa: E402
from __future__ import annotations

"""
Common high-level tasks for TOYOPUC users.

What this sample shows:
- word read / write
- bit read / write
- `read_devices(...)`
- packed `W/H/L` access on bit families
- extended-area access such as `ES0000`

Examples:
    python samples/high_level_basic.py --host 192.168.250.100 --port 1025 \
        --profile toyopuc:plus:extended
    python samples/high_level_basic.py --host 192.168.250.100 --port 1035 \
        --protocol udp --local-port 12000 --profile toyopuc:plus:extended
"""

import argparse
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from toyopuc import ToyopucDeviceClient


def main() -> int:
    p = argparse.ArgumentParser(
        description="Basic high-level Toyopuc client example",
        epilog=(
            "Examples:\n"
            "  python samples/high_level_basic.py --host 192.168.250.100 --port 1025 "
            "--profile toyopuc:plus:extended\n"
            "  python samples/high_level_basic.py --host 192.168.250.100 --port 1035 "
            "--protocol udp --local-port 12000 --profile toyopuc:plus:extended"
        ),
        formatter_class=argparse.RawTextHelpFormatter,
    )
    p.add_argument("--host", required=True)
    p.add_argument("--port", required=True, type=int)
    p.add_argument("--protocol", choices=["tcp", "udp"], default="tcp")
    p.add_argument("--local-port", type=int, default=0)
    p.add_argument("--timeout", type=float, default=3.0)
    p.add_argument("--retries", type=int, default=0)
    p.add_argument("--profile", required=True, help="Canonical PLC profile, e.g. toyopuc:plus:extended")
    args = p.parse_args()

    with ToyopucDeviceClient(
        args.host,
        args.port,
        transport=args.protocol,
        local_port=args.local_port,
        timeout=args.timeout,
        retries=args.retries,
        plc_profile=args.profile,
    ) as plc:
        # The sample uses high-level device strings instead of raw protocol addresses.
        print("scenario: daily high-level tasks")
        plc.write("P1-D0000", 0x1234)
        print("P1-D0000 =", hex(plc.read_one("P1-D0000")))

        plc.write("P1-D0000L", 0x56)
        print("P1-D0000L =", hex(plc.read_one("P1-D0000L")))

        plc.write("P1-M0000", 1)
        print("P1-M0000 =", plc.read_one("P1-M0000"))

        plc.write("P1-D0000", 0x2222)
        print("P1-D0000 =", hex(plc.read_one("P1-D0000")))

        plc.write("ES0000", 0x3333)
        print("ES0000 =", hex(plc.read_one("ES0000")))

        values = plc.read_devices(["P1-D0000", "P1-D0001"])
        print("read_devices =", values)

        plc.write("P1-M0010W", 0x1234)
        print("P1-M0010W =", hex(plc.read_one("P1-M0010W")))
        print("P1-M0010L =", hex(plc.read_one("P1-M0010L")))
        print("P1-M0010H =", hex(plc.read_one("P1-M0010H")))

        plc.write("EX0010L", 0xAB)
        print("EX0010L =", hex(plc.read_one("EX0010L")))
        print(
            "EX0100..EX0107 =",
            [plc.read_one(f"EX{index:04X}") for index in range(0x0100, 0x0108)],
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
