# Gotchas

## Address prefix missing

If your read raises an "invalid address" error:

The basic area families require a `P1-`, `P2-`, or `P3-` prefix. `D0000` alone is rejected.

Fix:

```python
address = "P1-D0000"
```

## `.D` returns bit 13 instead of a 32-bit value

If reading `P1-D0100.D` returns a single bit value instead of a 32-bit integer:

`.D` on a word address means bit offset 13, not a 32-bit dword view.

Fix:

```python
from toyopuc import read_named, read_typed

async def read_dword_value(client) -> tuple[int, int]:
    value = await read_typed(client, "P1-D0100", "D")
    snapshot = await read_named(client, ["P1-D0100:D"])
    return int(value), int(snapshot["P1-D0100:D"])
```

## FR value reverts after power cycle

If an FR write does not survive a power cycle:

FR writes are staged in RAM and require an explicit commit to persist to flash.

Fix:

```python
async def persist_fr_value(client) -> None:
    await client.write_fr("FR000000", 0x1234, commit=False)
    await client.commit_fr("FR000000", wait=True)
```

## Relay reads fail silently

If relay reads return no data and no error:

Relay hops are not probed automatically.

Fix:

```python
hops = "P1-L2:N2"
values = client.relay_read_words(hops, "P1-D0000", count=1)
```

## Packed bit notation misread

If `P1-M0010W` or similar is parsed unexpectedly:

`W`/`H`/`L` appended to a bit-area address is packed-word notation, not a type suffix.

Fix:

```python
packed_word = client.read("P1-M0010W")
high_byte = client.read("P1-M0010H")
low_byte = client.read("P1-M0010L")
```

`W` = full 16-bit word, `H` = high byte, `L` = low byte.

## Constructor uses transport, not protocol

If constructing a client raises `TypeError: unexpected keyword argument 'protocol'`:

The public client constructors use `transport="tcp"` or `transport="udp"`.

Fix:

```python
from toyopuc import ToyopucDeviceClient

with ToyopucDeviceClient("192.168.250.100", 1035, transport="udp") as client:
    value = client.read("P1-D0000")
    print(f"P1-D0000 = {value}")
```
