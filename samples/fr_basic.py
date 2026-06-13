# ruff: noqa: E402
from __future__ import annotations

"""
High-level FR storage example.

What this sample shows:
- read one FR word
- write one FR word
- optionally commit the touched FR block to flash

Examples:
    python samples/fr_basic.py --host 192.168.250.100 --port 1035 \
        --protocol udp --local-port 12000 --target FR000000 --value 0x1234
    python samples/fr_basic.py --host 192.168.250.100 --port 1035 \
        --protocol udp --local-port 12000 --target FR000000 --value 0x1234 --commit
"""

import argparse
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from toyopuc import ToyopucDeviceClient


def parse_int_auto(text: str) -> int:
    return int(text, 0)


def main() -> int:
    p = argparse.ArgumentParser(
        description="FR read/write example",
        epilog=(
            "Examples:\n"
            "  python samples/fr_basic.py --host 192.168.250.100 --port 1035 "
            "--protocol udp --local-port 12000 --target FR000000 --value 0x1234\n"
            "  python samples/fr_basic.py --host 192.168.250.100 --port 1035 "
            "--protocol udp --local-port 12000 --target FR000000 --value 0x1234 --commit"
        ),
        formatter_class=argparse.RawTextHelpFormatter,
    )
    p.add_argument("--host", required=True)
    p.add_argument("--port", required=True, type=int)
    p.add_argument("--protocol", choices=["tcp", "udp"], default="tcp")
    p.add_argument("--local-port", type=int, default=0)
    p.add_argument("--timeout", type=float, default=5.0)
    p.add_argument("--retries", type=int, default=0)
    p.add_argument("--target", default="FR000000", help="FR word device such as FR000000")
    p.add_argument("--value", type=parse_int_auto, default=0x1234, help="word value to write")
    p.add_argument("--commit", action="store_true", help="persist the written FR block to flash")
    p.add_argument("--plc-profile", default="toyopuc:nano-10gx:native")
    args = p.parse_args()

    # Open a high-level client; FR availability depends on the selected profile and PLC configuration.
    with ToyopucDeviceClient(
        args.host,
        args.port,
        transport=args.protocol,
        local_port=args.local_port,
        timeout=args.timeout,
        retries=args.retries,
        plc_profile=args.plc_profile,
    ) as plc:
        # Profile selection: --plc-profile must name a catalog that exposes FR.
        print("scenario: FR read / write with optional flash commit")
        # Read the current FR word before touching it.
        before = plc.read_fr(args.target)
        print("target =", args.target)
        print("before =", hex(before))
        print("write  =", hex(args.value & 0xFFFF))
        print("commit =", args.commit)
        # FR writes are staged unless committed; see GOTCHAS.md for power-cycle persistence.
        plc.write_fr(args.target, args.value, commit=args.commit)
        # Read back the staged or committed value.
        after = plc.read_fr(args.target)
        print("after  =", hex(after))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
