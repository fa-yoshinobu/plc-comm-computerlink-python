# Computer Link Quality Overhaul Decisions — 2026-08-02

This maintainer record preserves approved target-state decisions before implementation. A checked
acceptance box requires recorded evidence; approval or intent alone is not completion evidence.

## COMPUTERLINK-ERROR-CMD-CORRELATION-001 — Correlate data-bearing NG responses before PLC-error publication

Decision status: implemented and verified on 2026-08-02.

### Implementation scope

The shared synchronous Computer Link response validator and every synchronous and asynchronous
public API that uses it over TCP or UDP. The scope includes command correlation, PLC-error
publication, malformed-response classification, state-changing outcome classification, transport
invalidation, tests, user documentation, migration notes, changelog, and generated API reference.

### Target contract

After a complete response frame and response frame type have been validated, a non-OK response
that contains response data must have its response command compared with the originating request
command before the response can be published as a definitive PLC error. If the commands match, the
existing `ToyopucPlcError` result and PLC-supplied error detail remain unchanged.

If the commands do not match, the response is malformed and uncorrelated. The active transport is
invalidated. A state-changing request that may have been transmitted reports
`ToyopucOperationOutcomeUnknownError` with `MALFORMED_RESPONSE` reason. A read-only request reports
the protocol/malformed-response error and never reports the mismatched response as a definitive PLC
error. The synchronous client and asynchronous wrapper expose the same result classification and
transport state transition.

The special no-data NG form in which the command byte carries the detailed PLC error code cannot
be command-correlated. In particular, an `RC=0x10` response with empty data retains its existing
interpretation of the command byte as the detailed error code and retains its existing definitive
PLC-error behavior. This item does not reinterpret that byte as an echoed request command.

### Compatibility and operational impact

A data-bearing NG response whose command differs from the active request no longer appears as that
request's definitive PLC error and no longer leaves the transport reusable. Callers of transmitted
state-changing operations must handle the newly surfaced outcome-unknown result rather than retry
on the assumption of a confirmed PLC rejection. Matching data-bearing NG responses and the special
no-data detailed-error form are unchanged. This is an intentional behavioral break with no silent
fallback.

### Machine-verifiable acceptance criteria

1. Data-bearing NG responses with a command equal to the request command retain the existing
   `ToyopucPlcError`, error code, detail data, and message semantics.
2. Independent synchronous TCP and UDP tests prove that a data-bearing NG response with a different
   command is rejected before PLC-error publication and invalidates the active transport.
3. For representative transmitted state-changing requests over TCP and UDP, that mismatch returns
   `ToyopucOperationOutcomeUnknownError` with `MALFORMED_RESPONSE` reason.
4. For representative read-only requests over TCP and UDP, that mismatch returns the documented
   protocol/malformed-response error and never `ToyopucPlcError`.
5. Equivalent asynchronous public API tests prove the same read-only and state-changing result
   types, reason, and transport invalidation without losing the worker exception to cancellation or
   wrapper translation.
6. After a mismatched response, a following request cannot consume or reuse the retired transport;
   fixed-port UDP retains its required tainted-session behavior.
7. An `RC=0x10` NG response with empty data remains a definitive PLC error whose command byte is
   interpreted as the detailed error code, with no attempted request-command comparison.
8. Validation-order tests prove that complete-frame and frame-type checks precede command
   correlation, while data-bearing NG command correlation precedes PLC-error construction.
9. All tests are deterministic local TCP/UDP or fake-transport checks and require no live PLC.

### Acceptance tracking

- [x] Implementation completed in this repository. Evidence: the shared response validator command-correlates every data-bearing NG response before PLC-error construction while leaving no-data NG semantics unchanged.
- [x] Tests added or updated for every acceptance criterion in this repository. Evidence: sync/async TCP/UDP read and write paths cover matching and mismatched data-bearing NG responses, no-data `RC=0x10`, transport retirement, fixed-port UDP taint, error ordering, and exact outcome classification.
- [x] Relevant static checks, unit tests, integration tests, examples, and package/build checks passed. Evidence: `run_ci.bat` passed Ruff, format, Mypy, script/sample compile, API coverage, 437 tests, and the PyInstaller CLI build; the 98-file current-worktree source archive and isolated wheel/sdist consumer gates also passed.
- [x] Codex self-review completed against the approved contract and cross-language consistency requirements. Evidence: the actual shared validation order, TCP/UDP and sync/async propagation, no-data special form, matching data-bearing PLC errors, state-changing outcome mapping, transport retirement, fixed-port taint, tests, package surface, documentation, and equivalent final .NET implementation were reviewed; no accepted finding remains.
- [x] Required live-PLC checks passed, or each unavailable check has an explicit release disposition. Disposition: no live PLC check is required because command mismatch, matching NG data, and the no-data special form are completely represented by deterministic response frames and fake TCP/UDP transports.
- [x] Documentation, migration notes, changelog, and generated API reference agree with the implementation. Evidence: the decision's compatibility section, user usage, gotchas, API reference, and Unreleased changelog describe the same migration and runtime behavior.
- [x] Final acceptance criteria verified and the item marked complete. Evidence: Python's full gate and package consumers passed, and the final .NET full gate independently passed equivalent data-bearing mismatch, matching-data, no-data, read/write, transport-invalidation, explicit-reopen, and high-level delegation vectors.

## COMPUTERLINK-ASYNC-CANCEL-OUTCOME-001 — Preserve a completed unknown outcome across task cancellation

Decision status: implemented and verified on 2026-08-02.

### Implementation scope

