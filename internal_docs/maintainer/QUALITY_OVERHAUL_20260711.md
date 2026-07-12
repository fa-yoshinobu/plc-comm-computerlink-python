# ComputerLink Python Quality Overhaul

This record preserves the approved target contracts for the breaking quality
overhaul. A checked box requires recorded evidence; intent is not evidence.

## D-001: Required destination port

Scope: public clients/options/factory and every maintained runnable sample.

Target: callers select a port in `1..65535`; omission or invalid input never becomes `1025`.

Acceptance criteria:

1. Every public connection path requires and validates port before socket use.
2. Single-PLC samples require `--port`; multi-PLC/config samples require a per-endpoint or explicitly supplied common port.
3. Source inspection finds no runnable `1025` port fallback.

- [x] Implementation and sample migration completed.
- [x] Tests cover constructor/options/factory boundaries.
- [x] `release_check.bat` passed Ruff, format, mypy, sample/script compilation, API docs, 233 tests, canonical profile parity, PyPI identity, and CLI packaging after the final diff.
- [x] Codex reviewed public signatures, sample/config parsing, and the no-fallback source scan.
- [ ] Claude review completed (`pending user authorization`).
- [ ] Claude findings dispositioned and affected checks rerun.
- [x] No live communication is required for local endpoint validation; no PLC communication was performed.
- [x] Documentation, changelog, samples, and API coverage agree.
- [ ] Final cross-language acceptance verified.

## D-066: UDP local port

Scope: synchronous and asynchronous clients, connection options, and factory.

Target: `local_port` is optional with value `0`; UDP always binds explicitly,
including the ephemeral-port case. TCP rejects a nonzero local port.

Acceptance criteria:

1. UDP port `0` and `1..65535` bind before communication.
2. TCP plus nonzero local port, Boolean, negative, and overflow values fail
   before socket use.

- [x] Implementation completed in this repository.
- [x] Tests cover the acceptance criteria.
- [x] Full static, unit, example, build, and package checks passed after the final diff (`release_check.bat`, 2026-07-11).
- [x] Codex final self-review completed against the diff, public surface, validation order, retry/cancel behavior, tests, docs, and approved cross-language contract.
- [ ] Claude review completed (`pending user authorization`).
- [ ] Claude findings dispositioned and affected checks rerun.
- [x] Live-PLC requirement dispositioned (no live PLC required; UDP bind-0, assigned source port, fixed-port collision, and TCP rejection are covered by local socket fixtures without claiming PLC compatibility).
- [x] Documentation, migration notes, changelog, samples, and generated API coverage agree with the implementation.
- [ ] Final acceptance verified.

## D-067: Required transport

Scope: all public construction and factory paths.

Target: callers explicitly select `tcp` or `udp`; no transport default or
protocol keyword alias remains.

Acceptance criteria:

1. Omission, blank, unknown, and wrong-type values fail before communication.
2. Every maintained sample selects a transport explicitly.

- [x] Implementation completed in this repository.
- [x] Tests cover the acceptance criteria.
- [x] Full checks passed after the final diff (`release_check.bat`, 2026-07-11).
- [x] Codex final self-review completed against the diff, public surface, validation order, retry/cancel behavior, tests, docs, and approved cross-language contract.
- [ ] Claude review completed (`pending user authorization`).
- [ ] Claude findings dispositioned and checks rerun.
- [x] Live-PLC requirement dispositioned (no live PLC required; required transport parsing and pre-socket rejection are deterministic constructor/factory behavior).
- [x] Documentation, changelog, samples, migration notes, and generated API coverage agree with the implementation.
- [ ] Final acceptance verified.

## D-068: Three-second communication timeout

Scope: clients, connection options, and factory.

Target: timeout omission means `3.0` seconds. Explicit values must be positive
and finite; Boolean, zero, negative, NaN, and infinity are rejected.

Acceptance criteria:

1. All public paths use the same `3.0`-second default.
2. Invalid values fail before socket configuration.

