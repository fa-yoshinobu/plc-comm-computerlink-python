# TOYOPUC Computerlink Python API Reference

This page is a user-facing index of the public Python TOYOPUC Computerlink API
surface. Use the usage guide for examples, and this page when you need to find
the operation name for a specific Computerlink workflow.

For normal application code, prefer `open_and_connect` plus the high-level
helper functions. Low-level clients remain exported for advanced and maintainer
workflows.

## Connection And PLC Control

| Operation | Public API |
| --- | --- |
| Open a ready-to-use connection | `open_and_connect`, `ToyopucConnectionOptions` |
| Low-level sync/async clients | `ToyopucClient`, `AsyncToyopucClient`, `ToyopucDeviceClient`, `AsyncToyopucDeviceClient` |
| Raw frame exchange | `send_raw`, `send_payload`, `last_tx`, `last_rx` |
| Clock and CPU status | `read_clock`, `write_clock`, `read_cpu_status`, `read_cpu_status_a0`, `read_cpu_status_a0_raw` |
| Scan control | `resume_scan`, `stop_scan`, `release_scan_stop` |
| Trace capture | `ToyopucTraceDirection`, `ToyopucTraceFrame` |

## Device Operations

| Operation | Public API |
| --- | --- |
| Word and byte access | `read_words`, `write_words`, `read_bytes`, `write_bytes` |
| Bit access | `read_bit`, `write_bit` |
| 32-bit values | `read_dword`, `write_dword`, `read_dwords`, `write_dwords` |
| Float32 values | `read_float32`, `write_float32`, `read_float32s`, `write_float32s` |
| Multi-point access | `read_words_multi`, `write_words_multi`, `read_bytes_multi`, `write_bytes_multi` |
| Extended area access | `read_ext_words`, `write_ext_words`, `read_ext_bytes`, `write_ext_bytes`, `read_ext_multi`, `write_ext_multi` |
| PC10 block and multi access | `pc10_block_read`, `pc10_block_write`, `pc10_multi_read`, `pc10_multi_write` |
| File register access | `read_fr_words`, `write_fr_words`, `write_fr_words_ex`, `commit_fr_block`, `commit_fr_range`, `write_fr_words_committed`, `fr_register` |
| Relay access | `relay_command`, `relay_nested`, `send_via_relay`, `relay_read_words`, `relay_write_words`, `relay_read_clock`, `relay_write_clock`, `relay_resume_scan`, `relay_stop_scan`, `relay_release_scan_stop`, `relay_read_cpu_status`, `relay_read_cpu_status_a0`, `relay_read_cpu_status_a0_raw` |
| Relay file register access | `relay_write_fr_words`, `relay_write_fr_words_ex`, `relay_fr_register`, `relay_commit_fr_block`, `relay_commit_fr_range`, `relay_wait_fr_write_complete` |

## High-Level Helpers

| Operation | Public API |
| --- | --- |
| Address parsing and formatting | `ToyopucAddress`, `parse_device_address`, `try_parse_device_address`, `format_device_address`, `normalize_address` |
| Address encoding helpers | `parse_address`, `parse_prefixed_address`, `encode_word_address`, `encode_byte_address`, `encode_bit_address`, `encode_program_word_address`, `encode_program_byte_address`, `encode_program_bit_address`, `encode_exno_bit_u32`, `encode_exno_byte_u32`, `split_u32_words`, `encode_ext_no_address`, `fr_block_ex_no`, `encode_fr_word_addr32` |
| Device resolver | `ResolvedDevice`, `resolve_device` |
| Typed values | `read_typed`, `write_typed` |
| Named snapshots and polling | `read_named`, `poll` |
| Word/dword reads | `read_words`, `read_dwords` |
| Single-request reads/writes | `read_words_single_request`, `read_dwords_single_request`, `write_words_single_request`, `write_dwords_single_request` |
| Explicit chunked reads/writes | `read_words_chunked`, `read_dwords_chunked`, `write_words_chunked`, `write_dwords_chunked` |
| Bit-in-word write | `write_bit_in_word` |

## Profiles, Relay, And Diagnostics

| Operation | Public API |
| --- | --- |
| Profile lookup | `ToyopucPlcProfiles`, `ToyopucPlcProfile`, `ToyopucAddressingOptions`, `display_name` |
| Device range catalog | `ToyopucDeviceCatalog`, `ToyopucAreaDescriptor`, `ToyopucAddressRange`, `ToyopucDeviceMatrixRow` |
| Relay helpers | `RelayLayer`, `parse_relay_hops`, `normalize_relay_hops`, `format_relay_hop` |
| Parsed payload types | `ClockData`, `CpuStatusData` |
| Errors | `ToyopucError`, `ToyopucProtocolError`, `ToyopucTimeoutError` |

## Public Symbol Index

The package exports these public names from `toyopuc.__all__`:

`AsyncToyopucClient`, `AsyncToyopucDeviceClient`, `ClockData`,
`CpuStatusData`, `RelayLayer`, `ResolvedDevice`, `ToyopucAddress`,
`ToyopucAddressRange`, `ToyopucAddressingOptions`, `ToyopucAreaDescriptor`,
`ToyopucClient`, `ToyopucConnectionOptions`, `ToyopucDeviceCatalog`,
`ToyopucDeviceClient`, `ToyopucDeviceMatrixRow`, `ToyopucError`,
`ToyopucPlcProfile`, `ToyopucPlcProfiles`, `ToyopucProtocolError`,
`ToyopucTimeoutError`, `ToyopucTraceDirection`, `ToyopucTraceFrame`,
`display_name`, `encode_bit_address`, `encode_byte_address`,
`encode_exno_bit_u32`, `encode_exno_byte_u32`, `encode_ext_no_address`,
`encode_fr_word_addr32`, `encode_program_bit_address`,
`encode_program_byte_address`, `encode_program_word_address`,
`encode_word_address`, `format_device_address`, `format_relay_hop`,
`fr_block_ex_no`, `normalize_address`, `normalize_relay_hops`,
`open_and_connect`, `parse_address`, `parse_device_address`,
`parse_prefixed_address`, `parse_relay_hops`, `poll`, `read_dwords`,
`read_dwords_chunked`, `read_dwords_single_request`, `read_named`,
`read_typed`, `read_words`, `read_words_chunked`,
`read_words_single_request`, `resolve_device`, `split_u32_words`,
`try_parse_device_address`, `write_bit_in_word`, `write_dwords_chunked`,
`write_dwords_single_request`, `write_typed`, `write_words_chunked`,
`write_words_single_request`.

## Generated API Details

The docs site renders the installed package with mkdocstrings so class,
function, dataclass, and enum signatures are searchable from the site API
reference.
