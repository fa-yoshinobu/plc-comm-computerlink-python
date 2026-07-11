# PLC profiles

Canonical profile names are part of the public configuration contract. The library rejects missing, blank, alias, and abbreviated profile strings immediately.
Use `plc_profile_descriptors()` or `ToyopucPlcProfiles.profile_descriptors()`
for a UI that needs canonical names, display labels, connection eligibility,
and base-profile metadata. Store the canonical profile string, not the display
name.

Device-family notation, type suffixes, practical range notes, and model-specific writable range summaries are shared across the Computerlink libraries. Use the common [Computerlink Device Ranges](https://fa-yoshinobu.github.io/plc-comm-docs-site/plc-setup/computerlink/device-ranges/) page for those details.

## Explicit selection is required

Always pass one exact canonical profile name through `plc_profile`.

- No profile is inferred from the PLC model, CPU status, address string, host, port, or transport.
- `toyopuc:generic` is not applied automatically when the profile is omitted.
- Old names, short names, aliases, and case variants are rejected.
- Address and dtype inputs may be normalized for convenience, but profile names are not.

## Canonical profiles

| Canonical profile | Hardware | Profile-specific cautions |
| --- | --- | --- |
| `toyopuc:generic` | Any TOYOPUC Computerlink | Broad range set; prefer a hardware-specific profile when the model is known. |
| `toyopuc:plus:standard` | TOYOPUC-Plus | U, EB, FR, GM, GX, and GY are not in the standard range. |
| `toyopuc:plus:extended` | TOYOPUC-Plus | Recommended for first examples; U, GM, GX, and GY are available. |
| `toyopuc:nano-10gx:native` | Nano 10GX | Native addressing; relay hops are still explicit. |
| `toyopuc:nano-10gx:compatible` | Nano 10GX | Compatible mode; pass relay hops manually when relaying. |
| `toyopuc:pc10g:standard-pc3jg` | PC10G | FR is not included. |
| `toyopuc:pc10g:pc10` | PC10G | PC10 addressing; FR is available. |
| `toyopuc:pc3jx:pc3-separate` | PC3JX | GM, GX, GY, EB, and FR are not included. |
| `toyopuc:pc3jx:plus-expansion` | PC3JX | B, EB, and FR are not included. |
| `toyopuc:pc3jg:pc3jg` | PC3JG | FR is not included. |
| `toyopuc:pc3jg:pc3-separate` | PC3JG | FR is not included. |

## How to select a profile

```python
from toyopuc import ToyopucPlcProfiles


def main() -> None:
    profile = ToyopucPlcProfiles.from_name("toyopuc:plus:extended")
    print(profile.name)


if __name__ == "__main__":
    main()
```

## Connection snippet

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
        value = await read_typed(client, "P1-D0000", "U")
        print(value)


asyncio.run(main())
```

## Selection table

| If your PLC is | Start with |
| --- | --- |
| TOYOPUC-Plus with U or GM/GX/GY access | `toyopuc:plus:extended` |
| TOYOPUC-Plus without extended ranges | `toyopuc:plus:standard` |
| Nano 10GX native configuration | `toyopuc:nano-10gx:native` |
| Nano 10GX compatible configuration | `toyopuc:nano-10gx:compatible` |
| PC10G PC10 addressing | `toyopuc:pc10g:pc10` |
| PC10G PC3JG-compatible standard addressing | `toyopuc:pc10g:standard-pc3jg` |
| PC3JX PC3 separate addressing | `toyopuc:pc3jx:pc3-separate` |
| PC3JX plus expansion addressing | `toyopuc:pc3jx:plus-expansion` |
| PC3JG mode | `toyopuc:pc3jg:pc3jg` |
| Unknown hardware during exploration | `toyopuc:generic` |