- [x] Implementation completed in this repository.
- [x] Tests cover the acceptance criteria.
- [x] Full checks passed after the final diff (`release_check.bat`, 2026-07-11).
- [x] Codex final self-review completed against the diff, public surface, validation order, retry/cancel behavior, tests, docs, and approved cross-language contract.
- [ ] Claude review completed (`pending user authorization`).
- [ ] Claude findings dispositioned and checks rerun.
- [x] Live-PLC requirement dispositioned (no live PLC required; timeout default/validation and per-attempt session disposal are covered by deterministic local timeout fixtures).
- [x] Documentation, changelog, samples, migration notes, and generated API coverage agree with the implementation.
- [ ] Final acceptance verified.

## D-069/D-070: Retry count and retry delay

Scope: connect and request retry paths, synchronous and asynchronous wrappers.

Target: retry count defaults to zero and delay defaults to `0.2` seconds.
Only idempotent reads, pre-send failures, or explicitly retryable responses may
retry. Raw, write, clock, scan, and FR commit operations never retry after an
uncertain send. Async cancellation must end the retrying worker operation.

Acceptance criteria:

1. Invalid count/delay values fail before communication.
2. State-changing operations and raw commands send at most once.
3. Connect retry and async cancellation behavior are deterministic.

- [x] Implementation completed, including pre-send connect retry and async worker cancellation completion.
- [x] Tests cover retry eligibility, connect retry, state-changing no-retry behavior, and worker termination on cancellation.
- [x] Full checks passed after the final diff (`release_check.bat`, 2026-07-11).
- [x] Codex final self-review completed against the diff, public surface, validation order, retry/cancel behavior, tests, docs, and approved cross-language contract.
- [ ] Claude review completed (`pending user authorization`).
- [ ] Claude findings dispositioned and checks rerun.
- [x] Live-PLC requirement dispositioned (no live PLC required; retry eligibility, send-count boundaries, delay, cancellation, and no-retry state transitions are covered by fault-injected transports).
- [x] Documentation, changelog, samples, migration notes, and generated API coverage agree with the implementation.
- [ ] Final acceptance verified.

## D-071: Internal UDP receive size

Scope: clients, options, factories, samples, and documentation.

Target: receive buffer size is not a public option. UDP receives use the
internal full-datagram size of 65535 bytes.

Acceptance criteria:

1. No public constructor, option, helper, sample, or documentation exposes the value.
2. UDP receive uses the internal constant and cannot be configured to truncate a datagram.

- [x] Implementation completed in this repository.
- [x] Tests cover the acceptance criteria.
- [x] Full checks passed after the final diff (`release_check.bat`, 2026-07-11).
- [x] Codex final self-review completed against the diff, public surface, validation order, retry/cancel behavior, tests, docs, and approved cross-language contract.
- [ ] Claude review completed (`pending user authorization`).
- [ ] Claude findings dispositioned and checks rerun.
- [x] Live-PLC requirement dispositioned (no live PLC required; full-datagram receive and truncation/length handling are covered by local UDP fixtures).
- [x] Documentation, changelog, samples, migration notes, and generated API coverage agree with the implementation.
- [ ] Final acceptance verified.

## D-072: Maintainer-only trace callback

Scope: raw-frame tracing in synchronous and asynchronous clients.

Target: tracing is absent from normal public configuration. Maintainer tracing
receives immutable copies, cannot fail communication, and cannot delay or
reorder the request lifecycle.

Acceptance criteria:

1. Callback exceptions never affect request results.
2. Slow callbacks are isolated from transport timing and ordering.

- [x] Implementation completed; callback work runs on a bounded single-worker diagnostic queue outside transport timing.
- [x] Tests cover callback exception isolation, ordering, immutable frame copies, and slow-callback non-blocking behavior.
- [x] Full checks passed after the final diff (`release_check.bat`, 2026-07-11).
- [x] Codex final self-review completed against the diff, public surface, validation order, retry/cancel behavior, tests, docs, and approved cross-language contract.
- [ ] Claude review completed (`pending user authorization`).
- [ ] Claude findings dispositioned and checks rerun.
- [x] Live-PLC requirement dispositioned (no live PLC required; diagnostic copy ownership, ordering, exception isolation, and timing isolation do not depend on PLC behavior).
- [x] Documentation, changelog, samples, migration notes, and generated API coverage agree with the implementation.
- [ ] Final acceptance verified.

## D-073: Profile-bound addressing

Scope: high-level client, resolver, parser/formatter, and public address objects.

