# Model-Specific Writable Ranges

This document records writable device ranges confirmed per hardware model.

The intent is practical:
- where writes are accepted
- where writes are rejected
- whether there are holes inside the accepted span

Evidence types used in this file:

- `exhaustive scan`
  Confirmed by `tools/exhaustive_writable_scan.py`.
- `runtime tests`
  Confirmed by the normal runtime test set in `TESTING.md`.

These ranges are based primarily on `tools/exhaustive_writable_scan.py`.

## TOYOPUC-Plus CPU (TCC-6740)

Source command:

```bash
python -m tools.exhaustive_writable_scan --host <HOST> --port <PORT> --protocol tcp --targets all --log exhaustive.log
```

Evidence:

- exhaustive scan
- runtime tests also agree with the supported/unsupported split for the tested paths

### Basic Bit

| Device | Writable range |
| --- | --- |
| `P` | `P0000-P17FF` |
| `K` | `K0000-K02FF` |
| `V` | `V0000-V17FF` |
| `T` | `T0000-T17FF` |
| `C` | `C0000-C17FF` |
| `L` | `L0000-L2FFF` |
| `X` | `X0000-X07FF` |
| `Y` | `Y0000-Y07FF` |
| `M` | `M0000-M17FF` |

### Basic Word

| Device | Writable range |
| --- | --- |
| `S` | `S0000-S13FF` |
| `N` | `N0000-N17FF` |
| `R` | `R0000-R07FF` |
| `D` | `D0000-D0FFF` |
| `B` | unsupported |

### Prefixed Bit (`P1/P2/P3`)

| Device | Writable range |
| --- | --- |
| `P` | `P000-P1FF` |
| `K` | `K000-K2FF` |
| `V` | `V000-V0FF` |
| `T` | `T000-T1FF` |
| `C` | `C000-C1FF` |
| `L` | `L000-L7FF` |
| `X` | `X000-X7FF` |
| `Y` | `Y000-Y7FF` |
| `M` | `M000-M7FF` |

Not writable on this model:
- `P1000-P17FF`
- `V1000-V17FF`
- `T1000-T17FF`
- `C1000-C17FF`
- `L1000-L2FFF`
- `M1000-M17FF`

### Prefixed Word (`P1/P2/P3`)

| Device | Writable range |
| --- | --- |
| `S` | `S0000-S03FF` |
| `N` | `N0000-N01FF` |
| `R` | `R0000-R07FF` |
| `D` | `D0000-D0FFF` |
| `B` | unsupported |

Not writable on this model:
- `S1000-S13FF`
- `N1000-N17FF`
- `D1000-D2FFF`

### Extension Bit

| Device | Writable range |
| --- | --- |
| `EP` | `EP0000-EP0FFF` |
| `EK` | `EK0000-EK0FFF` |
| `EV` | `EV0000-EV0FFF` |
| `ET` | `ET0000-ET07FF` |
| `EC` | `EC0000-EC07FF` |
| `EL` | `EL0000-EL1FFF` |
| `EX` | `EX0000-EX07FF` |
| `EY` | `EY0000-EY07FF` |
| `EM` | `EM0000-EM1FFF` |
| `GX` | `GX0000-GXFFFF` |
| `GY` | `GY0000-GYFFFF` |
| `GM` | `GM0000-GMFFFF` |

### Extension Word

| Device | Writable range |
| --- | --- |
| `ES` | `ES0000-ES07FF` |
| `EN` | `EN0000-EN07FF` |
| `H` | `H0000-H07FF` |
| `U` | `U00000-U07FFF` |
| `EB` | not present on this model |

Does not exist on this model:
- `U08000-U1FFFF`

### Notes

- No holes were observed inside the writable spans above.
- Unsupported spans were contiguous in the observed scan.
- This is a write-acceptance result. It does not imply readback validation.
- For this model, the exhaustive scan is the primary source for final upper bounds such as `D0000-D0FFF` and `U00000-U07FFF`.
