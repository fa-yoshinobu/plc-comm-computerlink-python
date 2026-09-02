# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

**Entry labels**

- `Release`: Package/version metadata and publishing preparation.
- `Library`: Runtime behavior, public API, protocol handling, or validation in the distributed library.
- `Docs`: README, user guides, generated API docs, or other documentation-only changes.
- `Samples`: Examples, sample flows, sample scripts, or sample applications.
- `Tests`: Test suites, test fixtures, golden vectors, or verification data.
- `Tooling`: Developer/operator command-line tools and helper utilities.
- `CI`: Release checks, workflow scripts, or automation-only changes.

## [Unreleased]

## [4.2.0] - 2026-09-02

- Release: Bumped package metadata and `toyopuc.__version__` to `4.2.0` for the named-request, FR naming, program timer/counter, and corrected PC10 C4/C5 contracts.
- Library: `read_named` and each `poll` cycle now accept one or more unique compatible named addresses only when the complete set fits one protocol request; automatic splitting and partial results are rejected before transport.
- Library: Added canonical FR names `write_fr_work_area`, `relay_write_fr_work_area`, `commit_fr_block_by_device`, and `relay_commit_fr_block_by_device`; the former four names warn and forward for one release without changing wire behavior.
- Library: Added direct/relay and sync/async program-explicit timer/counter preset/current operations using native A0 selectors `40` through `43` and mandatory `P1`/`P2`/`P3` device prefixes.
- Tests: Added one-request named/polling, FR migration, exact A0 selector, response-shape, relay, and pre-transport validation coverage.
- Library: Corrected PC10 C4 response correlation and long-value length calculation for direct, relay, synchronous, asynchronous, and aggregate reads; malformed count echoes are now rejected instead of decoded.
- Library: Corrected PC10 C5 sparse word and bit writes to encode each address immediately followed by its value/data byte without changing the public API surface or single-point frames.
- Tests: Added exact C4/C5 regression vectors, all four count-mismatch cases, direct/relay long-response coverage, and unchanged single-point vectors.

## [4.1.0] - 2026-08-27

- Release: Bumped the package and runtime metadata to `4.1.0` for the canonical single-request word and DWord read contract.
- Library: Made `read_words_single_request` and `read_dwords_single_request` reject multi-segment ranges before transport; the former short top-level names now warn and delegate to the canonical APIs.

## [4.0.0] - 2026-08-07

- Release: Bumped package metadata and `toyopuc.__version__` to `4.0.0` for the approved breaking contract release.
- Library: Fixed every public semantic bit-write surface to preflight before sync/async FIFO admission and preserve native `bool` values through planning and validation, converting to integer `0`/`1` only at final wire encoding. Valid Boolean writes no longer fail after an internal integer conversion; integer, string, and truthy substitutes fail immediately without waiting for a busy client or sending a request.
- Library: Added explicit synchronous and asynchronous `write_bit_in_word` and `relay_write_bit_in_word` surfaces. They validate the complete ordinary 16-bit word route before communication, hold one FIFO turn, use one absolute post-admission deadline, and always issue one read followed by one write. The sequence is not PLC-atomic; cancellation or failure after the write may have started is outcome-unknown and requires transport retirement, reconnect, and PLC-state reconciliation.
- Tests: Added strict native-Boolean preservation and direct/relay bit-in-word read-modify-write contract coverage.

- BREAKING: Async clients no longer own a private sync-client executor or `_run_sync_in_worker` compatibility seam. Private executor/sync-client substitutions were never public API; tests and extensions must use the documented async methods.
- Library: Async TCP/UDP communication now uses native asyncio socket waits under one FIFO turn and one absolute deadline across DNS, connect, send, receive, validation, and decode. Queued cancellation sends nothing; active cancellation retires the transport; a post-send state change remains outcome-unknown.
- Library: Direct/relay aggregate reads retain fully validated prepared segment frames, normalize relay hops once, and decode into the final result without segment result lists. Async aggregates execute one native prepared sequence without replaying completed segment decode work. Typed response and nested relay decoding use private memory views while public raw responses remain owned bytes.
- Tests: Replaced private worker tests with native async FIFO/DNS/socket integration tests and added prepared-segment, borrowed-view, relay-route, public-ownership, and no-worker contract coverage.

