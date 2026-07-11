"""Cross-language spec compliance: TOYOPUC Computer Link protocol vectors.

Each vector in computerlink_frame_vectors.json defines the expected binary
output of a frame-builder function or the expected parsed fields of a response
frame. The same JSON is consumed by the .NET test suite, ensuring Python and
.NET produce identical bytes on the wire.
"""

import inspect
import json
from pathlib import Path
from typing import Any

import pytest

from toyopuc.protocol import (
    ClockData,
    build_bit_read,
    build_bit_write,
    build_byte_read,
    build_clock_read,
    build_command,
    build_cpu_status_read,
    build_cpu_status_read_a0,
    build_ext_multi_read,
    build_ext_multi_write,
    build_multi_word_read,
    build_pc10_block_read,
    build_pc10_multi_read,
    build_scan_resume,
    build_scan_stop,
    build_scan_stop_release,
    build_word_read,
    pack_bcd,
    parse_cpu_status_data_a0,
    parse_response,
)

_VECTORS_PATH = Path(__file__).parent / "vectors" / "computerlink_frame_vectors.json"
_DATA = json.loads(_VECTORS_PATH.read_text())

_FRAME_VECTORS = _DATA["frame_vectors"]
_RESPONSE_VECTORS = _DATA["response_vectors"]
_BCD_VECTORS = _DATA["bcd_vectors"]


def test_clock_datetime_conversion_requires_explicit_century() -> None:
    clock = ClockData(second=3, minute=2, hour=1, day=15, month=3, year_2digit=26, weekday=0)
    assert "year_base" in inspect.signature(clock.as_datetime).parameters
    with pytest.raises(TypeError):
        clock.as_datetime()  # type: ignore[call-arg]
    assert clock.as_datetime(year_base=1900).year == 1926
    assert clock.as_datetime(year_base=2000).year == 2026
    assert clock.as_datetime(year_base=2100).year == 2126
    for invalid in (True, -100, 1950):
        with pytest.raises(ValueError, match="year_base"):
            clock.as_datetime(year_base=invalid)  # type: ignore[arg-type]


@pytest.mark.parametrize("cmd", [-1, 256, 0x11C, True, 1.5])
def test_build_command_rejects_invalid_command_code(cmd: object) -> None:
    with pytest.raises((TypeError, ValueError)):
        build_command(cmd, b"")  # type: ignore[arg-type]


def test_build_command_requires_explicit_bytes_and_valid_length() -> None:
    with pytest.raises(TypeError):
        build_command(0x00, None)  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        build_command(0x00, 3)  # type: ignore[arg-type]
    assert build_command(0x00, b"") == bytes.fromhex("0000010000")
    assert len(build_command(0xFF, bytes(65_534))) == 65_539
    with pytest.raises(ValueError, match="too large"):
        build_command(0xFF, bytes(65_535))


def _build_frame(vec: dict[str, Any]) -> bytes:
    fn = vec["function"]
    if fn == "build_clock_read":
        return build_clock_read()
    if fn == "build_cpu_status_read":
        return build_cpu_status_read()
    if fn == "build_word_read":
        return build_word_read(vec["addr"], vec["count"])
    if fn == "build_byte_read":
        return build_byte_read(vec["addr"], vec["count"])
    if fn == "build_bit_read":
        return build_bit_read(vec["addr"])
    if fn == "build_bit_write":
        return build_bit_write(vec["addr"], vec["value"])
    raise ValueError(f"Unknown function: {fn}")


@pytest.mark.parametrize("vec", _FRAME_VECTORS, ids=lambda v: v["id"])
def test_frame_build(vec: dict[str, Any]) -> None:
    result = _build_frame(vec)
    expected = bytes.fromhex(vec["hex"])
    assert result == expected, f"[{vec['id']}] got {result.hex()}, expected {vec['hex']}"


def test_scan_control_frame_builders() -> None:
    assert build_scan_resume() == bytes([0x00, 0x00, 0x03, 0x00, 0x32, 0x01, 0x00])
    assert build_scan_stop() == bytes([0x00, 0x00, 0x04, 0x00, 0x32, 0x02, 0x00, 0x01])
    assert build_scan_stop_release() == bytes([0x00, 0x00, 0x04, 0x00, 0x32, 0x02, 0x00, 0x00])


def test_a0_cpu_status_frame_and_parse() -> None:
    assert build_cpu_status_read_a0() == bytes([0x00, 0x00, 0x04, 0x00, 0xA0, 0x00, 0x11, 0x00])
    status = parse_cpu_status_data_a0(bytes([0x00, 0x11, 0x00, 0x42, 0, 0, 0, 0, 0, 0, 0]))
    assert status.raw_bytes == bytes([0x42, 0, 0, 0, 0, 0, 0, 0])


def test_protocol_builders_reject_over_limit_single_frame_requests() -> None:
    with pytest.raises(ValueError, match="CMD=1C"):
        build_word_read(0x0000, 0x0201)
    with pytest.raises(ValueError, match="CMD=22"):
        build_multi_word_read(range(0x0081))
    with pytest.raises(ValueError, match="CMD=98 response data"):
        build_ext_multi_read([], [], [(0x01, i * 2) for i in range(65)])
    with pytest.raises(ValueError, match="CMD=99 write data"):
        build_ext_multi_write([(0x01, 0, i, 1) for i in range(129)], [], [])
    with pytest.raises(ValueError, match="CMD=C2"):
        build_pc10_block_read(0x00000000, 0x03F1)
    with pytest.raises(ValueError, match="block boundary"):
        build_pc10_block_read(0x0000FFFE, 4)
    with pytest.raises(ValueError, match="CMD=C4"):
        build_pc10_multi_read(bytes(0x0201))


@pytest.mark.parametrize("vec", _RESPONSE_VECTORS, ids=lambda v: v["id"])
def test_response_parse(vec: dict[str, Any]) -> None:
    raw = bytes.fromhex(vec["hex"])
    frame = parse_response(raw)
    assert frame.ft == vec["ft"], f"[{vec['id']}] ft mismatch"
    assert frame.rc == vec["rc"], f"[{vec['id']}] rc mismatch"
    assert frame.cmd == vec["cmd"], f"[{vec['id']}] cmd mismatch"
    assert frame.data == bytes.fromhex(vec["data_hex"]), f"[{vec['id']}] data mismatch"


@pytest.mark.parametrize("vec", _BCD_VECTORS, ids=lambda v: f"bcd_{v['value']}")
def test_pack_bcd(vec: dict[str, Any]) -> None:
    result = pack_bcd(vec["value"])
    assert result == vec["bcd_decimal"], f"pack_bcd({vec['value']}) = {result}, expected {vec['bcd_decimal']}"
