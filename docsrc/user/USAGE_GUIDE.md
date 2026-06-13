# Usage guide

## Recommended entry points

| Function | Use |
| --- | --- |
| `open_and_connect` | Create and connect an async high-level client. |
| `read_typed` | Read one word, dword, signed value, or float. |
| `write_typed` | Write one word, dword, signed value, or float. |
| `read_named` | Read a mixed snapshot by address string. |
| `read_words_single_request` | Read a contiguous word block as one logical request. |
| `read_dwords_single_request` | Read a contiguous dword block as one logical request. |
| `read_words_chunked` | Read a larger word block in explicit chunks. |
| `read_dwords_chunked` | Read a larger dword block in explicit chunks. |
| `write_bit_in_word` | Change one bit inside a word register. |
| `poll` | Yield repeated named snapshots. |

## Connection

```python
import asyncio
from toyopuc import ToyopucConnectionOptions, open_and_connect, read_typed

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
        value = await read_typed(client, "P1-D0000", "U")
        print(f"P1-D0000 = {value}")

asyncio.run(main())
```

`ToyopucConnectionOptions` holds the network settings and the profile selector for your PLC. Use `transport="udp"` with UDP port `1035` when your PLC is configured for UDP.

## Read a single value

```python
import asyncio
from toyopuc import ToyopucConnectionOptions, open_and_connect, read_typed

async def main() -> None:
    options = ToyopucConnectionOptions(host="192.168.250.100", port=1025, plc_profile="toyopuc:plus:extended")
    async with await open_and_connect(options) as client:
        word = await read_typed(client, "P1-D0000", "U")
        signed = await read_typed(client, "P1-D0002", "S")
        counter = await read_typed(client, "P1-D0010", "D")
        print(f"word={word} signed={signed} counter={counter}")

asyncio.run(main())
```

| Type suffix | Example | Meaning |
| --- | --- | --- |
| `U` | `P1-D0000:U` | Unsigned 16-bit word. |
| `S` | `P1-D0000:S` | Signed 16-bit word. |
| `D` | `P1-D0000:D` | Unsigned 32-bit value from two words. |
| `L` | `P1-D0000:L` | Signed 32-bit value from two words. |
| `F` | `P1-D0000:F` | IEEE-754 float32 from two words. |

## Write a single value

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

Use a test word register that you control. Match the read and write type codes so the same number of words is used.

## Named snapshot read

```python
import asyncio
from toyopuc import ToyopucConnectionOptions, open_and_connect, read_named

async def main() -> None:
    options = ToyopucConnectionOptions(host="192.168.250.100", port=1025, plc_profile="toyopuc:plus:extended")
    async with await open_and_connect(options) as client:
        snapshot = await read_named(
            client,
            ["P1-D0000", "P1-D0002:S", "P1-D0010:D", "P1-D0020:F", "P1-D0000.3"],
        )
        print(f"snapshot = {snapshot}")

asyncio.run(main())
```

`read_named` returns a dictionary keyed by the address strings you supplied.

## Contiguous block reads

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
    options = ToyopucConnectionOptions(host="192.168.250.100", port=1025, plc_profile="toyopuc:plus:extended")
    async with await open_and_connect(options) as client:
        words = await read_words_single_request(client, "P1-D0000", 8)
        dwords = await read_dwords_single_request(client, "P1-D0010", 4)
        more_words = await read_words_chunked(client, "P1-D0100", 96, max_words_per_request=32)
        more_dwords = await read_dwords_chunked(client, "P1-D0200", 48, max_dwords_per_request=16)
        print(f"words={words} dwords={dwords} more_words={len(more_words)} more_dwords={len(more_dwords)}")

asyncio.run(main())
```

Use the single-request helpers when one contiguous operation is important. Use the chunked helpers when the caller accepts multiple requests.

## Bit in word

```python
import asyncio
from toyopuc import ToyopucConnectionOptions, open_and_connect, read_named, write_bit_in_word