- BREAKING: A data-bearing NG response must echo the active request command before it can be published as a definitive PLC error. A mismatch is malformed, retires the transport, and becomes outcome-unknown for a possibly applied state change; the no-data `RC=0x10` special error form retains its existing command-byte meaning.
- Library: Async task cancellation no longer hides an already-established `ToyopucOperationOutcomeUnknownError`. That established unknown outcome wins the completion race, while completed success and ordinary failures still preserve `asyncio.CancelledError`.
- Tests: Added sync/async data-bearing NG command-correlation and deterministic native-async cancellation-race regressions.
- Library: Explicit and lazy TCP/UDP connection establishment now uses one monotonic absolute deadline covering IPv4 DNS, first-IPv4 selection, socket creation, UDP bind/connect, TCP configuration, and final adoption. Late resolver/socket results cannot mutate client state and abandoned sockets are closed; deadline expiry remains Timeout while a pre-deadline native connection failure remains Transport.
- Library: Sync and async clients now serialize ordinary operations in arrival-order FIFO turns, snapshot timeout and transport generation at admission, lazily connect, and let `close()` retire active and already queued work without coupling independent client instances.
- Library: Connect, transmit, receive, and response decode now share one monotonic request deadline. Timeout and cancellation retire the transport, and no request is automatically resent after it may have been sent, including reads and PLC retry-required responses.
- Library: Added dedicated cancellation, closed, not-connected, transport, timeout, malformed-response, PLC-NG, and machine-readable unknown-outcome classifications while preserving native exception causes.
- Library: Read aggregates and `read_named` now preserve declared order, preflight the complete plan, split only when protocol capacity or routing requires it, hold one FIFO turn, and return all results or raise. Cross-request results remain non-atomic; write aggregates remain single-request-only.
- Library: `write_bit_in_word` remains an explicit non-atomic read-modify-write helper and now holds one exclusive FIFO turn across its read and write.
- Tests: Added exact maximum/maximum-plus-one protocol-capacity checks, deadline, pre-send/post-send classification, sync/async FIFO, cancellation, close-generation, aggregate preflight/order/splitting, and exclusive RMW regressions.
- Release: Aligned artifact roles so the registry package contains consumer runtime, native API metadata, license, README, and ecosystem-native examples where applicable while excluding repository tests and maintainer tooling; the GitHub source archive retains tracked non-hardware validation and maintainer inputs.
- Library: Audited profile-bound `ResolvedDevice` inputs: every live read/write path requires exact canonical profile identity with the client before request construction or transport state changes; no base-family or addressing-mode fallback is used.
- Tests: Added profile-mismatch regression coverage for both canonical identities, traffic counters, and last-frame state.
- Docs: README documentation links now include the shared Performance and Choosing a Language pages, and package registry metadata was expanded for discoverability. No functional change.
- CI: GitHub source archives now include the complete test suite, and the archive gate extracts each archive and requires its package build and tests to pass.
- CI: Package validation now installs the built wheel into a fresh isolated virtual environment and checks public imports, signatures, docstrings, version identity, and installed origin without checkout or `PYTHONPATH` access.
- CI: Worktree source-archive validation now builds one synthetic Git tree containing modifications, untracked files, and deletions, then requires the extracted archive to pass the complete non-hardware and isolated package-consumer gates.

### BREAKING

