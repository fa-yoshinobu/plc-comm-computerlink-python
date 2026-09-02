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
| A contiguous or multi-device operation can require multiple protocol requests, incompatible protocol groups, or a PC10 block boundary crossing. | Read aggregates validate the complete plan and split only when necessary while holding one FIFO turn. The result is ordered and all-or-error, but not an atomic PLC snapshot. Writes still reject every multi-request plan before communication. |

## Symptom: a write value is rejected instead of truncated

This is intentional. Semantic bit writes accept only actual `bool` values; byte writes
accept integers in `0..255`; word writes accept integers in `0..65535`; and
dword writes accept integers in `0..4294967295`. Boolean values are not word
or dword integers. Fractional values and numeric strings are never converted.
Raw frame and payload builders are the wire layer and therefore use validated
integer `0`/`1` bit fields rather than semantic Boolean values.
All direct, relay, single, aggregate, and explicit bit-in-word semantic writes
perform this validation before entering the sync FIFO or async lock. An invalid
value therefore does not wait behind active communication and sends no request.

## Symptom: a bit-in-word update races with another writer

`write_bit_in_word` and `relay_write_bit_in_word` always issue one word read
followed by one word write under one local FIFO turn and one absolute deadline.
They are not PLC-atomic, so PLC logic or another connection can update the word
between requests. Use PLC-side coordination when the whole word is shared. A
cancellation or failure after the write may have started is outcome-unknown;
retire and reconnect the transport and reconcile PLC state before retrying.

## Symptom: an IPv6 PLC endpoint is rejected

Computerlink connections are IPv4-only. TCP and UDP accept an IPv4 literal or
a hostname that resolves to IPv4. An IPv6 literal, including an IPv4-mapped
IPv6 literal such as `::ffff:192.0.2.1`, raises `ValueError` before a socket is
created. For a hostname with multiple results, the library uses the first IPv4
result in resolver order; a hostname with no IPv4 result fails without falling
back to IPv6.

## Symptom: not every resolved or retried connection phase gets a full timeout

This is intentional. One absolute connection deadline covers IPv4 DNS,
first-IPv4 selection, socket creation, UDP bind/connect, TCP configuration, and
client adoption. Pre-send retries use only the time remaining to that same
deadline. An IPv4 literal bypasses DNS. If an operating-system resolver or
socket call finishes after timeout or async cancellation, its result is not
adopted and any late socket is closed.

## Symptom: a fixed-port UDP client cannot reconnect after a timeout

Connection timeouts, retry delays, and polling intervals have a common
inclusive maximum of `2,147,483.647` seconds (`2,147,483,647` milliseconds,
about 24.86 days). Timeouts and polling intervals must be greater than zero;
retry delay may be zero. Invalid values raise `ValueError` before communication
or waiting starts.

A connected UDP socket accepts datagrams only from its configured PLC endpoint.
However, Computerlink has no request serial that can distinguish a late response
from a later request to the same endpoint. After a request may have been sent and
a fixed-local-port UDP session times out or fails, that client instance is
terminal. Create a new client only after the network can no longer contain the
late response; prefer `local_port=0` unless a fixed source port is required.

When a state-changing request may already have reached the PLC, Python raises
`ToyopucOperationOutcomeUnknownError`. Reconcile PLC state before retrying.

Malformed command-specific data is handled inside the same post-send
lifecycle. Reads raise `ToyopucProtocolError`; state-changing calls raise
`ToyopucOperationOutcomeUnknownError` with malformed-response reason and the
protocol error as their cause. The affected transport is retired, and a
fixed-local-port UDP client is tainted. Validation failures found before send do
not retire the transport.

Cancellation does not prove that a write was unapplied. Async clients cancel
their native socket wait and retire that transport; when a state-changing
request may already have been sent, they raise
`ToyopucOperationOutcomeUnknownError` instead of implying non-application.

## Symptom: a multi-address `read_named` call is rejected before transport

| Root cause | Fix |
| --- | --- |
| The complete named address set does not fit one compatible protocol request. | Reduce the address set or issue multiple explicit calls. `read_named` and each `poll` cycle never split automatically. |

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
        snapshot = await read_named(client, ["P1-D0000:U", "P1-D0001:U"])
        print(snapshot["P1-D0000:U"], snapshot["P1-D0001:U"])


asyncio.run(main())
```

## Symptom: a request was not retried after a disconnect

Only a connection failure proven to happen before any send attempt is eligible
for automatic retry. Once a read or write may have been sent, the client retires
the transport and does not resend it. This avoids applying a response from a
different request or repeating a state change whose outcome is unknown.

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
| `write_fr_work_area(...)` updates only the FR work area. It never commits flash. | Call `commit_fr_block_by_device()` separately with the first word of exactly one block only when persistence is intended. |
| An FR word is an unsigned 16-bit value. | Pass an integer in `0..65535`; Boolean, fractional, string, negative, and overflowing values are rejected before communication. |

FR writes are intentionally available only through `write_fr_work_area` /
`relay_write_fr_work_area`. Generic, aggregate, typed dword/float, and bit-in-word write
APIs reject an FR address before opening or using the transport. Migrate an
intentional FR write to the explicit FR work-area API so its separate commit
lifecycle remains visible.

```python
from toyopuc import ToyopucDeviceClient


def main() -> None:
    with ToyopucDeviceClient(
        "192.168.250.100", 1025, transport="tcp", plc_profile="toyopuc:pc10g:pc10"
    ) as client:
        # Use only a test FR address. commit_fr_block_by_device persists the staged value
        # to flash and does not restore the previous value automatically.
        client.write_fr_work_area("FR000000", 0x1234)
        client.commit_fr_block_by_device("FR000000")


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

Relay text is decimal-only. Use `P10-L11:N20` for component notation or
`171:32` for a direct link/station pair. Hexadecimal prefixes, hexadecimal
suffixes, and A-F digits are rejected; `format_relay_hop()` also returns decimal
text.

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
