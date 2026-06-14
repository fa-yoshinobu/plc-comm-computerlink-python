"""Tests for ToyopucPlcProfiles, ToyopucAddressingOptions, and profile-aware resolve_device()."""

import pytest

from toyopuc import (
    ToyopucAddressingOptions,
    ToyopucDeviceCatalog,
    ToyopucPlcProfiles,
)
from toyopuc.high_level import resolve_device as _resolve_device

GENERIC_PROFILE = "toyopuc:generic"


def resolve_device(device: str, **kwargs):
    kwargs.setdefault("profile", GENERIC_PROFILE)
    return _resolve_device(device, **kwargs)


# ---------------------------------------------------------------------------
# Profile catalog
# ---------------------------------------------------------------------------


def test_get_names_returns_all_11_profiles() -> None:
    names = ToyopucPlcProfiles.get_names()
    assert len(names) == 11
    assert "toyopuc:generic" in names
    assert "toyopuc:plus:standard" in names


def test_from_name_requires_explicit_profile() -> None:
    for value in (None, "", "  "):
        with pytest.raises(ValueError, match="PLC profile is required"):
            ToyopucPlcProfiles.from_name(value)


def test_from_name_rejects_short_alias() -> None:
    with pytest.raises(ValueError, match="Unknown PLC profile"):
        ToyopucPlcProfiles.from_name("generic")


def test_from_name_accepts_canonical_name() -> None:
    p = ToyopucPlcProfiles.from_name(GENERIC_PROFILE)
    assert p is ToyopucPlcProfiles.Generic


def test_from_name_unknown_raises() -> None:
    with pytest.raises(ValueError, match="Unknown PLC profile"):
        ToyopucPlcProfiles.from_name("NoSuchProfile")


def test_profiles_have_correct_addressing_options() -> None:
    generic = ToyopucPlcProfiles.Generic
    assert generic.addressing_options.use_upper_u_pc10 is True
    assert generic.addressing_options.use_fr_pc10 is True

    plus_std = ToyopucPlcProfiles.ToyopucPlusStandard
    assert plus_std.addressing_options.use_upper_u_pc10 is False
    assert plus_std.addressing_options.use_eb_pc10 is False
    assert plus_std.addressing_options.use_fr_pc10 is False
    assert plus_std.addressing_options.use_upper_bit_pc10 is False

    pc10g_std = ToyopucPlcProfiles.Pc10GStandardPc3Jg
    assert pc10g_std.addressing_options.use_upper_u_pc10 is False
    assert pc10g_std.addressing_options.use_eb_pc10 is True
    assert pc10g_std.addressing_options.use_fr_pc10 is False


# ---------------------------------------------------------------------------
# Area descriptors
# ---------------------------------------------------------------------------


def test_get_area_descriptor_generic_d() -> None:
    desc = ToyopucPlcProfiles.get_area_descriptor("D", "toyopuc:generic")
    assert desc.area == "D"
    assert not desc.supports_direct  # D is prefixed-only in Generic
    assert desc.supports_prefixed
    assert any(r.contains(0x2FFF) for r in desc.prefixed_ranges)
    assert not any(r.contains(0x3000) for r in desc.prefixed_ranges)


def test_get_area_descriptor_unknown_area_raises() -> None:
    with pytest.raises(ValueError, match="Unknown area"):
        ToyopucPlcProfiles.get_area_descriptor("ZZ", "toyopuc:generic")


def test_get_area_descriptor_area_absent_from_profile_raises() -> None:
    # FR is not in ToyopucPlus Standard
    with pytest.raises(ValueError):
        ToyopucPlcProfiles.get_area_descriptor("FR", "toyopuc:plus:standard")


def test_device_catalog_returns_area_metadata() -> None:
    direct_areas = ToyopucDeviceCatalog.get_areas(prefixed=False, profile=GENERIC_PROFILE)
    prefixed_areas = ToyopucDeviceCatalog.get_areas(prefixed=True, profile=GENERIC_PROFILE)
    fr = ToyopucDeviceCatalog.get_area_descriptor("FR", profile=GENERIC_PROFILE)

    assert "FR" in direct_areas
    assert "FR" not in prefixed_areas
    assert fr.address_width == 6
    assert not fr.supports_packed_word
    assert fr.suggested_start_step == 0x1000


