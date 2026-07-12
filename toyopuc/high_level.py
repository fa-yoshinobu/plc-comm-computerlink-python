from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, replace
from typing import Any, cast

from ._batching import (
    _batch_key,
    _batch_run_length,
    _contains_packed_pc10_word_device,
    _is_consecutive_basic,
    _is_consecutive_ext_word,
    _is_consecutive_pc10_word,
    _pc10_word_segment_length,
)
from ._batching import (
    _pc10_block as _pc10_block,
)
from ._pc10 import (
    _build_pc10_multi_word_read_payload,
    _pack_pc10_multi_bit_payload,
    _pack_pc10_multi_word_payload,
    _parse_ext_multi_bit_data,
    _parse_pc10_multi_word_data,
    _read_pc10_block_word,
    _read_pc10_multi_bits,
    _read_pc10_multi_words,
    _write_pc10_block_word,
)
from ._shared import _require
from .address import (
    ParsedAddress,
    encode_bit_address,
    encode_byte_address,
    encode_exno_byte_u32,
    encode_ext_no_address,
    encode_fr_word_addr32,
    encode_program_bit_address,
    encode_program_byte_address,
    encode_program_word_address,
    encode_word_address,
    parse_address,
    parse_prefixed_address,
)
from .client import (
    ToyopucClient,
    _normalize_bit_value,
    _normalize_byte_values,
    _normalize_word_values,
    _pack_float32_low_word_first_words,
    _pack_uint32_low_word_first_words,
    _unpack_float32_low_word_first_words,
    _unpack_uint32_low_word_first_words,
)
from .errors import ToyopucProtocolError
from .profiles import ToyopucAddressingOptions, ToyopucPlcProfiles
from .protocol import (
    build_bit_read,
    build_bit_write,
    build_byte_read,
    build_byte_write,
    build_ext_byte_read,
    build_ext_byte_write,
    build_ext_multi_read,
    build_ext_multi_write,
    build_ext_word_read,
    build_ext_word_write,
    build_multi_byte_read,
    build_multi_byte_write,
    build_multi_word_read,
    build_multi_word_write,
    build_pc10_block_read,
    build_pc10_block_write,
    build_pc10_multi_read,
    build_pc10_multi_write,
    build_word_read,
    build_word_write,
    unpack_u16_le,
)

_BASIC_BIT_AREAS = {"P", "K", "V", "T", "C", "L", "X", "Y", "M"}
_BASIC_WORD_AREAS = {"S", "N", "R", "D", "B"}
_EXT_BIT_AREAS = {
    "EP",
    "EK",
    "EV",
    "ET",
    "EC",
    "EL",
    "EX",
    "EY",
    "EM",
    "GX",
    "GY",
    "GM",
}
_EXT_WORD_AREAS = {"ES", "EN", "H", "U", "EB", "FR"}
_PREFIX_REQUIRED_AREAS = {
    "P",
    "K",
    "V",
    "T",
    "C",
    "L",
    "X",
    "Y",
    "M",
    "S",
    "N",
    "R",
    "D",
}
_PREFIX_PROGRAM_NO = {"P1": 0x01, "P2": 0x02, "P3": 0x03}
_EXT_BIT_SPECS = {
    "EP": (0x00, 0x0000),
    "EK": (0x00, 0x0200),
    "EV": (0x00, 0x0400),
    "ET": (0x00, 0x0600),
    "EC": (0x00, 0x0600),
    "EL": (0x00, 0x0700),
    "EX": (0x00, 0x0B00),
    "EY": (0x00, 0x0B00),
    "EM": (0x00, 0x0C00),
    "GX": (0x07, 0x0000),
    "GY": (0x07, 0x0000),
    "GM": (0x07, 0x2000),
}

_DEVICE_CACHE_MAX = 512
_RUN_PLAN_CACHE_MAX = 256


def _ext_word_monitor_addr(word_addr: int) -> int:
    """Convert a `CMD=94/95` word address into the monitor byte address.

    `CMD=98/99` word points carry byte addresses (manual: "byte address N"),
    while `ResolvedDevice.addr` holds the `CMD=94/95` word address.
    """
    return word_addr * 2


@dataclass(frozen=True)
class ResolvedDevice:
    """Resolved high-level device description."""

    text: str
    scheme: str
    unit: str
    area: str
    index: int
    digits: int = 0
    prefix: str | None = None
    high: bool = False
    packed: bool = False
    basic_addr: int | None = None
    no: int | None = None
    addr: int | None = None
    bit_no: int | None = None
    addr32: int | None = None
    plc_profile: str = ""


def _infer_unit_and_area(device: str) -> tuple[str | None, str, str]:
    text = device.strip().upper()
    prefix = None
    body = text
    if text.startswith(("P1-", "P2-", "P3-")):
        prefix, body = text.split("-", 1)

    if body.endswith("W"):
        parsed_packed_word = body[:-1]
        for area in sorted(_BASIC_BIT_AREAS | _EXT_BIT_AREAS, key=len, reverse=True):
            if parsed_packed_word.startswith(area):
                return prefix, area, "word"
        raise ValueError(f"Unknown packed word area: {device}")

    if body.endswith(("L", "H")):
        parsed_byte = body[:-1]
        for area in sorted(
            _BASIC_BIT_AREAS | _BASIC_WORD_AREAS | _EXT_BIT_AREAS | _EXT_WORD_AREAS,
            key=len,
            reverse=True,
        ):
            if parsed_byte.startswith(area):
                return prefix, area, "byte"
        raise ValueError(f"Unknown address area: {device}")

    for area in sorted(
        _EXT_BIT_AREAS | _EXT_WORD_AREAS | _BASIC_BIT_AREAS | _BASIC_WORD_AREAS,
        key=len,
        reverse=True,
    ):
        if body.startswith(area):
            if area in _EXT_BIT_AREAS or area in _BASIC_BIT_AREAS:
                return prefix, area, "bit"
            return prefix, area, "word"
    raise ValueError(f"Unknown address area: {device}")


def _pc10_u_addr32(index: int, *, byte: bool = False, high: bool = False) -> int:
    if index < 0x08000 or index > 0x1FFFF:
        raise ValueError("U PC10 range is 0x08000-0x1FFFF")
    block = index // 0x8000
    ex_no = 0x03 + block
    byte_addr = (index % 0x8000) * 2 + (1 if byte and high else 0)
    if byte and not high:
        byte_addr = (index % 0x8000) * 2
    return encode_exno_byte_u32(ex_no, byte_addr)


def _pc10_eb_addr32(index: int, *, byte: bool = False, high: bool = False) -> int:
    if index < 0x00000 or index > 0x3FFFF:
        raise ValueError("EB PC10 range is 0x00000-0x3FFFF")
    block = index // 0x8000
    ex_no = 0x10 + block
    byte_addr = (index % 0x8000) * 2 + (1 if byte and high else 0)
    if byte and not high:
        byte_addr = (index % 0x8000) * 2
    return encode_exno_byte_u32(ex_no, byte_addr)


def _resolve_ext_bit(parsed: ParsedAddress, text: str) -> ResolvedDevice:
    no, byte_base = _EXT_BIT_SPECS[parsed.area]
    return ResolvedDevice(
        text=text,
        scheme="ext-bit",
        unit="bit",
        area=parsed.area,
        index=parsed.index,
        digits=parsed.digits,
        no=no,
        bit_no=parsed.index & 0x07,
        addr=byte_base + (parsed.index >> 3),
    )


def _try_resolve_direct_pc10_bit(
    parsed: ParsedAddress,
    text: str,
    options: ToyopucAddressingOptions,
) -> ResolvedDevice | None:
    """Return a pc10-bit ResolvedDevice if the address falls in the PC10 upper bit range."""
    area = parsed.area
    if area in {"P", "V", "T", "C"}:
        if not (options.use_upper_bit_pc10 and 0x1000 <= parsed.index <= 0x17FF):
            return None
    elif area == "L":
        if not (options.use_upper_bit_pc10 and 0x1000 <= parsed.index <= 0x2FFF):
            return None
    elif area == "M":
        if not (options.use_upper_m_bit_pc10 and 0x1000 <= parsed.index <= 0x17FF):
            return None
    else:
        return None
    return ResolvedDevice(
        text=text,
        scheme="pc10-bit",
        unit="bit",
        area=parsed.area,
        index=parsed.index,
        digits=parsed.digits,
        packed=parsed.packed,
        addr32=encode_bit_address(parsed),
    )


def _try_resolve_direct_pc10_derived(
    parsed: ParsedAddress,
    text: str,
    options: ToyopucAddressingOptions,
) -> ResolvedDevice | None:
    """Return a pc10-word/byte device if the address is a derived bit-area PC10 access."""
    area = parsed.area
    if area in {"P", "V", "T", "C", "L"}:
        if not (options.use_upper_bit_pc10 and parsed.index >= 0x100):
            return None
    elif area == "M":
        if not (options.use_upper_m_bit_pc10 and parsed.index >= 0x100):
            return None
    else:
        return None

    if parsed.unit == "word":
        byte_addr = encode_word_address(parsed) * 2
        return ResolvedDevice(
            text=text,
            scheme="pc10-word",
            unit="word",
            area=parsed.area,
            index=parsed.index,
            digits=parsed.digits,
            packed=parsed.packed,
            addr32=encode_exno_byte_u32(0x00, byte_addr),
        )
    # byte
    byte_addr = encode_byte_address(parsed)
    return ResolvedDevice(
        text=text,
        scheme="pc10-byte",
        unit="byte",
        area=parsed.area,
        index=parsed.index,
        digits=parsed.digits,
        high=parsed.high,
        packed=parsed.packed,
        addr32=encode_exno_byte_u32(0x00, byte_addr),
    )


def _validate_profile_access(
    parsed: ParsedAddress,
    prefix: str | None,
    profile: str,
    device: str,
) -> None:
    """Reject profile-level route/family combinations that cannot be encoded.

    Catalog address ranges are intentionally advisory and are not enforced
    here.  Whether a usable index exists is PLC/configuration dependent and
    belongs in application-layer validation.
    """
    descriptor = ToyopucPlcProfiles.get_area_descriptor(parsed.area, profile)
    if parsed.packed and not descriptor.supports_packed_word:
        raise ValueError(f"W suffix is not available for area {parsed.area!r} in profile {profile!r}: {device}")
    expected_width = descriptor.get_address_width(parsed.unit, parsed.packed)
    if parsed.digits and parsed.digits > expected_width:
        raise ValueError(
            f"Address width exceeds the protocol notation for profile {profile!r}: "
            f"{device} (max {expected_width} hex digits)"
        )
    prefixed = prefix is not None
    ranges = descriptor.get_ranges_for_unit(prefixed, parsed.unit, parsed.packed)
    if not ranges:
        access_mode = "prefixed" if prefixed else "direct"
        raise ValueError(
            f"Area {parsed.area!r} is not available for {access_mode} access in profile {profile!r}: {device}"
        )


