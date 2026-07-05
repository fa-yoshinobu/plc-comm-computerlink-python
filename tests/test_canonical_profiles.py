"""Tests for canonical TOYOPUC profile fixtures."""

from __future__ import annotations

import json
from pathlib import Path

from toyopuc import ToyopucPlcProfiles, display_name


def _range_to_dict(value) -> dict[str, int]:
    return {"start": value.start, "end": value.end}


def _ranges_to_list(values) -> list[dict[str, int]]:
    return [_range_to_dict(value) for value in values]


def _options_to_dict(options) -> dict[str, bool]:
    return {
        "use_upper_u_pc10": options.use_upper_u_pc10,
        "use_eb_pc10": options.use_eb_pc10,
        "use_fr_pc10": options.use_fr_pc10,
        "use_upper_bit_pc10": options.use_upper_bit_pc10,
        "use_upper_m_bit_pc10": options.use_upper_m_bit_pc10,
    }


def _area_to_dict(area) -> dict[str, object]:
    result: dict[str, object] = {
        "area": area.area,
        "direct_ranges": _ranges_to_list(area.direct_ranges),
        "prefixed_ranges": _ranges_to_list(area.prefixed_ranges),
        "supports_packed_word": area.supports_packed_word,
        "address_width": area.address_width,
        "suggested_start_step": area.suggested_start_step,
    }
    if area.packed_direct_ranges_override is not None:
        result["packed_direct_ranges_override"] = _ranges_to_list(area.packed_direct_ranges_override)
    if area.packed_prefixed_ranges_override is not None:
        result["packed_prefixed_ranges_override"] = _ranges_to_list(area.packed_prefixed_ranges_override)
    return result


def test_embedded_toyopuc_profiles_match_canonical_fixture() -> None:
    fixture = Path(__file__).parent / "fixtures" / "toyopuc_profiles.json"
    expected = json.loads(fixture.read_text(encoding="utf-8"))["profiles"]

    assert ToyopucPlcProfiles.get_names() == list(expected)
    for profile_id, expected_profile in expected.items():
        assert display_name(profile_id) == expected_profile["display_name"]
        actual = ToyopucPlcProfiles.from_name(profile_id)
        assert _options_to_dict(actual.addressing_options) == expected_profile["addressing_options"]
        assert [_area_to_dict(area) for area in actual.areas] == expected_profile["areas"]