Target: addressing behavior comes only from the required canonical PLC
profile. Public callers cannot override routing with independent addressing
flags, and reusable public address objects remain bound to that profile.

Acceptance criteria:

1. Constructor override options are absent.
2. Cross-profile address-object reuse is rejected before communication.

- [x] Implementation completed; public overrides are removed and resolved/parsed address objects carry their canonical profile.
- [x] Tests cover required profile selection, bound objects, and cross-profile rejection before transport.
- [x] Full checks passed after the final diff (`release_check.bat`, 2026-07-11).
- [x] Codex final self-review completed against the diff, public surface, validation order, retry/cancel behavior, tests, docs, and approved cross-language contract.
- [ ] Claude review completed (`pending user authorization`).
- [ ] Claude findings dispositioned and checks rerun.
- [x] Live-PLC requirement dispositioned (no live PLC required; canonical profile derivation, profile-bound object identity, and pre-transport mismatch rejection are deterministic resolver/vector properties).
- [x] Documentation, changelog, samples, migration notes, and generated API coverage agree with the implementation.
- [ ] Final acceptance verified.

## D-076: Explicit named value type

Scope: named reads, typed helpers, polling, parsing, and formatting.

Target: named addresses require `:U/:S/:D/:L/:F`; `.0` through `.F` mean a
bit inside a word. Unknown types, separators, Boolean/fractional writes, and
out-of-range values are rejected without masking or fallback.

Acceptance criteria:

1. `:D` is a Dword and `.D` is bit 13.
2. Missing/unknown types and invalid values fail before communication.
3. Returned values outside the declared type range raise a protocol error.

- [x] Implementation completed in this repository.
- [x] Tests cover the acceptance criteria.
- [x] Full checks passed after the final diff (`release_check.bat`, 2026-07-11).
- [x] Codex final self-review completed against the diff, public surface, validation order, retry/cancel behavior, tests, docs, and approved cross-language contract.
- [ ] Claude review completed (`pending user authorization`).
- [ ] Claude findings dispositioned and checks rerun.
- [x] Live-PLC requirement dispositioned (no live PLC required; named-type grammar, width/range validation, and result decoding are covered by parser and protocol fixtures).
- [x] Documentation, changelog, samples, migration notes, and generated API coverage agree with the implementation.
- [ ] Final acceptance verified.

## D-077: Scalar and multiple reads

Scope: direct, relay, FR, word, synchronous, and asynchronous high-level reads.

Target: `read_one`/`relay_read_one` return one scalar and take no count.
Count-based reads require a positive integer and always return a list,
including count one. `read_devices` names the sparse-device form. Every call
uses one protocol request; no public chunk helper exists.

Acceptance criteria:

1. Omitted count fails on range APIs; Boolean, non-integer, zero, and negative counts fail before transport.
2. Count one returns a one-item list on every range path.
3. Command-group, PC10/FR block, and protocol-limit overflow send zero requests.
4. Public chunking helpers and implicit run splitting are absent from maintained use paths.

- [x] Implementation completed in this repository.
- [x] Tests cover scalar/list shape, invalid counts, boundaries, and zero-send rejection.
- [x] Full checks passed after the final diff (`release_check.bat`, 2026-07-11).
- [x] Codex final self-review completed against the diff, public surface, validation order, retry/cancel behavior, tests, docs, and approved cross-language contract.
- [ ] Claude review completed (`pending user authorization`).
- [ ] Claude findings dispositioned and checks rerun.
- [x] Live-PLC requirement dispositioned (no live PLC required; scalar/list return shape, count limits, one-request enforcement, and zero-send rejection are deterministic API/mock-transport properties).
- [x] Documentation, changelog, samples, migration notes, and generated API coverage agree with the implementation.
- [ ] Final acceptance verified.

## D-078: Single-request Dword and float arrays

Scope: direct/relay, read/write, synchronous/asynchronous Dword and float32 arrays.

Target: `atomic_transfer` is removed. Every array operation is one protocol
request or fails before communication; low and high words and array elements
are never split or partially written.

Acceptance criteria:

1. Count/value conversion, protocol limit, address range, route, and block boundary are validated before transport.
2. Boundary and limit failures send zero requests and writes have no partial completion.
3. No public atomic or chunking switch remains.

