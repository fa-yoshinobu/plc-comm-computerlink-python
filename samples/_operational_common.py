# ruff: noqa: E402
"""Shared helpers for read-only operational TOYOPUC Computerlink samples."""

from __future__ import annotations

import argparse
import asyncio
import sys
from collections.abc import Awaitable, Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from toyopuc import ToyopucConnectionOptions, open_and_connect, read_typed
from toyopuc.errors import ToyopucError, ToyopucProtocolError, ToyopucTimeoutError

RETRYABLE_ERRORS = (
    OSError,
    ConnectionError,
    TimeoutError,
    EOFError,
    asyncio.TimeoutError,
    ToyopucTimeoutError,
)

SnapshotHandler = Callable[["PlcEndpoint", Mapping[str, object]], Awaitable[None]]


@dataclass(frozen=True)
class TagSpec:
    """One read-only tag in an operational polling sample."""

    name: str
    address: str


@dataclass(frozen=True)
class PlcEndpoint:
    """Connection and polling settings for one PLC."""

    name: str
    host: str
    plc_profile: str
    port: int = 1025
    transport: str = "tcp"
    local_port: int = 0
    timeout: float = 3.0
    interval: float = 1.0


async def ignore_snapshot(_endpoint: PlcEndpoint, _snapshot: Mapping[str, object]) -> None:
    """Use when console logging is enough and no additional output is required."""


