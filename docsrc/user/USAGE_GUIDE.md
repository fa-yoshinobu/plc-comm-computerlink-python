# Usage guide

## Recommended entry points

| Entry point | When to use it |
| --- | --- |
| `ToyopucConnectionOptions` | Store one explicit connection profile for async code. |
| `open_and_connect(options)` | Create and connect an async high-level client. |
| `read_typed` / `write_typed` | Read or write one typed value. |
| `read_named` | Read one named word, typed, or bit-in-word address. |
| `read_words_single_request` / `read_dwords_single_request` | Keep a contiguous read as one logical request. |
| `read_words_chunked` / `read_dwords_chunked` | Split a large contiguous read deliberately. |
| `write_bit_in_word` | Change one bit inside a word with read-modify-write. |
| `poll` | Repeatedly yield one named address. |
| `ToyopucDeviceClient` | Use the synchronous high-level API. |

## Connection

```python
import asyncio

from toyopuc import ToyopucConnectionOptions, open_and_connect


async def main() -> None:
    options = ToyopucConnectionOptions(
        host="192.168.250.100",
        port=1025,
        transport="tcp",
        timeout=3.0,
        retries=0,
        plc_profile="toyopuc:plus:extended",
    )

    async with await open_and_connect(options) as client:
        print(client.plc_profile)


asyncio.run(main())
```

For UDP, keep the same profile rule and use port `1035`.

```python
import asyncio

from toyopuc import ToyopucConnectionOptions, open_and_connect, read_typed


async def main() -> None:
    options = ToyopucConnectionOptions(
        host="192.168.250.100",
        port=1035,
        local_port=12000,
        transport="udp",
        retries=2,
        plc_profile="toyopuc:plus:extended",
    )

    async with await open_and_connect(options) as client:
        print(await read_typed(client, "P1-D0000", "U"))


asyncio.run(main())
```

## Read single

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
        unsigned_word = await read_typed(client, "P1-D0000", "U")
        signed_word = await read_typed(client, "P1-D0002", "S")
        dword = await read_typed(client, "P1-D0100", "D")
        print(unsigned_word, signed_word, dword)


asyncio.run(main())
```

## Write single

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
        original_d0001 = await read_typed(client, "P1-D0001", "U")
        original_d0200 = await read_typed(client, "P1-D0200", "L")
        try:
            await write_typed(client, "P1-D0001", "U", 1234)
            await write_typed(client, "P1-D0200", "L", -500)
        finally:
            await write_typed(client, "P1-D0200", "L", original_d0200)
            await write_typed(client, "P1-D0001", "U", original_d0001)


asyncio.run(main())
```

## Named snapshot

```python
import asyncio

from toyopuc import ToyopucConnectionOptions, open_and_connect, read_named


async def main() -> None:
    options = ToyopucConnectionOptions(
        host="192.168.250.100",
        port=1025,
        plc_profile="toyopuc:plus:extended",
    )

    async with await open_and_connect(options) as client:
        snapshot = await read_named(client, ["P1-D0100:F"])
        print(snapshot)


asyncio.run(main())
```

## Batching and request boundaries

`ToyopucDeviceClient.read_many` and `ToyopucDeviceClient.write_many` execute only when all requested devices can be represented by one compatible protocol request. They raise `ToyopucProtocolError` before communication when the request would need multiple protocol requests, such as incompatible protocol groups, PC10 block boundary crossings, or helper paths that would fall back to individual requests.

Async `read_named` accepts one named address per call. Use explicit repeated calls when multiple named reads are intentional.

For contiguous word ranges, use `read_words_single_request`, `read_dwords_single_request`, `write_words_single_request`, or `write_dwords_single_request`. These helpers also fail if the requested range cannot be represented as one compatible protocol request. Use the `*_chunked` helpers, or separate explicit calls, only when splitting is intentional and partial completion is acceptable.

## Block reads

```python
import asyncio

from toyopuc import (
    ToyopucConnectionOptions,
    open_and_connect,
    read_dwords_chunked,
    read_dwords_single_request,
    read_words_chunked,
    read_words_single_request,
)


async def main() -> None:
    options = ToyopucConnectionOptions(
        host="192.168.250.100",
        port=1025,
        plc_profile="toyopuc:plus:extended",
    )

    async with await open_and_connect(options) as client:
        words = await read_words_single_request(client, "P1-D0000", 10)
        dwords = await read_dwords_single_request(client, "P1-D0100", 4)
        large_words = await read_words_chunked(client, "P1-D1000", 128)
        large_dwords = await read_dwords_chunked(client, "P1-D1200", 32)
        print(words, dwords, large_words[:4], large_dwords[:4])


asyncio.run(main())
```

