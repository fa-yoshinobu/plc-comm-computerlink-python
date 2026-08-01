# Usage guide

## Recommended entry points

| Entry point | When to use it |
| --- | --- |
| `ToyopucConnectionOptions` | Store one explicit connection profile for async code. |
| `open_and_connect(options)` | Create and connect an async high-level client. |
| `read_typed` / `write_typed` | Read or write one typed value. |
| `read_named` | Read an ordered named collection of word, typed, and bit-in-word entries. |
| `read_words_single_request` / `read_dwords_single_request` | Keep a contiguous read as one logical request. |
| `write_bit_in_word` | Change one bit inside a word with read-modify-write. |
| `poll` | Repeatedly yield one named read result. |
| `ToyopucDeviceClient` | Use the synchronous high-level API. |

A `ResolvedDevice` is bound to the exact canonical PLC profile that resolved it. Passing it to a client configured for any other profile is rejected before request construction or transport activity, even when both profiles share addressing rules. Resolve the device again through the destination client instead of reusing it across profiles.

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

## Connection reuse and concurrent requests

Keep one client open for repeated reads, writes, and polling. Each sync or async
client admits ordinary operations in arrival order and uses its transport for
one operation at a time. Different client instances remain independent.
Connection is lazy: the first operation connects when necessary. `close()`
interrupts the active operation and rejects operations already queued in that
transport generation; a later new operation may connect again.

The configured `timeout` is one absolute bound for explicit connection
establishment and, separately, one absolute bound for each request. Connection
timing starts before IPv4 DNS. The same deadline covers first-IPv4 selection,
TCP/UDP socket creation, UDP bind/connect, TCP no-delay configuration, and final
client adoption. An IPv4 literal bypasses DNS. No phase or retry receives a
fresh timeout, and IPv6 is never attempted.

If a platform resolver or socket call cannot be cancelled, timeout or async
caller cancellation returns without adopting it. A late socket is closed by
the isolated connection worker and cannot send a request or change client
state. Absolute expiry raises `ToyopucTimeoutError`; a native connection failure
that finishes before expiry raises `ToyopucTransportError` with its cause.

## Read single

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
        transport="tcp",
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

## Named read collection

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
        read_result = await read_named(client, ["P1-D0100:F", "P1-D0102:S", "P1-D0103.3"])
        print(read_result)


asyncio.run(main())
```

## Batching and request boundaries

`ToyopucDeviceClient.read` reads a contiguous range. Its `count` is required and
it always returns a list. Use `read_one` only when a scalar is intended.
`read`, `read_devices`, relay read aggregates, and `read_named` preserve caller
order and automatically split only when a protocol limit, route family, or
PC10 block boundary requires another read request. Every entry is indivisible,
the entire plan is validated before transport, and all requests hold one FIFO
client turn. The result is non-atomic because the PLC can change between
requests; the API returns all values or raises without returning a partial
result.

Writes are different: `write`, `write_many`, typed array writes, and their relay
forms reject a plan that would require multiple requests before transport.

For contiguous word ranges, use `read_words_single_request`,
`read_dwords_single_request`, `write_words_single_request`, or
`write_dwords_single_request` when one wire request is itself required. There
are no public chunking switches. Write separate explicit calls only when
partial completion is acceptable.

`write_bit_in_word` is an explicit read-modify-write helper, not part of read
aggregation. It holds one exclusive FIFO turn across its read and write, but it
is not PLC-atomic: PLC logic or another connection can still change the word
between the two requests.

## Timeouts, cancellation, and retry safety

One monotonic deadline covers IPv4 resolution, lazy connect, transmit, receive,
and response decode for each request. Timeout and cancellation retire the current transport.
Automatic retries are allowed only for connection failures proven to occur
before a send attempt, and those retries share the original deadline. After a
request may have been sent, neither reads nor writes are automatically resent.

Timeout, cancellation, explicit close, not-connected state, transport failure,
malformed response, and PLC NG responses have distinct exception types. A
state-changing operation that may have been sent raises
`ToyopucOperationOutcomeUnknownError`; inspect its `reason` and reconcile PLC
state before deciding whether another write is safe.

## Block reads

```python
import asyncio

