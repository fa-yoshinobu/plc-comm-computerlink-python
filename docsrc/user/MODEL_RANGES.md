# Model-specific writable ranges

This page lists the practical writable ranges that differ by confirmed hardware model. Use it when you need a model-aware address picker or when a profile-level range still needs a hardware-specific write check.

For normal communication calls, select the canonical profile first in [PROFILES.md](PROFILES.md), then use the address forms in [SUPPORTED_REGISTERS.md](SUPPORTED_REGISTERS.md).

## TOYOPUC-Plus CPU with Plus EX2

| Area | Writable range summary |
| --- | --- |
| Basic bit | `P0000-P17FF`, `K0000-K02FF`, `V/T/C/M0000-17FF`, `L0000-L2FFF`, `X/Y0000-07FF` |
| Basic word | `S0000-S13FF`, `N0000-N17FF`, `R0000-R07FF`, `D0000-D0FFF`; `B` is not writable |
| Prefixed bit | `P1/P2/P3-P000-P1FF`, `K000-K2FF`, `V/T/C000-C1FF`, `L000-L7FF`, `X/Y000-X7FF`, `M000-M7FF` |
| Prefixed word | `P1/P2/P3-S0000-S03FF`, `N0000-N01FF`, `R0000-R07FF`, `D0000-D0FFF`; `B` is not writable |
| Extension bit | `EP/EK/EV0000-0FFF`, `ET/EC/EX/EY0000-07FF`, `EL0000-1FFF`, `EM0000-1FFF`, `GX/GY/GM0000-FFFF` |
| Extension word | `ES/EN/H0000-07FF`, `U00000-U07FFF`; `EB` is not present |
| FR | Not exposed on this CPU |

## Nano 10GX

| Area | Writable range summary |
| --- | --- |
| Basic bit | `P/K/V/T/C/L/X/Y/M` standard ranges |
| Basic word | `S0000-S13FF`, `N0000-N17FF`, `R0000-R07FF`, `D0000-D2FFF`; `B` is not present |
| Prefixed bit | `P1/P2/P3` standard ranges |
| Prefixed word | `S0000-S13FF`, `N0000-N17FF`, `R0000-R07FF`, `D0000-D2FFF`; upper prefixed `1000` series are not implemented |
| Extension | Standard `EP/EK/EV/ET/EC/EL/EX/EY/EM`, `GX/GY/GM`, `ES/EN/H`; `U00000-U1FFFF` in PC10 mode |
| FR | `FR000000-FR1FFFFF` when the CPU/configuration exposes FR |

## PC10G-CPU

| Area | Writable range summary |
| --- | --- |
| Basic bit | `P0000-P17FF`, `K0000-K02FF`, `V/T/C/M0000-17FF`, `L0000-L2FFF`, `X/Y0000-07FF` |
| Basic word | `S0000-S13FF`, `N0000-N17FF`, `R0000-R07FF`, `D0000-D2FFF` |
| Prefixed bit | `P1/P2/P3` standard ranges, including the upper `1000` series on this CPU |
| Prefixed word | `S0000-S13FF`, `N0000-N17FF`, `R0000-R07FF`, `D0000-D2FFF` |
| Extension bit | `EP/EK/EV0000-0FFF`, `ET/EC/EX/EY0000-07FF`, `EL0000-1FFF`, `EM0000-1FFF`, `GX/GY/GM0000-FFFF` |
| Extension word | `ES/EN/H0000-07FF`, `U00000-U1FFFF`, `EB00000-EB3FFFF` |
| FR | Not exposed on the tested PC10G unit |

## Notes

- These are writable-range summaries, not a complete hardware manual.
- A profile can make an address syntactically valid while the connected PLC still rejects it because of hardware, mode, or project configuration.
- FR writes are persistent operations. Use the dedicated FR helpers only on test addresses you control.
