"""High-level utility helpers for the TOYOPUC client.

These helpers provide the user-facing surface that samples and maintained
documentation should point to first. They wrap the lower-level async client
with typed reads and writes, named snapshots, polling, and contiguous access
helpers that each use exactly one protocol request.
"""

from __future__ import annotations

import asyncio
import math
from collections.abc import AsyncIterator
from dataclasses import KW_ONLY, dataclass
from typing import TYPE_CHECKING, Any, cast

from .errors import ToyopucProtocolError

if TYPE_CHECKING:
    from .async_client import AsyncToyopucDeviceClient


# ---------------------------------------------------------------------------
# Connection helper
# ---------------------------------------------------------------------------


def _validate_int_range(value: int, name: str, min_value: int, max_value: int) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or not min_value <= value <= max_value:
        raise ValueError(f"{name} must be in the range {min_value}-{max_value}")


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
        plc_profile: Canonical PLC profile name such as
            ``"toyopuc:pc10g:pc10"``. Required when creating a high-level
            device client.
    """

    host: str
    port: int
    transport: str
    plc_profile: str
    _: KW_ONLY
    local_port: int = 0
    timeout: float = 3.0
    retries: int = 0
    retry_delay: float = 0.2

    def __post_init__(self) -> None:
        from .profiles import ToyopucPlcProfiles

        if self.host is None or not str(self.host).strip():
            raise ValueError("Host must not be empty")
        _validate_int_range(self.port, "Port", 1, 65_535)
        _validate_int_range(self.local_port, "LocalPort", 0, 65_535)
        if not isinstance(self.transport, str) or self.transport.strip().lower() not in {"tcp", "udp"}:
            raise ValueError("Transport must be 'tcp' or 'udp'")
        normalized_transport = self.transport.strip().lower()
        if normalized_transport == "tcp" and self.local_port != 0:
            raise ValueError("LocalPort is only valid for UDP transport")
        if (
            isinstance(self.timeout, bool)
            or not isinstance(self.timeout, (int, float))
            or not math.isfinite(self.timeout)
            or self.timeout <= 0
        ):
            raise ValueError("Timeout must be a positive finite number")
        if isinstance(self.retries, bool) or not isinstance(self.retries, int) or self.retries < 0:
            raise ValueError("Retries must be a non-negative integer")
        if (
            isinstance(self.retry_delay, bool)
            or not isinstance(self.retry_delay, (int, float))
            or not math.isfinite(self.retry_delay)
            or self.retry_delay < 0
        ):
            raise ValueError("RetryDelay must be a non-negative finite number")

        object.__setattr__(self, "transport", normalized_transport)
        object.__setattr__(self, "plc_profile", ToyopucPlcProfiles.from_name(self.plc_profile).name)


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
    plc_profile: str = ""


def normalize_address(device: str, *, profile: str) -> str:
    """Return the canonical TOYOPUC device string.

    Args:
        device: User-facing device text such as ``"p1-d0100"``.
        profile: Required canonical addressing profile used by
            :func:`resolve_device`.

    Returns:
        Canonical uppercase address text suitable for logs and configuration
        storage.
    """

    from .high_level import resolve_device

    return resolve_device(device, profile=profile).text


def parse_device_address(device: str, *, profile: str) -> ToyopucAddress:
    """Parse user-facing TOYOPUC address notation.

    Supported forms match :func:`read_named`:

    - ``"P1-D0100:U"`` as unsigned 16-bit word notation
    - ``"P1-D0100:F"`` with explicit dtype ``U/S/D/L/F``
    - ``"P1-D0100.A"`` for one bit inside a word
    """

    base_device, dtype, bit_index = _parse_address(device)
    canonical_base = normalize_address(base_device, profile=profile)
    if dtype == "BIT_IN_WORD":
        bit_index = _require_bit_in_word_index(device, bit_index)
        return ToyopucAddress(
            text=f"{canonical_base}.{bit_index:X}",
            base_device=canonical_base,
            dtype=dtype,
            bit_index=bit_index,
            plc_profile=profile,
        )

    if dtype not in {"U", "S", "D", "L", "F"}:
        raise ValueError(f"Unsupported dtype {dtype!r}; expected one of U/S/D/L/F")
    suffix = f":{dtype}"
    return ToyopucAddress(
        text=f"{canonical_base}{suffix}",
        base_device=canonical_base,
        dtype=dtype,
        bit_index=None,
        plc_profile=profile,
    )


def try_parse_device_address(device: str, *, profile: str) -> ToyopucAddress | None:
    """Return parsed address information, or ``None`` when parsing fails."""

    try:
        return parse_device_address(device, profile=profile)
    except Exception:
        return None


def format_device_address(address: ToyopucAddress | str, *, profile: str | None = None) -> str:
    """Return canonical public address text for a parsed address or string."""

    if isinstance(address, str):
        if profile is None:
            raise ValueError("profile is required when formatting address text")
        return parse_device_address(address, profile=profile).text
    effective_profile = address.plc_profile if profile is None else profile
    if not effective_profile:
        raise ValueError("ToyopucAddress is not bound to a PLC profile")
    if profile is not None and address.plc_profile and profile != address.plc_profile:
        raise ValueError("ToyopucAddress profile does not match the requested profile")
    base = normalize_address(address.base_device, profile=effective_profile)
    if address.dtype == "BIT_IN_WORD":
        if address.bit_index is None or not 0 <= address.bit_index <= 15:
            raise ValueError("bit-in-word address requires bit_index 0-F")
        return f"{base}.{address.bit_index:X}"
    if address.dtype not in {"U", "S", "D", "L", "F"}:
        raise ValueError(f"Unsupported dtype {address.dtype!r}; expected one of U/S/D/L/F")
    return f"{base}:{address.dtype}"


async def read_words_single_request(
    client: AsyncToyopucDeviceClient,
    device: str,
    count: int,
) -> list[int]:
    """Read contiguous word values using one high-level logical operation.

    This name is retained as an explicit statement of the operation's
    single-request contract.
    """

    return await read_words(client, device, count)


async def read_dwords_single_request(
    client: AsyncToyopucDeviceClient,
    device: str,
    count: int,
) -> list[int]:
    """Read contiguous dword values using one high-level logical operation.

    Dword arrays always use one protocol request; there is no switch that can
    silently enable splitting.
    """

    values = await client.read_dwords(device, count)
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
    await runner(sync_client._write_resolved_word_values, resolved, [int(v) & 0xFFFF for v in values])


async def write_dwords_single_request(
    client: AsyncToyopucDeviceClient,
    device: str,
    values: list[int],
) -> None:
    """Write contiguous dword values using one high-level logical operation.

    Dword arrays always use one protocol request; there is no switch that can
    silently enable splitting.
    """

    await client.write_dwords(device, [int(value) & 0xFFFFFFFF for value in values])


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


async def open_and_connect(options: ToyopucConnectionOptions) -> AsyncToyopucDeviceClient:
    """Create and connect an AsyncToyopucDeviceClient.

    Args:
        options: Validated explicit connection options.

    Returns:
        A connected AsyncToyopucDeviceClient.
    """
    from .async_client import AsyncToyopucDeviceClient

    client = AsyncToyopucDeviceClient(
        options.host,
        options.port,
        local_port=options.local_port,
        transport=options.transport,
        timeout=options.timeout,
        retries=options.retries,
        retry_delay=options.retry_delay,
        plc_profile=options.plc_profile,
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
    key = _normalize_dtype(dtype)
    if key == "F":
        values = await client.read_float32s(device, 1)
        value = cast(float, values[0])
        if not math.isfinite(value):
            raise ToyopucProtocolError("PLC returned a non-finite float32 value")
        return value
    if key == "D":
        values = await client.read_dwords(device, 1)
        value = cast(int, values[0])
        if not 0 <= value <= 0xFFFFFFFF:
            raise ToyopucProtocolError("PLC returned a Dword value outside 0..4294967295")
        return value
    if key == "L":
        values = await client.read_dwords(device, 1)
        value = cast(int, values[0])
        if not 0 <= value <= 0xFFFFFFFF:
            raise ToyopucProtocolError("PLC returned a Dword value outside 0..4294967295")
        return (value ^ 0x80000000) - 0x80000000  # reinterpret as signed
    raw = int(await client.read_one(device))
    if not 0 <= raw <= 0xFFFF:
        raise ToyopucProtocolError("PLC returned a word value outside 0..65535")
    if key == "S":
        return raw - 0x10000 if raw & 0x8000 else raw
    return raw


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
    key = _normalize_dtype(dtype)
    if key == "F":
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError("F value must be a finite number")
        await client.write_float32s(device, [float(value)])
        return
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{key} value must be an integer")
    limits = {
        "U": (0, 0xFFFF),
        "S": (-0x8000, 0x7FFF),
        "D": (0, 0xFFFFFFFF),
        "L": (-0x80000000, 0x7FFFFFFF),
    }
    low, high = limits[key]
    if not low <= value <= high:
        raise ValueError(f"{key} value must be in the range {low}..{high}")
    if key in ("D", "L"):
        encoded = value if value >= 0 else value + 0x100000000
        await client.write_dwords(device, [encoded])
        return
    encoded = value if value >= 0 else value + 0x10000
    await client.write(device, encoded)


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
    current = int(await client.read_one(device)) & 0xFFFF
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
    - ``"D100:U"``: device as unsigned 16-bit word
    - ``"D100:F"``: device with explicit dtype code
    - ``"D100.3"``: bit 3 within one word device (dtype ``"BIT_IN_WORD"``)
    """
    if ":" in address:
        base, dtype = address.split(":", 1)
        normalized_dtype = dtype.strip().upper()
        if not normalized_dtype:
            raise ValueError(f"dtype is required after ':' in {address!r}")
        if normalized_dtype == "BIT_IN_WORD":
            raise ValueError(f"bit-in-word address requires explicit bit index 0-F: {address!r}")
        return base.strip(), normalized_dtype, None
    if "." in address:
        base, bit_str = address.split(".", 1)
        bit_text = bit_str.strip()
        if len(bit_text) == 1 and bit_text.upper() in "0123456789ABCDEF":
            return base.strip(), "BIT_IN_WORD", int(bit_text, 16)
        raise ValueError(f"Invalid bit-in-word index {bit_str!r}; use one hex digit 0-F or ':' for dtype.")
    raise ValueError(f"named address requires explicit dtype ':U/:S/:D/:L/:F' or bit index '.0'..'.F': {address!r}")