from toyopuc import (
    ToyopucConnectionOptions,
    open_and_connect,
    read_dwords_single_request,
    read_words_single_request,
)


async def main() -> None:
    options = ToyopucConnectionOptions(
        host="192.168.250.100",
        port=1025,
        transport="tcp",
        plc_profile="toyopuc:plus:extended",
    )

    async with await open_and_connect(options) as client:
        words = await read_words_single_request(client, "P1-D0000", 10)
        dwords = await read_dwords_single_request(client, "P1-D0100", 4)
        print(words, dwords)


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
        transport="tcp",
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
        transport="tcp",
        plc_profile="toyopuc:plus:extended",
    )

    async with await open_and_connect(options) as client:
        count = 0
        async for read_result in poll(client, ["P1-D0000"], interval=1.0):
            print(read_result)
            count += 1
            if count >= 3:
                break


asyncio.run(main())
```

## Operational recipes

The samples directory includes two read-only operational recipes:

- `samples/multi_plc_monitor.py` reads one or more PLCs in one loop and writes CSV rows as `timestamp,plc,tag,value`.
- `samples/config_polling.py` runs the same polling workflow from a JSON or YAML configuration file.

Both recipes use the same reconnect states as `polling_reconnect.py`: `connected`, `lost`, `reconnecting`, and `recovered`. The default reconnect backoff starts at 1 second and caps at 30 seconds.

Validate a monitor setup without opening a PLC connection:

```bash
python samples/multi_plc_monitor.py --plc line-a=192.168.250.100,toyopuc:plus:extended,1025,tcp --tag d0100=P1-D0100:U --cycles 1 --dry-run
```

Validate a configuration file without opening a PLC connection:

```bash
python samples/config_polling.py --config samples/config_polling.example.json --dry-run
```

## FR two-phase write

FR writes update RAM first. Persist the touched FR block only when you intentionally call the commit phase.

```python
from toyopuc import ToyopucDeviceClient


def main() -> None:
    with ToyopucDeviceClient(
        "192.168.250.100",
        1025,
        transport="tcp",
        plc_profile="toyopuc:pc10g:pc10",
    ) as client:
        before = client.read_fr_one("FR000000")
        try:
            client.write_fr("FR000000", 0x1234)
            after = client.read_fr_one("FR000000")
            print(before, after)
        finally:
            client.write_fr("FR000000", before)

        # Call commit_fr only when the staged FR value is intentionally
        # persistent. Committed FR writes survive PLC power cycles.
        # client.commit_fr("FR000000")


if __name__ == "__main__":
    main()
```

FR work-area values must be integers in `0..65535`. The library rejects negative, overflowing, Boolean, fractional, and string values instead of masking or converting them.

Use only `write_fr` / `relay_write_fr` for FR writes. Generic `write` and
`write_many`, typed dword/float, and bit-in-word write helpers reject FR before
transport. This is a breaking contract: callers that previously passed FR to a
generic or typed write must migrate to the explicit FR work-area API and invoke
`commit_fr` separately only when persistence is intended.

## Relay helpers

Relay hops are not probed automatically. Pass the hops you intend to use.

Relay strings use decimal values only. Component notation accepts `P0..P15`,
`L0..L15`, and station `N1..N65535`, for example `P10-L11:N20`. Direct notation
accepts link `0..255` and station `1..65535`, for example `171:32`.
Hexadecimal prefixes/suffixes and A-F digits are invalid.

```python
from toyopuc import ToyopucDeviceClient


def main() -> None:
    with ToyopucDeviceClient(
        "192.168.250.100",
        1025,
        transport="tcp",
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

## Traffic statistics

Call `client.traffic_stats()` for cumulative request, transmitted-byte, and received-byte counts.
