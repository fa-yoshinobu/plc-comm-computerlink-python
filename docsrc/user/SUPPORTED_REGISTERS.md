# Supported registers

This page lists the public high-level device forms verified from the source catalog. Exact ranges are profile-dependent; use [profiles](./PROFILES.md) to choose the model first.

## Bit devices

| Family | Access | Example | Notes |
| --- | --- | --- | --- |
| `P` | Prefixed | `P1-P0000` | Shared relay family. |
| `K` | Prefixed | `P1-K0000` | Keep relay family. |
| `V` | Prefixed | `P1-V0000` | Profile-dependent split ranges. |
| `T` | Prefixed | `P1-T0000` | Timer bit family. |
| `C` | Prefixed | `P1-C0000` | Counter bit family. |
| `L` | Prefixed | `P1-L0000` | Link relay family. |
| `X` | Prefixed | `P1-X0000` | Input relay family. |
| `Y` | Prefixed | `P1-Y0000` | Output relay family. |
| `M` | Prefixed | `P1-M0000` | Internal relay family. |
| `EP` | Direct | `EP0000` | Extension bit family. |
| `EK` | Direct | `EK0000` | Extension bit family. |
| `EV` | Direct | `EV0000` | Extension bit family. |
| `ET` | Direct | `ET0000` | Extension timer bit family. |
| `EC` | Direct | `EC0000` | Extension counter bit family. |
| `EL` | Direct | `EL0000` | Extension link relay family. |
| `EX` | Direct | `EX0000` | Extension input family. |
| `EY` | Direct | `EY0000` | Extension output family. |
| `EM` | Direct | `EM0000` | Extension internal relay family. |
| `GM` | Direct | `GM0000` | Profile-dependent extended bit family. |
| `GX` | Direct | `GX0000` | Profile-dependent extended input family. |
| `GY` | Direct | `GY0000` | Profile-dependent extended output family. |

## Word devices

| Family | Access | Example | Notes |
| --- | --- | --- | --- |
| `S` | Prefixed | `P1-S0000` | Special register family. |
| `N` | Prefixed | `P1-N0000` | File register family. |
| `R` | Prefixed | `P1-R0000` | Register family. |
| `D` | Prefixed | `P1-D0000` | Recommended first smoke-test word. |
| `B` | Direct | `B0000` | Direct word family in selected profiles. |
| `ES` | Direct | `ES0000` | Extension special register. |
| `EN` | Direct | `EN0000` | Extension file register. |
| `H` | Direct | `H0000` | Extension word family. |
| `U` | Direct | `U00000` | Profile-dependent upper word area. |
| `EB` | Direct | `EB00000` | Profile-dependent EB word area. |
| `FR` | Direct | `FR000000` | FR storage; use dedicated FR helpers. |

## Type suffixes

| Form | Size | Meaning | Example |
| --- | --- | --- | --- |
| No suffix or `:U` | 1 word | Unsigned 16-bit integer | `P1-D0100` |
| `:S` | 1 word | Signed 16-bit integer | `P1-D0100:S` |
| `:D` | 2 words | Unsigned 32-bit integer | `P1-D0100:D` |
| `:L` | 2 words | Signed 32-bit integer | `P1-D0100:L` |
| `:F` | 2 words | IEEE-754 float32 | `P1-D0100:F` |
| `.0` through `.F` | 1 bit | Bit inside one word | `P1-D0100.3` |
| `W` | Packed word | 16-bit packed view of a bit family | `P1-M0010W` |
| `L` / `H` | Packed byte | Low or high byte view of a bit family | `P1-M0010L` |

## Addressing rules

| Rule | Correct form |
| --- | --- |
| Basic families require a program prefix. | `P1-D0000`, `P2-M0000`, `P3-S0000` |
| Extension families are direct. | `ES0000`, `EP0000`, `U00000`, `FR000000` |
| Data type views use a colon. | `P1-D0100:D` |
| Bit-in-word views use a dot. | `P1-D0100.D` means bit 13. |
| FR writes are explicit. | `write_fr(..., commit=False)` then `commit_fr()` when persistence is intended. |