def _resolve_device_unbound(
    device: str,
    options: ToyopucAddressingOptions | None = None,
    profile: str | None = None,
) -> ResolvedDevice:
    """Resolve a string device address into a normalized access descriptor.

    Args:
        device: Device address string (e.g. ``"P1-D0100"``, ``"P1-M1000"``).
        options: Optional addressing option flags that control PC10 routing.
            When omitted, the selected profile's options are used.
        profile: Required canonical PLC profile name (e.g.
            ``"toyopuc:plus:standard"``). The profile selects addressing
            behavior and unsupported route/family decisions. Catalog index
            ranges remain advisory and are not a communication guard.
    """
    plc_profile = ToyopucPlcProfiles.from_name(profile)
    normalized_profile = plc_profile.name
    if options is None:
        options = plc_profile.addressing_options

    prefix, area, unit = _infer_unit_and_area(device)
    text = device.strip().upper()
    if prefix is None and area in _PREFIX_REQUIRED_AREAS:
        raise ValueError(f"{area} area requires P1-/P2-/P3- prefix: {text}")

    if prefix:
        ex_no, parsed = parse_prefixed_address(text, unit)
        _validate_profile_access(parsed, prefix, normalized_profile, device)
        if unit == "bit":
            bit_no, addr = encode_program_bit_address(parsed)
            addr32: int | None = None
            try:
                addr32 = encode_bit_address(parsed) | (ex_no << 19)
            except ValueError:
                addr32 = None
            return ResolvedDevice(
                text=text,
                scheme="program-bit",
                unit="bit",
                area=parsed.area,
                index=parsed.index,
                digits=parsed.digits,
                prefix=prefix,
                packed=parsed.packed,
                no=_PREFIX_PROGRAM_NO[prefix],
                bit_no=bit_no,
                addr=addr,
                addr32=addr32,
            )
        if unit == "word":
            if parsed.packed and parsed.area not in _BASIC_BIT_AREAS:
                raise ValueError(f"W suffix is only valid for bit-device families: {text}")
            return ResolvedDevice(
                text=text,
                scheme="program-word",
                unit="word",
                area=parsed.area,
                index=parsed.index,
                digits=parsed.digits,
                prefix=prefix,
                packed=parsed.packed,
                no=_PREFIX_PROGRAM_NO[prefix],
                addr=encode_program_word_address(parsed),
            )
        return ResolvedDevice(
            text=text,
            scheme="program-byte",
            unit="byte",
            area=parsed.area,
            index=parsed.index,
            digits=parsed.digits,
            prefix=prefix,
            high=parsed.high,
            packed=parsed.packed,
            no=_PREFIX_PROGRAM_NO[prefix],
            addr=encode_program_byte_address(parsed),
        )

    parsed = parse_address(text, unit)
    _validate_profile_access(parsed, prefix=None, profile=normalized_profile, device=device)

    if unit == "bit":
        pc10_bit = _try_resolve_direct_pc10_bit(parsed, text, options)
        if pc10_bit is not None:
            return pc10_bit
        if parsed.area in _BASIC_BIT_AREAS:
            return ResolvedDevice(
                text=text,
                scheme="basic-bit",
                unit="bit",
                area=parsed.area,
                index=parsed.index,
                digits=parsed.digits,
                packed=parsed.packed,
                basic_addr=encode_bit_address(parsed),
            )
        return _resolve_ext_bit(parsed, text)

    if unit == "word":
        if parsed.packed and parsed.area in _BASIC_WORD_AREAS | _EXT_WORD_AREAS:
            raise ValueError(f"W suffix is only valid for bit-device families: {text}")
        pc10_derived = _try_resolve_direct_pc10_derived(parsed, text, options)
        if pc10_derived is not None:
            return pc10_derived
        if parsed.area in _BASIC_WORD_AREAS | _BASIC_BIT_AREAS:
            return ResolvedDevice(
                text=text,
                scheme="basic-word",
                unit="word",
                area=parsed.area,
                index=parsed.index,
                digits=parsed.digits,
                packed=parsed.packed,
                basic_addr=encode_word_address(parsed),
            )
        if parsed.area == "U" and parsed.index >= 0x08000 and options.use_upper_u_pc10:
            return ResolvedDevice(
                text=text,
                scheme="pc10-word",
                unit="word",
                area=parsed.area,
                index=parsed.index,
                digits=parsed.digits,
                packed=parsed.packed,
                addr32=_pc10_u_addr32(parsed.index),
            )
        if parsed.area == "EB" and parsed.index <= 0x3FFFF and options.use_eb_pc10:
            return ResolvedDevice(
                text=text,
                scheme="pc10-word",
                unit="word",
                area=parsed.area,
                index=parsed.index,
                digits=parsed.digits,
                packed=parsed.packed,
                addr32=_pc10_eb_addr32(parsed.index),
            )
        if parsed.area == "FR" and options.use_fr_pc10:
            return ResolvedDevice(
                text=text,
                scheme="pc10-word",
                unit="word",
                area=parsed.area,
                index=parsed.index,
                digits=parsed.digits,
                packed=parsed.packed,
                addr32=encode_fr_word_addr32(parsed.index),
            )
        ext = encode_ext_no_address(parsed.area, parsed.index, "word")
        return ResolvedDevice(
            text=text,
            scheme="ext-word",
            unit="word",
            area=parsed.area,
            index=parsed.index,
            digits=parsed.digits,
            packed=parsed.packed,
            no=ext.no,
            addr=ext.addr,
        )

    # byte unit
    pc10_derived_byte = _try_resolve_direct_pc10_derived(parsed, text, options)
    if pc10_derived_byte is not None:
        return pc10_derived_byte
    if parsed.area in _BASIC_WORD_AREAS | _BASIC_BIT_AREAS:
        return ResolvedDevice(
            text=text,
            scheme="basic-byte",
            unit="byte",
            area=parsed.area,
            index=parsed.index,
            digits=parsed.digits,
            high=parsed.high,
            packed=parsed.packed,
            basic_addr=encode_byte_address(parsed),
        )
    if parsed.area == "U" and parsed.index >= 0x08000 and options.use_upper_u_pc10:
        return ResolvedDevice(
            text=text,
            scheme="pc10-byte",
            unit="byte",
            area=parsed.area,
            index=parsed.index,
            digits=parsed.digits,
            high=parsed.high,
            packed=parsed.packed,
            addr32=_pc10_u_addr32(parsed.index, byte=True, high=parsed.high),
        )
    if parsed.area == "EB" and parsed.index <= 0x3FFFF and options.use_eb_pc10:
        return ResolvedDevice(
            text=text,
            scheme="pc10-byte",
            unit="byte",
            area=parsed.area,
            index=parsed.index,
            digits=parsed.digits,
            high=parsed.high,
            packed=parsed.packed,
            addr32=_pc10_eb_addr32(parsed.index, byte=True, high=parsed.high),
        )
    if parsed.area == "FR":
        raise ValueError("FR does not support byte access; use word access via PC10 block commands")

    ext = encode_ext_no_address(parsed.area, parsed.index * 2 + (1 if parsed.high else 0), "byte")
    return ResolvedDevice(
        text=text,
        scheme="ext-byte",
        unit="byte",
        area=parsed.area,
        index=parsed.index,
        digits=parsed.digits,
        high=parsed.high,
        packed=parsed.packed,
        no=ext.no,
        addr=ext.addr,
    )


def resolve_device(device: str, *, profile: str) -> ResolvedDevice:
    """Resolve an address and bind the result to one canonical PLC profile."""
    canonical_profile = ToyopucPlcProfiles.from_name(profile).name
    return replace(
        _resolve_device_unbound(device, profile=canonical_profile),
        plc_profile=canonical_profile,
    )


def _raise_generic_fr_write_error() -> None:
    raise ValueError("Generic FR writes are disabled; use write_fr() for the work area and commit_fr() separately")


def _require_positive_count(count: int, label: str = "count") -> int:
    if isinstance(count, bool) or not isinstance(count, int) or count < 1:
        raise ValueError(f"{label} must be an integer >= 1")
    return count


def _normalize_device_value(resolved: ResolvedDevice, value: object) -> int:
    if resolved.unit == "bit":
        return _normalize_bit_value(value)
    if resolved.unit == "byte":
        return _normalize_byte_values([value])[0]  # type: ignore[list-item]
    if resolved.unit == "word":
        return _normalize_word_values([value])[0]  # type: ignore[list-item]
    raise ValueError(f"Unsupported device unit: {resolved.unit}")


