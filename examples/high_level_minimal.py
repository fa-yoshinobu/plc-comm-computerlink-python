from __future__ import annotations

import argparse

from toyopuc import ToyopucHighLevelClient


def main() -> int:
    # Shortest high-level example: connect, read one word, write one word.
    p = argparse.ArgumentParser(description="Minimal high-level Toyopuc client example")
    p.add_argument("--host", required=True)
    p.add_argument("--port", required=True, type=int)
    p.add_argument("--protocol", choices=["tcp", "udp"], default="tcp")
    p.add_argument("--local-port", type=int, default=0)
    p.add_argument("--timeout", type=float, default=3.0)
    p.add_argument("--retries", type=int, default=0)
    args = p.parse_args()

    with ToyopucHighLevelClient(
        args.host,
        args.port,
        protocol=args.protocol,
        local_port=args.local_port,
        timeout=args.timeout,
        retries=args.retries,
    ) as plc:
        print("before:", hex(plc.read("D0000")))
        plc.write("D0000", 0x1234)
        print("after :", hex(plc.read("D0000")))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
