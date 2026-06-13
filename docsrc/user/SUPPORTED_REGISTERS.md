# Supported registers

This page lists device families supported by the Python high-level API.

## Bit device families

| Family | Kind | Example | Notes |
| --- | --- | --- | --- |
| `P` | Basic bit | `P1-P0000` | Requires `P1-`, `P2-`, or `P3-`. |
| `K` | Basic bit | `P1-K0000` | Requires `P1-`, `P2-`, or `P3-`. |
| `V` | Basic bit | `P1-V0000` | Requires `P1-`, `P2-`, or `P3-`. |
| `T` | Basic bit | `P1-T0000` | Timer-related bit family; requires a program prefix. |
| `C` | Basic bit | `P1-C0000` | Counter-related bit family; requires a program prefix. |
| `L` | Basic bit | `P1-L0000` | Link-related bit family; requires a program prefix. |
| `X` | Basic bit | `P1-X0000` | Input bit family; requires a program prefix. |
| `Y` | Basic bit | `P1-Y0000` | Output bit family; requires a program prefix. |
| `M` | Basic bit | `P1-M0000` | Internal relay bit family; requires a program prefix. |
| `EP` | Extension bit | `EP0000` | Direct extension bit area. |
| `EK` | Extension bit | `EK0000` | Direct extension bit area. |
| `EV` | Extension bit | `EV0000` | Direct extension bit area. |
| `ET` | Extension bit | `ET0000` | Direct extension timer bit area. |
| `EC` | Extension bit | `EC0000` | Direct extension counter bit area. |
| `EL` | Extension bit | `EL0000` | Direct extension link bit area. |
| `EX` | Extension bit | `EX0000` | Direct extension input bit area. |
| `EY` | Extension bit | `EY0000` | Direct extension output bit area. |
| `EM` | Extension bit | `EM0000` | Direct extension relay bit area. |
| `GX` | Extension bit | `GX0000` | Global extension bit area on profiles that expose it. |
| `GY` | Extension bit | `GY0000` | Global extension bit area on profiles that expose it. |
| `GM` | Extension bit | `GM0000` | Global extension bit area on profiles that expose it. |

## Word device families

| Family | Kind | Example | Notes |
| --- | --- | --- | --- |
| `S` | Basic word | `P1-S0000` | Requires `P1-`, `P2-`, or `P3-`. |
| `N` | Basic word | `P1-N0000` | Requires `P1-`, `P2-`, or `P3-`. |
| `R` | Basic word | `P1-R0000` | Requires `P1-`, `P2-`, or `P3-`. |
| `D` | Basic word | `P1-D0000` | Data register family; requires a program prefix. |
| `B` | Basic word | `B0000` | Direct basic word area on profiles that expose it. |
| `ES` | Extension word | `ES0000` | Direct extension special register. |
| `EN` | Extension word | `EN0000` | Direct extension file register. |
| `H` | Extension word | `H0000` | Direct extension word area. |
| `U` | Extension word | `U00000` | Direct extension word area on profiles that expose it. |
| `EB` | Extension word | `EB00000` | Extended block word area on profiles that expose it. |
| `FR` | Flash word | `FR000000` | Flash-backed file-register storage with two-phase write semantics. |

## Type suffixes

| Form | Example | Meaning |
| --- | --- | --- |
| `:U` | `P1-D0100:U` | Unsigned 16-bit word. |
| `:S` | `P1-D0100:S` | Signed 16-bit word. |
| `:D` | `P1-D0100:D` | Unsigned 32-bit value from two words. |
| `:L` | `P1-D0100:L` | Signed 32-bit value from two words. |
| `:F` | `P1-D0100:F` | Float32 value from two words. |
| `.n` | `P1-D0100.3` | One bit inside a word, where `n` is `0` through `F`. |
| `W` | `P1-M0010W` | Packed 16-bit word view of a bit family. |
| `H` | `P1-M0010H` | High byte of a packed bit-family word. |
| `L` | `P1-M0010L` | Low byte of a packed bit-family word. |

## Addressing notes

- Basic families `P`, `K`, `V`, `T`, `C`, `L`, `X`, `Y`, `M`, `S`, `N`, `R`, and `D` require a `P1-`, `P2-`, or `P3-` prefix.
- `FR` is a separate flash storage area with two-phase write semantics.
- `ES` and `EN` are extension areas with no prefix required.
- `.D` on a word address means bit 13; use `:D` with a colon for 32-bit dword access.

See [PROFILES.md](PROFILES.md) for per-profile range limits.