- [x] Implementation completed in this repository.
- [x] Tests cover strict counts, block crossing, zero-send rejection, and removed options/helpers.
- [x] Full checks passed after the final diff (`release_check.bat`, 2026-07-11).
- [x] Codex final self-review completed against the diff, public surface, validation order, retry/cancel behavior, tests, docs, and approved cross-language contract.
- [ ] Claude review completed (`pending user authorization`).
- [ ] Claude findings dispositioned and checks rerun.
- [x] Live-PLC requirement dispositioned (no live PLC required; Dword/float conversion, block/limit validation, and one-request/no-partial-write behavior are covered by exact frame and send-count fixtures).
- [x] Documentation, changelog, samples, migration notes, and generated API coverage agree with the implementation.
- [ ] Final acceptance verified.

## D-079: Explicit maintainer raw payload

Scope: raw sender and generic command builder.

Target: data is required, including explicit empty bytes. Command code is an
integer `0..255`, payload is bytes-like and length-representable, and raw
requests never auto-retry. Raw access is maintainer/testing infrastructure,
not a normal application entry point.

Acceptance criteria:

1. Missing data, invalid command codes/types, null/wrong data, and oversized payloads fail before transport.
2. Explicit empty and normal payloads produce exact frames.
3. Raw requests send at most once after uncertain transport failure.

- [x] Implementation completed; raw senders are underscore-only maintainer paths and absent from async/documented public surfaces.
- [x] Tests cover validation, exact frame bytes, explicit empty payload, oversize rejection, and no retry.
- [x] Full checks passed after the final diff (`release_check.bat`, 2026-07-11).
- [x] Codex final self-review completed against the diff, public surface, validation order, retry/cancel behavior, tests, docs, and approved cross-language contract.
- [ ] Claude review completed (`pending user authorization`).
- [ ] Claude findings dispositioned and checks rerun.
- [x] Live-PLC requirement dispositioned (no live PLC required; maintainer-only visibility, raw payload validation, exact frame construction, and post-send no-retry are deterministic).
- [x] Documentation, changelog, samples, migration notes, and generated API coverage agree with the implementation.
- [ ] Final acceptance verified.

## D-080: FR work-area write separated from commit

Scope: direct/relay, low/high-level, synchronous/asynchronous FR writes.

Target: `write_fr`/`write_fr_words` update only the work area with one request.
There is no commit Boolean, combined write-and-commit helper, internal block
enumeration, chunking, or wait behavior.

Acceptance criteria:

1. One-block, within-limit work-area writes send exactly one C3 request and no CA request.
2. Boundary/limit overflow sends zero requests.
3. Combined and committed convenience APIs are absent.
4. Every direct/relay and low/high-level FR word value is an integer in `0..65535`; Boolean, fractional, string, negative, and overflowing values fail before transport without masking or coercion.

- [x] Implementation completed in this repository.
- [x] Tests cover boundary/limit rejection, strict FR value domains, sync/async direct/relay zero-send rejection, and removed public surfaces.
- [x] Full checks passed after the final diff (`release_check.bat`, 2026-07-12): Ruff, format, mypy, API coverage, 233 tests, all samples/scripts, PyInstaller, canonical profile fixture, and PyPI identity check.
- [x] Codex final self-review completed against the diff, public surface, validation order, retry/cancel behavior, tests, docs, and approved cross-language contract.
- [ ] Claude review completed (`pending user authorization`).
- [ ] Claude findings dispositioned and checks rerun.
- [ ] Live-PLC work-area and durability checks remain unverified and require item-level release disposition.
- [x] Documentation, changelog, samples, migration notes, and generated API coverage agree with the implementation.
- [ ] Final acceptance verified.

Self-review finding (2026-07-12): Python `write_fr_words` and `relay_write_fr_words` converted each input with `int(value) & 0xFFFF`, so invalid public values could become valid but different PLC values. The high-level FR methods also called `int(...)` before the low-level path. This was accepted as a contract violation, corrected with one shared strict FR-word validator, and covered for direct and relay paths before the final release check.

## D-081: One-block FR commit acceptance

Scope: direct/relay, low/high-level, synchronous/asynchronous FR commit.

Target: commit requires the first word of one explicit FR block, sends one CA
request, and returns after command acceptance. Count/range, wait, timeout,
poll interval, automatic status reads, and status-command fallback are absent.