def _normalize_dtype(dtype: str) -> str:
    if not isinstance(dtype, str):
        raise ValueError("dtype must be one of U/S/D/L/F")
    key = dtype.strip().upper()
    if key not in {"U", "S", "D", "L", "F"}:
        raise ValueError(f"Unsupported dtype {dtype!r}; expected one of U/S/D/L/F")
    return key


def _require_bit_in_word_index(address: str, bit_index: int | None) -> int:
    if bit_index is None:
        raise ValueError(f"bit-in-word address requires explicit bit index 0-F: {address!r}")
    if not 0 <= bit_index <= 15:
        raise ValueError(f"bit-in-word index must be 0-F: {address!r}")
    return bit_index


async def read_named(
    client: AsyncToyopucDeviceClient,
    addresses: list[str],
) -> dict[str, int | float | bool]:
    """Read one device by address string and return the result as a dict.

    The returned dictionary preserves the original address strings as keys so
    application code can display or diff snapshots without rebuilding the
    request list.

    Address format examples:

    - ``"P1-D0100:U"``: unsigned 16-bit int
    - ``"P1-D0100:F"``: float32
    - ``"P1-D0100:S"``: signed 16-bit int
    - ``"P1-D0100:D"``: unsigned 32-bit int
    - ``"P1-D0100:L"``: signed 32-bit int
    - ``"P1-D0100.3"``: bit 3 within one word (bool)

    Args:
        client: Connected AsyncToyopucDeviceClient.
        addresses: List containing exactly one address string.

    Returns:
        Dictionary mapping each address string to its value.
    """
    if len(addresses) != 1:
        raise ToyopucProtocolError(
            "read_named requires exactly one named address per call. "
            "Split the operation into explicit calls when multiple requests are intentional."
        )

    result: dict[str, int | float | bool] = {}
    for address in addresses:
        base, dtype, bit_idx = _parse_address(address)
        if dtype == "BIT_IN_WORD":
            bit_idx = _require_bit_in_word_index(address, bit_idx)
            raw = int(await client.read_one(base)) & 0xFFFF
            result[address] = bool((raw >> bit_idx) & 1)
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
    """Yield one named-device snapshot every *interval* seconds.

    This helper performs repeated :func:`read_named` calls and sleeps for the
    requested interval between snapshots.

    Args:
        client: Connected AsyncToyopucDeviceClient.
        addresses: List containing exactly one address string.
        interval: Poll interval in seconds.

    Usage::

        async for snapshot in poll(client, ["P1-D0100"], interval=1.0):
            print(snapshot)
    """
    while True:
        yield await read_named(client, addresses)
        await asyncio.sleep(interval)
