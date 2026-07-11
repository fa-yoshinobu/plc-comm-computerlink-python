# Gotchas

## Symptom: `D0000` is rejected

| Root cause | Fix |
| --- | --- |
| Basic area families require a program prefix. `D`, `M`, `S`, `N`, `R`, `P`, `K`, `V`, `T`, `C`, `L`, `X`, and `Y` must be written as `P1-*`, `P2-*`, or `P3-*`. | Use `P1-D0000`, `P2-D0000`, or `P3-D0000` for the intended program area. |

```python
from toyopuc import ToyopucDeviceClient


def main() -> None:
    with ToyopucDeviceClient(
        "192.168.250.100", 1025, transport="tcp", plc_profile="toyopuc:plus:extended"
    ) as client:
        print(client.read_one("P1-D0000"))


if __name__ == "__main__":
    main()
```

## Symptom: multi-address access hides splitting

| Root cause | Fix |
| --- | --- |
| A contiguous or multi-device operation can require multiple protocol requests, incompatible protocol groups, or a PC10 block boundary crossing. | `read`, `read_devices`, and `write_many` reject those cases before communication. Split the operation into separate explicit calls only when different acquisition times or partial completion are acceptable. |

## Symptom: `read_named(["P1-D0000", "P1-D0001"])` is rejected

| Root cause | Fix |
| --- | --- |
| Computerlink named reads intentionally accept one named address per call. Unlike SLMP or Host Link snapshots, they do not split a multi-address list into several PLC requests. | Call `read_named` once per named address, or use `read_words_single_request` for a contiguous range. |

```python
import asyncio

from toyopuc import ToyopucConnectionOptions, open_and_connect, read_named


async def main() -> None:
    options = ToyopucConnectionOptions(
        host="192.168.250.100",
        port=1025,
        transport="tcp",
        plc_profile="toyopuc:plus:extended",
    )
    async with await open_and_connect(options) as client:
        d0000 = await read_named(client, ["P1-D0000"])
        d0001 = await read_named(client, ["P1-D0001"])
        print(d0000["P1-D0000"], d0001["P1-D0001"])


asyncio.run(main())
```

## Symptom: `P1-D0100.D` reads a bit instead of a dword

| Root cause | Fix |
| --- | --- |
| A dot means bit-in-word access. `.D` is hexadecimal bit 13. | Use a colon for typed views: `P1-D0100:D`. |

```python
import asyncio

from toyopuc import ToyopucConnectionOptions, open_and_connect, read_typed


async def main() -> None:
    options = ToyopucConnectionOptions(
        host="192.168.250.100",
        port=1025,
        transport="tcp",
        plc_profile="toyopuc:plus:extended",
    )
    async with await open_and_connect(options) as client:
        print(await read_typed(client, "P1-D0100", "D"))


asyncio.run(main())
```

## Symptom: FR values revert after power cycle

| Root cause | Fix |
| --- | --- |
| `write_fr(...)` updates only the FR work area. It never commits flash. | Call `commit_fr()` separately with the first word of exactly one block only when persistence is intended. |

```python
from toyopuc import ToyopucDeviceClient


def main() -> None:
    with ToyopucDeviceClient(
        "192.168.250.100", 1025, transport="tcp", plc_profile="toyopuc:pc10g:pc10"
    ) as client:
        # Use only a test FR address. commit_fr persists the staged value
        # to flash and does not restore the previous value automatically.
        client.write_fr("FR000000", 0x1234)
        client.commit_fr("FR000000")


if __name__ == "__main__":
    main()
```

## Symptom: non-canonical profile string fails immediately

| Root cause | Fix |
| --- | --- |
| The library accepts only exact canonical profile strings from source. Aliases and blank values are rejected. | Copy the exact string from [profiles](./PROFILES.md). |

```python
from toyopuc import ToyopucPlcProfiles


def main() -> None:
    profile = ToyopucPlcProfiles.from_name("toyopuc:plus:extended")
    print(profile.name)


if __name__ == "__main__":
    main()
```

## Symptom: relay access does not find the route automatically

| Root cause | Fix |
| --- | --- |
| Relay hops are not probed automatically because automatic routing can hide configuration mistakes. | Pass the exact relay hop string to the relay helper you call. |

```python
from toyopuc import ToyopucDeviceClient


def main() -> None:
    with ToyopucDeviceClient(
        "192.168.250.100", 1025, transport="tcp", plc_profile="toyopuc:nano-10gx:compatible"
    ) as client:
        hops = "P1-L2:N2"
        print(client.relay_read_words(hops, "P1-D0000", count=1))


if __name__ == "__main__":
    main()
```

## Symptom: `P1-M0010W` is mistaken for a type suffix

| Root cause | Fix |
| --- | --- |
| `W`, `H`, and `L` after a bit-area address are packed-word or byte notation, not `:D` or `:F` type suffixes. | Use `P1-M0010W` for a packed 16-bit view, and use `P1-D0100:D` for typed dword reads. |

```python
from toyopuc import ToyopucDeviceClient


def main() -> None:
    with ToyopucDeviceClient(
        "192.168.250.100", 1025, transport="tcp", plc_profile="toyopuc:plus:extended"
    ) as client:
        packed = client.read_one("P1-M0010W")
        dword = client.read_dword("P1-D0100")
        print(packed, dword)


if __name__ == "__main__":
    main()
```
