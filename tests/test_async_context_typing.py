"""The context manager must retain both concrete client types."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_async_context_retains_concrete_client_types(tmp_path: Path) -> None:
    source = """
from toyopuc import AsyncToyopucClient, AsyncToyopucDeviceClient

async def check(low: AsyncToyopucClient, high: AsyncToyopucDeviceClient) -> None:
    async with low as entered_low:
        typed_low: AsyncToyopucClient = entered_low
    async with high as entered_high:
        typed_high: AsyncToyopucDeviceClient = entered_high
"""
    consumer = tmp_path / "context_consumer.py"
    consumer.write_text(source, encoding="utf-8")
    result = subprocess.run(
        [sys.executable, "-m", "mypy", "--follow-imports=silent", str(consumer)],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
