# Python Bit-Device Derived Access Migration Checklist

This note is intended to be copied into a Python-side issue or PR description.

It covers the hardware manual rule that derived `W` / `L` / `H` notation for
bit-device families uses one fewer hex digit than the bit form.

Examples:

- `GMFFFF` -> `GMFFFW`, `GMFFFL`, `GMFFFH`
- `M17FF` -> `M17FW`, `M17FL`, `M17FH`
- `EP0FFF` -> `EP0FFW`, `EP0FFL`, `EP0FFH`

Related matrix:

- [PYTHON_PYTEST_CASE_MATRIX.md](d:/Github/toyopucdriver/docs/internal/PYTHON_PYTEST_CASE_MATRIX.md)

## Issue Template

### Summary

Python packed-word handling still assumes the same address width and range as
bit-device notation. This is not correct for TOYOPUC manual notation.

Derived notation for bit-device families must:

- use one fewer hex digit than the bit form
- validate against derived ranges, not bit ranges
- format canonical device strings with derived width

### Scope

Families affected:

- basic bit: `P`, `K`, `V`, `T`, `C`, `L`, `X`, `Y`, `M`
- ext bit: `EP`, `EK`, `EV`, `ET`, `EC`, `EL`, `EX`, `EY`, `EM`, `GM`, `GX`, `GY`

Examples of correct behavior:

- `GMFFFF` is valid bit notation
- `GMFFFW` is valid word notation
- `GMFFFL` is valid byte notation
- `GM1000W` must be rejected
- `GM1000L` must be rejected
- `M17FF` is valid bit notation
- `M17FW` is valid word notation
- `M17FL` is valid byte notation
- `M0000W` must be rejected
- `M0000L` must be rejected

### Required Changes

- [ ] Preserve input hex digit count when parsing device strings.
- [ ] Add derived `W` / `L` / `H` width separate from bit width for bit-device families.
- [ ] Add derived `W` / `L` / `H` ranges separate from bit ranges for bit-device families.
- [ ] Reject derived forms written with bit-width notation.
- [ ] Update canonical formatting to emit derived width.
- [ ] Update any UI/dropdown/device suggestion logic to use derived width.
- [ ] Update round-trip tests to use manual derived notation.
- [ ] Add explicit negative tests for over-width derived forms.

### Acceptance Criteria

- [ ] `GMFFFW` resolves successfully.
- [ ] `GMFFFL` resolves successfully.
- [ ] `GM1000W` is rejected.
- [ ] `GM1000L` is rejected.
- [ ] `M17FW` resolves successfully.
- [ ] `M17FL` resolves successfully.
- [ ] `M0000W` is rejected.
- [ ] `M0000L` is rejected.
- [ ] `EP0FFW` resolves successfully.
- [ ] `EP0FFL` resolves successfully.
- [ ] `EP0000W` is rejected.
- [ ] `EP0000L` is rejected.
- [ ] Formatting code does not emit `*0000W` or `*0000L` style bit-width forms.
- [ ] Derived validation does not reuse bit-device end ranges directly.

## PR Checklist

### Parser

- [ ] The parser records the original digit count for the numeric part.
- [ ] Derived parsing keeps `W` / `L` / `H` semantics but validates the shorter width.
- [ ] Prefixed forms such as `P1-M17FW` follow the same width rule.

### Model

- [ ] Descriptor/profile data can express derived width separately.
- [ ] Descriptor/profile data can express derived ranges separately.
- [ ] Default derivation for derived ranges is documented if generated from bit ranges.

### Validation

- [ ] Range checks for `W` / `L` / `H` use derived ranges.
- [ ] Width checks for `W` / `L` / `H` use derived width.
- [ ] Error messages clearly distinguish width/range failures from unsupported areas.

### Formatting

- [ ] Canonical formatter emits manual derived notation.
- [ ] Windowing, monitor, dump, or logging code does not expand derived addresses to bit width.
- [ ] Suggested addresses for derived devices use derived width.

### Tests

- [ ] Positive tests added for boundary derived devices.
- [ ] Negative tests added for one-digit-too-wide derived devices.
- [ ] Round-trip tests added for parse -> resolve -> format.
- [ ] Profile-specific tests cover any model-specific derived-access limits.

### Documentation

- [ ] User-facing docs explain that bit and derived notation use different widths.
- [ ] Developer docs explain that derived access is not "bit range + suffix".

## Additional Python Remaining Tasks

These are adjacent Python-side follow-up items that came out of the same
validation and profile cleanup work.

### Profile-Enforced Basic Families

When a reviewed profile is active, `P/K/V/T/C/L/X/Y/M/S/N/R/D` should be
treated as prefixed-only.

Required changes:

- [ ] Profile-backed resolver rejects unprefixed `D0000`, `M0000`, `D0000L`, `M000W`.
- [ ] Profile-backed resolver accepts `P1-D0000`, `P1-M0000`, `P1-D0000L`, `P1-M000W`.
- [ ] Profile matrix/catalog marks `P/K/V/T/C/L/X/Y/M/S/N/R/D` as prefixed-only.
- [ ] Validation scripts and sample commands use `P1-*`, `P2-*`, or `P3-*` when a profile is supplied.

Acceptance criteria:

- [ ] Under a profile, `D0000` is rejected.
- [ ] Under a profile, `M0000` is rejected.
- [ ] Under a profile, `P1-D0000` resolves successfully.
- [ ] Under a profile, `P1-M0000` resolves successfully.

### `GX` / `GY` Naming

Synthetic area names such as `GXY` should not exist in the Python port.

Required changes:

- [ ] Remove any internal `GXY` normalization or canonical formatting.
- [ ] Keep `GX` and `GY` explicit in parser, resolver, and formatting code.
- [ ] Keep target-specific alias behavior documented as runtime behavior, not as a synthetic area name.

Acceptance criteria:

- [ ] `GX000W` resolves as area `GX`.
- [ ] `GY000W` resolves as area `GY`.
- [ ] No parser, formatter, or round-trip path emits `GXY`.