def positive_float(value: str) -> float:
    """Parse a positive floating-point CLI value."""

    parsed = float(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("value must be greater than zero")
    return parsed


def positive_int(value: str) -> int:
    """Parse a positive integer CLI value."""

    parsed = int(value, 0)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("value must be greater than zero")
    return parsed


def non_negative_int(value: str) -> int:
    """Parse a non-negative integer CLI value."""

    parsed = int(value, 0)
    if parsed < 0:
        raise argparse.ArgumentTypeError("value must be zero or greater")
    return parsed


def normalize_tag_name(address: str) -> str:
    """Create a readable tag name from an address string."""

    return address.replace("\\", "_").replace(":", "_").replace(".", "_").replace("-", "_").replace("/", "_").lower()


def parse_tag_spec(value: str) -> TagSpec:
    """Parse NAME=ADDRESS or ADDRESS into a tag specification."""

    name, separator, address = value.partition("=")
    if separator:
        if not name or not address:
            raise argparse.ArgumentTypeError("expected NAME=ADDRESS")
        return TagSpec(name=name, address=address)
    return TagSpec(name=normalize_tag_name(value), address=value)


def parse_transport(value: str) -> str:
    """Validate a transport string."""

    transport = value.lower()
    if transport not in {"tcp", "udp"}:
        raise argparse.ArgumentTypeError("transport must be tcp or udp")
    return transport


def parse_plc_spec(
    value: str,
    *,
    default_port: int,
    default_transport: str,
    default_local_port: int,
    default_timeout: float,
    default_interval: float,
) -> PlcEndpoint:
    """Parse NAME=HOST,PROFILE[,PORT[,TRANSPORT[,LOCAL_PORT]]] for multi-PLC samples."""

    name, separator, rest = value.partition("=")
    if not separator or not name or not rest:
        raise argparse.ArgumentTypeError("expected NAME=HOST,PROFILE[,PORT[,TRANSPORT[,LOCAL_PORT]]]")

    parts = [part.strip() for part in rest.split(",")]
    if len(parts) < 2 or len(parts) > 5:
        raise argparse.ArgumentTypeError("expected NAME=HOST,PROFILE[,PORT[,TRANSPORT[,LOCAL_PORT]]]")

    port = int(parts[2], 0) if len(parts) >= 3 and parts[2] else default_port
    transport = parse_transport(parts[3]) if len(parts) >= 4 and parts[3] else default_transport
    local_port = int(parts[4], 0) if len(parts) == 5 and parts[4] else default_local_port
    return PlcEndpoint(
        name=name,
        host=parts[0],
        plc_profile=parts[1],
        port=port,
        transport=transport,
        local_port=local_port,
        timeout=default_timeout,
        interval=default_interval,
    )


def split_address(address: str) -> tuple[str, str]:
    """Split DEVICE:DTYPE text for read_typed."""

    device, separator, dtype = address.rpartition(":")
    if not separator:
        return address, "U"
    if not device or not dtype:
        raise ValueError(f"address must be DEVICE:DTYPE: {address!r}")
    return device, dtype.upper()


def log_state(plc_name: str, state: str, message: str) -> None:
    """Print a timestamped monitoring state line."""

    timestamp = datetime.now().isoformat(timespec="seconds")
    print(f"{timestamp} [{plc_name}] [{state}] {message}", flush=True)


def is_retryable(exc: BaseException) -> bool:
    """Return true for transport-level failures that should reconnect."""

    if isinstance(exc, RETRYABLE_ERRORS):
        return True
    if isinstance(exc, ToyopucProtocolError) and str(exc) == "Connection closed while receiving":
        return True
    return isinstance(exc, ToyopucError) and str(exc) == "Socket error"


async def close_quietly(client: Any | None) -> None:
    """Close a client while suppressing cleanup errors."""

    if client is None:
        return
    try:
        await client.close()
    except Exception:
        pass


def build_options(endpoint: PlcEndpoint) -> ToyopucConnectionOptions:
    """Build high-level connection options for one endpoint."""

    return ToyopucConnectionOptions(
        host=endpoint.host,
        port=endpoint.port,
        local_port=endpoint.local_port,
        transport=endpoint.transport,
        timeout=endpoint.timeout,
        plc_profile=endpoint.plc_profile,
    )


def format_snapshot(snapshot: Mapping[str, object]) -> str:
    """Format a snapshot for compact console output."""

    return ", ".join(f"{name}={value!r}" for name, value in snapshot.items())


async def monitor_endpoint(
    endpoint: PlcEndpoint,
    tags: Sequence[TagSpec],
    *,
    cycles: int | None,
    initial_backoff: float,
    max_backoff: float,
    handle_snapshot: SnapshotHandler,
) -> None:
    """Poll one PLC forever or for a fixed number of successful cycles."""

    if not tags:
        raise ValueError("at least one tag is required")

    client: Any | None = None
    completed = 0
    backoff = initial_backoff
    connected_once = False

    try:
        while cycles is None or completed < cycles:
            if client is None:
                log_state(
                    endpoint.name,
                    "reconnecting",
                    f"{endpoint.transport} {endpoint.host}:{endpoint.port} profile={endpoint.plc_profile}",
                )
                try:
                    client = await open_and_connect(build_options(endpoint))
                except Exception as exc:
                    if not is_retryable(exc):
                        raise
                    log_state(endpoint.name, "reconnecting", f"connect failed: {exc}; retry in {backoff:.1f}s")
                    await asyncio.sleep(backoff)
                    backoff = min(backoff * 2.0, max_backoff)
                    continue

                log_state(endpoint.name, "recovered" if connected_once else "connected", f"{len(tags)} tags")
                connected_once = True
                backoff = initial_backoff

            try:
                snapshot: dict[str, object] = {}
                for tag in tags:
                    device, dtype = split_address(tag.address)
                    snapshot[tag.name] = await read_typed(client, device, dtype)
                log_state(endpoint.name, "read", format_snapshot(snapshot))
                await handle_snapshot(endpoint, snapshot)
                completed += 1
                if cycles is None or completed < cycles:
                    await asyncio.sleep(endpoint.interval)
            except Exception as exc:
                if not is_retryable(exc):
                    raise
                log_state(endpoint.name, "lost", str(exc) or exc.__class__.__name__)
                await close_quietly(client)
                client = None
                log_state(endpoint.name, "reconnecting", f"retry in {backoff:.1f}s")
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2.0, max_backoff)
    finally:
        await close_quietly(client)