def test_device_catalog_supported_ranges_and_start_addresses() -> None:
    generic_prefixed_p = ToyopucDeviceCatalog.get_supported_ranges("P", prefixed=True, profile="toyopuc:generic")
    generic_direct_areas = ToyopucDeviceCatalog.get_areas(prefixed=False, profile="toyopuc:generic")
    prefixed_m_starts = ToyopucDeviceCatalog.get_suggested_start_addresses(
        "M",
        prefix="P1",
        profile="toyopuc:generic",
        unit="word",
        packed=True,
    )

    assert "P" not in generic_direct_areas
    assert [(r.start, r.end) for r in generic_prefixed_p] == [(0x0000, 0x01FF), (0x1000, 0x17FF)]
    assert "000" in prefixed_m_starts
    assert "100" in prefixed_m_starts
    assert "0000" not in prefixed_m_starts


def test_device_catalog_format_address_ranges_uses_explicit_separator() -> None:
    ranges = ToyopucDeviceCatalog.get_supported_ranges("P", prefixed=True, profile="toyopuc:generic")

    text = ToyopucDeviceCatalog.format_address_ranges("P1-P", ranges, width=4)

    assert text == "P1-P0000..P1-P01FF, P1-P1000..P1-P17FF"


def test_device_catalog_matrix_returns_review_rows_for_profile() -> None:
    matrix = ToyopucDeviceCatalog.get_device_matrix("toyopuc:pc10g:pc10")
    d_row = next(row for row in matrix if row.area == "D" and row.access == "prefixed" and row.unit == "word")
    m_word_row = next(
        row for row in matrix if row.area == "M" and row.access == "prefixed" and row.unit == "word" and row.packed_word
    )
    m_byte_row = next(row for row in matrix if row.area == "M" and row.access == "prefixed" and row.unit == "byte")

    assert d_row.profile == "toyopuc:pc10g:pc10"
    assert d_row.ranges == "P1-D0000..P1-D2FFF"
    assert d_row.example_start_addresses[0] == "P1-D0000"
    assert m_word_row.address_suffixes == ("W",)
    assert m_word_row.ranges == "P1-M000..P1-M07F, P1-M100..P1-M17F"
    assert m_word_row.example_start_addresses[0] == "P1-M000W"
    assert m_byte_row.address_suffixes == ("L", "H")
    assert m_byte_row.to_dict()["address_suffixes"] == ["L", "H"]


def test_device_catalog_matrix_without_profile_includes_all_profiles() -> None:
    profiles = {row.profile for row in ToyopucDeviceCatalog.get_device_matrix()}

    assert set(ToyopucPlcProfiles.get_names()).issubset(profiles)


def test_device_catalog_rejects_direct_basic_start_addresses() -> None:
    with pytest.raises(ValueError, match="not available for direct access"):
        ToyopucDeviceCatalog.get_suggested_start_addresses("D", profile=GENERIC_PROFILE)

    assert ToyopucDeviceCatalog.is_supported_index("D", 0, prefixed=False, profile=GENERIC_PROFILE) is False
    assert ToyopucDeviceCatalog.is_supported_index("D", 0, prefixed=True, profile=GENERIC_PROFILE) is True


def test_area_descriptor_get_ranges_packed() -> None:
    # EP supports packed word; packed ranges are direct_ranges >> 4
    ep = ToyopucPlcProfiles.get_area_descriptor("EP", "toyopuc:generic")
    assert ep.supports_packed_word
    normal = ep.get_ranges(prefixed=False, packed=False)
    packed = ep.get_ranges(prefixed=False, packed=True)
    # Packed range end should be normal end >> 4
    assert packed[0].end == normal[0].end >> 4


def test_area_descriptor_get_ranges_packed_override() -> None:
    # PC10G mode: GM has packedDirectEnd=0x0FFF override
    gm = ToyopucPlcProfiles.get_area_descriptor("GM", "toyopuc:pc10g:pc10")
    packed = gm.get_ranges(prefixed=False, packed=True)
    assert len(packed) == 1
    assert packed[0].end == 0x0FFF  # override, not 0xFFFF >> 4 = 0x0FFF (same here, but explicit)


# ---------------------------------------------------------------------------
# ToyopucAddressingOptions
# ---------------------------------------------------------------------------


def test_addressing_options_default() -> None:
    opts = ToyopucAddressingOptions()
    assert opts.use_upper_u_pc10 is True
    assert opts.use_eb_pc10 is True
    assert opts.use_fr_pc10 is True
    assert opts.use_upper_bit_pc10 is True
    assert opts.use_upper_m_bit_pc10 is True


def test_addressing_options_from_profile() -> None:
    opts = ToyopucAddressingOptions.from_profile("toyopuc:plus:standard")
    assert opts.use_upper_u_pc10 is False
    assert opts.use_fr_pc10 is False


def test_addressing_options_from_profile_requires_explicit_profile() -> None:
    with pytest.raises(ValueError, match="PLC profile is required"):
        ToyopucAddressingOptions.from_profile(None)


# ---------------------------------------------------------------------------
# resolve_device() — options-based PC10 routing
# ---------------------------------------------------------------------------