async def main() -> None:
    options = ToyopucConnectionOptions(host="192.168.250.100", port=1025, plc_profile="toyopuc:plus:extended")
    async with await open_and_connect(options) as client:
        await write_bit_in_word(client, "P1-D0100", bit_index=3, value=True)
        snapshot = await read_named(client, ["P1-D0100.3"])
        print(f"P1-D0100.3 = {snapshot['P1-D0100.3']}")

asyncio.run(main())
```

Dot notation such as `P1-D0100.3` reads one bit inside a word. Use `:D` when you want a 32-bit value.

## Polling

```python
import asyncio
from toyopuc import ToyopucConnectionOptions, open_and_connect, poll

async def main() -> None:
    options = ToyopucConnectionOptions(host="192.168.250.100", port=1025, plc_profile="toyopuc:plus:extended")
    async with await open_and_connect(options) as client:
        count = 0
        async for snapshot in poll(client, ["P1-D0000", "P1-D0002:S", "P1-D0000.3"], interval=1.0):
            print(f"snapshot {count + 1}: {snapshot}")
            count += 1
            if count == 3:
                break

asyncio.run(main())
```

`poll` is an async generator. Break the loop when your application has collected enough samples.

## FR file-register flash helpers

### Read current FR values

```python
import asyncio
from toyopuc import ToyopucConnectionOptions, open_and_connect

async def main() -> None:
    options = ToyopucConnectionOptions(host="192.168.250.100", port=1025, plc_profile="toyopuc:nano-10gx:native")
    async with await open_and_connect(options) as client:
        values = await client.read_fr("FR000000", count=4)
        print(f"FR000000..FR000003 = {values}")

asyncio.run(main())
```

### Stage a write

```python
import asyncio
from toyopuc import ToyopucConnectionOptions, open_and_connect

async def main() -> None:
    options = ToyopucConnectionOptions(host="192.168.250.100", port=1025, plc_profile="toyopuc:nano-10gx:native")
    async with await open_and_connect(options) as client:
        await client.write_fr("FR000000", 0x1234, commit=False)
        value = await client.read_fr("FR000000")
        print(f"staged FR000000 = 0x{value:04X}")

asyncio.run(main())
```

### Commit

```python
import asyncio
from toyopuc import ToyopucConnectionOptions, open_and_connect

async def main() -> None:
    options = ToyopucConnectionOptions(host="192.168.250.100", port=1025, plc_profile="toyopuc:nano-10gx:native")
    async with await open_and_connect(options) as client:
        await client.commit_fr("FR000000", wait=True)
        value = await client.read_fr("FR000000")
        print(f"committed FR000000 = 0x{value:04X}")

asyncio.run(main())
```

> **Caution:** FR writes are two-phase. Staging without committing leaves the value in RAM. A power cycle will revert it to the last committed value.

## Relay helpers

```python
from toyopuc import ToyopucDeviceClient

host = "192.168.250.100"
port = 1025
hops = "P1-L2:N2"

with ToyopucDeviceClient(host, port) as client:
    values = client.relay_read_words(hops, "P1-D0000", count=1)
    print(f"P1-D0000 through relay = {values[0]}")
```

Relay topology is not auto-discovered. The current API passes relay hops explicitly to `relay_*` methods; `ToyopucConnectionOptions` does not define a `relay_hops` field.

## Address reference table

| Form | Example | Meaning |
| --- | --- | --- |
| Plain word | `P1-D0100` | Unsigned 16-bit word by default. |
| `:U` | `P1-D0100:U` | Unsigned 16-bit word. |
| `:S` | `P1-D0100:S` | Signed 16-bit word. |
| `:D` | `P1-D0100:D` | Unsigned 32-bit value. |
| `:L` | `P1-D0100:L` | Signed 32-bit value. |
| `:F` | `P1-D0100:F` | Float32 value. |
| `.n` | `P1-D0100.3` | One bit inside a word; `n` is `0` through `F`. |
| `W` | `P1-M0010W` | Packed 16-bit word view of a bit-area address. |
| `H` | `P1-M0010H` | High byte of a packed bit-area word. |
| `L` | `P1-M0010L` | Low byte of a packed bit-area word. |
