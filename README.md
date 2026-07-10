[![CI](https://github.com/fa-yoshinobu/plc-comm-computerlink-python/actions/workflows/ci.yml/badge.svg)](https://github.com/fa-yoshinobu/plc-comm-computerlink-python/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/plc-comm-toyopuc.svg)](https://pypi.org/project/plc-comm-toyopuc/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://github.com/fa-yoshinobu/plc-comm-computerlink-python/blob/main/LICENSE)

# TOYOPUC Computerlink for Python

Python library for TOYOPUC Computerlink PLC communication over TCP or UDP.

## PLC Comm Family

This library is part of the plc-comm family. See the [package matrix](https://fa-yoshinobu.github.io/plc-comm-docs-site/package-matrix/) for protocol, language, registry, and install-command mapping.

## Supported PLC profiles

The maintained profile table is in [PLC profiles](https://fa-yoshinobu.github.io/plc-comm-docs-site/computerlink/python/PROFILES/). Choose one exact canonical PLC profile from that table.

## Supported device types

The shared device and range tables are in the [Computerlink Device Ranges](https://fa-yoshinobu.github.io/plc-comm-docs-site/plc-setup/computerlink/device-ranges/) page. Use that page for supported device families, address syntax, and profile-specific notes.

## Installation

```bash
pip install plc-comm-toyopuc
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
| [Getting started](https://fa-yoshinobu.github.io/plc-comm-docs-site/computerlink/python/GETTING_STARTED/) | First connection, first read, and first write. |
| [Usage guide](https://fa-yoshinobu.github.io/plc-comm-docs-site/computerlink/python/USAGE_GUIDE/) | Recommended entry points and common workflows. |
| [API reference](https://fa-yoshinobu.github.io/plc-comm-docs-site/computerlink/python/API_REFERENCE/) | Find public client methods, helpers, profile APIs, and error types. |
| [PLC profiles](https://fa-yoshinobu.github.io/plc-comm-docs-site/computerlink/python/PROFILES/) | Exact canonical profile names and profile-specific cautions. |
| [Computerlink Device Ranges](https://fa-yoshinobu.github.io/plc-comm-docs-site/plc-setup/computerlink/device-ranges/) | Check shared device families, address notation, and model range notes. |
| [Computerlink Troubleshooting & Codes](https://fa-yoshinobu.github.io/plc-comm-docs-site/plc-setup/computerlink/troubleshooting-codes/) | Troubleshoot common connection, address, write, relay, and PLC error-code symptoms. |
| [Gotchas](https://fa-yoshinobu.github.io/plc-comm-docs-site/computerlink/python/GOTCHAS/) | Symptoms, root causes, and fixes for common mistakes. |
| [Samples](https://github.com/fa-yoshinobu/plc-comm-computerlink-python/blob/main/samples/README.md) | Complete sample programs and command lines. |

## License and registry

| Item | Value |
| --- | --- |
| License | [MIT](https://github.com/fa-yoshinobu/plc-comm-computerlink-python/blob/main/LICENSE) |
| Registry | [PyPI](https://pypi.org/project/plc-comm-toyopuc/) |
| Package | `plc-comm-toyopuc` |

## Commercial support

If you plan to embed this library in a paid or commercial product, please consider a separate support agreement or supporting the project as a sponsor.

Contact: <https://fa-labo.com/contact.html>
