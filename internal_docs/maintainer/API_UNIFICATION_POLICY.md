# API Unification Policy

This document defines the public API rules for the TOYOPUC Python library.
The current high-level helper surface follows these rules as of 0.1.8.

## Purpose

- Keep the user-facing API aligned with the TOYOPUC .NET library.
- Keep protocol-oriented access available for advanced use.
- Add asyncio support without inventing different method names.

## Public API Layers

The library must keep two explicit layers.

1. `ToyopucClient`
   Low-level API for numeric addresses, raw commands, relay frames, and FR details.
2. `ToyopucDeviceClient`
   High-level API for string device addresses.

Planned asyncio parity must use separate async classes.

1. `AsyncToyopucClient`
2. `AsyncToyopucDeviceClient`

Do not expose provisional top-level constructors such as `Toyopuc(...)`.

The top-level async helper surface is:

- `ToyopucConnectionOptions`
- `open_and_connect`
- `normalize_address`
- `parse_device_address`
- `try_parse_device_address`
- `format_device_address`
- `read_typed`
- `write_typed`
- `write_bit_in_word`
- `read_named`
- `poll`
- `read_words_single_request`
- `read_dwords_single_request`
- `write_words_single_request`
- `write_dwords_single_request`
- `read_words_chunked`
- `read_dwords_chunked`
- `write_words_chunked`
- `write_dwords_chunked`

## Naming Rules

High-level generic device access must use these names.

- `read`
- `write`
- `read_many`
- `write_many`
- `read_dword`
- `write_dword`
- `read_dwords`
- `write_dwords`
- `read_float32`
- `write_float32`
- `read_float32s`
- `write_float32s`
- `read_fr`
- `write_fr`
- `commit_fr`
- `resolve_device`
- `relay_read`
- `relay_write`
- `relay_read_many`
- `relay_write_many`

Low-level typed access must keep explicit protocol-oriented names.

- `read_words`
- `write_words`
- `read_bytes`
- `write_bytes`
- `read_bit`
- `write_bit`
- `read_dwords`
- `write_dwords`
- `read_float32s`
- `write_float32s`
- `read_ext_words`
- `write_ext_words`
- `pc10_block_read`
- `pc10_block_write`
- `read_clock`
- `write_clock`
- `read_cpu_status`

Do not add a second high-level naming family such as `read_word`, `write_word`, or `read_device` when the input is already a string device address.

## 32-Bit Value Rules

The library should distinguish raw 32-bit integers from IEEE 754 floating-point values.

- `dword` means a raw 32-bit unsigned value stored across two PLC words.
- Signed 32-bit helpers, if added later, should be named `read_int32` and `write_int32`.
- Floating-point helpers should use `float32` in the public name, not plain `float`.

Default 32-bit word-pair interpretation:

- The default contract is protocol-native low-word-first ordering.
- If alternate word order must be supported, use an explicit keyword such as `word_order`.
- Avoid public names such as `read_float_swap`.

## Async Rules

Async method names must stay identical to sync method names.
The async boundary is expressed by the async class and `await`, not by `_async` suffixes.

Examples:

- `await client.connect()`
- `await client.read("P1-D0000")`
- `await client.write("P1-M0000", True)`
- `await client.read_many([...])`
- `await client.commit_fr("FR000000", wait=True)`

Async classes must also support:

- `async with AsyncToyopucClient(...) as client:`
- `async with AsyncToyopucDeviceClient(...) as client:`

Async methods must follow these rules.

- Keep argument names and order aligned with the sync method.
- Return the same logical result shape as the sync method.
- Keep the same exception classes where practical.

## Internal Naming Rules

Private helper names must describe the resolved object or protocol path they operate on.

Avoid vague names such as:

- `_read_one`
- `_write_one`
- `_relay_read_one`
- `_relay_write_one`
- `_offset`

Prefer names such as:

- `_read_resolved_device`
- `_write_resolved_device`
- `_relay_read_resolved_device`
- `_relay_write_resolved_device`
- `_offset_resolved_device`
- `_pack_uint32_low_word_first`
- `_unpack_uint32_low_word_first`
- `_pack_float32_low_word_first`
- `_unpack_float32_low_word_first`

When a helper is protocol-family specific, keep that family in the name.

- `_read_pc10_multi_words`
- `_pack_pc10_multi_word_payload`
- `_resolve_ext_bit`

## Documentation Rules

README and samples must prefer these canonical entry points.

- Sync quick start: `ToyopucDeviceClient`
- Async quick start: `AsyncToyopucDeviceClient`
- Advanced samples: `ToyopucClient` or `AsyncToyopucClient`

README must not use undocumented aliases as the primary form.

## Address Helper Rules

Public application helpers must use string-device notation and must not require
callers to know protocol command units.

- Use `normalize_address(...)` when only canonical text is needed.
- Use `parse_device_address(...)` when dtype or bit-in-word notation must be retained.
- Use `try_parse_device_address(...)` for UI validation paths that should not raise.
- Use `format_device_address(...)` when stored address metadata must be rendered back to canonical text.
- Keep `toyopuc.address.parse_address(...)` available for protocol-oriented code that already knows the command unit.

## Protocol Option Rules

TOYOPUC-specific options must stay explicit at the API boundary.

- Connection helpers expose `transport`, `local_port`, `timeout`, `retries`, `retry_delay`, `recv_bufsize`, and `trace_hook`.
- Device range validation uses explicit `profile` parameters.
- Relay access uses explicit `hops` arguments and the public relay-hop parse/format helpers.

## Addressing Matrix Rules

Device/profile range knowledge must be reviewable from code, not only from prose.

- Use `ToyopucDeviceCatalog.get_device_matrix(profile)` for release-review tables and UI option generation.
- Matrix rows include profile, area, access mode, unit, suffixes, supported ranges, and example start addresses.
- Hardware evidence can update range data, but the matrix API shape should remain stable.

## Semantic Atomicity Rules

High-level helpers must keep one user-visible logical value intact unless the
caller chooses a chunked helper.

- `*_single_request` helpers keep contiguous logical access on the single-request path.
- `*_chunked` helpers are explicit opt-in paths and must keep 32-bit values aligned.
- FR segmentation and PC10 block segmentation are allowed only at protocol-defined boundaries.

## Stability Rules

- Sync naming remains the base contract.
- Async support must be additive.
- Do not keep legacy public class aliases once the canonical class names are published.
