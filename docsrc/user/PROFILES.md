# PLC profiles

Each profile selects addressing rules and device ranges.

## Profiles table

| Profile string | Hardware | Key devices available | Notes |
| --- | --- | --- | --- |
| `toyopuc:generic` | Generic TOYOPUC catalog | Prefixed basic areas, `B`, extension bits, `ES`, `EN`, `H`, `U`, `EB`, `FR` | Broadest source catalog. |
| `toyopuc:plus:standard` | TOYOPUC-Plus standard addressing | Prefixed basic areas, extension bits, `ES`, `EN`, `H` | Standard Plus profile. |
| `toyopuc:plus:extended` | TOYOPUC-Plus extended addressing | Prefixed basic areas, extension bits, `GM`, `GX`, `GY`, `ES`, `EN`, `H`, `U` | Extended Plus profile. |
| `toyopuc:nano-10gx:native` | Nano 10GX native profile | Prefixed basic areas, extension bits, `GM`, `GX`, `GY`, `ES`, `EN`, `H`, `U`, `EB`, `FR` | Native Nano 10GX profile. |
| `toyopuc:nano-10gx:compatible` | Nano 10GX compatible profile | Prefixed basic areas, extension bits, `GM`, `GX`, `GY`, `ES`, `EN`, `H`, `U`, `EB`, `FR` | Same source area catalog as native. |
| `toyopuc:pc10g:standard-pc3jg` | PC10G standard PC3JG profile | Prefixed basic areas, `B`, extension bits, `GM`, `GX`, `GY`, `ES`, `EN`, `H`, `U`, `EB` | No `FR` in this profile. |
| `toyopuc:pc10g:pc10` | PC10G PC10 mode | Prefixed basic areas, `B`, extension bits, `GM`, `GX`, `GY`, `ES`, `EN`, `H`, `U`, `EB`, `FR` | PC10 mode profile. |
| `toyopuc:pc3jx:pc3-separate` | PC3JX PC3 separate mode | Prefixed basic areas, `B`, extension bits, `ES`, `EN`, `H`, `U` | No `GM`, `GX`, `GY`, `EB`, or `FR`. |
| `toyopuc:pc3jx:plus-expansion` | PC3JX Plus expansion mode | Prefixed basic areas, extension bits, `GM`, `GX`, `GY`, `ES`, `EN`, `H`, `U` | No `B`, `EB`, or `FR`. |
| `toyopuc:pc3jg:pc3jg` | PC3JG mode | Prefixed basic areas, `B`, extension bits, `GM`, `GX`, `GY`, `ES`, `EN`, `H`, `U`, `EB` | No `FR` in this profile. |
| `toyopuc:pc3jg:pc3-separate` | PC3JG PC3 separate mode | Prefixed basic areas, `B`, extension bits, `GM`, `GX`, `GY`, `ES`, `EN`, `H`, `U`, `EB` | No `FR` in this profile. |

## How to select

```python
from toyopuc import ToyopucConnectionOptions
options = ToyopucConnectionOptions(host="192.168.250.100", plc_profile="toyopuc:plus:extended")
```

`ToyopucConnectionOptions` uses TCP port `1025` by default.

## Profile-specific cautions

- `toyopuc:generic`: This profile exposes the broadest source catalog and is useful when you do not know the exact hardware. Use a hardware-specific profile when you want range validation to match your PLC more closely.
- `toyopuc:plus:standard`: The source catalog does not include `B`, `GM`, `GX`, `GY`, `U`, `EB`, or `FR`. Start with prefixed `D` and `M` addresses.
- `toyopuc:plus:extended`: This profile adds `GM`, `GX`, `GY`, and `U` compared with the standard Plus profile. It still does not expose `B`, `EB`, or `FR`.
- `toyopuc:nano-10gx:native`: The source catalog includes `EB` and `FR`. The verification notes say `FR` exposure is profile-dependent and should not be your first smoke test.
- `toyopuc:nano-10gx:compatible`: The source catalog matches the native Nano 10GX area list. Keep the same caution for `FR` exposure.
- `toyopuc:pc10g:standard-pc3jg`: The profile includes `B`, `GM`, `GX`, `GY`, `U`, and `EB`, but not `FR`. Use `toyopuc:pc10g:pc10` when you need the PC10-mode catalog.
- `toyopuc:pc10g:pc10`: The profile includes `B`, `EB`, and `FR`. The latest verification notes say exact writable ranges depend on hardware, and the tested PC10G unit had model-specific unsupported areas.
- `toyopuc:pc3jx:pc3-separate`: The profile includes `B` and `U`, but not `GM`, `GX`, `GY`, `EB`, or `FR`. Keep extension-area examples within the exposed catalog.
- `toyopuc:pc3jx:plus-expansion`: The profile includes `GM`, `GX`, `GY`, and `U`, but not `B`, `EB`, or `FR`. Use the PC3 separate profile if your source catalog needs `B`.
- `toyopuc:pc3jg:pc3jg`: The profile includes `B`, `GM`, `GX`, `GY`, `U`, and `EB`, but not `FR`. Use `EB` only when your hardware exposes it.
- `toyopuc:pc3jg:pc3-separate`: The profile exposes the same key extra areas as `toyopuc:pc3jg:pc3jg` in the source catalog. It does not include `FR`.
