# ruff: noqa: E402
"""Read-only TOYOPUC Computerlink polling sample with automatic reconnect."""

from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from toyopuc import ToyopucConnectionOptions, open_and_connect, read_typed
from toyopuc.errors import ToyopucError, ToyopucProtocolError, ToyopucTimeoutError

RETRYABLE_ERRORS = (OSError, ConnectionError, TimeoutError, EOFError, asyncio.TimeoutError, ToyopucTimeoutError)


def positive_float(value: str) -> float:
    parsed = float(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("value must be greater than zero")
    return parsed


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Read one TOYOPUC Computerlink value forever and reconnect after transport loss."
    )
    parser.add_argument("--host", required=True, help="PLC IP address or hostname")
    parser.add_argument("--port", type=int, default=1025, help="Computerlink TCP port (default 1025)")
    parser.add_argument("--transport", choices=("tcp", "udp"), default="tcp", help="Transport protocol")
    parser.add_argument("--local-port", type=int, default=0, help="UDP local port, or 0 for ephemeral")
    parser.add_argument("--profile", required=True, help="Canonical PLC profile, for example toyopuc:plus:extended")
    parser.add_argument("--device", default="P1-D0100", help="Device to poll (default P1-D0100)")
    parser.add_argument("--dtype", choices=("U", "S", "D", "L", "F"), default="U", help="Read type")
    parser.add_argument("--interval", type=positive_float, default=1.0, help="Polling interval in seconds")
    parser.add_argument("--timeout", type=positive_float, default=3.0, help="Socket timeout in seconds")
    parser.add_argument("--initial-backoff", type=positive_float, default=1.0, help="First reconnect delay")
    parser.add_argument("--max-backoff", type=positive_float, default=30.0, help="Maximum reconnect delay")
    return parser.parse_args()


def log_state(state: str, message: str) -> None:
    timestamp = datetime.now().isoformat(timespec="seconds")
    print(f"{timestamp} [{state}] {message}", flush=True)


def is_retryable(exc: BaseException) -> bool:
    if isinstance(exc, RETRYABLE_ERRORS):
        return True
    if isinstance(exc, ToyopucProtocolError) and str(exc) == "Connection closed while receiving":
        return True
    return isinstance(exc, ToyopucError) and str(exc) == "Socket error"


async def close_quietly(client: Any | None) -> None:
    if client is None:
        return
    try:
        await client.close()
    except Exception:
        pass


async def poll_forever(args: argparse.Namespace) -> None:
    options = ToyopucConnectionOptions(
        host=args.host,
        port=args.port,
        local_port=args.local_port,
        transport=args.transport,
        timeout=args.timeout,
        plc_profile=args.profile,
    )

    client: Any | None = None
    backoff = args.initial_backoff
    connected_once = False

    try:
        while True:
            if client is None:
                log_state("reconnecting", f"{args.transport} {args.host}:{args.port} profile={args.profile}")
                try:
                    client = await open_and_connect(options)
                except Exception as exc:
                    if not is_retryable(exc):
                        raise
                    log_state("reconnecting", f"connect failed: {exc}; retry in {backoff:.1f}s")
                    await asyncio.sleep(backoff)
                    backoff = min(backoff * 2.0, args.max_backoff)
                    continue

                if connected_once:
                    log_state("recovered", f"{args.device}:{args.dtype}")
                else:
                    log_state("connected", f"{args.device}:{args.dtype}")
                    connected_once = True
                backoff = args.initial_backoff

            try:
                value = await read_typed(client, args.device, args.dtype)
                log_state("read", f"{args.device}:{args.dtype}={value!r}")
                await asyncio.sleep(args.interval)
            except Exception as exc:
                if not is_retryable(exc):
                    raise
                log_state("lost", str(exc) or exc.__class__.__name__)
                await close_quietly(client)
                client = None
                log_state("reconnecting", f"retry in {backoff:.1f}s")
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2.0, args.max_backoff)
    finally:
        await close_quietly(client)


def main() -> int:
    args = parse_args()
    if args.max_backoff < args.initial_backoff:
        raise SystemExit("--max-backoff must be greater than or equal to --initial-backoff")
    try:
        asyncio.run(poll_forever(args))
    except KeyboardInterrupt:
        log_state("closed", "interrupted by Ctrl+C")
        return 0
    except ToyopucError as exc:
        log_state("lost", str(exc))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