- Library: Named, aggregate, typed dword/float, bit-in-word, direct, relay, sync, and async generic write paths now reject FR addresses before transport. Migrate intentional FR updates to `write_fr` / `relay_write_fr`; low-level numeric/raw and explicit FR APIs remain available.
- Library: Relay route strings and `format_relay_hop()` are now decimal-only. Migrate hexadecimal route text such as `PA-LB:N20` or `0xAB:0x20` to `P10-L11:N20` or `171:32`.
- Library: Automatic post-send retries were removed for every command, including reads and relay collision responses. Applications that intentionally retry must reconcile the prior request and issue a new explicit call.
- Library: Read aggregates can now span multiple protocol requests while preserving order and one FIFO client turn. Callers that require one wire request must use a `*_single_request` helper; callers that require one atomic observation must provide PLC-side consistency control.
- Library: Concurrent sync calls are serialized, and `close()` rejects active and already queued operations from the retired generation with dedicated structured errors.
- Library: Protocol integers now require actual `int` values (not `bool`) within their exact wire range; PC10 addresses, extended-area numbers, FR indices, module fields, and polling intervals no longer accept truncation, wrapping, or non-finite values.
- Library: Fixed-format PC10 and relay responses now require exact command-specific fields and lengths; empty relay elements, trailing data, and malformed responses that were previously tolerated now fail.
- Library: Semantic bit-write APIs now accept only actual `bool` values. Integer `0`/`1` callers must migrate to `False`/`True`; raw frame builders continue to use validated wire integers.
- Library: Connection timeouts, retry delays, and polling intervals now share an inclusive maximum of `2,147,483.647` seconds. Larger values fail with `ValueError` before transport or timer creation instead of leaking platform-dependent overflow errors.
- Library: TCP and UDP connections are now IPv4-only. IPv6 literals are rejected before socket creation, and hostnames use the first IPv4 result returned by the resolver; callers using IPv6 endpoints must migrate to an IPv4 address or IPv4-resolving hostname.

### Fixed

- Library: Full and header-trimmed relay requests now share one strict parser, including a zero length-low byte, and every command-specific response validator runs inside the post-send lifecycle boundary. Malformed reads retire the transport and raise `ToyopucProtocolError`; malformed state-changing calls raise outcome-unknown with the protocol error preserved as the cause.
- Library: Public PC10 multi-bit reads retain one Boolean per requested device while now enforcing their exact `4 + ceil(count / 8)` response size; malformed responses raise `ToyopucProtocolError` instead of leaking `IndexError`.
- Library: Random/sparse write duplicate detection now uses the complete encoded wire identity, including extended and relay routes.
- Library: Sync and async state-changing operations now classify EOF and malformed post-send responses as `ToyopucOperationOutcomeUnknownError`; affected fixed-endpoint UDP clients are tainted before reuse.
- Library: Async cancellation is generation-scoped, retires the active transport, and cannot leak a stale cancellation request into a later operation.
- Library: Iterable inputs are snapshotted exactly once before validation and encoding so caller mutation or a one-shot iterable cannot change the transmitted request. Async admission passes private prepared inputs into native async execution, and high-level delegation does not repeat the same logical snapshot.
- Library: `write_bit_in_word` rejects every non-`bool` value and invalid bit index before its read-modify-write I/O.

### Tests

- Tests: Added deterministic explicit/lazy sync/async delayed-DNS deadlines, async cancellation, close-during-DNS, IPv4-literal DNS bypass, late TCP/UDP socket cleanup, shared retry-deadline, and pre-deadline transport-classification regressions.
- Tests: Added wire-boundary, strict-response, duplicate-destination, iterable snapshot, EOF, malformed-response, cancellation-generation, relay, UDP-taint, IPv6-rejection, and IPv4-resolution regressions.

## [3.2.1] - 2026-07-29

- Release: Bumped package metadata and `toyopuc.__version__` to `3.2.1`.
- Release: GitHub Release drafts now prepend this version's changelog section to generated notes and repair a missing section on workflow reruns.
- Tooling: Pinned canonical profile fixture refreshes to `plc-comm-computerlink-profiles` `v1.0.4`, matching the embedded profile data used by this release.

### BREAKING

- Library: Removed obsolete command upper-bit response flags and routes. Consumers must classify responses from their structural length and command contract instead of the removed flags.

### Fixed

- Library: Write commands are never retried after a transport failure that may follow transmission; read-only classification is structural rather than dependent on the removed flags.
- Library: Relay response length decoding now handles a zero low byte correctly and rejects truncated or trailing response data exactly.
- Library: Profile catalog address bounds are advisory and do not reject transport sends; wire-format width checks remain.

## [3.2.0] - 2026-07-17

- Release: Bumped package metadata and `toyopuc.__version__` to `3.2.0`.
- CI: Excluded maintainer-only files, tests, and release tooling from generated source archives while retaining the complete sample set, and added source-archive contract checks to local, CI, and release gates.

