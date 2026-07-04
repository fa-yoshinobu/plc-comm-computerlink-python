# Getting started

## Start here

Use this page for your first TOYOPUC Computerlink read and write from Python.

| Step | What you do |
| --- | --- |
| 1 | Install `toyopuc-computerlink`. |
| 2 | Choose one exact canonical profile string. |
| 3 | Connect to `192.168.250.100:1025` over TCP. |
| 4 | Read `P1-D0000`. |
| 5 | Write only to a known-safe test word or bit. |

## Prerequisites

| Item | Requirement |
| --- | --- |
| Python | Python 3.10 or later. |
| PLC network | Your PLC is reachable at `192.168.250.100`. |
| TCP port | Computerlink TCP examples use `1025`. |
| UDP port | Computerlink UDP examples use `1035`. |
| Canonical profile | A profile such as `toyopuc:plus:extended`. |

## Install

```bash
pip install toyopuc-computerlink
```

## Choose profile

Start with `toyopuc:plus:extended` only when your PLC is a TOYOPUC-Plus target. Use [profiles](./PROFILES.md) for the exact list.

```python
from toyopuc import ToyopucPlcProfiles


def main() -> None:
    profile = ToyopucPlcProfiles.from_name("toyopuc:plus:extended")
    print(profile.name)


if __name__ == "__main__":
    main()
```

## First read

```python
import asyncio

from toyopuc import ToyopucConnectionOptions, open_and_connect, read_typed


async def main() -> None:
    options = ToyopucConnectionOptions(
        host="192.168.250.100",
        port=1025,
        plc_profile="toyopuc:plus:extended",
    )

    async with await open_and_connect(options) as client:
        value = await read_typed(client, "P1-D0000", "U")
        print(f"P1-D0000 = {value}")


asyncio.run(main())
```

## First write

Use a known-safe test word. Do not write to production outputs or motion-related registers while testing.

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
        original = await read_typed(client, "P1-D0001", "U")
        try:
            await write_typed(client, "P1-D0001", "U", 1234)
            value = await read_typed(client, "P1-D0001", "U")
            print(f"P1-D0001 = {value}")
        finally:
            await write_typed(client, "P1-D0001", "U", original)


asyncio.run(main())
```

## Confirm success

| Check | Expected result |
| --- | --- |
| Connection | No timeout from `open_and_connect`. |
| Read | `P1-D0000` returns one integer value. |
| Write | The readback from `P1-D0001` matches your test value. |
| Address text | Basic families use `P1-`, `P2-`, or `P3-` prefixes. |

## If it does not work

Use the shared [Computerlink Troubleshooting & Codes](https://fa-yoshinobu.github.io/plc-comm-docs-site/plc-setup/computerlink/troubleshooting-codes/) page for connection, addressing, write, relay, and PLC error-code checks.

| Symptom | Check |
| --- | --- |
| Timeout | Confirm host `192.168.250.100`, TCP port `1025`, and PLC network settings. |
| Profile error | Use only exact canonical strings from [profiles](./PROFILES.md). |
| Address error | Use `P1-D0000`, not `D0000`, for basic area families. |
| Dword reads look wrong | Use `P1-D0100:D` or dtype `"D"`; `P1-D0100.D` means bit 13. |
| FR write does not persist | Use `write_fr(..., commit=True)` or call `commit_fr()`. |

## Next steps

- Open the runnable samples: [samples README](https://github.com/fa-yoshinobu/plc-comm-computerlink-python/tree/main/samples).
- Continue with the [Usage guide](USAGE_GUIDE.md) and [Gotchas](GOTCHAS.md).
