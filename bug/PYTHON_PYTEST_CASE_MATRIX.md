# Python `pytest` Case Matrix

This note turns the current .NET-side findings into concrete Python-side
`pytest` cases.

Use it together with:

- [PYTHON_PORTING_NOTES.md](d:/Github/toyopucdriver/docs/internal/PYTHON_PORTING_NOTES.md)
- [PYTHON_DERIVED_ACCESS_CHECKLIST.md](d:/Github/toyopucdriver/docs/internal/PYTHON_DERIVED_ACCESS_CHECKLIST.md)

## Recommended Test Files

- `tests/test_profile_prefixed_only.py`
- `tests/test_derived_access_width.py`
- `tests/test_gx_gy_naming.py`

If the Python repository already has a different layout, keep the existing
layout and only reuse the case matrix below.

## 1. Profile-Enforced Prefixed-Only Cases

Use a shared profile list that includes every reviewed profile where
`P/K/V/T/C/L/X/Y/M/S/N/R/D` exists.

Recommended profile parameter set:

- `Generic`
- `TOYOPUC-Plus:Plus Standard mode`
- `TOYOPUC-Plus:Plus Extended mode`
- `Nano 10GX:Nano 10GX mode`
- `Nano 10GX:Compatible mode`
- `PC10G:PC10 standard/PC3JG mode`
- `PC10G:PC10 mode`
- `PC3JX:PC3 separate mode`
- `PC3JX:Plus expansion mode`
- `PC3JG:PC3JG mode`
- `PC3JG:PC3 separate mode`

### Accept Cases

| test id | profile | device | expected |
| --- | --- | --- | --- |
| `prefixed_word_p1_d0000` | all profiles above | `P1-D0000` | resolves |
| `prefixed_word_p2_d0000` | all profiles above | `P2-D0000` | resolves |
| `prefixed_word_p3_d0000` | all profiles above | `P3-D0000` | resolves |
| `prefixed_bit_p1_m0000` | all profiles above | `P1-M0000` | resolves |
| `prefixed_byte_p1_d0000l` | all profiles above | `P1-D0000L` | resolves |
| `prefixed_derived_p1_m000w` | all profiles above | `P1-M000W` | resolves |

### Reject Cases

| test id | profile | device | expected |
| --- | --- | --- | --- |
| `direct_word_d0000_rejected` | all profiles above | `D0000` | rejects |
| `direct_bit_m0000_rejected` | all profiles above | `M0000` | rejects |
| `direct_byte_d0000l_rejected` | all profiles above | `D0000L` | rejects |
| `direct_derived_m000w_rejected` | all profiles above | `M000W` | rejects |

### Minimum Assertions

- resolved device keeps the original prefix: `P1`, `P2`, or `P3`
- unprefixed cases fail because the profile does not expose direct access for those families
- the no-profile compatibility path may keep accepting unprefixed devices, but that must be tested separately and not mixed into profile-backed tests

## 2. Derived Width And Range Cases

These cases verify the manual rule:

- bit notation keeps the full bit width
- derived `W/L/H` notation uses one fewer hex digit

### Basic Bit Families

| test id | device | expected |
| --- | --- | --- |
| `bit_m17ff_ok` | `M17FF` | resolves |
| `word_m17fw_ok` | `M17FW` | resolves |
| `byte_m17fl_ok` | `M17FL` | resolves |
| `byte_m17fh_ok` | `M17FH` | resolves |
| `word_m0000w_ng` | `M0000W` | rejects |
| `byte_m0000l_ng` | `M0000L` | rejects |
| `byte_m0000h_ng` | `M0000H` | rejects |

### Extended Bit Families

| test id | device | expected |
| --- | --- | --- |
| `bit_ep0fff_ok` | `EP0FFF` | resolves |
| `word_ep0ffw_ok` | `EP0FFW` | resolves |
| `byte_ep0ffl_ok` | `EP0FFL` | resolves |
| `byte_ep0ffh_ok` | `EP0FFH` | resolves |
| `word_ep0000w_ng` | `EP0000W` | rejects |
| `byte_ep0000l_ng` | `EP0000L` | rejects |
| `byte_ep0000h_ng` | `EP0000H` | rejects |

### GM Boundary Cases

| test id | device | expected |
| --- | --- | --- |
| `bit_gmffff_ok` | `GMFFFF` | resolves |
| `word_gmfffw_ok` | `GMFFFW` | resolves |
| `byte_gmfffl_ok` | `GMFFFL` | resolves |
| `byte_gmfffh_ok` | `GMFFFH` | resolves |
| `word_gm1000w_ng` | `GM1000W` | rejects |
| `byte_gm1000l_ng` | `GM1000L` | rejects |
| `byte_gm1000h_ng` | `GM1000H` | rejects |

### Prefixed Derived Cases

| test id | device | expected |
| --- | --- | --- |
| `prefixed_word_p1_m17fw_ok` | `P1-M17FW` | resolves |
| `prefixed_byte_p1_m17fl_ok` | `P1-M17FL` | resolves |
| `prefixed_word_p1_m0000w_ng` | `P1-M0000W` | rejects |

### Minimum Assertions

- parsed digit count is checked against the derived width, not the bit width
- canonical formatting never expands `M17FW` into `M017FW` or `M0000W`
- range validation for `W/L/H` uses derived ranges, not raw bit ranges

## 3. `GX` / `GY` Naming Cases

These cases verify that the Python port does not introduce a synthetic `GXY`
area name.

| test id | input | expected |
| --- | --- | --- |
| `gx_word_name_preserved` | `GX000W` | area is `GX` |
| `gy_word_name_preserved` | `GY000W` | area is `GY` |
| `gx_roundtrip_no_gxy` | `GX000W` | formatted text contains `GX`, not `GXY` |
| `gy_roundtrip_no_gxy` | `GY000W` | formatted text contains `GY`, not `GXY` |
| `gxy_rejected_or_absent` | `GXY000W` | parser/reformatter does not support it |

### Minimum Assertions

- `GX` and `GY` remain explicit in parsed objects
- canonical formatting never emits `GXY`
- any target-specific alias behavior is tested separately from naming

## 4. Suggested `pytest.parametrize` Layout

### `test_profile_prefixed_only.py`

Use one profile list and two case lists:

- `ACCEPT_CASES = ["P1-D0000", "P2-D0000", "P3-D0000", "P1-M0000", "P1-D0000L", "P1-M000W"]`
- `REJECT_CASES = ["D0000", "M0000", "D0000L", "M000W"]`

### `test_derived_access_width.py`

Use positive and negative case lists:

- positive:
  - `M17FW`, `M17FL`, `M17FH`
  - `EP0FFW`, `EP0FFL`, `EP0FFH`
  - `GMFFFW`, `GMFFFL`, `GMFFFH`
  - `P1-M17FW`, `P1-M17FL`
- negative:
  - `M0000W`, `M0000L`, `M0000H`
  - `EP0000W`, `EP0000L`, `EP0000H`
  - `GM1000W`, `GM1000L`, `GM1000H`
  - `P1-M0000W`

### `test_gx_gy_naming.py`

Use explicit round-trip cases:

- `GX000W`
- `GY000W`

And one synthetic negative:

- `GXY000W`

## 5. Done Criteria

The Python side is done for this topic when all of the following are true:

- every reviewed profile rejects unprefixed `P/K/V/T/C/L/X/Y/M/S/N/R/D`
- prefixed forms resolve correctly in those same profiles
- derived `W/L/H` notation uses the shorter manual width
- canonical formatting preserves `GX` and `GY`
- no test, log, formatter, or canonical path emits `GXY`