- Library: Added immutable client-lifetime traffic snapshots through `traffic_stats()` on synchronous and asynchronous clients.

## [3.1.0] - 2026-07-13

### BREAKING
- Samples: All runnable endpoint, multi-PLC, and configuration-driven samples require an explicit destination port and transport instead of defaulting to `1025`/TCP.
- Library: Split scalar `read_one` / `relay_read_one` from count-required list reads; `count=1` now returns a list and all range reads reject implicit multi-request splitting.
- Library: Renamed sparse `read_many` / `relay_read_many` to `read_devices` / `relay_read_devices` so contiguous and sparse semantics are not overloaded.
- Library: Removed public chunking helpers and the `atomic_transfer` option. Dword and float arrays now require one protocol request and reject boundary or limit overflow before communication.
- Library: Removed FR write/commit combination, range commit, wait/poll helpers, and raw FR-register methods. FR work-area writes and one-block commits are separate operations.
- Library: FR work-area word values require actual integers in `0..65535`; negative, overflowing, Boolean, fractional, and string values are rejected before transport instead of being coerced or masked.
- Library: Generic bit/byte/word/dword writes reject masking and coercion; sequence writes use one request or fail before transport, and empty collections are invalid.
- Library: Added `ToyopucOperationOutcomeUnknownError` for state-changing requests that may have reached the PLC before timeout, disconnect, or cancellation.
- Library: UDP sockets are connected to the configured PLC endpoint. A fixed-local-port UDP client becomes terminal after an uncertain post-send failure because Computerlink cannot identify stale same-endpoint responses.
- Library: Relay reads retry the retry-required outer response when configured; relay writes remain non-retryable after send.
- Library: Retries now apply to pre-send connection failures and approved reads only; async cancellation interrupts the synchronous worker and waits for it to finish before returning.
- Library: Removed public trace callback configuration and isolated the maintainer callback on a bounded background queue so callback delay or failure cannot alter communication.
- Library: Bound resolved and parsed address objects to one canonical PLC profile, removed public addressing-option overrides, and reject cross-profile object reuse.
- Library: Moved raw command and prebuilt-payload senders to maintainer-only underscore paths and removed them from async and documented public surfaces.
- Migration: Replace scalar `read(device)` with `read_one(device)`, sparse `read_many(devices)` with `read_devices(devices)`, and intentional multi-request ranges with explicit application calls.
- Migration: Replace `write_fr(..., commit=True)` with `write_fr(...)` followed by `commit_fr(block_start)`; use explicit CPU-status reads when completion monitoring is required.

### Added
- Library: Added `ToyopucPlcProfileDescriptor` and `plc_profile_descriptors()` for canonical TOYOPUC Computer Link profile metadata.

### Fixed
- Library: Keep protocol-width and unsupported-route validation while treating profile catalog index ranges as advisory application/UI metadata.
- Samples: Updated all sample and maintainer-tool client constructors from the removed `protocol=` keyword to `transport=`.
- CI: Made release dispatch check out an existing exact tag and verify the tag, manifest, runtime version, and built asset names before upload.
- Docs: Corrected the release guide and removed the hand-maintained Getting Started navigation block.

### Tests
- Tests: Added return-shape, strict count, request-boundary, Dword/float no-partial-transfer, FR single-request and strict-value, explicit block commit, and removed-surface regression coverage.
- CI: Write the generated PyInstaller spec under the ignored `build` directory so a successful release check does not leave a root-level untracked artifact.

## [3.0.0] - 2026-07-10

### Changed
- Release: Bumped package metadata and `toyopuc.__version__` to `3.0.0`.
- Docs: Replaced relative README links with absolute URLs so they resolve on package registry pages.

### BREAKING
- Library: Breaking: `ToyopucConnectionOptions` and the direct `open_and_connect` helper now require an explicit `plc_profile`.
- Migration: Pass a canonical `plc_profile` to `ToyopucConnectionOptions` and direct `open_and_connect` calls; use the profile `name` for storage and `display_name` for UI labels.
- Library: `ToyopucPlcProfile` now includes `display_name`; use `display_name` for UI labels and the canonical `name` for storage.

