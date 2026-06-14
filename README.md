[![CI](https://github.com/fa-yoshinobu/plc-comm-computerlink-python/actions/workflows/ci.yml/badge.svg)](https://github.com/fa-yoshinobu/plc-comm-computerlink-python/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/toyopuc-computerlink.svg)](https://pypi.org/project/toyopuc-computerlink/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

# TOYOPUC Computerlink for Python

Python library for TOYOPUC Computerlink PLC communication over TCP or UDP.

## Supported PLC profiles

The maintained profile table is in [PLC profiles](docsrc/user/PROFILES.md). Choose one exact canonical PLC profile from that table.

## Supported device types

The maintained device and range tables are in [Supported registers](docsrc/user/SUPPORTED_REGISTERS.md). Use that page for supported device families, address syntax, and profile-specific notes.

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

## Documentation

| Page | Use it for |
| --- | --- |
| [Full documentation site](https://fa-yoshinobu.github.io/plc-comm-docs-site/) | Unified docs for all PLC communication libraries. |
| [Getting started](docsrc/user/GETTING_STARTED.md) | First connection, first read, and first write. |
| [Usage guide](docsrc/user/USAGE_GUIDE.md) | Recommended entry points and common workflows. |
| [Supported registers](docsrc/user/SUPPORTED_REGISTERS.md) | Public device families and typed address forms. |
| [PLC profiles](docsrc/user/PROFILES.md) | Exact canonical profile names and profile-specific cautions. |
| [Gotchas](docsrc/user/GOTCHAS.md) | Symptoms, root causes, and fixes for common mistakes. |
| [Samples](samples/README.md) | Complete sample programs and command lines. |

## Hardware verified

Live-device verification is maintained in [Latest communication verification](docsrc/user/LATEST_COMMUNICATION_VERIFICATION.md).
See that page for verified PLC models, transports, dates, limitations, and retained validation notes.

## License and registry

| Item | Value |
| --- | --- |
| License | [MIT](LICENSE) |
| Registry | [PyPI](https://pypi.org/project/toyopuc-computerlink/) |
| Package | `toyopuc-computerlink` |
