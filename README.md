[![CI](https://github.com/fa-yoshinobu/plc-comm-computerlink-python/actions/workflows/ci.yml/badge.svg)](https://github.com/fa-yoshinobu/plc-comm-computerlink-python/actions/workflows/ci.yml) [![PyPI](https://img.shields.io/pypi/v/toyopuc-computerlink.svg)](https://pypi.org/project/toyopuc-computerlink/) [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

# Computer Link Protocol for Python

`toyopuc-computerlink` speaks the JTEKT TOYOPUC Computer Link protocol over TCP or UDP for TOYOPUC-Plus, Nano 10GX, PC10G, PC3JX, and PC3JG profile families.

## Supported PLC profiles

| Profile string | Hardware | Notes |
| --- | --- | --- |
| `toyopuc:generic` | Generic TOYOPUC catalog | Broadest source catalog; prefer a hardware-specific profile when you know your PLC. |
| `toyopuc:plus:standard` | TOYOPUC-Plus standard addressing | Prefixed basic areas plus standard extension areas. |
| `toyopuc:plus:extended` | TOYOPUC-Plus extended addressing | Adds `GM`, `GX`, `GY`, and `U` extension areas. |
| `toyopuc:nano-10gx:native` | Nano 10GX native profile | Includes upper ranges, `EB`, and `FR` in the source catalog. |
| `toyopuc:nano-10gx:compatible` | Nano 10GX compatible profile | Same source area catalog as the native Nano 10GX profile. |
| `toyopuc:pc10g:standard-pc3jg` | PC10G standard PC3JG profile | Includes `B`, `GM`, `GX`, `GY`, `U`, and `EB`; no `FR` area in the profile. |
| `toyopuc:pc10g:pc10` | PC10G PC10 mode | Includes `B`, `GM`, `GX`, `GY`, `U`, `EB`, and `FR`. |
| `toyopuc:pc3jx:pc3-separate` | PC3JX PC3 separate mode | Includes `B` and `U`; no `GM`, `GX`, `GY`, `EB`, or `FR`. |
| `toyopuc:pc3jx:plus-expansion` | PC3JX Plus expansion mode | Includes `GM`, `GX`, `GY`, and `U`; no `B`, `EB`, or `FR`. |
| `toyopuc:pc3jg:pc3jg` | PC3JG mode | Includes `B`, `GM`, `GX`, `GY`, `U`, and `EB`; no `FR`. |
| `toyopuc:pc3jg:pc3-separate` | PC3JG PC3 separate mode | Includes `B`, `GM`, `GX`, `GY`, `U`, and `EB`; no `FR`. |

## Supported device types

| Family | Description |
| --- | --- |
| `D` | Data registers, usually your first word read target such as `P1-D0000`. |
| `M` | Internal relays for bit reads and writes such as `P1-M0000`. |
| `X` / `Y` | Input and output relay families. |
| `S` / `N` / `R` | Special, file, and register word families. |
| `ES` / `EN` / `H` | Direct extension word areas with no program prefix. |
| `U` / `EB` | Larger extension word areas on profiles that expose them. |
| `FR` | Flash-backed file-register storage with explicit commit semantics. |
| `P` / `K` / `V` / `T` / `C` / `L` | Additional bit families, including timer, counter, and link-related areas. |

See the full table in [Supported registers](docsrc/user/SUPPORTED_REGISTERS.md).

## Installation

```bash
pip install toyopuc-computerlink
```

## Quick example

```python
import asyncio
from toyopuc import ToyopucConnectionOptions, open_and_connect, read_typed

async def main() -> None:
    options = ToyopucConnectionOptions(host="192.168.250.100", port=1025, plc_profile="toyopuc:plus:extended")
    async with await open_and_connect(options) as client:
        value = await read_typed(client, "P1-D0000", "U")
        print(f"P1-D0000 = {value}")

asyncio.run(main())
```

## Documentation links

- [Getting started](docsrc/user/GETTING_STARTED.md)
- [Usage guide](docsrc/user/USAGE_GUIDE.md)
- [Supported registers](docsrc/user/SUPPORTED_REGISTERS.md)
- [PLC profiles](docsrc/user/PROFILES.md)
- [Examples](samples/README.md)

## Hardware verified

Physical communication has been verified against `TOYOPUC-Plus CPU`, `Nano 10GX`, and `PC10G-CPU`.

## License and registry

Distributed under the [MIT License](LICENSE).

Package registry: <https://pypi.org/project/toyopuc-computerlink/>