### Docs
- Docs: Clarified required profile selection and the separation between canonical names and display names.

## [2.0.0] - 2026-07-06

### BREAKING
- Release: Renamed the PyPI install package while keeping the Python import name unchanged.

| Old install name | New install name | Import name |
| --- | --- | --- |
| `toyopuc-computerlink` | `plc-comm-toyopuc` | `toyopuc` |

### Added
- Docs: Added `docsrc/user/API_REFERENCE.md` as the standard user-facing API index and linked it from the README.

### Changed
- Release: Bumped package metadata to `2.0.0`.
- Docs: Added the plc-comm family package matrix link to the README.
- Tests: Added package-rename import-name coverage for `import toyopuc`.
- Tooling: Updated release duplicate checks to query `plc-comm-toyopuc`.

## [1.2.0] - 2026-07-05

### Changed
- Release: Bumped package metadata to `1.2.0`.
- Tooling: Normalized line-ending handling in the canonical profile JSON update script so `-SourceRoot` runs no longer report false changes.
- Release: Synced `__version__` with the package version.
- Library: Synced the embedded TOYOPUC profile fixture to `plc-comm-computerlink-profiles` `v1.0.1`, including canonical `display_name` labels.
- Library: Added `display_name(profile)` and `ToyopucPlcProfiles.display_name(profile)` as public UI-label helpers while keeping stored PLC profile values canonical.
- Docs: Documented the profile display-name helpers and canonical-ID storage guidance.
- Tests: Added canonical fixture parity coverage for profile `display_name` values.
- Samples: Added read-only `multi_plc_monitor.py` and `config_polling.py` operational recipes with dry-run validation and reconnect backoff.
- Docs: Added public API docstrings for the Computerlink Python package and a CI coverage check for public API documentation.
- Docs: Added a Gotchas entry clarifying that `read_named()` accepts one address per call and should not be used as a multi-address snapshot helper.
- Docs: Removed the per-library troubleshooting/code page; shared Computerlink troubleshooting and code guidance now lives in the PLC Setup Guide.
- Docs: Removed the per-library latest communication verification page and links so user docs stay focused on usage, not verification logs.
- Docs: Removed the manual page-navigation block from Getting Started and rely on site navigation instead.
- Docs: Moved shared supported-register, model-range, and troubleshooting guidance to the common PLC Setup Guide and kept the user docs to Getting Started, Usage Guide, PLC Profiles, and Gotchas.

## [1.1.0] - 2026-06-29

### Changed
- Release: Bumped package metadata to `1.1.0`.
- Library: Made byte-unit parsing require explicit `L` / `H` suffixes and made `read_many` / `write_many` / `read_named` reject implicit multi-request splitting before communication.
- Docs: Documented explicit request-boundary behavior for multi-address helpers.
- Samples: Updated high-level samples to keep `read_many`, `write_many`, `read_named`, and `poll` request boundaries explicit.
- Tests: Added coverage for explicit byte suffix requirements and rejected implicit multi-request named reads.

### Fixed
- Library: Made `BIT_IN_WORD` helper addresses require an explicit bit index such as `P1-D0100.0` through `P1-D0100.F`; `P1-D0100:BIT_IN_WORD` now fails in `parse_device_address`, `try_parse_device_address`, and `read_named` instead of silently reading bit 0.
- Tests: Added coverage for rejecting `BIT_IN_WORD` addresses without an explicit bit index.

## [1.0.1] - 2026-06-25

### Changed
- Release: Bumped Python package metadata to `1.0.1`.
- Docs: Documented that `plc_profile` must be an explicit canonical profile name: missing values, aliases, abbreviations, case variants, and implicit `toyopuc:generic` fallback are rejected.
- Samples: Updated Computerlink sample scripts and guidance to use safer write/restore patterns.

## [1.0.0] - 2026-06-24

### Changed
- Release: Bumped package metadata to `1.0.0` for the first stable release line.

### Fixed
- Library: Added factory-level validation for `ToyopucConnectionOptions` host, port, local port, and receive-buffer size so Python rejects invalid connection settings at the same layer as the .NET factory.
