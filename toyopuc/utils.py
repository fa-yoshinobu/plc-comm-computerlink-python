"""High-level utility helpers for the TOYOPUC client.

These helpers provide the user-facing surface that samples and generated API
documentation should point to first. They wrap the lower-level async client
with typed reads and writes, named snapshots, polling, and explicit
single-request or chunked contiguous access helpers.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from .async_client import AsyncToyopucDeviceClient
    from .client import ToyopucTraceFrame


# ---------------------------------------------------------------------------
# Connection helper
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ToyopucConnectionOptions:
    """Stable connection settings for one TOYOPUC session.

    Attributes:
        host: PLC hostname or IP address.
        port: TOYOPUC computer-link port.
        local_port: UDP source port. Leave zero for an ephemeral port.
        transport: ``"tcp"`` or ``"udp"``.
        timeout: Socket timeout in seconds.
        retries: Number of retry attempts performed by the async client.
        retry_delay: Delay between retry attempts, in seconds.
        recv_bufsize: Socket receive buffer size used by the sync client.
        trace_hook: Optional callback invoked for sent and received frames.
    """

    host: str
    port: int = 1025
    local_port: int = 0
    transport: str = "tcp"
    timeout: float = 3.0
    retries: int = 0
    retry_delay: float = 0.2
    recv_bufsize: int = 8192
    trace_hook: Callable[[ToyopucTraceFrame], None] | None = None


@dataclass(frozen=True)
class ToyopucAddress:
    """Parsed public device address notation.

    ``text`` is the canonical full notation. ``base_device`` is the resolved
    PLC device without value-format or bit-in-word suffix.
    """

    text: str
    base_device: str
    dtype: str
    bit_index: int | None = None


def normalize_address(device: str, *, profile: str | None = None) -> str:
    """Return the canonical TOYOPUC device string.

    Args:
        device: User-facing device text such as ``"p1-d0100"``.
        profile: Optional addressing profile used by :func:`resolve_device`.

    Returns:
        Canonical uppercase address text suitable for logs and configuration
        storage.
    """

    from .high_level import resolve_device

    return resolve_device(device, profile=profile).text


def parse_device_address(device: str, *, profile: str | None = None) -> ToyopucAddress:
    """Parse user-facing TOYOPUC address notation.

    Supported forms match :func:`read_named`:

    - ``"P1-D0100"`` as unsigned 16-bit word notation
    - ``"P1-D0100:F"`` with explicit dtype ``U/S/D/L/F``
    - ``"P1-D0100.A"`` for one bit inside a word
    """

    base_device, dtype, bit_index = _parse_address(device)
    canonical_base = normalize_address(base_device, profile=profile)
    if dtype == "BIT_IN_WORD":
        if bit_index is None or not 0 <= bit_index <= 15:
            raise ValueError(f"bit-in-word index must be 0-F: {device!r}")
        return ToyopucAddress(
            text=f"{canonical_base}.{bit_index:X}",
            base_device=canonical_base,
            dtype=dtype,
            bit_index=bit_index,
        )

    if dtype not in {"U", "S", "D", "L", "F"}:
        raise ValueError(f"Unsupported dtype {dtype!r}; expected one of U/S/D/L/F")
    suffix = "" if dtype == "U" else f":{dtype}"
    return ToyopucAddress(
        text=f"{canonical_base}{suffix}",
        base_device=canonical_base,
        dtype=dtype,
        bit_index=None,
    )


def try_parse_device_address(device: str, *, profile: str | None = None) -> ToyopucAddress | None:
    """Return parsed address information, or ``None`` when parsing fails."""

    try:
        return parse_device_address(device, profile=profile)
    except Exception:
        return None


def format_device_address(address: ToyopucAddress | str, *, profile: str | None = None) -> str:
    """Return canonical public address text for a parsed address or string."""

    if isinstance(address, str):
        return parse_device_address(address, profile=profile).text
    base = normalize_address(address.base_device, profile=profile) if profile else address.base_device
    if address.dtype == "BIT_IN_WORD":
        if address.bit_index is None or not 0 <= address.bit_index <= 15:
            raise ValueError("bit-in-word address requires bit_index 0-F")
        return f"{base}.{address.bit_index:X}"
    if address.dtype == "U":
        return base
    if address.dtype not in {"S", "D", "L", "F"}:
        raise ValueError(f"Unsupported dtype {address.dtype!r}; expected one of U/S/D/L/F")
    return f"{base}:{address.dtype}"


async def read_words_single_request(
    client: AsyncToyopucDeviceClient,
    device: str,
    count: int,
) -> list[int]:
    """Read contiguous word values using one high-level logical operation.

    This is the explicit atomic path for a contiguous word range. If the
    caller wants multiple protocol requests, use :func:`read_words_chunked`.
    """

    return await read_words(client, device, count)


async def read_dwords_single_request(
    client: AsyncToyopucDeviceClient,
    device: str,
    count: int,
) -> list[int]:
    """Read contiguous dword values using one high-level logical operation.

    The helper requests dwords through the client with ``atomic_transfer=True``
    so each logical 32-bit value stays intact.
    """

    values = await client.read_dwords(device, count, atomic_transfer=True)
    return [int(value) & 0xFFFFFFFF for value in values]


async def write_words_single_request(
    client: AsyncToyopucDeviceClient,
    device: str,
    values: list[int],
) -> None:
    """Write contiguous word values using one high-level logical operation.

    This helper is intended for ranges that should remain one logical write
    from the caller's perspective.
    """

    sync_client = cast(Any, client._client)
    runner = cast(Any, client._run_sync_in_worker)
    resolved = sync_client.resolve_device(device)
    await runner(sync_client._write_resolved_word_values, resolved, [int(v) & 0xFFFF for v in values], False)


async def write_dwords_single_request(
    client: AsyncToyopucDeviceClient,
    device: str,
    values: list[int],
) -> None:
    """Write contiguous dword values using one high-level logical operation.

    The helper uses ``atomic_transfer=True`` so the logical dword range is
    written through the dedicated dword API instead of implicit word pairs.
    """

    await client.write_dwords(device, [int(value) & 0xFFFFFFFF for value in values], atomic_transfer=True)


async def read_words_chunked(
    client: AsyncToyopucDeviceClient,
    device: str,
    count: int,
    max_words_per_request: int = 64,
) -> list[int]:
    """Read contiguous word values across multiple logical operations.

    Chunking is explicit here. Use this helper only when the caller accepts
    multi-request read semantics.
    """

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
    """Read contiguous dword values across multiple logical operations.

    Chunk boundaries are aligned to full dwords so a 32-bit value is never
    torn across requests.
    """

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
    """Write contiguous word values across multiple logical operations.

    Use this helper only when multiple write operations are acceptable to the
    caller.
    """

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
    """Write contiguous dword values across multiple logical operations.

    Each chunk boundary is aligned to full dwords so one logical value remains
    intact inside one request.
    """

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
        device: Starting device address string, e.g. ``"P1-D0100"``.
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
    *,
    local_port: int = 0,
    transport: str = "tcp",
    retry_delay: float = 0.2,
    recv_bufsize: int = 8192,
    trace_hook: Callable[[ToyopucTraceFrame], None] | None = None,
) -> AsyncToyopucDeviceClient:
    """Create and connect an AsyncToyopucDeviceClient.

    Args:
        host: PLC IP address, hostname, or a
            :class:`ToyopucConnectionOptions` instance.
        port: TOYOPUC computer-link port. Defaults to 1025.
        local_port: UDP source port. Leave zero for an ephemeral port.
        transport: ``"tcp"`` or ``"udp"``.
        timeout: Socket timeout in seconds.
        retries: Retry count used by the async client.
        retry_delay: Delay between retry attempts, in seconds.
        recv_bufsize: Socket receive buffer size.
        trace_hook: Optional callback invoked for sent and received frames.

    Returns:
        A connected AsyncToyopucDeviceClient.
    """
    from .async_client import AsyncToyopucDeviceClient

    if isinstance(host, ToyopucConnectionOptions):
        options = host
    else:
        options = ToyopucConnectionOptions(
            host,
            port=port,
            local_port=local_port,
            transport=transport,
            timeout=timeout,
            retries=retries,
            retry_delay=retry_delay,
            recv_bufsize=recv_bufsize,
            trace_hook=trace_hook,
        )

    client = AsyncToyopucDeviceClient(
        options.host,
        options.port,
        local_port=options.local_port,
        transport=options.transport,
        timeout=options.timeout,
        retries=options.retries,
        retry_delay=options.retry_delay,
        recv_bufsize=options.recv_bufsize,
        trace_hook=options.trace_hook,
    )
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

    Supported dtype codes are ``"U"``, ``"S"``, ``"D"``, ``"L"``, and
    ``"F"``. The helper keeps the public surface aligned with the .NET and C++
    helper layers.

    Args:
        client: Connected AsyncToyopucDeviceClient.
        device: Device address string (e.g. "P1-D0100", "B0000").
        dtype: Type code.
            ``"U"`` for unsigned 16-bit int,
            ``"S"`` for signed 16-bit int,
            ``"D"`` for unsigned 32-bit int,
            ``"L"`` for signed 32-bit int,
            ``"F"`` for float32.

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

    The dtype codes match :func:`read_typed`. Word-sized values are written as
    one logical word, while ``"D"``, ``"L"``, and ``"F"`` use the dedicated
    32-bit helper paths.

    Args:
        client: Connected AsyncToyopucDeviceClient.
        device: Device address string.
        dtype: Type code accepted by :func:`read_typed`.
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

    This helper is intended for expressions such as ``"P1-D0100.3"``. Direct bit
    devices should be written through :func:`write_typed` or the lower-level
    client API.

    Args:
        client: Connected AsyncToyopucDeviceClient.
        device: Word device address.
        bit_index: Bit position within the word, in the range ``0`` to ``15``.
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

    This parser supports the address forms accepted by :func:`read_named` and
    :func:`poll`.

    Supported formats:
    - ``"D100"``: device as unsigned 16-bit word (dtype ``"U"``)
    - ``"D100:F"``: device with explicit dtype code
    - ``"D100.3"``: bit 3 within one word device (dtype ``"BIT_IN_WORD"``)
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

    The returned dictionary preserves the original address strings as keys so
    application code can display or diff snapshots without rebuilding the
    request list.

    Address format examples:

    - ``"P1-D0100"``: unsigned 16-bit int
    - ``"P1-D0100:F"``: float32
    - ``"P1-D0100:S"``: signed 16-bit int
    - ``"P1-D0100:D"``: unsigned 32-bit int
    - ``"P1-D0100:L"``: signed 32-bit int
    - ``"P1-D0100.3"``: bit 3 within one word (bool)

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

    This helper performs repeated :func:`read_named` calls and sleeps for the
    requested interval between snapshots.

    Args:
        client: Connected AsyncToyopucDeviceClient.
        addresses: Address strings (same format as :func:`read_named`).
        interval: Poll interval in seconds.

    Usage::

        async for snapshot in poll(client, ["P1-D0100", "P1-D0200:F"], interval=1.0):
            print(snapshot)
    """
    while True:
        yield await read_named(client, addresses)
        await asyncio.sleep(interval)