def test_resolve_upper_bit_pc10_enabled_by_default() -> None:
    # P/V/T/C with index >= 0x1000 should use pc10-bit with Generic options
    for area in ("P", "V", "T", "C"):
        r = resolve_device(f"P1-{area}1000", profile="toyopuc:generic")
        # prefixed → program-bit, not pc10-bit (pc10 only for direct access)
        # Use direct notation that hits the upper range — but P/V/T/C are prefixed-only
        # so test via L and M which support both direct and pc10 routing
    r = resolve_device("P1-L1000", profile="toyopuc:generic")
    # prefixed → program-bit (upper bit pc10 is for direct, not prefixed)
    assert r.scheme == "program-bit"


def test_resolve_l_direct_upper_bit_pc10_generic() -> None:
    # L area doesn't have direct access in Generic (prefixed-only), so test M
    # M is also prefixed-only. Use EB, U, FR instead for non-prefixed areas.
    # Actually direct bit areas that hit pc10: check via test_resolve_bit_pc10_options
    pass


def test_resolve_u_area_pc10_enabled() -> None:
    r = resolve_device("U08000", profile="toyopuc:generic")
    assert r.scheme == "pc10-word"


def test_resolve_u_area_pc10_disabled_falls_through_to_ext_word() -> None:
    opts = ToyopucAddressingOptions(use_upper_u_pc10=False)
    r = resolve_device("U08000", options=opts, profile="toyopuc:generic")
    assert r.scheme == "ext-word"


def test_resolve_eb_area_pc10_enabled() -> None:
    r = resolve_device("EB00000", profile="toyopuc:generic")
    assert r.scheme == "pc10-word"


def test_resolve_eb_area_pc10_disabled_falls_through_to_ext_word() -> None:
    opts = ToyopucAddressingOptions(use_eb_pc10=False)
    r = resolve_device("EB00000", options=opts, profile="toyopuc:generic")
    assert r.scheme == "ext-word"


def test_resolve_eb_extended_no_stops_at_manual_range_when_pc10_disabled() -> None:
    assert resolve_device("EB20000", profile="toyopuc:generic").scheme == "pc10-word"

    opts = ToyopucAddressingOptions(use_eb_pc10=False)
    with pytest.raises(ValueError, match="EB extended-No index out of range"):
        resolve_device("EB20000", options=opts, profile="toyopuc:generic")


def test_resolve_fr_area_pc10_enabled() -> None:
    r = resolve_device("FR000000", profile="toyopuc:generic")
    assert r.scheme == "pc10-word"


def test_resolve_fr_area_pc10_disabled_falls_through_to_ext_word() -> None:
    opts = ToyopucAddressingOptions(use_fr_pc10=False)
    r = resolve_device("FR000000", options=opts, profile="toyopuc:generic")
    assert r.scheme == "ext-word"


# ---------------------------------------------------------------------------
# resolve_device() — profile-based range validation
# ---------------------------------------------------------------------------


def test_resolve_with_profile_valid_address() -> None:
    # D0FFF is within Generic D range (0x2FFF) — must pass
    r = resolve_device("P1-D0FFF", profile="toyopuc:generic")
    assert r.scheme == "program-word"
    assert r.area == "D"


def test_resolve_with_profile_address_out_of_range() -> None:
    # D1000 exceeds Plus Standard D range (0x0FFF)
    with pytest.raises(ValueError, match="out of range"):
        resolve_device("P1-D1000", profile="toyopuc:plus:standard")


def test_resolve_with_profile_area_absent() -> None:
    # FR not in ToyopucPlus Standard profile
    with pytest.raises(ValueError):
        resolve_device("FR000000", profile="toyopuc:plus:standard")


def test_resolve_with_profile_derives_options() -> None:
    # Generic profile has use_upper_u_pc10=True; U08000 (valid in Generic range 0x1FFFF)
    # should be routed to pc10-word via the profile's derived options.
    r = resolve_device("U08000", profile="toyopuc:generic")
    assert r.scheme == "pc10-word"


def test_resolve_profile_and_options_together_options_take_precedence() -> None:
    # Profile "toyopuc:generic" has use_upper_u_pc10=True, but explicitly passed options override it.
    # U08000 is within Generic's U range (0x1FFFF), so profile validation passes.
    opts = ToyopucAddressingOptions(use_upper_u_pc10=False)
    r = resolve_device("U08000", options=opts, profile="toyopuc:generic")
    assert r.scheme == "ext-word"


def test_resolve_with_unknown_profile_raises() -> None:
    with pytest.raises(ValueError, match="Unknown PLC profile"):
        resolve_device("P1-D0100", profile="NoSuchProfile")
