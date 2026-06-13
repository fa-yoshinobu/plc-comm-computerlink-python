# Getting Started

## Start Here

Use this package when you want the shortest Python path to TOYOPUC Computer Link communication through the public high-level API.

Recommended first path:

1. Install `toyopuc-computerlink`.
2. Choose the correct profile for your target.
3. Open one client and read `P1-D0000`.
4. Write only to a known-safe test word or bit after the first read is stable.

## First PLC Registers To Try

Start with these first:

- `P1-D0000`
- `P1-D0001`
- `P1-M0000`
- `P1-D0100:F`

Do not start with these:

- relay hops
- `FR` writes
- large chunked reads

## Minimal Synchronous Pattern

```python
from toyopuc import ToyopucDeviceClient

with ToyopucDeviceClient("192.168.250.100", 1025) as client:
    value = client.read("P1-D0000")
    print(value)
```

## Minimal Async Pattern

```python
from toyopuc import ToyopucConnectionOptions, open_and_connect

options = ToyopucConnectionOptions(host="192.168.250.100", port=1025)
```

If a profile is in use, basic area families should use the correct `P1-`, `P2-`, or `P3-` prefix.

## First Successful Run

Recommended order:

1. `client.read("P1-D0000")`
2. `client.write("P1-D0001", 1234)` only on a safe test word
3. `client.write("P1-M0000", 1)` only on a safe test bit
4. `read_named(plc, ["P1-D0000", "P1-D0100:F", "P1-D0000.0"])`

## Common Beginner Checks

If the first read fails, check these in order:

- correct host and port
- correct profile
- correct `P1-`, `P2-`, or `P3-` prefix
- start with `P1-D0000` instead of `FR` or relay addresses

## Next Pages

- [Supported PLC Registers](./SUPPORTED_REGISTERS.md)
- [Latest Communication Verification](./LATEST_COMMUNICATION_VERIFICATION.md)
- [User Guide](./USER_GUIDE.md)
