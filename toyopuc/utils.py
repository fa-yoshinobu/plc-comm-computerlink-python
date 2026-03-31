"""High-level utility helpers for the TOYOPUC client."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from .async_client import AsyncToyopucDeviceClient


# ---------------------------------------------------------------------------
# Connection helper
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ToyopucConnectionOptions:
    """Stable connection settings for one TOYOPUC session."""

    host: str
    port: int = 1025
    timeout: float = 3.0
    retries: int = 0


def normalize_address(device: str, *, profile: str | None = None) -> str:
    """Return the canonical TOYOPUC device string."""

    from .high_level import resolve_device

    return resolve_device(device, profile=profile).text


async def read_words_single_request(
    client: AsyncToyopucDeviceClient,
    device: str,
    count: int,
) -> list[int]:
    """Read contiguous word values using one high-level logical operation."""

    return await read_words(client, device, count)


async def read_dwords_single_request(
    client: AsyncToyopucDeviceClient,
    device: str,
    count: int,
) -> list[int]:
    """Read contiguous dword values using one high-level logical operation."""

    values = await client.read_dwords(device, count, atomic_transfer=True)
    return [int(value) & 0xFFFFFFFF for value in values]


async def write_words_single_request(
    client: AsyncToyopucDeviceClient,
    device: str,
    values: list[int],
) -> None:
    """Write contiguous word values using one high-level logical operation."""

    sync_client = cast(Any, client._client)
    runner = cast(Any, client._run_sync_in_worker)
    resolved = sync_client.resolve_device(device)
    await runner(sync_client._write_resolved_word_values, resolved, [int(v) & 0xFFFF for v in values], False)


async def write_dwords_single_request(
    client: AsyncToyopucDeviceClient,
    device: str,
    values: list[int],
) -> None:
    """Write contiguous dword values using one high-level logical operation."""

    await client.write_dwords(device, [int(value) & 0xFFFFFFFF for value in values], atomic_transfer=True)


async def read_words_chunked(
    client: AsyncToyopucDeviceClient,
    device: str,
    count: int,
    max_words_per_request: int = 64,
) -> list[int]:
    """Read contiguous word values across multiple logical operations."""

    if max_words_per_request <= 0:
        raise ValueError("max_words_per_request must be at least 1")

    sync_client = cast(Any, client._client)
    start = sync_client.resolve_device(device)
    result: list[int] = []
    remaining = count
    offset = 0
    while remaining > 0:
        chunk = min(remaining, max_words_per_request)
        chunk_device = sync_client._offset_resolved_device(start, offset).text
        result.extend(await read_words_single_request(client, chunk_device, chunk))
        offset += chunk
        remaining -= chunk
    return result


async def read_dwords_chunked(
    client: AsyncToyopucDeviceClient,
    device: str,
    count: int,
    max_dwords_per_request: int = 32,
) -> list[int]:
    """Read contiguous dword values across multiple logical operations."""

    if max_dwords_per_request <= 0:
        raise ValueError("max_dwords_per_request must be at least 1")

    sync_client = cast(Any, client._client)
    start = sync_client.resolve_device(device)
    result: list[int] = []
    remaining = count
    offset = 0
    while remaining > 0:
        chunk = min(remaining, max_dwords_per_request)
        chunk_device = sync_client._offset_resolved_device(start, offset * 2).text
        result.extend(await read_dwords_single_request(client, chunk_device, chunk))
        offset += chunk
        remaining -= chunk
    return result


async def write_words_chunked(
    client: AsyncToyopucDeviceClient,
    device: str,
    values: list[int],
    max_words_per_request: int = 64,
) -> None:
    """Write contiguous word values across multiple logical operations."""

    if max_words_per_request <= 0:
        raise ValueError("max_words_per_request must be at least 1")

    sync_client = cast(Any, client._client)
    start = sync_client.resolve_device(device)
    offset = 0
    while offset < len(values):
        chunk = min(len(values) - offset, max_words_per_request)
        chunk_device = sync_client._offset_resolved_device(start, offset).text
        await write_words_single_request(client, chunk_device, values[offset : offset + chunk])
        offset += chunk


async def write_dwords_chunked(
    client: AsyncToyopucDeviceClient,
    device: str,
    values: list[int],
    max_dwords_per_request: int = 32,
) -> None:
    """Write contiguous dword values across multiple logical operations."""

    if max_dwords_per_request <= 0:
        raise ValueError("max_dwords_per_request must be at least 1")

    sync_client = cast(Any, client._client)
    start = sync_client.resolve_device(device)
    offset = 0
    while offset < len(values):
        chunk = min(len(values) - offset, max_dwords_per_request)
        chunk_device = sync_client._offset_resolved_device(start, offset * 2).text
        await write_dwords_single_request(client, chunk_device, values[offset : offset + chunk])
        offset += chunk


async def read_words(
    client: AsyncToyopucDeviceClient,
    device: str,
    count: int,
) -> list[int]:
    """Read *count* contiguous word values starting at *device*.

    Args:
        client: Connected AsyncToyopucDeviceClient.
        device: Starting device address string, e.g. ``"D0100"``.
        count: Number of words to read.

    Returns:
        List of unsigned 16-bit integers.
    """
    result = await client.read(device, count)
    if count == 1:
        return [int(result) & 0xFFFF]
    return [int(v) & 0xFFFF for v in result]


async def read_dwords(
    client: AsyncToyopucDeviceClient,
    device: str,
    count: int,
) -> list[int]:
    """Read *count* contiguous DWord (32-bit unsigned) values starting at *device*.

    Reads ``count * 2`` words and combines adjacent word pairs (lo, hi).

    Args:
        client: Connected AsyncToyopucDeviceClient.
        device: Starting device address string (must be a word device).
        count: Number of DWords to read.

    Returns:
        List of unsigned 32-bit integers.
    """
    words = await read_words(client, device, count * 2)
    return [(words[i] | (words[i + 1] << 16)) for i in range(0, count * 2, 2)]


async def open_and_connect(
    host: str | ToyopucConnectionOptions,
    port: int = 1025,
    timeout: float = 3.0,
    retries: int = 0,
) -> AsyncToyopucDeviceClient:
    """Create and connect an AsyncToyopucDeviceClient.

    Args:
        host: PLC IP address or hostname.
        port: TOYOPUC computer-link port. Defaults to 1025.
        timeout: Socket timeout in seconds.

    Returns:
        A connected AsyncToyopucDeviceClient.
    """
    from .async_client import AsyncToyopucDeviceClient

    if isinstance(host, ToyopucConnectionOptions):
        options = host
    else:
        options = ToyopucConnectionOptions(host, port=port, timeout=timeout, retries=retries)

    client = AsyncToyopucDeviceClient(options.host, options.port, timeout=options.timeout, retries=options.retries)
    await client.connect()
    return client


# ---------------------------------------------------------------------------
# Typed single-device read / write
# ---------------------------------------------------------------------------


async def read_typed(
    client: AsyncToyopucDeviceClient,
    device: str,
    dtype: str,
) -> int | float:
    """Read one device value and convert it to the specified Python type.

    Args:
        client: Connected AsyncToyopucDeviceClient.
        device: Device address string (e.g. "D0100", "B0000").
        dtype: Type code —
            "U" unsigned 16-bit int,
            "S" signed 16-bit int,
            "D" unsigned 32-bit int,
            "L" signed 32-bit int,
            "F" float32.

    Returns:
        Converted value as int or float.
    """
    key = dtype.upper()
    if key == "F":
        values = await client.read_float32s(device, 1)
        return cast(float, values[0])
    if key == "D":
        values = await client.read_dwords(device, 1)
        return cast(int, values[0])
    if key == "L":
        values = await client.read_dwords(device, 1)
        return cast(int, (values[0] ^ 0x80000000) - 0x80000000)  # reinterpret as signed
    raw = int(await client.read(device))
    if key == "S":
        return (raw & 0xFFFF) - 0x10000 if raw & 0x8000 else raw & 0xFFFF
    return raw & 0xFFFF  # "U"


async def write_typed(
    client: AsyncToyopucDeviceClient,
    device: str,
    dtype: str,
    value: int | float,
) -> None:
    """Write one device value using the specified type format.

    Args:
        client: Connected AsyncToyopucDeviceClient.
        device: Device address string.
        dtype: Type code — same as :func:`read_typed`.
        value: Value to write.
    """
    key = dtype.upper()
    if key == "F":
        await client.write_float32s(device, [float(value)])
        return
    if key in ("D", "L"):
        await client.write_dwords(device, [int(value) & 0xFFFFFFFF])
        return
    await client.write(device, int(value) & 0xFFFF)


# ---------------------------------------------------------------------------
# Bit-in-word
# ---------------------------------------------------------------------------


async def write_bit_in_word(
    client: AsyncToyopucDeviceClient,
    device: str,
    bit_index: int,
    value: bool,
) -> None:
    """Set or clear a single bit within a word device (read-modify-write).

    Args:
        client: Connected AsyncToyopucDeviceClient.
        device: Word device address.
        bit_index: Bit position within the word (0–15).
        value: New bit state.
    """
    if not 0 <= bit_index <= 15:
        raise ValueError(f"bit_index must be 0-15, got {bit_index}")
    current = int(await client.read(device)) & 0xFFFF
    if value:
        current |= 1 << bit_index
    else:
        current &= ~(1 << bit_index) & 0xFFFF
    await client.write(device, current)


# ---------------------------------------------------------------------------
# Named-device read
# ---------------------------------------------------------------------------


def _parse_address(address: str) -> tuple[str, str, int | None]:
    """Parse extended address notation into (base_device, dtype, bit_index).

    Supported formats:
    - ``"D100"``      → device as unsigned 16-bit word (dtype "U")
    - ``"D100:F"``    → device with explicit dtype code
    - ``"D100.3"``    → bit 3 within word device (dtype "BIT_IN_WORD")
    """
    if ":" in address:
        base, dtype = address.split(":", 1)
        return base.strip(), dtype.strip().upper(), None
    if "." in address:
        base, bit_str = address.split(".", 1)
        try:
            return base.strip(), "BIT_IN_WORD", int(bit_str, 16)
        except ValueError:
            pass
    return address.strip(), "U", None


async def read_named(
    client: AsyncToyopucDeviceClient,
    addresses: list[str],
) -> dict[str, int | float | bool]:
    """Read multiple devices by address string and return results as a dict.

    Address format examples:

    - ``"D0100"``    — unsigned 16-bit int
    - ``"D0100:F"``  — float32
    - ``"D0100:S"``  — signed 16-bit int
    - ``"D0100:D"``  — unsigned 32-bit int
    - ``"D0100:L"``  — signed 32-bit int
    - ``"D0100.3"``  — bit 3 within word (bool)

    Args:
        client: Connected AsyncToyopucDeviceClient.
        addresses: List of address strings.

    Returns:
        Dictionary mapping each address string to its value.
    """
    result: dict[str, int | float | bool] = {}
    for address in addresses:
        base, dtype, bit_idx = _parse_address(address)
        if dtype == "BIT_IN_WORD":
            raw = int(await client.read(base)) & 0xFFFF
            result[address] = bool((raw >> (bit_idx or 0)) & 1)
        else:
            result[address] = await read_typed(client, base, dtype)
    return result


# ---------------------------------------------------------------------------
# Polling
# ---------------------------------------------------------------------------


async def poll(
    client: AsyncToyopucDeviceClient,
    addresses: list[str],
    interval: float,
) -> AsyncIterator[dict[str, int | float | bool]]:
    """Yield a snapshot of all devices every *interval* seconds.

    Args:
        client: Connected AsyncToyopucDeviceClient.
        addresses: Address strings (same format as :func:`read_named`).
        interval: Poll interval in seconds.

    Usage::

        async for snapshot in poll(client, ["D0100", "D0200:F"], interval=1.0):
            print(snapshot)
    """
    while True:
        yield await read_named(client, addresses)
        await asyncio.sleep(interval)