Acceptance criteria:

1. Aligned block start sends exactly one CA request with no automatic status request or retry.
2. Non-aligned block selection fails before transport.
3. Removed range/wait/fallback APIs are not public; completion monitoring uses explicit status reads.

- [x] Implementation completed in this repository.
- [x] Tests cover exact CA frame, alignment rejection, fixed return behavior, and removed surfaces.
- [x] Full checks passed after the final diff (`release_check.bat`, 2026-07-11).
- [x] Codex final self-review completed against the diff, public surface, validation order, retry/cancel behavior, tests, docs, and approved cross-language contract.
- [ ] Claude review completed (`pending user authorization`).
- [ ] Claude findings dispositioned and checks rerun.
- [ ] Live-PLC CA acceptance/durability checks remain unverified and require item-level release disposition.
- [x] Documentation, changelog, samples, migration notes, and generated API coverage agree with the implementation.
- [ ] Final acceptance verified.

## D-082: Fixed hexadecimal address notation

Scope: address parsers, resolver, formatter, samples, and documentation.

Target: numeric device fields are hexadecimal. Public radix overrides are absent.

Acceptance criteria:

1. Same text resolves identically on every public path.
2. Public signatures and docs contain no radix option.

- [x] Implementation completed in this repository.
- [x] Tests cover the acceptance criteria.
- [x] Full checks passed after the final diff (`release_check.bat`, 2026-07-11).
- [x] Codex final self-review completed against the diff, public surface, validation order, retry/cancel behavior, tests, docs, and approved cross-language contract.
- [ ] Claude review completed (`pending user authorization`).
- [ ] Claude findings dispositioned and checks rerun.
- [x] Live-PLC requirement dispositioned (no live PLC required; fixed hexadecimal parsing, normalization, formatting, and wire round trips are deterministic vectors).
- [x] Documentation, changelog, samples, migration notes, and generated API coverage agree with the implementation.
- [ ] Final acceptance verified.

## D-083: Explicit PLC clock century

Scope: clock conversion and direct/relay clock write.

Target: `year_base` is required, is a nonnegative century boundary, and the
datetime year must be within that century. Timezone-aware values are rejected.

Acceptance criteria:

1. Omitted/invalid year base, out-of-century year, and aware datetime fail before transport.
2. Direct and relay paths encode the same two-digit year for the same explicit base.

- [x] Implementation completed in this repository.
- [x] Tests cover the acceptance criteria.
- [x] Full checks passed after the final diff (`release_check.bat`, 2026-07-11).
- [x] Codex final self-review completed against the diff, public surface, validation order, retry/cancel behavior, tests, docs, and approved cross-language contract.
- [ ] Claude review completed (`pending user authorization`).
- [ ] Claude findings dispositioned and checks rerun.
- [ ] Live-PLC clock-write check remains unverified and requires release disposition.
- [x] Documentation, changelog, samples, migration notes, and generated API coverage agree with the implementation.
- [ ] Final acceptance verified.

## D-084: Fixed relay ENQ and strict route values

Scope: single/nested relay builders, parser, formatter, tuple input, and high-level routes.

Target: relay ENQ is internally fixed at `0x05`. Link is integer `0..255` and
station is integer `1..65535`; no masking or wrapping occurs. All nested hops
are validated before frame construction.

Acceptance criteria:

1. Boundary values produce exact frames.
2. Boolean, wrong-type, negative, overflow, and station zero fail before transport.
3. One invalid nested hop prevents the entire frame and sends zero requests.

- [x] Implementation completed in this repository.
- [x] Tests cover the acceptance criteria.
- [x] Full checks passed after the final diff (`release_check.bat`, 2026-07-11).
- [x] Codex final self-review completed against the diff, public surface, validation order, retry/cancel behavior, tests, docs, and approved cross-language contract.
- [ ] Claude review completed (`pending user authorization`).
- [ ] Claude findings dispositioned and checks rerun.
- [ ] Live-PLC relay-route checks remain unverified and require release disposition.
- [x] Documentation, changelog, samples, migration notes, and generated API coverage agree with the implementation.
- [ ] Final acceptance verified.

## Current verification evidence