class ToyopucDeviceClient(ToyopucClient):
    """High-level client that accepts string device addresses."""

    def __init__(
        self,
        *args: Any,
        plc_profile: str,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.plc_profile = ToyopucPlcProfiles.from_name(plc_profile).name
        self._resolved_device_cache: dict[str, ResolvedDevice] = {}
        self._run_plan_cache: dict[tuple[bool, tuple[ResolvedDevice, ...]], tuple[int, ...]] = {}

    def __enter__(self) -> ToyopucDeviceClient:
        super().__enter__()
        return self

    def _get_run_plan(self, devices: list[ResolvedDevice], split_pc10: bool) -> tuple[int, ...]:
        key = (split_pc10, tuple(devices))
        plan = self._run_plan_cache.get(key)
        if plan is None:
            lengths: list[int] = []
            idx = 0
            while idx < len(devices):
                run = _batch_run_length(devices, idx, split_pc10)
                lengths.append(run)
                idx += run
            plan = tuple(lengths)
            if len(self._run_plan_cache) >= _RUN_PLAN_CACHE_MAX:
                self._run_plan_cache.clear()
            self._run_plan_cache[key] = plan
        return plan

    def _require_single_read_request(self, devices: list[ResolvedDevice], split_pc10: bool, operation: str) -> None:
        if not devices:
            raise ValueError(f"{operation} requires at least one device")
        if len(devices) == 1:
            return
        plan = self._get_run_plan(devices, split_pc10)
        if len(plan) != 1 or not self._can_read_as_single_request(devices):
            self._raise_implicit_split_error(operation)

    def _require_single_write_request(self, devices: list[ResolvedDevice], split_pc10: bool, operation: str) -> None:
        if not devices:
            raise ValueError(f"{operation} requires at least one value")
        if len(devices) == 1:
            return
        plan = self._get_run_plan(devices, split_pc10)
        if len(plan) != 1 or not self._can_write_as_single_request(devices):
            self._raise_implicit_split_error(operation)

    @staticmethod
    def _raise_implicit_split_error(operation: str) -> None:
        raise ToyopucProtocolError(
            f"{operation} requires one compatible protocol request. "
            "Split the operation into explicit calls when multiple requests are intentional."
        )

    @staticmethod
    def _pc10_block_consecutive(devices: list[ResolvedDevice], step: int) -> bool:
        if not devices:
            return True
        start = _require(devices[0].addr32, "pc10 addr32")
        block = start >> 16
        for i, device in enumerate(devices):
            addr32 = _require(device.addr32, "pc10 addr32")
            if addr32 != start + (i * step) or (addr32 >> 16) != block:
                return False
        return True

    @staticmethod
    def _can_read_as_single_request(devices: list[ResolvedDevice]) -> bool:
        key = _batch_key(devices[0])
        if key is None or any(_batch_key(device) != key for device in devices):
            return False
        if key == "pc10-byte":
            return ToyopucDeviceClient._pc10_block_consecutive(devices, 1)
        if key == "pc10-word" and _contains_packed_pc10_word_device(devices):
            return ToyopucDeviceClient._pc10_block_consecutive(devices, 2)
        return True

    @staticmethod
    def _can_write_as_single_request(devices: list[ResolvedDevice]) -> bool:
        key = _batch_key(devices[0])
        if key is None or any(_batch_key(device) != key for device in devices):
            return False
        if len({device.text for device in devices}) != len(devices):
            return False
        if key == "pc10-byte":
            return ToyopucDeviceClient._pc10_block_consecutive(devices, 1)
        return True

    def resolve_device(self, device: str) -> ResolvedDevice:
        """Resolve a string address into a `ResolvedDevice`."""
        key = device.strip().upper()
        resolved = self._resolved_device_cache.get(key)
        if resolved is None:
            resolved = resolve_device(key, profile=self.plc_profile)
            if len(self._resolved_device_cache) >= _DEVICE_CACHE_MAX:
                self._resolved_device_cache.clear()
            self._resolved_device_cache[key] = resolved
        return resolved

    def _coerce_device(self, device: str | ResolvedDevice) -> ResolvedDevice:
        resolved = self.resolve_device(device) if isinstance(device, str) else device
        if resolved.plc_profile != self.plc_profile:
            raise ValueError(
                f"ResolvedDevice profile mismatch: expected {self.plc_profile!r}, received {resolved.plc_profile!r}"
            )
        return resolved

    def relay_read_one(
        self,
        hops: str | Iterable[tuple[int, int]],
        device: str | ResolvedDevice,
    ) -> object:
        """Read exactly one item through relay hops and return a scalar."""
        resolved = self._coerce_device(device)
        return self._relay_read_resolved_device(hops, resolved)

    def relay_read(
        self,
        hops: str | Iterable[tuple[int, int]],
        device: str | ResolvedDevice,
        count: int,
    ) -> list[object]:
        """Read a contiguous sequence through relay hops using one request."""
        _require_positive_count(count)
        resolved = self._coerce_device(device)
        devices = self._seq_devices(resolved, count)
        self._require_single_read_request(devices, split_pc10=True, operation="relay_read")
        return self._relay_read_runs(hops, devices, split_pc10=True)

    def relay_write(
        self,
        hops: str | Iterable[tuple[int, int]],
        device: str | ResolvedDevice,
        value: Any,
    ) -> None:
        """Write one item or a contiguous sequence through relay hops."""
        resolved = self._coerce_device(device)
        if isinstance(value, (bytes, bytearray, list, tuple)):
            devices = self._seq_devices(resolved, len(value))
            normalized = [_normalize_device_value(device, item) for device, item in zip(devices, value, strict=True)]
            self._require_single_write_request(devices, split_pc10=True, operation="relay_write")
            self._relay_write_runs(hops, devices, normalized, split_pc10=True)
            return
        self._relay_write_resolved_device(hops, resolved, value)

    def relay_read_words(
        self,
        hops: str | Iterable[tuple[int, int]],
        device: int | str | ResolvedDevice,
        count: int,
    ) -> list[int]:
        """Read one or more word devices through relay hops."""
        _require_positive_count(count)
        if isinstance(device, int):
            return super().relay_read_words(hops, device, count)
        resolved = self._coerce_device(device)
        if resolved.unit != "word":
            raise ValueError("relay_read_words() requires a word device")
        return [int(cast(Any, item)) for item in self.relay_read(hops, resolved, count)]

    def relay_write_words(
        self,
        hops: str | Iterable[tuple[int, int]],
        device: int | str | ResolvedDevice,
        value: Iterable[int] | int,
    ) -> None:
        """Write one or more word devices through relay hops."""
        if isinstance(device, int):
            if isinstance(value, int):
                super().relay_write_words(hops, device, [value])
            else:
                super().relay_write_words(hops, device, value)
            return
        resolved = self._coerce_device(device)
        if resolved.unit != "word":
            raise ValueError("relay_write_words() requires a word device")
        self.relay_write(hops, resolved, value)

    def relay_read_devices(
        self,
        hops: str | Iterable[tuple[int, int]],
        devices: Sequence[str | ResolvedDevice],
    ) -> list[object]:
        """Read multiple devices through relay hops as one compatible protocol request."""
        resolved = [self._coerce_device(d) for d in devices]
        self._require_single_read_request(resolved, split_pc10=False, operation="relay_read_devices")
        return self._relay_read_runs(hops, resolved, split_pc10=False)

    def relay_write_many(
        self,
        hops: str | Iterable[tuple[int, int]],
        items: Mapping[str | ResolvedDevice, object],
    ) -> None:
        """Write multiple devices through relay hops as one compatible protocol request."""
        resolved_items = []
        for device, value in items.items():
            resolved = self._coerce_device(device)
            resolved_items.append((resolved, _normalize_device_value(resolved, value)))
        self._require_single_write_request(
            [resolved for resolved, _ in resolved_items],
            split_pc10=True,
            operation="relay_write_many",
        )
        self._relay_write_runs(
            hops,
            [resolved for resolved, _ in resolved_items],
            [value for _, value in resolved_items],
            split_pc10=True,
        )

    def read_fr_one(self, device: str | ResolvedDevice) -> int:
        """Read exactly one FR word and return a scalar."""
        return self.read_fr(device, 1)[0]

    def read_fr(self, device: str | ResolvedDevice, count: int) -> list[int]:
        """Read contiguous FR words using exactly one PC10 block request."""
        _require_positive_count(count)
        resolved = self._coerce_device(device)
        if resolved.area != "FR" or resolved.unit != "word":
            raise ValueError("read_fr() requires an FR word device such as FR000000")
        return self._read_resolved_word_values(resolved, count)

    def relay_read_fr_one(
        self,
        hops: str | Iterable[tuple[int, int]],
        device: str | ResolvedDevice,
    ) -> int:
        """Read exactly one FR word through relay hops and return a scalar."""
        return self.relay_read_fr(hops, device, 1)[0]

    def relay_read_fr(
        self,
        hops: str | Iterable[tuple[int, int]],
        device: str | ResolvedDevice,
        count: int,
    ) -> list[int]:
        """Read contiguous FR words through relay hops using one request."""
        _require_positive_count(count)
        resolved = self._coerce_device(device)
        if resolved.area != "FR" or resolved.unit != "word":
            raise ValueError("relay_read_fr() requires an FR word device such as FR000000")
        return [int(cast(Any, value)) for value in self.relay_read(hops, resolved, count)]

    def write_fr(
        self,
        device: str | ResolvedDevice,
        value: Any,
    ) -> None:
        """Update FR work-area words with exactly one request; never commit."""
        resolved = self._coerce_device(device)
        if resolved.area != "FR" or resolved.unit != "word":
            raise ValueError("write_fr() requires an FR word device such as FR000000")
        if isinstance(value, (list, tuple)):
            values = list(value)
        else:
            values = [value]
        self.write_fr_words(resolved.index, values)

    def relay_write_fr(
        self,
        hops: str | Iterable[tuple[int, int]],
        device: str | ResolvedDevice,
        value: Any,
    ) -> None:
        """Update remote FR work-area words with one request; never commit."""
        resolved = self._coerce_device(device)
        if resolved.area != "FR" or resolved.unit != "word":
            raise ValueError("relay_write_fr() requires an FR word device such as FR000000")
        if isinstance(value, (list, tuple)):
            values = list(value)
        else:
            values = [value]
        self.relay_write_fr_words(hops, resolved.index, values)

    def commit_fr(
        self,
        device: str | ResolvedDevice,
    ) -> None:
        """Commit the one FR block whose first word is explicitly specified."""
        resolved = self._coerce_device(device)
        if resolved.area != "FR" or resolved.unit != "word":
            raise ValueError("commit_fr() requires an FR word device such as FR000000")
        self.commit_fr_block(resolved.index)

    def relay_commit_fr(
        self,
        hops: str | Iterable[tuple[int, int]],
        device: str | ResolvedDevice,
    ) -> None:
        """Commit one explicitly selected remote FR block."""
        resolved = self._coerce_device(device)
        if resolved.area != "FR" or resolved.unit != "word":
            raise ValueError("relay_commit_fr() requires an FR word device such as FR000000")
        self.relay_commit_fr_block(hops, resolved.index)

    def read_one(self, device: str | ResolvedDevice) -> object:
        """Read exactly one item and return a scalar."""
        resolved = self._coerce_device(device)
        return self._read_resolved_device(resolved)

    def read(self, device: str | ResolvedDevice, count: int) -> list[object]:
        """Read a contiguous sequence using exactly one protocol request."""
        _require_positive_count(count)
        resolved = self._coerce_device(device)
        devices = self._seq_devices(resolved, count)
        self._require_single_read_request(devices, split_pc10=True, operation="read")
        return self._read_runs(devices, split_pc10=True)

    def write(self, device: str | ResolvedDevice, value: Any) -> None:
        """Write one item or a contiguous sequence to a device address."""
        resolved = self._coerce_device(device)
        if resolved.area == "FR":
            _raise_generic_fr_write_error()
        if isinstance(value, (bytes, bytearray, list, tuple)):
            devices = self._seq_devices(resolved, len(value))
            normalized = [_normalize_device_value(device, item) for device, item in zip(devices, value, strict=True)]
            self._require_single_write_request(devices, split_pc10=True, operation="write")
            self._write_runs(devices, normalized, split_pc10=True)
            return
        self._write_resolved_device(resolved, value)

    def read_devices(self, devices: Sequence[str | ResolvedDevice]) -> list[object]:
        """Read multiple devices as one compatible protocol request and preserve input order."""
        resolved = [self._coerce_device(d) for d in devices]
        self._require_single_read_request(resolved, split_pc10=False, operation="read_devices")
        return self._read_runs(resolved, split_pc10=False)

    def write_many(self, items: Mapping[str | ResolvedDevice, object]) -> None:
        """Write multiple devices as one compatible protocol request in mapping iteration order."""
        resolved_items = []
        for device, value in items.items():
            resolved = self._coerce_device(device)
            if resolved.area == "FR":
                _raise_generic_fr_write_error()
            resolved_items.append((resolved, _normalize_device_value(resolved, value)))
        self._require_single_write_request(
            [resolved for resolved, _ in resolved_items],
            split_pc10=True,
            operation="write_many",
        )
        self._write_runs(
            [resolved for resolved, _ in resolved_items],
            [value for _, value in resolved_items],
            split_pc10=True,
        )

    def read_dword(self, device: int | str | ResolvedDevice) -> int:
        """Read one 32-bit value from two consecutive word devices."""
        return self.read_dwords(device, 1)[0]

    def write_dword(self, device: int | str | ResolvedDevice, value: int) -> None:
        """Write one 32-bit value to two consecutive word devices."""
        self.write_dwords(device, [value])

    def read_dwords(self, device: int | str | ResolvedDevice, count: int) -> list[int]:
        """Read one or more 32-bit values from consecutive word devices."""
        if isinstance(device, int):
            return super().read_dwords(device, count)
        resolved = self._coerce_device(device)
        self._ensure_word_device(resolved, "read_dwords()")
        _require_positive_count(count)
        words = self._read_resolved_word_values(resolved, count * 2)
        return _unpack_uint32_low_word_first_words(words)

    def write_dwords(self, device: int | str | ResolvedDevice, values: Iterable[int]) -> None:
        """Write one or more 32-bit values to consecutive word devices."""
        if isinstance(device, int):
            return super().write_dwords(device, values)
        resolved = self._coerce_device(device)
        self._ensure_word_device(resolved, "write_dwords()")
        self._write_resolved_word_values(resolved, _pack_uint32_low_word_first_words(values))

    def read_float32(self, device: int | str | ResolvedDevice) -> float:
        """Read one IEEE-754 float32 from two consecutive word devices."""
        return self.read_float32s(device, 1)[0]

    def write_float32(self, device: int | str | ResolvedDevice, value: float) -> None:
        """Write one IEEE-754 float32 to two consecutive word devices."""
        self.write_float32s(device, [value])

    def read_float32s(self, device: int | str | ResolvedDevice, count: int) -> list[float]:
        """Read one or more IEEE-754 float32 values from consecutive word devices."""
        if isinstance(device, int):
            return super().read_float32s(device, count)
        resolved = self._coerce_device(device)
        self._ensure_word_device(resolved, "read_float32s()")
        _require_positive_count(count)
        words = self._read_resolved_word_values(resolved, count * 2)
        return _unpack_float32_low_word_first_words(words)

    def write_float32s(self, device: int | str | ResolvedDevice, values: Iterable[float]) -> None:
        """Write one or more IEEE-754 float32 values to consecutive word devices."""
        if isinstance(device, int):
            return super().write_float32s(device, values)
        resolved = self._coerce_device(device)
        self._ensure_word_device(resolved, "write_float32s()")
        self._write_resolved_word_values(resolved, _pack_float32_low_word_first_words(values))

    def relay_read_dword(
        self,
        hops: str | Iterable[tuple[int, int]],
        device: str | ResolvedDevice,
    ) -> int:
        """Read one 32-bit value through relay hops."""
        return self.relay_read_dwords(hops, device, 1)[0]

    def relay_write_dword(
        self,
        hops: str | Iterable[tuple[int, int]],
        device: str | ResolvedDevice,
        value: int,
    ) -> None:
        """Write one 32-bit value through relay hops."""
        self.relay_write_dwords(hops, device, [value])

    def relay_read_dwords(
        self,
        hops: str | Iterable[tuple[int, int]],
        device: str | ResolvedDevice,
        count: int,
    ) -> list[int]:
        """Read one or more 32-bit values through relay hops."""
        resolved = self._coerce_device(device)
        self._ensure_word_device(resolved, "relay_read_dwords()")
        _require_positive_count(count)
        words = self._relay_read_resolved_word_values(hops, resolved, count * 2)
        return _unpack_uint32_low_word_first_words(words)

    def relay_write_dwords(
        self,
        hops: str | Iterable[tuple[int, int]],
        device: str | ResolvedDevice,
        values: Iterable[int],
    ) -> None:
        """Write one or more 32-bit values through relay hops."""
        resolved = self._coerce_device(device)
        self._ensure_word_device(resolved, "relay_write_dwords()")
        self._relay_write_resolved_word_values(hops, resolved, _pack_uint32_low_word_first_words(values))

    def relay_read_float32(
        self,
        hops: str | Iterable[tuple[int, int]],
        device: str | ResolvedDevice,
    ) -> float:
        """Read one IEEE-754 float32 through relay hops."""
        return self.relay_read_float32s(hops, device, 1)[0]

    def relay_write_float32(
        self,
        hops: str | Iterable[tuple[int, int]],
        device: str | ResolvedDevice,
        value: float,
    ) -> None:
        """Write one IEEE-754 float32 through relay hops."""
        self.relay_write_float32s(hops, device, [value])

    def relay_read_float32s(
        self,
        hops: str | Iterable[tuple[int, int]],
        device: str | ResolvedDevice,
        count: int,
    ) -> list[float]:
        """Read one or more IEEE-754 float32 values through relay hops."""
        resolved = self._coerce_device(device)
        self._ensure_word_device(resolved, "relay_read_float32s()")
        _require_positive_count(count)
        words = self._relay_read_resolved_word_values(hops, resolved, count * 2)
        return _unpack_float32_low_word_first_words(words)

    def relay_write_float32s(
        self,
        hops: str | Iterable[tuple[int, int]],
        device: str | ResolvedDevice,
        values: Iterable[float],
    ) -> None:
        """Write one or more IEEE-754 float32 values through relay hops."""
        resolved = self._coerce_device(device)
        self._ensure_word_device(resolved, "relay_write_float32s()")
        self._relay_write_resolved_word_values(hops, resolved, _pack_float32_low_word_first_words(values))

    def _ensure_word_device(self, resolved: ResolvedDevice, method_name: str) -> None:
        if resolved.unit != "word":
            raise ValueError(f"{method_name} requires a word device")

    def _read_resolved_word_values(self, resolved: ResolvedDevice, word_count: int) -> list[int]:
        _require_positive_count(word_count, "word_count")
        devices = self._seq_devices(resolved, word_count)
        self._require_single_read_request(devices, split_pc10=True, operation="word read")
        return [int(v) & 0xFFFF for v in self._read_runs(devices, split_pc10=True)]

    def _relay_read_resolved_word_values(
        self,
        hops: str | Iterable[tuple[int, int]],
        resolved: ResolvedDevice,
        word_count: int,
    ) -> list[int]:
        _require_positive_count(word_count, "word_count")
        devices = self._seq_devices(resolved, word_count)
        self._require_single_read_request(devices, split_pc10=True, operation="relay word read")
        runs = self._relay_read_runs(hops, devices, split_pc10=True)
        return [int(v) & 0xFFFF for v in runs]

    def _write_resolved_word_values(self, resolved: ResolvedDevice, word_values: Iterable[int]) -> None:
        values = _normalize_word_values(word_values)
        devices = self._seq_devices(resolved, len(values))
        self._require_single_write_request(devices, split_pc10=True, operation="word write")
        if resolved.area == "FR":
            self.write_fr_words(resolved.index, values)
            return
        self._write_runs(devices, values, split_pc10=True)

    def _relay_write_resolved_word_values(
        self,
        hops: str | Iterable[tuple[int, int]],
        resolved: ResolvedDevice,
        word_values: Iterable[int],
    ) -> None:
        values = _normalize_word_values(word_values)
        devices = self._seq_devices(resolved, len(values))
        self._require_single_write_request(devices, split_pc10=True, operation="relay word write")
        if resolved.area == "FR":
            self.relay_write_fr_words(hops, resolved.index, values)
            return
        self._relay_write_runs(hops, devices, values, split_pc10=True)

    def _read_resolved_device(self, resolved: ResolvedDevice) -> Any:
        if resolved.scheme == "basic-bit":
            addr = _require(resolved.basic_addr, "basic_addr")
            return self.read_bit(addr)
        if resolved.scheme == "basic-word":
            addr = _require(resolved.basic_addr, "basic_addr")
            return self.read_words(addr, 1)[0]
        if resolved.scheme == "basic-byte":
            addr = _require(resolved.basic_addr, "basic_addr")
            return self.read_bytes(addr, 1)[0]
        if resolved.scheme == "program-bit":
            no = _require(resolved.no, "program number")
            bit_no = _require(resolved.bit_no, "program bit")
            addr = _require(resolved.addr, "program addr")
            return bool(self.read_ext_multi([(no, bit_no, addr)], [], [])[0] & 0x01)
        if resolved.scheme == "program-word":
            no = _require(resolved.no, "program number")
            addr = _require(resolved.addr, "program addr")
            return self.read_ext_words(no, addr, 1)[0]
        if resolved.scheme == "program-byte":
            no = _require(resolved.no, "program number")
            addr = _require(resolved.addr, "program addr")
            return self.read_ext_bytes(no, addr, 1)[0]
        if resolved.scheme == "ext-bit":
            no = _require(resolved.no, "extended number")
            bit_no = _require(resolved.bit_no, "extended bit")
            addr = _require(resolved.addr, "extended addr")
            return bool(self.read_ext_multi([(no, bit_no, addr)], [], [])[0] & 0x01)
        if resolved.scheme == "ext-word":
            no = _require(resolved.no, "extended number")
            addr = _require(resolved.addr, "extended addr")
            return self.read_ext_words(no, addr, 1)[0]
        if resolved.scheme == "ext-byte":
            no = _require(resolved.no, "extended number")
            addr = _require(resolved.addr, "extended addr")
            return self.read_ext_bytes(no, addr, 1)[0]
        if resolved.scheme == "pc10-bit":
            addr32 = _require(resolved.addr32, "pc10 addr32")
            return bool(_read_pc10_multi_bits(self, [addr32])[0])
        if resolved.scheme == "pc10-word":
            addr32 = _require(resolved.addr32, "pc10 addr32")
            return _read_pc10_block_word(self, addr32)
        if resolved.scheme == "pc10-byte":
            addr32 = _require(resolved.addr32, "pc10 addr32")
            return self.pc10_block_read(addr32, 1)[0]
        raise ValueError(f"Unsupported resolved scheme: {resolved.scheme}")

    def _relay_read_resolved_device(self, hops: str | Iterable[tuple[int, int]], resolved: ResolvedDevice) -> Any:
        if resolved.scheme == "basic-bit":
            resp = self.send_via_relay(hops, build_bit_read(_require(resolved.basic_addr, "basic_addr")))
            if resp.cmd != 0x20:
                raise ToyopucProtocolError("Unexpected CMD in relay bit-read response")
            if len(resp.data) != 1:
                raise ToyopucProtocolError("Relay bit-read response must be 1 byte")
            return bool(resp.data[0] & 0x01)
        if resolved.scheme == "basic-word":
            resp = self.send_via_relay(hops, build_word_read(_require(resolved.basic_addr, "basic_addr"), 1))
            if resp.cmd != 0x1C:
                raise ToyopucProtocolError("Unexpected CMD in relay word-read response")
            return unpack_u16_le(resp.data)[0]
        if resolved.scheme == "basic-byte":
            resp = self.send_via_relay(hops, build_byte_read(_require(resolved.basic_addr, "basic_addr"), 1))
            if resp.cmd != 0x1E:
                raise ToyopucProtocolError("Unexpected CMD in relay byte-read response")
            if len(resp.data) != 1:
                raise ToyopucProtocolError("Relay byte-read response must be 1 byte")
            return resp.data[0]
        if resolved.scheme == "program-bit":
            resp = self.send_via_relay(
                hops,
                build_ext_multi_read(
                    [
                        (
                            _require(resolved.no, "program number"),
                            _require(resolved.bit_no, "program bit"),
                            _require(resolved.addr, "program addr"),
                        )
                    ],
                    [],
                    [],
                ),
            )
            if resp.cmd != 0x98:
                raise ToyopucProtocolError("Unexpected CMD in relay multi-read response")
            if not resp.data:
                raise ToyopucProtocolError("Relay multi-read response missing bit payload")
            return bool(resp.data[0] & 0x01)
        if resolved.scheme == "program-word":
            resp = self.send_via_relay(
                hops,
                build_ext_word_read(
                    _require(resolved.no, "program number"),
                    _require(resolved.addr, "program addr"),
                    1,
                ),
            )
            if resp.cmd != 0x94:
                raise ToyopucProtocolError("Unexpected CMD in relay ext word-read response")
            return unpack_u16_le(resp.data)[0]
        if resolved.scheme == "program-byte":
            resp = self.send_via_relay(
                hops,
                build_ext_byte_read(
                    _require(resolved.no, "program number"),
                    _require(resolved.addr, "program addr"),
                    1,
                ),
            )
            if resp.cmd != 0x96:
                raise ToyopucProtocolError("Unexpected CMD in relay ext byte-read response")
            if len(resp.data) != 1:
                raise ToyopucProtocolError("Relay ext byte-read response must be 1 byte")
            return resp.data[0]
        if resolved.scheme == "ext-bit":
            resp = self.send_via_relay(
                hops,
                build_ext_multi_read(
                    [
                        (
                            _require(resolved.no, "extended number"),
                            _require(resolved.bit_no, "extended bit"),
                            _require(resolved.addr, "extended addr"),
                        )
                    ],
                    [],
                    [],
                ),
            )
            if resp.cmd != 0x98:
                raise ToyopucProtocolError("Unexpected CMD in relay multi-read response")
            if not resp.data:
                raise ToyopucProtocolError("Relay multi-read response missing bit payload")
            return bool(resp.data[0] & 0x01)
        if resolved.scheme == "ext-word":
            resp = self.send_via_relay(
                hops,
                build_ext_word_read(
                    _require(resolved.no, "extended number"),
                    _require(resolved.addr, "extended addr"),
                    1,
                ),
            )
            if resp.cmd != 0x94:
                raise ToyopucProtocolError("Unexpected CMD in relay ext word-read response")
            return unpack_u16_le(resp.data)[0]
        if resolved.scheme == "ext-byte":
            resp = self.send_via_relay(
                hops,
                build_ext_byte_read(
                    _require(resolved.no, "extended number"),
                    _require(resolved.addr, "extended addr"),
                    1,
                ),
            )
            if resp.cmd != 0x96:
                raise ToyopucProtocolError("Unexpected CMD in relay ext byte-read response")
            if len(resp.data) != 1:
                raise ToyopucProtocolError("Relay ext byte-read response must be 1 byte")
            return resp.data[0]
        if resolved.scheme == "pc10-bit":
            addr32 = _require(resolved.addr32, "pc10 addr32")
            payload = bytearray([0x01, 0x00, 0x00, 0x00])
            payload.extend(addr32.to_bytes(4, "little"))
            resp = self.send_via_relay(hops, build_pc10_multi_read(bytes(payload)))
            if resp.cmd != 0xC4:
                raise ToyopucProtocolError("Unexpected CMD in relay PC10 multi-read response")
            if len(resp.data) < 5:
                raise ToyopucProtocolError("Relay PC10 bit-read response too short")
            return bool(resp.data[4] & 0x01)
        if resolved.scheme == "pc10-word":
            resp = self.send_via_relay(hops, build_pc10_block_read(_require(resolved.addr32, "pc10 addr32"), 2))
            if resp.cmd != 0xC2:
                raise ToyopucProtocolError("Unexpected CMD in relay PC10 block-read response")
            if len(resp.data) < 2:
                raise ToyopucProtocolError("Relay PC10 word-read response too short")
            return int.from_bytes(resp.data[:2], "little")
        if resolved.scheme == "pc10-byte":
            resp = self.send_via_relay(hops, build_pc10_block_read(_require(resolved.addr32, "pc10 addr32"), 1))
            if resp.cmd != 0xC2:
                raise ToyopucProtocolError("Unexpected CMD in relay PC10 block-read response")
            if len(resp.data) < 1:
                raise ToyopucProtocolError("Relay PC10 byte-read response too short")
            return resp.data[0]
        raise ValueError(f"Unsupported resolved scheme: {resolved.scheme}")

    def _write_resolved_device(self, resolved: ResolvedDevice, value: Any) -> None:
        value = _normalize_device_value(resolved, value)
        if resolved.scheme == "basic-bit":
            addr = _require(resolved.basic_addr, "basic_addr")
            self.write_bit(addr, value == 1)
            return
        if resolved.scheme == "basic-word":
            addr = _require(resolved.basic_addr, "basic_addr")
            self.write_words(addr, [int(value)])
            return
        if resolved.scheme == "basic-byte":
            addr = _require(resolved.basic_addr, "basic_addr")
            self.write_bytes(addr, [int(value)])
            return
        if resolved.scheme == "program-bit":
            no = _require(resolved.no, "program number")
            bit_no = _require(resolved.bit_no, "program bit")
            addr = _require(resolved.addr, "program addr")
            self.write_ext_multi([(no, bit_no, addr, value)], [], [])
            return
        if resolved.scheme == "program-word":
            no = _require(resolved.no, "program number")
            addr = _require(resolved.addr, "program addr")
            self.write_ext_words(no, addr, [int(value)])
            return
        if resolved.scheme == "program-byte":
            no = _require(resolved.no, "program number")
            addr = _require(resolved.addr, "program addr")
            self.write_ext_bytes(no, addr, [int(value)])
            return
        if resolved.scheme == "ext-bit":
            no = _require(resolved.no, "extended number")
            bit_no = _require(resolved.bit_no, "extended bit")
            addr = _require(resolved.addr, "extended addr")
            self.write_ext_multi([(no, bit_no, addr, value)], [], [])
            return
        if resolved.scheme == "ext-word":
            no = _require(resolved.no, "extended number")
            addr = _require(resolved.addr, "extended addr")
            self.write_ext_words(no, addr, [int(value)])
            return
        if resolved.scheme == "ext-byte":
            no = _require(resolved.no, "extended number")
            addr = _require(resolved.addr, "extended addr")
            self.write_ext_bytes(no, addr, [int(value)])
            return
        if resolved.scheme == "pc10-bit":
            addr32 = _require(resolved.addr32, "pc10 addr32")
            self.pc10_multi_write(_pack_pc10_multi_bit_payload([(addr32, value)]))
            return
        if resolved.scheme == "pc10-word":
            addr32 = _require(resolved.addr32, "pc10 addr32")
            _write_pc10_block_word(self, addr32, int(value))
            return
        if resolved.scheme == "pc10-byte":
            addr32 = _require(resolved.addr32, "pc10 addr32")
            self.pc10_block_write(addr32, bytes([value]))
            return
        raise ValueError(f"Unsupported resolved scheme: {resolved.scheme}")

    def _relay_write_resolved_device(
        self,
        hops: str | Iterable[tuple[int, int]],
        resolved: ResolvedDevice,
        value: Any,
    ) -> None:
        value = _normalize_device_value(resolved, value)
        if resolved.scheme == "basic-bit":
            resp = self.send_via_relay(
                hops,
                build_bit_write(_require(resolved.basic_addr, "basic_addr"), value),
            )
            if resp.cmd != 0x21:
                raise ToyopucProtocolError("Unexpected CMD in relay bit-write response")
            return
        if resolved.scheme == "basic-word":
            resp = self.send_via_relay(
                hops,
                build_word_write(_require(resolved.basic_addr, "basic_addr"), [int(value)]),
            )
            if resp.cmd != 0x1D:
                raise ToyopucProtocolError("Unexpected CMD in relay word-write response")
            return
        if resolved.scheme == "basic-byte":
            resp = self.send_via_relay(
                hops,
                build_byte_write(_require(resolved.basic_addr, "basic_addr"), [int(value)]),
            )
            if resp.cmd != 0x1F:
                raise ToyopucProtocolError("Unexpected CMD in relay byte-write response")
            return
        if resolved.scheme == "program-bit":
            resp = self.send_via_relay(
                hops,
                build_ext_multi_write(
                    [
                        (
                            _require(resolved.no, "program number"),
                            _require(resolved.bit_no, "program bit"),
                            _require(resolved.addr, "program addr"),
                            value,
                        )
                    ],
                    [],
                    [],
                ),
            )
            if resp.cmd != 0x99:
                raise ToyopucProtocolError("Unexpected CMD in relay multi-write response")
            return
        if resolved.scheme == "program-word":
            resp = self.send_via_relay(
                hops,
                build_ext_word_write(
                    _require(resolved.no, "program number"),
                    _require(resolved.addr, "program addr"),
                    [int(value)],
                ),
            )
            if resp.cmd != 0x95:
                raise ToyopucProtocolError("Unexpected CMD in relay ext word-write response")
            return
        if resolved.scheme == "program-byte":
            resp = self.send_via_relay(
                hops,
                build_ext_byte_write(
                    _require(resolved.no, "program number"),
                    _require(resolved.addr, "program addr"),
                    [int(value)],
                ),
            )
            if resp.cmd != 0x97:
                raise ToyopucProtocolError("Unexpected CMD in relay ext byte-write response")
            return
        if resolved.scheme == "ext-bit":
            resp = self.send_via_relay(
                hops,
                build_ext_multi_write(
                    [
                        (
                            _require(resolved.no, "extended number"),
                            _require(resolved.bit_no, "extended bit"),
                            _require(resolved.addr, "extended addr"),
                            value,
                        )
                    ],
                    [],
                    [],
                ),
            )
            if resp.cmd != 0x99:
                raise ToyopucProtocolError("Unexpected CMD in relay multi-write response")
            return
        if resolved.scheme == "ext-word":
            resp = self.send_via_relay(
                hops,
                build_ext_word_write(
                    _require(resolved.no, "extended number"),
                    _require(resolved.addr, "extended addr"),
                    [int(value)],
                ),
            )
            if resp.cmd != 0x95:
                raise ToyopucProtocolError("Unexpected CMD in relay ext word-read response")
            return
        if resolved.scheme == "ext-byte":
            resp = self.send_via_relay(
                hops,
                build_ext_byte_write(
                    _require(resolved.no, "extended number"),
                    _require(resolved.addr, "extended addr"),
                    [int(value)],
                ),
            )
            if resp.cmd != 0x97:
                raise ToyopucProtocolError("Unexpected CMD in relay ext byte-write response")
            return
        if resolved.scheme == "pc10-bit":
            resp = self.send_via_relay(
                hops,
                build_pc10_multi_write(
                    _pack_pc10_multi_bit_payload([(_require(resolved.addr32, "pc10 addr32"), value)])
                ),
            )
            if resp.cmd != 0xC5:
                raise ToyopucProtocolError("Unexpected CMD in relay PC10 multi-write response")
            return
        if resolved.scheme == "pc10-word":
            resp = self.send_via_relay(
                hops,
                build_pc10_block_write(
                    _require(resolved.addr32, "pc10 addr32"),
                    value.to_bytes(2, "little"),
                ),
            )
            if resp.cmd != 0xC3:
                raise ToyopucProtocolError("Unexpected CMD in relay PC10 block-write response")
            return
        if resolved.scheme == "pc10-byte":
            resp = self.send_via_relay(
                hops,
                build_pc10_block_write(_require(resolved.addr32, "pc10 addr32"), bytes([value])),
            )
            if resp.cmd != 0xC3:
                raise ToyopucProtocolError("Unexpected CMD in relay PC10 block-write response")
            return
        raise ValueError(f"Unsupported resolved scheme: {resolved.scheme}")

    def _offset_resolved_device(self, resolved: ResolvedDevice, delta: int) -> ResolvedDevice:
        if delta == 0:
            return resolved
        width = resolved.digits if resolved.digits > 0 else max(4, len(f"{resolved.index:X}"))
        if resolved.unit == "byte":
            suffix = "H" if resolved.high else "L"
            index = resolved.index + delta
            if resolved.prefix:
                return self.resolve_device(f"{resolved.prefix}-{resolved.area}{index:0{width}X}{suffix}")
            return self.resolve_device(f"{resolved.area}{index:0{width}X}{suffix}")
        index = resolved.index + delta
        suffix = "W" if resolved.packed and resolved.unit == "word" else ""
        if resolved.prefix:
            return self.resolve_device(f"{resolved.prefix}-{resolved.area}{index:0{width}X}{suffix}")
        return self.resolve_device(f"{resolved.area}{index:0{width}X}{suffix}")

    def _seq_devices(self, resolved: ResolvedDevice, count: int) -> list[ResolvedDevice]:
        """Build a list of *count* sequentially-offset ResolvedDevices."""
        devs: list[ResolvedDevice] = [resolved]
        for i in range(1, count):
            devs.append(self._offset_resolved_device(resolved, i))
        return devs

    # ------------------------------------------------------------------
    # Batch-read helpers
    # ------------------------------------------------------------------

    def _read_basic_word_batch(self, devices: list[ResolvedDevice]) -> list[int]:
        addrs = [_require(d.basic_addr, "basic_addr") for d in devices]
        if _is_consecutive_basic(devices):
            return self.read_words(addrs[0], len(devices))
        return list(self.read_words_multi(addrs))

    def _read_ext_word_batch(self, devices: list[ResolvedDevice]) -> list[int]:
        if _is_consecutive_ext_word(devices):
            no = _require(devices[0].no, "no")
            addr = _require(devices[0].addr, "addr")
            return self.read_ext_words(no, addr, len(devices))
        return unpack_u16_le(
            self.read_ext_multi(
                [],
                [],
                [(_require(d.no, "no"), _ext_word_monitor_addr(_require(d.addr, "addr"))) for d in devices],
            )
        )[: len(devices)]

    def _read_ext_byte_batch(self, devices: list[ResolvedDevice]) -> list[int]:
        no0 = devices[0].no
        if no0 is not None and all(d.no == no0 for d in devices):
            addrs = [_require(d.addr, "addr") for d in devices]
            if all(a == addrs[0] + i for i, a in enumerate(addrs)):
                return list(self.read_ext_bytes(no0, addrs[0], len(devices)))
        return list(
            self.read_ext_multi(
                [],
                [(_require(d.no, "no"), _require(d.addr, "addr")) for d in devices],
                [],
            )[: len(devices)]
        )

    def _read_ext_bit_batch(self, devices: list[ResolvedDevice]) -> list[bool]:
        bits = [(_require(d.no, "no"), _require(d.bit_no, "bit_no"), _require(d.addr, "addr")) for d in devices]
        data = self.read_ext_multi(bits, [], [])
        return [bool(v) for v in _parse_ext_multi_bit_data(data, len(devices))]

    def _read_pc10_word_batch_by_segments(self, devices: list[ResolvedDevice]) -> list[int]:
        values: list[int] = []
        segment_start = 0
        while segment_start < len(devices):
            segment_len = _pc10_word_segment_length(devices, segment_start)
            start_addr = _require(devices[segment_start].addr32, "pc10 addr32")
            words = unpack_u16_le(self.pc10_block_read(start_addr, segment_len * 2))
            if len(words) < segment_len:
                raise ToyopucProtocolError("PC10 block-read response too short")
            values.extend(words[:segment_len])
            segment_start += segment_len
        return values

    def _read_pc10_word_batch(self, devices: list[ResolvedDevice]) -> list[int]:
        if _is_consecutive_pc10_word(devices):
            addr32 = _require(devices[0].addr32, "pc10 addr32")
            raw = self.pc10_block_read(addr32, len(devices) * 2)
            return [int.from_bytes(raw[i * 2 : i * 2 + 2], "little") for i in range(len(devices))]
        if _contains_packed_pc10_word_device(devices):
            return self._read_pc10_word_batch_by_segments(devices)
        return _read_pc10_multi_words(self, [_require(d.addr32, "pc10 addr32") for d in devices])

    def _read_pc10_byte_batch(self, devices: list[ResolvedDevice]) -> list[int]:
        addrs32 = [_require(d.addr32, "pc10 addr32") for d in devices]
        if all(a == addrs32[0] + i for i, a in enumerate(addrs32)):
            raw = self.pc10_block_read(addrs32[0], len(devices))
            return list(raw)
        return [self.pc10_block_read(a, 1)[0] for a in addrs32]

    def _read_batch(self, devices: list[ResolvedDevice]) -> list[Any]:
        if not devices:
            return []
        key = _batch_key(devices[0])
        if key == "basic-word":
            return self._read_basic_word_batch(devices)
        if key == "basic-byte":
            return list(self.read_bytes_multi([_require(d.basic_addr, "basic_addr") for d in devices]))
        if key == "ext-word":
            return self._read_ext_word_batch(devices)
        if key == "ext-byte":
            return self._read_ext_byte_batch(devices)
        if key == "ext-bit":
            return self._read_ext_bit_batch(devices)
        if key == "pc10-word":
            return self._read_pc10_word_batch(devices)
        if key == "pc10-bit":
            return [bool(b) for b in _read_pc10_multi_bits(self, [_require(d.addr32, "pc10 addr32") for d in devices])]
        if key == "pc10-byte":
            return self._read_pc10_byte_batch(devices)
        return [self._read_resolved_device(d) for d in devices]

    def _read_runs(self, devices: list[ResolvedDevice], split_pc10: bool) -> list[Any]:
        results: list[Any] = [None] * len(devices)
        idx = 0
        for run in self._get_run_plan(devices, split_pc10):
            batch = self._read_batch(devices[idx : idx + run])
            for j, v in enumerate(batch):
                results[idx + j] = v
            idx += run
        return results

    # ------------------------------------------------------------------
    # Batch-read helpers (relay)
    # ------------------------------------------------------------------

    def _relay_read_basic_word_batch(self, hops: Any, devices: list[ResolvedDevice]) -> list[int]:
        if _is_consecutive_basic(devices):
            start = _require(devices[0].basic_addr, "basic_addr")
            resp = self.send_via_relay(hops, build_word_read(start, len(devices)))
            if resp.cmd != 0x1C:
                raise ToyopucProtocolError("Unexpected CMD in relay word-read response")
            return unpack_u16_le(resp.data)[: len(devices)]
        resp = self.send_via_relay(hops, build_multi_word_read([_require(d.basic_addr, "basic_addr") for d in devices]))
        if resp.cmd != 0x22:
            raise ToyopucProtocolError("Unexpected CMD in relay multi-word-read response")
        return unpack_u16_le(resp.data)[: len(devices)]

    def _relay_read_basic_byte_batch(self, hops: Any, devices: list[ResolvedDevice]) -> list[int]:
        addrs = [_require(d.basic_addr, "basic_addr") for d in devices]
        if _is_consecutive_basic(devices):
            resp = self.send_via_relay(hops, build_byte_read(addrs[0], len(devices)))
            if resp.cmd != 0x1E:
                raise ToyopucProtocolError("Unexpected CMD in relay byte-read response")
            return list(resp.data[: len(devices)])
        resp = self.send_via_relay(hops, build_multi_byte_read(addrs))
        if resp.cmd != 0x24:
            raise ToyopucProtocolError("Unexpected CMD in relay multi-byte-read response")
        return list(resp.data[: len(devices)])

    def _relay_read_ext_word_batch(self, hops: Any, devices: list[ResolvedDevice]) -> list[int]:
        if _is_consecutive_ext_word(devices):
            no = _require(devices[0].no, "no")
            addr = _require(devices[0].addr, "addr")
            resp = self.send_via_relay(hops, build_ext_word_read(no, addr, len(devices)))
            if resp.cmd != 0x94:
                raise ToyopucProtocolError("Unexpected CMD in relay ext-word-read response")
            return unpack_u16_le(resp.data)[: len(devices)]
        resp = self.send_via_relay(
            hops,
            build_ext_multi_read(
                [],
                [],
                [(_require(d.no, "no"), _ext_word_monitor_addr(_require(d.addr, "addr"))) for d in devices],
            ),
        )
        if resp.cmd != 0x98:
            raise ToyopucProtocolError("Unexpected CMD in relay ext multi-read response")
        return unpack_u16_le(resp.data)[: len(devices)]

    def _relay_read_ext_byte_batch(self, hops: Any, devices: list[ResolvedDevice]) -> list[int]:
        no0 = devices[0].no
        if no0 is not None and all(d.no == no0 for d in devices):
            addrs = [_require(d.addr, "addr") for d in devices]
            if all(a == addrs[0] + i for i, a in enumerate(addrs)):
                resp = self.send_via_relay(hops, build_ext_byte_read(no0, addrs[0], len(devices)))
                if resp.cmd != 0x96:
                    raise ToyopucProtocolError("Unexpected CMD in relay ext byte-read response")
                return list(resp.data[: len(devices)])
        resp = self.send_via_relay(
            hops,
            build_ext_multi_read(
                [],
                [(_require(d.no, "no"), _require(d.addr, "addr")) for d in devices],
                [],
            ),
        )
        if resp.cmd != 0x98:
            raise ToyopucProtocolError("Unexpected CMD in relay ext multi-read response")
        return list(resp.data[: len(devices)])

    def _relay_read_ext_bit_batch(self, hops: Any, devices: list[ResolvedDevice]) -> list[bool]:
        bits = [(_require(d.no, "no"), _require(d.bit_no, "bit_no"), _require(d.addr, "addr")) for d in devices]
        resp = self.send_via_relay(hops, build_ext_multi_read(bits, [], []))
        if resp.cmd != 0x98:
            raise ToyopucProtocolError("Unexpected CMD in relay ext-multi-read response")
        return [bool(v) for v in _parse_ext_multi_bit_data(resp.data, len(devices))]

    def _relay_read_pc10_word_batch_by_segments(self, hops: Any, devices: list[ResolvedDevice]) -> list[int]:
        values: list[int] = []
        segment_start = 0
        while segment_start < len(devices):
            segment_len = _pc10_word_segment_length(devices, segment_start)
            start_addr = _require(devices[segment_start].addr32, "pc10 addr32")
            resp = self.send_via_relay(hops, build_pc10_block_read(start_addr, segment_len * 2))
            if resp.cmd != 0xC2:
                raise ToyopucProtocolError("Unexpected CMD in relay PC10 block-read response")
            words = unpack_u16_le(resp.data)
            if len(words) < segment_len:
                raise ToyopucProtocolError("PC10 block-read response too short")
            values.extend(words[:segment_len])
            segment_start += segment_len
        return values

    def _relay_read_pc10_word_batch(self, hops: Any, devices: list[ResolvedDevice]) -> list[int]:
        if _is_consecutive_pc10_word(devices):
            addr32 = _require(devices[0].addr32, "pc10 addr32")
            resp = self.send_via_relay(hops, build_pc10_block_read(addr32, len(devices) * 2))
            if resp.cmd != 0xC2:
                raise ToyopucProtocolError("Unexpected CMD in relay PC10 block-read response")
            expected = len(devices) * 2
            if len(resp.data) != expected:
                raise ToyopucProtocolError(
                    f"Relay PC10 block-read response size mismatch: expected={expected}, actual={len(resp.data)}"
                )
            return [int.from_bytes(resp.data[i * 2 : i * 2 + 2], "little") for i in range(len(devices))]
        if _contains_packed_pc10_word_device(devices):
            return self._relay_read_pc10_word_batch_by_segments(hops, devices)
        payload = _build_pc10_multi_word_read_payload([_require(d.addr32, "pc10 addr32") for d in devices])
        resp = self.send_via_relay(
            hops,
            build_pc10_multi_read(payload),
        )
        if resp.cmd != 0xC4:
            raise ToyopucProtocolError("Unexpected CMD in relay PC10 multi-read response")
        return _parse_pc10_multi_word_data(resp.data, len(devices))

    def _relay_read_pc10_bit_batch(self, hops: Any, devices: list[ResolvedDevice]) -> list[bool]:
        addrs32 = [_require(d.addr32, "pc10 addr32") for d in devices]
        payload = bytearray([len(addrs32) & 0xFF, 0x00, 0x00, 0x00])
        for a in addrs32:
            payload.extend(a.to_bytes(4, "little"))
        resp = self.send_via_relay(hops, build_pc10_multi_read(bytes(payload)))
        if resp.cmd != 0xC4:
            raise ToyopucProtocolError("Unexpected CMD in relay PC10 multi-read response")
        bit_data = resp.data[4:]
        return [bool((bit_data[i // 8] >> (i % 8)) & 0x01) for i in range(len(devices))]

    def _relay_read_pc10_byte_batch(self, hops: Any, devices: list[ResolvedDevice]) -> list[int]:
        addrs32 = [_require(d.addr32, "pc10 addr32") for d in devices]
        if all(a == addrs32[0] + i for i, a in enumerate(addrs32)):
            resp = self.send_via_relay(hops, build_pc10_block_read(addrs32[0], len(devices)))
            if resp.cmd != 0xC2:
                raise ToyopucProtocolError("Unexpected CMD in relay PC10 block-read response")
            if len(resp.data) != len(devices):
                raise ToyopucProtocolError(
                    f"Relay PC10 block-read response size mismatch: expected={len(devices)}, actual={len(resp.data)}"
                )
            return list(resp.data[: len(devices)])
        return [int(self._relay_read_resolved_device(hops, d)) for d in devices]

    def _relay_read_batch(self, hops: Any, devices: list[ResolvedDevice]) -> list[Any]:
        if not devices:
            return []
        key = _batch_key(devices[0])
        if key == "basic-word":
            return self._relay_read_basic_word_batch(hops, devices)
        if key == "basic-byte":
            return self._relay_read_basic_byte_batch(hops, devices)
        if key == "ext-word":
            return self._relay_read_ext_word_batch(hops, devices)
        if key == "ext-byte":
            return self._relay_read_ext_byte_batch(hops, devices)
        if key == "ext-bit":
            return self._relay_read_ext_bit_batch(hops, devices)
        if key == "pc10-word":
            return self._relay_read_pc10_word_batch(hops, devices)
        if key == "pc10-bit":
            return self._relay_read_pc10_bit_batch(hops, devices)
        if key == "pc10-byte":
            return self._relay_read_pc10_byte_batch(hops, devices)
        return [self._relay_read_resolved_device(hops, d) for d in devices]

    def _relay_read_runs(self, hops: Any, devices: list[ResolvedDevice], split_pc10: bool) -> list[Any]:
        results: list[Any] = [None] * len(devices)
        idx = 0
        for run in self._get_run_plan(devices, split_pc10):
            batch = self._relay_read_batch(hops, devices[idx : idx + run])
            for j, v in enumerate(batch):
                results[idx + j] = v
            idx += run
        return results

    # ------------------------------------------------------------------
    # Batch-write helpers
    # ------------------------------------------------------------------

    def _write_basic_word_batch(self, devices: list[ResolvedDevice], values: list[int]) -> None:
        addrs = [_require(d.basic_addr, "basic_addr") for d in devices]
        if _is_consecutive_basic(devices):
            self.write_words(addrs[0], values)
        else:
            self.write_words_multi(list(zip(addrs, values, strict=False)))

    def _write_basic_byte_batch(self, devices: list[ResolvedDevice], values: list[int]) -> None:
        self.write_bytes_multi(
            [(_require(d.basic_addr, "basic_addr"), v) for d, v in zip(devices, values, strict=False)]
        )

    def _write_ext_word_batch(self, devices: list[ResolvedDevice], values: list[int]) -> None:
        if _is_consecutive_ext_word(devices):
            no = _require(devices[0].no, "no")
            addr = _require(devices[0].addr, "addr")
            self.write_ext_words(no, addr, values)
        else:
            self.write_ext_multi(
                [],
                [],
                [
                    (_require(d.no, "no"), _ext_word_monitor_addr(_require(d.addr, "addr")), v)
                    for d, v in zip(devices, values, strict=False)
                ],
            )

    def _write_ext_byte_batch(self, devices: list[ResolvedDevice], values: list[int]) -> None:
        no0 = devices[0].no
        if no0 is not None and all(d.no == no0 for d in devices):
            addrs = [_require(d.addr, "addr") for d in devices]
            if all(a == addrs[0] + i for i, a in enumerate(addrs)):
                self.write_ext_bytes(no0, addrs[0], values)
                return
        self.write_ext_multi(
            [],
            [(_require(d.no, "no"), _require(d.addr, "addr"), v) for d, v in zip(devices, values, strict=False)],
            [],
        )

    def _write_ext_bit_batch(self, devices: list[ResolvedDevice], values: list[int]) -> None:
        self.write_ext_multi(
            [
                (_require(d.no, "no"), _require(d.bit_no, "bit_no"), _require(d.addr, "addr"), v)
                for d, v in zip(devices, values, strict=False)
            ],
            [],
            [],
        )

    def _write_pc10_word_batch(self, devices: list[ResolvedDevice], values: list[int]) -> None:
        if _is_consecutive_pc10_word(devices):
            addr32 = _require(devices[0].addr32, "pc10 addr32")
            data = b"".join(v.to_bytes(2, "little") for v in values)
            self.pc10_block_write(addr32, data)
            return
        self.pc10_multi_write(
            _pack_pc10_multi_word_payload(
                [(_require(d.addr32, "pc10 addr32"), v) for d, v in zip(devices, values, strict=False)]
            )
        )

    def _write_pc10_bit_batch(self, devices: list[ResolvedDevice], values: list[int]) -> None:
        self.pc10_multi_write(
            _pack_pc10_multi_bit_payload(
                [(_require(d.addr32, "pc10 addr32"), v) for d, v in zip(devices, values, strict=False)]
            )
        )

    def _write_pc10_byte_batch(self, devices: list[ResolvedDevice], values: list[int]) -> None:
        addrs32 = [_require(d.addr32, "pc10 addr32") for d in devices]
        if all(a == addrs32[0] + i for i, a in enumerate(addrs32)):
            self.pc10_block_write(addrs32[0], bytes(values))
            return
        for d, v in zip(devices, values, strict=False):
            self._write_resolved_device(d, v)

    def _write_batch(self, devices: list[ResolvedDevice], values: list[Any]) -> None:
        if not devices:
            return
        values = [_normalize_device_value(device, value) for device, value in zip(devices, values, strict=True)]
        key = _batch_key(devices[0])
        if key == "basic-word":
            self._write_basic_word_batch(devices, values)
            return
        if key == "basic-byte":
            self._write_basic_byte_batch(devices, values)
            return
        if key == "ext-word":
            self._write_ext_word_batch(devices, values)
            return
        if key == "ext-byte":
            self._write_ext_byte_batch(devices, values)
            return
        if key == "ext-bit":
            self._write_ext_bit_batch(devices, values)
            return
        if key == "pc10-word":
            self._write_pc10_word_batch(devices, values)
            return
        if key == "pc10-bit":
            self._write_pc10_bit_batch(devices, values)
            return
        if key == "pc10-byte":
            self._write_pc10_byte_batch(devices, values)
            return
        for d, v in zip(devices, values, strict=False):
            self._write_resolved_device(d, v)

    def _write_runs(self, devices: list[ResolvedDevice], values: list[Any], split_pc10: bool) -> None:
        idx = 0
        for run in self._get_run_plan(devices, split_pc10):
            self._write_batch(devices[idx : idx + run], values[idx : idx + run])
            idx += run

    def _relay_write_basic_word_batch(self, hops: Any, devices: list[ResolvedDevice], values: list[int]) -> None:
        if _is_consecutive_basic(devices):
            start = _require(devices[0].basic_addr, "basic_addr")
            resp = self.send_via_relay(hops, build_word_write(start, values))
            if resp.cmd != 0x1D:
                raise ToyopucProtocolError("Unexpected CMD in relay word-write response")
            return
        resp = self.send_via_relay(
            hops,
            build_multi_word_write(
                [(_require(d.basic_addr, "basic_addr"), v) for d, v in zip(devices, values, strict=False)]
            ),
        )
        if resp.cmd != 0x23:
            raise ToyopucProtocolError("Unexpected CMD in relay multi-word-write response")

    def _relay_write_basic_byte_batch(self, hops: Any, devices: list[ResolvedDevice], values: list[int]) -> None:
        addrs = [_require(d.basic_addr, "basic_addr") for d in devices]
        if _is_consecutive_basic(devices):
            resp = self.send_via_relay(hops, build_byte_write(addrs[0], values))
            if resp.cmd != 0x1F:
                raise ToyopucProtocolError("Unexpected CMD in relay byte-write response")
            return
        resp = self.send_via_relay(
            hops,
            build_multi_byte_write(list(zip(addrs, values, strict=False))),
        )
        if resp.cmd != 0x25:
            raise ToyopucProtocolError("Unexpected CMD in relay multi-byte-write response")

    def _relay_write_ext_word_batch(self, hops: Any, devices: list[ResolvedDevice], values: list[int]) -> None:
        if _is_consecutive_ext_word(devices):
            no = _require(devices[0].no, "no")
            addr = _require(devices[0].addr, "addr")
            resp = self.send_via_relay(hops, build_ext_word_write(no, addr, values))
            if resp.cmd != 0x95:
                raise ToyopucProtocolError("Unexpected CMD in relay ext word-write response")
            return
        resp = self.send_via_relay(
            hops,
            build_ext_multi_write(
                [],
                [],
                [
                    (_require(d.no, "no"), _ext_word_monitor_addr(_require(d.addr, "addr")), v)
                    for d, v in zip(devices, values, strict=False)
                ],
            ),
        )
        if resp.cmd != 0x99:
            raise ToyopucProtocolError("Unexpected CMD in relay ext multi-write response")

    def _relay_write_ext_byte_batch(self, hops: Any, devices: list[ResolvedDevice], values: list[int]) -> None:
        no0 = devices[0].no
        if no0 is not None and all(d.no == no0 for d in devices):
            addrs = [_require(d.addr, "addr") for d in devices]
            if all(a == addrs[0] + i for i, a in enumerate(addrs)):
                resp = self.send_via_relay(hops, build_ext_byte_write(no0, addrs[0], values))
                if resp.cmd != 0x97:
                    raise ToyopucProtocolError("Unexpected CMD in relay ext byte-write response")
                return
        resp = self.send_via_relay(
            hops,
            build_ext_multi_write(
                [],
                [(_require(d.no, "no"), _require(d.addr, "addr"), v) for d, v in zip(devices, values, strict=False)],
                [],
            ),
        )
        if resp.cmd != 0x99:
            raise ToyopucProtocolError("Unexpected CMD in relay ext multi-write response")

    def _relay_write_ext_bit_batch(self, hops: Any, devices: list[ResolvedDevice], values: list[int]) -> None:
        resp = self.send_via_relay(
            hops,
            build_ext_multi_write(
                [
                    (_require(d.no, "no"), _require(d.bit_no, "bit_no"), _require(d.addr, "addr"), v)
                    for d, v in zip(devices, values, strict=False)
                ],
                [],
                [],
            ),
        )
        if resp.cmd != 0x99:
            raise ToyopucProtocolError("Unexpected CMD in relay ext multi-write response")

    def _relay_write_pc10_word_batch(self, hops: Any, devices: list[ResolvedDevice], values: list[int]) -> None:
        if _is_consecutive_pc10_word(devices):
            addr32 = _require(devices[0].addr32, "pc10 addr32")
            data = b"".join(v.to_bytes(2, "little") for v in values)
            resp = self.send_via_relay(hops, build_pc10_block_write(addr32, data))
            if resp.cmd != 0xC3:
                raise ToyopucProtocolError("Unexpected CMD in relay PC10 block-write response")
            return
        resp = self.send_via_relay(
            hops,
            build_pc10_multi_write(
                _pack_pc10_multi_word_payload(
                    [(_require(d.addr32, "pc10 addr32"), v) for d, v in zip(devices, values, strict=False)]
                )
            ),
        )
        if resp.cmd != 0xC5:
            raise ToyopucProtocolError("Unexpected CMD in relay PC10 multi-write response")

    def _relay_write_pc10_bit_batch(self, hops: Any, devices: list[ResolvedDevice], values: list[int]) -> None:
        resp = self.send_via_relay(
            hops,
            build_pc10_multi_write(
                _pack_pc10_multi_bit_payload(
                    [(_require(d.addr32, "pc10 addr32"), v) for d, v in zip(devices, values, strict=False)]
                )
            ),
        )
        if resp.cmd != 0xC5:
            raise ToyopucProtocolError("Unexpected CMD in relay PC10 multi-write response")

    def _relay_write_pc10_byte_batch(self, hops: Any, devices: list[ResolvedDevice], values: list[int]) -> None:
        addrs32 = [_require(d.addr32, "pc10 addr32") for d in devices]
        if all(a == addrs32[0] + i for i, a in enumerate(addrs32)):
            resp = self.send_via_relay(hops, build_pc10_block_write(addrs32[0], bytes(values)))
            if resp.cmd != 0xC3:
                raise ToyopucProtocolError("Unexpected CMD in relay PC10 block-write response")
            return
        for d, v in zip(devices, values, strict=False):
            self._relay_write_resolved_device(hops, d, v)

    def _relay_write_batch(self, hops: Any, devices: list[ResolvedDevice], values: list[Any]) -> None:
        if not devices:
            return
        values = [_normalize_device_value(device, value) for device, value in zip(devices, values, strict=True)]
        key = _batch_key(devices[0])
        if key == "basic-word":
            self._relay_write_basic_word_batch(hops, devices, values)
            return
        if key == "basic-byte":
            self._relay_write_basic_byte_batch(hops, devices, values)
            return
        if key == "ext-word":
            self._relay_write_ext_word_batch(hops, devices, values)
            return
        if key == "ext-byte":
            self._relay_write_ext_byte_batch(hops, devices, values)
            return
        if key == "ext-bit":
            self._relay_write_ext_bit_batch(hops, devices, values)
            return
        if key == "pc10-word":
            self._relay_write_pc10_word_batch(hops, devices, values)
            return
        if key == "pc10-bit":
            self._relay_write_pc10_bit_batch(hops, devices, values)
            return
        if key == "pc10-byte":
            self._relay_write_pc10_byte_batch(hops, devices, values)
            return
        for d, v in zip(devices, values, strict=False):
            self._relay_write_resolved_device(hops, d, v)

    def _relay_write_runs(self, hops: Any, devices: list[ResolvedDevice], values: list[Any], split_pc10: bool) -> None:
        idx = 0
        for run in self._get_run_plan(devices, split_pc10):
            self._relay_write_batch(hops, devices[idx : idx + run], values[idx : idx + run])
            idx += run
