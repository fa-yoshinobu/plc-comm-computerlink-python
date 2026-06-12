"""Cross-language spec compliance: TOYOPUC Computer Link protocol vectors.

Each vector in computerlink_frame_vectors.json defines the expected binary
output of a frame-builder function or the expected parsed fields of a response
frame. The same JSON is consumed by the .NET test suite, ensuring Python and
.NET produce identical bytes on the wire.
"""

import json
from pathlib import Path
from typing import Any

import pytest

from toyopuc.protocol import (
    build_bit_read,
    build_bit_write,
    build_byte_read,
    build_clock_read,
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
