# ComputerLink Python Quality Overhaul

This record preserves the approved target contracts for the breaking quality
overhaul. A checked box requires recorded evidence; intent is not evidence.

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
- [ ] Live-PLC requirement dispositioned.
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
- [ ] Live-PLC requirement dispositioned.
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
- [ ] Live-PLC requirement dispositioned.
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
- [ ] Live-PLC requirement dispositioned.
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
- [ ] Live-PLC requirement dispositioned.
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
- [ ] Live-PLC requirement dispositioned.
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
- [ ] Live-PLC requirement dispositioned.
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
- [ ] Live-PLC requirement dispositioned.
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
- [ ] Live-PLC requirement dispositioned.
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
- [ ] Live-PLC requirement dispositioned.
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
- [ ] Live-PLC requirement dispositioned.
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

- [x] Implementation completed in this repository.
- [x] Tests cover boundary/limit rejection and removed public surfaces.
- [x] Full checks passed after the final diff (`release_check.bat`, 2026-07-11).
- [x] Codex final self-review completed against the diff, public surface, validation order, retry/cancel behavior, tests, docs, and approved cross-language contract.
- [ ] Claude review completed (`pending user authorization`).
- [ ] Claude findings dispositioned and checks rerun.
- [ ] Live-PLC work-area and durability checks remain unverified and require item-level release disposition.
- [x] Documentation, changelog, samples, migration notes, and generated API coverage agree with the implementation.
- [ ] Final acceptance verified.

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
- [ ] Live-PLC requirement dispositioned.
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

- `release_check.bat`: passed on 2026-07-11.
- Canonical profile fixture: unchanged against `plc-comm-computerlink-profiles` v1.0.1.
- Ruff lint/format: passed; Mypy: passed for 13 source files.
- Public API docstring coverage: 107 definitions and 164 methods.
- Unit tests: `223 passed`; all maintained samples/scripts compiled.
- PyInstaller CLI executable build: passed.
- Claude: not invoked; explicit user authorization is required for each batch.
- Live PLC: not invoked; exact test plan and user `OK` are required.
