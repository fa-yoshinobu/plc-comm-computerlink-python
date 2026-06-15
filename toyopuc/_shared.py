from __future__ import annotations

from typing import TypeVar

T = TypeVar("T")


def _require(value: T | None, label: str) -> T:
    if value is None:
        raise ValueError(f"Resolved device missing {label}")
    return value