## Bit-in-word

Use `.` for one bit inside a word. Use `:` for data type suffixes.

```python
import asyncio

from toyopuc import ToyopucConnectionOptions, open_and_connect, read_named, write_bit_in_word


async def main() -> None:
    options = ToyopucConnectionOptions(
        host="192.168.250.100",
        port=1025,
        plc_profile="toyopuc:plus:extended",
    )

    async with await open_and_connect(options) as client:
        before = await read_named(client, ["P1-D0100.3"])
        original_bit = bool(before["P1-D0100.3"])
        try:
            await write_bit_in_word(client, "P1-D0100", bit_index=3, value=True)
            snapshot = await read_named(client, ["P1-D0100.3"])
            print(snapshot)
        finally:
            await write_bit_in_word(client, "P1-D0100", bit_index=3, value=original_bit)


asyncio.run(main())
```

## Polling

```python
import asyncio

from toyopuc import ToyopucConnectionOptions, open_and_connect, poll


async def main() -> None:
    options = ToyopucConnectionOptions(
        host="192.168.250.100",
        port=1025,
        plc_profile="toyopuc:plus:extended",
    )

    async with await open_and_connect(options) as client:
        count = 0
        async for snapshot in poll(client, ["P1-D0000"], interval=1.0):
            print(snapshot)
            count += 1
            if count >= 3:
                break


asyncio.run(main())
```

## FR two-phase write

FR writes update RAM first. Persist the touched FR block only when you intentionally call the commit phase.

```python
from toyopuc import ToyopucDeviceClient


def main() -> None:
    with ToyopucDeviceClient(
        "192.168.250.100",
        1025,
        plc_profile="toyopuc:pc10g:pc10",
    ) as client:
        before = client.read_fr("FR000000")
        try:
            client.write_fr("FR000000", 0x1234, commit=False)
            after = client.read_fr("FR000000")
            print(before, after)
        finally:
            client.write_fr("FR000000", before, commit=False)

        # Call commit_fr only when the staged FR value is intentionally
        # persistent. Committed FR writes survive PLC power cycles.
        # client.commit_fr("FR000000", wait=True)


if __name__ == "__main__":
    main()
```

## Relay helpers

Relay hops are not probed automatically. Pass the hops you intend to use.

```python
from toyopuc import ToyopucDeviceClient


def main() -> None:
    with ToyopucDeviceClient(
        "192.168.250.100",
        1025,
        plc_profile="toyopuc:nano-10gx:compatible",
    ) as client:
        hops = "P1-L2:N2"
        status = client.relay_read_cpu_status(hops)
        words = client.relay_read_words(hops, "P1-D0000", count=4)
        print(status.run, words)


if __name__ == "__main__":
    main()
```

## Address reference table

| Form | Meaning | Example |
| --- | --- | --- |
| `P1-D0000` | Prefixed basic word address | `P1-D0000` |
| `P1-M0000` | Prefixed basic bit address | `P1-M0000` |
| `ES0000` | Direct extension word address | `ES0000` |
| `EP0000` | Direct extension bit address | `EP0000` |
| `U00000` | Direct U word address | `U00000` |
| `EB00000` | Direct EB word address | `EB00000` |
| `FR000000` | FR storage word address | `FR000000` |
| `P1-M0010W` | Packed 16-bit word view of a bit area | `P1-M0010W` |
| `P1-M0010L` / `P1-M0010H` | Low or high byte view of a packed bit area | `P1-M0010L` |
| `P1-D0100:S` | Signed 16-bit typed view | `P1-D0100:S` |
| `P1-D0100:D` | Unsigned 32-bit typed view | `P1-D0100:D` |
| `P1-D0100:L` | Signed 32-bit typed view | `P1-D0100:L` |
| `P1-D0100:F` | Float32 typed view | `P1-D0100:F` |
| `P1-D0100.3` | Bit 3 inside one word | `P1-D0100.3` |
