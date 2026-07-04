# ruff: noqa: E402
"""Read-only monitor for multiple TOYOPUC Computerlink PLCs at the same time."""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from samples._operational_common import (
    ignore_snapshot,
    monitor_endpoint,
    non_negative_int,
    parse_plc_spec,
    parse_tag_spec,
    parse_transport,
    positive_float,
    positive_int,
)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""

    parser = argparse.ArgumentParser(description="Read the same tag set from multiple Computerlink PLCs concurrently.")
    parser.add_argument(
        "--plc", action="append", required=True, metavar="NAME=HOST,PROFILE[,PORT[,TRANSPORT[,LOCAL_PORT]]]"
    )
    parser.add_argument("--tag", action="append", default=[], metavar="NAME=ADDRESS")
    parser.add_argument("--port", type=int, default=1025, help="Default port when a --plc omits it")
    parser.add_argument("--transport", type=parse_transport, default="tcp", help="Default transport")
    parser.add_argument("--local-port", type=non_negative_int, default=0, help="Default UDP local port")
    parser.add_argument("--timeout", type=positive_float, default=3.0, help="Socket timeout in seconds")
    parser.add_argument("--interval", type=positive_float, default=1.0, help="Polling interval in seconds")
    parser.add_argument(
        "--cycles", type=positive_int, default=None, help="Stop after this many successful reads per PLC"
    )
    parser.add_argument("--initial-backoff", type=positive_float, default=1.0, help="First reconnect delay")
    parser.add_argument("--max-backoff", type=positive_float, default=30.0, help="Maximum reconnect delay")
    parser.add_argument(
        "--dry-run", action="store_true", help="Validate arguments and print the plan without connecting"
    )
    return parser.parse_args()


async def run(args: argparse.Namespace) -> None:
    """Run one monitoring task per PLC."""

    tags = [parse_tag_spec(value) for value in args.tag] or [parse_tag_spec("P1-D0100:U")]
    endpoints = [
        parse_plc_spec(
            value,
            default_port=args.port,
            default_transport=args.transport,
            default_local_port=args.local_port,
            default_timeout=args.timeout,
            default_interval=args.interval,
        )
        for value in args.plc
    ]

    if args.dry_run:
        for endpoint in endpoints:
            print(
                f"{endpoint.name}: {endpoint.transport} {endpoint.host}:{endpoint.port} profile={endpoint.plc_profile}"
            )
        print("tags: " + ", ".join(f"{tag.name}={tag.address}" for tag in tags))
        return

    await asyncio.gather(
        *(
            monitor_endpoint(
                endpoint,
                tags,
                cycles=args.cycles,
                initial_backoff=args.initial_backoff,
                max_backoff=args.max_backoff,
                handle_snapshot=ignore_snapshot,
            )
            for endpoint in endpoints
        )
    )


def main() -> int:
    """CLI entry point."""

    args = parse_args()
    if args.max_backoff < args.initial_backoff:
        raise SystemExit("--max-backoff must be greater than or equal to --initial-backoff")
    try:
        asyncio.run(run(args))
    except KeyboardInterrupt:
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
