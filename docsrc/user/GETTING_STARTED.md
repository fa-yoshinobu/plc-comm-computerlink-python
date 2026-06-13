# Start here

Use this page when you want to connect to your PLC, read one word, and make one controlled test write. You need Python, network access to the PLC, and a safe test address that you are allowed to write.

## Prerequisites

| Requirement | Value |
| --- | --- |
| Python | 3.10 or newer |
| PLC host | `192.168.250.100` |
| TCP port | `1025` |
| Network | Your computer must be able to reach the PLC Computer Link port. |

## Install

```bash
pip install toyopuc-computerlink
```

## Choose your PLC profile

`plc_profile` in `ToyopucConnectionOptions` is the only required connection-time selector for the address catalog. The profile string must match one of the canonical values in [PROFILES.md](PROFILES.md).

```python
from toyopuc import ToyopucConnectionOptions

options = ToyopucConnectionOptions(host="192.168.250.100", port=1025, plc_profile="toyopuc:plus:extended")
```

## First read (step by step)

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

Expected output:

```text
P1-D0000 = 0
```

Your value may be different because it comes from your PLC.

## First write

Only write to a test address you control. This example uses a word register, not a bit, timer, counter, or flash-backed `FR` address.

```python
import asyncio
from toyopuc import ToyopucConnectionOptions, open_and_connect, read_typed, write_typed

async def main() -> None:
    options = ToyopucConnectionOptions(host="192.168.250.100", port=1025, plc_profile="toyopuc:plus:extended")
    async with await open_and_connect(options) as client:
        await write_typed(client, "P1-D0001", "U", 1234)
        value = await read_typed(client, "P1-D0001", "U")
        print(f"P1-D0001 = {value}")

asyncio.run(main())
```

## Confirm success

1. The program connects without a timeout.
2. The first read prints a numeric value for `P1-D0000`.
3. The test write returns without a PLC error.
4. The readback from `P1-D0001` matches the value you wrote.

## If it does not work

| Check | What to do |
| --- | --- |
| Wrong host or port | Confirm the PLC address and use TCP port `1025` for the first test. |
| Wrong profile string | Profile strings must match exactly; see [PROFILES.md](PROFILES.md). |
| Too much syntax at once | Start with plain word reads before typed reads or bit-in-word syntax. |
| Missing address prefix | Basic area families such as `D`, `M`, `X`, `Y`, `T`, and `C` require `P1-`, `P2-`, or `P3-`. |

## Next pages

- [USAGE_GUIDE.md](USAGE_GUIDE.md)
- [SUPPORTED_REGISTERS.md](SUPPORTED_REGISTERS.md)
