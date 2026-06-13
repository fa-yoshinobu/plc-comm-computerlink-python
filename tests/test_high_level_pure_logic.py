from dataclasses import replace

import pytest

from toyopuc.errors import ToyopucProtocolError
from toyopuc.high_level import (
    ResolvedDevice,
    _batch_key,
    _batch_run_length,
    _build_pc10_multi_word_read_payload,
    _contains_packed_pc10_word_device,
    _is_consecutive_basic,
    _is_consecutive_ext_word,
    _is_consecutive_pc10_word,
    _pack_pc10_multi_bit_payload,
    _pack_pc10_multi_word_payload,
    _parse_ext_multi_bit_data,
    _parse_pc10_multi_word_data,
    _pc10_block,
    _pc10_word_segment_length,
    _raise_generic_fr_write_error,
    resolve_device as _resolve_device,
)

GENERIC_PROFILE = "toyopuc:generic"


def resolve_device(device: str, **kwargs):
    kwargs.setdefault("profile", GENERIC_PROFILE)
    return _resolve_device(device, **kwargs)


def _devices(names: list[str]) -> list[ResolvedDevice]:
    return [resolve_device(name) for name in names]


def test_pc10_multi_bit_payload_packs_addresses_and_bit_values() -> None:
    payload = _pack_pc10_multi_bit_payload(
        [
            (0x00100000, 1),
            (0x00100001, 0),
            (0x00100002, 1),
            (0x00400000, 1),
            (0x00400001, 0),
            (0x00400002, 1),
            (0x00400003, 0),
            (0x00400004, 1),
            (0x00400005, 1),
        ]
    )

    assert payload == bytes.fromhex(
        "09 00 00 00"
        "00 00 10 00"
        "01 00 10 00"
        "02 00 10 00"
        "00 00 40 00"
        "01 00 40 00"
        "02 00 40 00"
        "03 00 40 00"
        "04 00 40 00"
        "05 00 40 00"
        "ad 01"
    )


def test_pc10_multi_word_payloads_pack_counts_addresses_and_values() -> None:
    assert _build_pc10_multi_word_read_payload([0x00100000, 0x00100002, 0x00400000]) == bytes.fromhex(
        "00 00 03 0000 00 10 0002 00 10 0000 00 40 00"
    )

    assert _pack_pc10_multi_word_payload(
        [(0x00100000, 0x1234), (0x00100002, 0xFFFF), (0x00400000, 0x10000), (0x00400002, -1)]
    ) == bytes.fromhex("00 00 04 0000 00 10 0002 00 10 0000 00 40 0002 00 40 0034 12 ff ff 00 00 ff ff")


def test_pc10_payload_helpers_reject_count_wrap_and_oversized_writes() -> None:
    with pytest.raises(ValueError, match="CMD=C4"):
        _build_pc10_multi_word_read_payload([0x00100000] * 0x80)
    with pytest.raises(ValueError, match="CMD=C5"):
        _pack_pc10_multi_word_payload([(0x00100000, 0)] * 85)
    with pytest.raises(ValueError, match="CMD=C5"):
        _pack_pc10_multi_bit_payload([(0x00100000 + i, 1) for i in range(124)])


def test_pc10_multi_response_parsers_keep_current_bit_and_word_layout() -> None:
    assert _parse_ext_multi_bit_data(bytes([0b10101101, 0b00000010]), 10) == [1, 0, 1, 1, 0, 1, 0, 1, 0, 1]
    assert _parse_pc10_multi_word_data(bytes.fromhex("aa bb cc dd 34 12 ff ff 00 00"), 3) == [
        0x1234,
        0xFFFF,
        0,
    ]

    with pytest.raises(ToyopucProtocolError, match="Extended multi-bit response too short"):
        _parse_ext_multi_bit_data(b"", 1)
    with pytest.raises(ToyopucProtocolError, match="PC10 multi-word response too short"):
        _parse_pc10_multi_word_data(b"\x00\x00\x00\x00\x34", 1)


def test_batch_run_length_groups_by_scheme_and_pc10_block_boundary() -> None:
    mixed = _devices(["P1-D0000", "P1-D0001", "P1-M0000", "P1-M0001", "ES0000"])
    assert [_batch_key(device) for device in mixed] == ["ext-word", "ext-word", "ext-bit", "ext-bit", "ext-word"]
    assert [_batch_run_length(mixed, index, split_pc10=True) for index in range(len(mixed))] == [2, 1, 2, 1, 1]

    boundary = _devices(["EBFFFF", "EB10000", "EB10001"])
    assert [_pc10_block(device) for device in boundary] == [17, 18, 18]
    assert [_batch_run_length(boundary, index, split_pc10=True) for index in range(len(boundary))] == [1, 2, 1]
    assert [_batch_run_length(boundary, index, split_pc10=False) for index in range(len(boundary))] == [3, 2, 1]


def test_consecutive_detectors_cover_basic_ext_pc10_and_fr_cases() -> None:
    assert _is_consecutive_basic(_devices(["B0000", "B0001", "B0002"]))
    assert not _is_consecutive_basic(_devices(["B0000", "B0002", "B0003"]))

    assert _is_consecutive_ext_word(_devices(["P1-D0000", "P1-D0001", "P1-D0002"]))
    assert _is_consecutive_ext_word(_devices(["ES0000", "ES0001"]))
    assert not _is_consecutive_ext_word(_devices(["P1-D0000", "P2-D0001"]))

    assert _is_consecutive_pc10_word(_devices(["EBFFFF", "EB10000", "EB10001"]))
    assert _is_consecutive_pc10_word(_devices(["FR0000", "FR0001"]))
    assert _pc10_word_segment_length(_devices(["FR0000", "FR0001"]), 0) == 2


def test_packed_pc10_word_detector_and_fr_guard_message() -> None:
    packed_pc10_word = ResolvedDevice(
        text="synthetic",
        scheme="pc10-word",
        unit="word",
        area="EB",
        index=0,
        packed=True,
        addr32=0x00100000,
    )
    plain_pc10_word = replace(packed_pc10_word, packed=False)

    assert _contains_packed_pc10_word_device([packed_pc10_word])
    assert not _contains_packed_pc10_word_device([plain_pc10_word])

    with pytest.raises(
        ValueError,
        match=r"Generic FR writes are disabled; use write_fr\(..., commit=False\|True\) or commit_fr\(\) explicitly",
    ):
        _raise_generic_fr_write_error()
