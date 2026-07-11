from __future__ import annotations

from typing import TypeVar

T = TypeVar("T")


def _require(value: T | None, label: str) -> T:
    if value is None:
        raise ValueError(f"Resolved device missing {label}")
    return value


def _validate_relay_hop(link: int, station: int) -> tuple[int, int]:
    if isinstance(link, bool) or not isinstance(link, int) or not 0 <= link <= 0xFF:
        raise ValueError("relay link must be an integer in the range 0..255")
    if isinstance(station, bool) or not isinstance(station, int) or not 1 <= station <= 0xFFFF:
        raise ValueError("relay station must be an integer in the range 1..65535")
    return link, station
