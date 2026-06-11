from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol, TypeVar

T = TypeVar("T")


class _BatchDevice(Protocol):
    @property
    def scheme(self) -> str: ...

    @property
    def unit(self) -> str: ...

    @property
    def packed(self) -> bool: ...

    @property
    def basic_addr(self) -> int | None: ...

    @property
    def no(self) -> int | None: ...

    @property
    def addr(self) -> int | None: ...

    @property
    def addr32(self) -> int | None: ...


def _require(value: T | None, label: str) -> T:
    if value is None:
        raise ValueError(f"Resolved device missing {label}")
    return value


_SCHEME_BATCH_KEY: dict[str, str] = {
    "basic-word": "basic-word",
    "basic-byte": "basic-byte",
    "ext-word": "ext-word",
    "program-word": "ext-word",
    "ext-byte": "ext-byte",
    "program-byte": "ext-byte",
    "ext-bit": "ext-bit",
    "program-bit": "ext-bit",
    "pc10-bit": "pc10-bit",
    "pc10-word": "pc10-word",
    "pc10-byte": "pc10-byte",
}


def _batch_key(resolved: _BatchDevice) -> str | None:
    return _SCHEME_BATCH_KEY.get(resolved.scheme)


def _pc10_block(resolved: _BatchDevice) -> int | None:
    if resolved.addr32 is not None and resolved.scheme in (
        "pc10-bit",
        "pc10-word",
        "pc10-byte",
    ):
        return resolved.addr32 >> 16
    return None


def _batch_run_length(devices: Sequence[_BatchDevice], start: int, split_pc10: bool) -> int:
    key = _batch_key(devices[start])
    if key is None:
        return 1
    pc10_blk = _pc10_block(devices[start]) if split_pc10 else None
    idx = start + 1
    while idx < len(devices):
        if _batch_key(devices[idx]) != key:
            break
        if split_pc10 and _pc10_block(devices[idx]) != pc10_blk:
            break
        idx += 1
    return idx - start


def _is_consecutive_basic(devices: Sequence[_BatchDevice], step: int = 1) -> bool:
    if not devices:
        return True
    start = devices[0].basic_addr
    if start is None:
        return False
    return all(d.basic_addr == start + i * step for i, d in enumerate(devices))


def _is_consecutive_ext_word(devices: Sequence[_BatchDevice]) -> bool:
    if not devices:
        return True
    no0 = devices[0].no
    addr0 = devices[0].addr
    if no0 is None or addr0 is None:
        return False
    return all(d.no == no0 and d.addr == addr0 + i for i, d in enumerate(devices))


def _is_consecutive_pc10_word(devices: Sequence[_BatchDevice]) -> bool:
    if not devices:
        return True
    a0 = devices[0].addr32
    if a0 is None:
        return False
    return all(d.addr32 == a0 + i * 2 for i, d in enumerate(devices))


def _contains_packed_pc10_word_device(devices: Sequence[_BatchDevice]) -> bool:
    return any(d.scheme == "pc10-word" and d.unit == "word" and d.packed for d in devices)


def _pc10_word_segment_length(devices: Sequence[_BatchDevice], start: int) -> int:
    a0 = _require(devices[start].addr32, "pc10 addr32")
    run = 1
    while start + run < len(devices):
        if _require(devices[start + run].addr32, "pc10 addr32") != a0 + run * 2:
            break
        run += 1
    return run