- `release_check.bat`: passed on 2026-07-12 after the strict FR-value correction.
- Canonical profile fixture: unchanged against `plc-comm-computerlink-profiles` v1.0.1.
- Ruff lint/format: passed; Mypy: passed for 13 source files.
- Public API docstring coverage: 107 definitions and 164 methods.
- Unit tests: `233 passed`; all maintained samples/scripts compiled.
- PyInstaller CLI executable build: passed.
- PyInstaller spec is generated under ignored `build/toyopuc.spec`; the final release check leaves no root-level `toyopuc.spec` artifact.
- Claude: not invoked; explicit user authorization is required for each batch.
- Live PLC: not invoked; exact test plan and user `OK` are required.

## Deferred live verification TODO

No command below is authorized merely by appearing here. Confirm the currently connected PLC and the physical route, present the selected exact row again, and wait for explicit user `OK` before communication.

| ID | Exact candidate target | Operation and evidence | Restoration / risk | Status |
|---|---|---|---|---|
| D-080 | Nano 10GX TUC-1157; `toyopuc:nano-10gx:compatible`; `192.168.250.100:1025` TCP; Direct; `FR000000` | Read original, write work-area value `0xE40F`, read it back, and prove one C3 request with no CA request. | Write the captured original back without commit and read it back. Current-build live result is unverified; 2026-06-12 C3 write/restore evidence exists. |
| D-081 | Same target; `FR000000`, the first word of the 0x8000-word block | On a dedicated test PLC reset to a known no-pending-change state, write `0xE40F`, send exactly one CA, observe completion with an explicit status read, restart, and verify persistence. | Restore the captured original, send one CA, restart, and verify restoration. CA can persist every pending change in the block; individual discussion and explicit `OK` are mandatory. |
| D-083 | Same target; PLC clock; Direct; `year_base=2000` | Read clock, write `2026-07-12 12:34:56`, then read and verify the explicit-century round trip. | Restore the original clock advanced by measured elapsed time. Clock-dependent operation may be affected; individual discussion and explicit `OK` are mandatory. |
| D-084-A | Nano 10GX; `toyopuc:nano-10gx:compatible`; `192.168.250.100:1035` UDP; local `12000`; `P1-L2:N2`; `P1-D0000` | Read original, write random test value `0x3DA4`, read back, and prove one-hop ENQ/response reaches the intended PLC. | Restore original and read back. Exact physical route and target PLC must first be confirmed. |
| D-084-B | Same endpoint; `P1-L2:N2,P1-L2:N4`; `P1-D0000` | Read original, write random test value `0x7C93`, read back, and prove nested response handling reaches the intended final PLC. | Restore original and read back. Wrong-route writes are high risk; exact hop order and target PLC plus explicit `OK` are mandatory. |

If hardware is unavailable, each item needs an explicit release disposition. The proposed dispositions are recorded in workspace `quality_overhaul_goal_20260711.md`; no proposal is approved merely by being documented.

## Claude review package status

- [x] Review package prepared; Claude was not invoked.
- [ ] Present the proposed Claude batch to the user and wait for explicit authorization.
- [ ] Run Claude only after that authorization, preserve findings, classify each finding, correct accepted findings, and rerun affected checks.

Prepared batch scope: all changes on `quality/2026-07-overhaul` relative to its merge base, with emphasis on `toyopuc/client.py`, `toyopuc/high_level.py`, async wrappers, transport/retry/cancellation state, generated/public API surface, D-066 through D-084 tests and documentation, and the 2026-07-12 strict FR-value correction.

Review purpose: independently identify contract violations, unsafe retry/cancellation transitions, hidden multi-request behavior, validation after transport, public compatibility remnants, direct/relay or sync/async divergence, FR/clock semantic errors, value coercion/masking, and missing tests.

Inputs to provide after authorization: approved contracts and acceptance criteria in this file; repository diff; public API reference; final `release_check.bat` result; Ruff/format/mypy evidence; 233-test result; sample/script compilation and PyInstaller evidence; the self-review FR finding and correction; canonical profile parity; deferred live-verification scope.

Expected output: findings only, each with severity, affected contract identifier, exact file/line evidence, failure scenario, recommended correction, and missing-test recommendation. A general quality score or approval is not a substitute for concrete findings.