The asynchronous Computer Link worker bridge used by all async public APIs, specifically the race
between completion of its concurrent worker Future and cancellation of the awaiting asyncio Task.
The scope includes terminal worker-result inspection, exception precedence, cancellation behavior,
deterministic race tests, user documentation where behavior is described, migration notes,
changelog, and generated API reference. Synchronous APIs and protocol behavior are unchanged.

### Target contract

When asyncio Task cancellation races with a worker Future that is already terminal, the async bridge
must inspect the worker's terminal result. If the worker completed with
`ToyopucOperationOutcomeUnknownError`, that exception wins over `asyncio.CancelledError` and is
returned to the caller unchanged. This preserves the safety-critical fact that a state-changing
operation may already have reached the PLC.

If the already-terminal worker completed successfully or with any other exception, the existing
`asyncio.CancelledError` result remains authoritative. The bridge must observe the terminal worker
exception while making this decision so it is not silently abandoned, but it must not publish a
non-outcome-unknown worker exception instead of the accepted cancellation result.

Existing behavior outside that narrow completed-Future race remains unchanged: a worker Future that
can still be cancelled before starting produces `asyncio.CancelledError`; a running worker receives
the existing cancellation signal and is awaited; and the running-worker path continues to publish
`ToyopucOperationOutcomeUnknownError` if that is its eventual result, otherwise preserving
`asyncio.CancelledError`.

### Compatibility and operational impact

In the narrow race where cancellation previously hid an already-established unknown write outcome,
callers now receive `ToyopucOperationOutcomeUnknownError` and must not assume that cancellation
prevented the PLC operation. Completed success, completed non-outcome-unknown failure, queued-worker
cancellation, and running-worker cancellation retain their current externally visible results. This
is an intentional safety correction with no compatibility alias or fallback.

### Machine-verifiable acceptance criteria

1. A deterministic barrier-based test completes the worker with
   `ToyopucOperationOutcomeUnknownError`, keeps asyncio delivery of that completion pending, cancels
   the awaiting Task, and proves that the exact outcome-unknown exception wins.
2. The same controlled completed-Future race with a successful worker result returns
   `asyncio.CancelledError`.
3. The same controlled completed-Future race with a representative non-outcome-unknown worker
   exception returns `asyncio.CancelledError`, while the terminal worker exception is observed.
4. Existing queued-worker cancellation still cancels before invocation and returns
   `asyncio.CancelledError` without starting the synchronous operation.
5. Existing running-worker cancellation still signals and awaits the worker; an eventual
   `ToyopucOperationOutcomeUnknownError` wins, while success or another exception retains
   `asyncio.CancelledError`.
6. Tests use explicit events, barriers, or controlled Futures rather than sleeps or scheduler timing,
   and prove no worker exception is reported as unobserved.
7. The contract is exercised through the shared worker bridge and at least one public async
   state-changing API without changing synchronous client behavior.

### Acceptance tracking

- [x] Implementation completed in this repository. Evidence: the shared async bridge inspects an already-terminal concurrent Future, preserves the exact outcome-unknown exception, observes every other terminal result, and otherwise keeps existing cancellation behavior.
- [x] Tests added or updated for every acceptance criterion in this repository. Evidence: explicit event barriers cover terminal outcome-unknown, success, ordinary error, exact exception identity, existing queued/running cancellation, and a public async write path without scheduler sleeps.
- [x] Relevant static checks, unit tests, integration tests, examples, and package/build checks passed. Evidence: `run_ci.bat` passed Ruff, format, Mypy, script/sample compile, API coverage, 437 tests, and the PyInstaller CLI build; the 98-file current-worktree source archive and isolated wheel/sdist consumer gates also passed.
- [x] Codex self-review completed against the approved contract and cross-language consistency requirements. Evidence: the actual cancellation branch, concurrent/async future terminal-state handling, exact exception identity, result observation, public write path, deterministic barriers, package surface, and documentation were reviewed; no accepted finding remains.
- [x] Required live-PLC checks passed, or each unavailable check has an explicit release disposition. Disposition: no live PLC check is required because this is an asyncio/concurrent-Future publication race fully controlled by local event barriers.
- [x] Documentation, migration notes, changelog, and generated API reference agree with the implementation. Evidence: the decision's compatibility section, user usage, gotchas, API reference, and Unreleased changelog document outcome-unknown precedence in the narrow completed-worker race.
- [x] Final acceptance criteria verified and the item marked complete. Evidence: terminal outcome-unknown, success, ordinary failure, queued cancellation, running cancellation, and public async write cases all passed with the approved precedence and no unobserved worker result.

## 2026-08-02 local Codex self-review classification

### COMPUTERLINK-ERROR-CMD-CORRELATION-001

- Accepted and corrected: the first regression covered TCP only. The completed
  matrix covers synchronous and asynchronous TCP/UDP reads and writes, matching
  and mismatched data-bearing NG responses, the no-data special form, and
  fixed-port UDP taint.
- Rejected: command-correlating the no-data `RC=0x10` form would reinterpret its
  detailed error-code byte and contradict the approved exception.
- Duplicate findings: none. Deferred findings: none.

### COMPUTERLINK-ASYNC-CANCEL-OUTCOME-001

- Accepted and corrected: the first completed-worker race could finish asyncio
  delivery before cancellation. Separate worker-start, release, and completion
  events now make the concurrent Future terminal while the event loop remains
  blocked, with no scheduler sleep used as the completion condition.
- Accepted and corrected: bridge-only coverage did not prove one public
  state-changing wrapper. A public async `write_words()` race now preserves the
  exact outcome-unknown exception object.
- Rejected: publishing an ordinary completed worker exception would violate the
  approved cancellation precedence. It is observed, while the caller continues
  to receive `asyncio.CancelledError`.
- Duplicate findings: none. Deferred findings: none.
