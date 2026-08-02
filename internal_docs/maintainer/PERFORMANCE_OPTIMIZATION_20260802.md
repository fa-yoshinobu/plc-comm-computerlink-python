# ComputerLink performance optimization decisions (2026-08-02)

## PERF2-003: prepared aggregate read segments

Scope: direct and relay `read`, `read_devices`, and async equivalents.

Target contract: validate and encode every segment before the first send, retain exact request bytes and normalized relay routes, and decode each validated response directly into the final list. Compatibility impact: wire bytes, split order, errors, and public result shapes are unchanged.

Acceptance criteria:

1. Each direct/relay segment is encoded once, including across async replay.
2. All segments finish preflight before transport.
3. Segment responses decode directly into final offsets without complete temporary result lists.
4. Failure publishes no partial result and preserves FIFO/deadline/transport classification.

## PERF2-004: private typed response views

Scope: typed direct and relay decode; public raw responses and diagnostics remain owned `bytes`.

Target contract: typed decode uses operation-scoped `memoryview` slices over the complete owned receive frame. Relay unwrap advances views without copying inner frames and validates wrapper depth/route before value decode. Compatibility impact: none.

Acceptance criteria:

1. Typed success performs no complete payload intermediate copy.
2. Frame, return code, command, relay route/depth, and expected length precede result construction.
3. Public raw results own immutable bytes and private views do not escape public objects.
4. Malformed responses retain retirement and outcome-unknown rules.

## PERF2-011: native async transport

Scope: `AsyncToyopucClient` and `AsyncToyopucDeviceClient` TCP/UDP I/O.

Target contract: asyncio socket APIs own connect/send/receive under one FIFO lock and one absolute deadline. No client-owned executor, `run_in_executor`, `to_thread`, or private worker compatibility surface performs socket I/O. Compatibility impact: private `_run_sync_in_worker`, `_executor`, and sync-client substitution are removed from the compatibility surface; documented public configuration and methods remain.

Acceptance criteria:

1. Async socket waits use native event-loop APIs and do not allocate one worker per client.
2. FIFO activation starts one deadline covering DNS, connect, send, receive, validation, and decode.
3. Queued cancellation sends nothing; active cancellation retires transport; post-send state change reports outcome unknown.
4. Close retires the active generation and explicit connect permits later reuse; fixed-port UDP uncertainty remains terminal.
5. Direct/relay and sync/async request bytes, validation, and result values agree.

## Self-review disposition

- Accepted and fixed: the first native-async aggregate adapter reused encoded payloads but replayed completed segment decode and reallocated the final list. Direct and relay async aggregates now execute one native prepared sequence, and the performance contract test requires each segment to be encoded, exchanged, and decoded exactly once.
- Accepted and fixed after the first GitHub gate: Python 3.10 does not provide
  `asyncio.timeout_at`, and the borrowed response view widened several private
  decoder inputs without widening their annotations. Native waits now use
  `asyncio.wait_for` with the same absolute deadline, and bytes/view-capable
  decoder annotations pass the Python 3.10 sample type-check gate.

## Evidence checklist

- [x] Implementation completed in this repository.
- [x] Tests added or updated for every locally exercisable acceptance criterion.
- [x] Unit/integration suite passed on the final implementation (`448 passed`).
- [x] Final-source verification passed: Ruff lint/format, mypy, public API documentation coverage (`115` definitions / `169` methods), full tests, source distribution, wheel, and `git diff --check`.
- [x] Codex self-review completed against the approved contracts and ComputerLink .NET consistency; stale worker-contract wording and aggregate replay found during review were corrected and the full final-source gate was rerun.
- [x] Live PLC communication is not required: exact frames and lifecycle behavior are deterministically verified with vectors, loopback TCP/UDP, controlled DNS, cancellation, and malformed responses; no PLC profile or supported wire behavior changes.
- [x] Documentation, migration notes, changelog, and API reference agree with the final implementation.
- [x] Final acceptance criteria verified and this record marked complete.
