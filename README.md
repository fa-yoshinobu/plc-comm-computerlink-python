[![CI](https://github.com/fa-yoshinobu/plc-comm-computerlink-python/actions/workflows/ci.yml/badge.svg)](https://github.com/fa-yoshinobu/plc-comm-computerlink-python/actions/workflows/ci.yml)
[![Documentation](https://img.shields.io/badge/docs-GitHub_Pages-blue.svg)](https://fa-yoshinobu.github.io/plc-comm-docs-site/computerlink/python/)
[![PyPI](https://img.shields.io/pypi/v/toyopuc-computerlink.svg)](https://pypi.org/project/toyopuc-computerlink/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Static Analysis: Ruff](https://img.shields.io/badge/Lint-Ruff-black.svg)](https://github.com/astral-sh/ruff)

# Computer Link Protocol for Python

A Python library for JTEKT TOYOPUC Computer Link communication over TCP or UDP, with `ToyopucDeviceClient` and `open_and_connect` as the recommended high-level entry points.

## Supported profiles

Choose one exact canonical profile string from source. Missing, blank, abbreviated, or alias profile names are rejected immediately.

| Canonical profile | Hardware | Notes |
| --- | --- | --- |
| `toyopuc:generic` | Any TOYOPUC Computer Link | Broad profile with U, EB, FR, and upper PC10 routes enabled. |
| `toyopuc:plus:standard` | TOYOPUC-Plus | Standard TOYOPUC-Plus ranges; U, EB, FR, GM, GX, and GY are not in this profile. |
| `toyopuc:plus:extended` | TOYOPUC-Plus | Recommended first example profile; adds GM, GX, GY, and U to the standard profile. |
| `toyopuc:nano-10gx:native` | Nano 10GX | Native Nano 10GX addressing with U, EB, and FR. |
| `toyopuc:nano-10gx:compatible` | Nano 10GX | Compatible mode; configure relay hops explicitly when relaying. |
| `toyopuc:pc10g:standard-pc3jg` | PC10G | PC3JG-compatible standard profile; FR is not included. |
| `toyopuc:pc10g:pc10` | PC10G | PC10 addressing profile; FR is available. |
| `toyopuc:pc3jx:pc3-separate` | PC3JX | PC3 separate ranges; GM, GX, GY, EB, and FR are not included. |
| `toyopuc:pc3jx:plus-expansion` | PC3JX | Plus expansion ranges; B, EB, and FR are not included. |
| `toyopuc:pc3jg:pc3jg` | PC3JG | PC3JG ranges; FR is not included. |
| `toyopuc:pc3jg:pc3-separate` | PC3JG | PC3 separate ranges; FR is not included. |

## Supported device types

The exact range depends on the selected profile. See [supported registers](docsrc/user/SUPPORTED_REGISTERS.md) for the full public table.

| Device type | Example | Notes |
| --- | --- | --- |
| Program word areas | `P1-D0000`, `P1-S0000`, `P1-N0000` | Basic word families require a `P1-`, `P2-`, or `P3-` prefix. |
| Program bit areas | `P1-M0000`, `P1-X0000`, `P1-Y0000` | Basic bit families also require a program prefix. |
| Extension bit areas | `EP0000`, `EX0000`, `GM0000` | Profile-dependent direct extension bit families. |
| Extension word areas | `ES0000`, `EN0000`, `H0000` | Direct extension word families. |
| U and EB areas | `U00000`, `EB00000` | Availability and routing are profile-dependent. |
| FR storage | `FR000000` | Use the dedicated FR helpers and commit deliberately. |
| Packed bit words | `P1-M0010W`, `P1-M0010L`, `P1-M0010H` | `W`, `L`, and `H` are packed-word or byte forms. |
| Typed word views | `P1-D0100:D`, `P1-D0100:F` | `:` selects a data type; `.` selects one bit inside a word. |

## Installation

```bash
pip install toyopuc-computerlink
```

## Quick example

```python
import asyncio

from toyopuc import ToyopucConnectionOptions, open_and_connect, read_typed, write_typed


async def main() -> None:
    options = ToyopucConnectionOptions(
        host="192.168.250.100",
        port=1025,
        plc_profile="toyopuc:plus:extended",
    )

    async with await open_and_connect(options) as client:
        value = await read_typed(client, "P1-D0000", "U")
        print(f"P1-D0000 = {value}")

        await write_typed(client, "P1-D0001", "U", 1234)


asyncio.run(main())
```

## Documentation links

| Page | Use it for |
| --- | --- |
| [Getting started](docsrc/user/GETTING_STARTED.md) | First connection, first read, and first write. |
| [Usage guide](docsrc/user/USAGE_GUIDE.md) | Recommended entry points and common workflows. |
| [Supported registers](docsrc/user/SUPPORTED_REGISTERS.md) | Public device families and typed address forms. |
| [Profiles](docsrc/user/PROFILES.md) | Exact canonical profile names and profile-specific cautions. |
| [Gotchas](docsrc/user/GOTCHAS.md) | Symptoms, root causes, and fixes for common mistakes. |
| [Samples](samples/README.md) | Complete sample programs and command lines. |

## Hardware verified

Retained verification notes record direct TOYOPUC checks against `192.168.250.100:1025`, including `P1-D0000`, `P1-M0000`, Nano 10GX, PC10G, and FR-related validation. The latest retained verification page is [LATEST_COMMUNICATION_VERIFICATION.md](docsrc/user/LATEST_COMMUNICATION_VERIFICATION.md).

## License and registry

This package is distributed under the [MIT License](LICENSE). The published package is [`toyopuc-computerlink` on PyPI](https://pypi.org/project/toyopuc-computerlink/).
