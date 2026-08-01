# Computerlink Python Contract Overhaul

This GOAL record preserves the approved cross-library target decisions applied
to the Python Computerlink implementation. It is a maintainer acceptance
record, not a user guide or release-execution checklist.

## CLPY-OVERHAUL-001 — Exact request, response, and output capacity

Implementation scope: protocol builders, low-level response validation,
high-level planning, sync and async entry points.

Target contract: every wire limit accepts its exact maximum and rejects
maximum plus one before transport. Python return values are dynamically
allocated, so caller-provided output-buffer capacity is not applicable;
command-specific response lengths are still exact.

Compatibility impact: callers that relied on truncation, wrapping, oversized
single requests, or partially executed invalid plans now receive a validation
error before transport.

Acceptance criteria:

1. Every request family has exact maximum and maximum-plus-one builder tests.
2. Fixed-size response families reject short and long payloads.
3. A multi-request read plan is completely constructed and validated before
   the first transport call.
4. A rejected request leaves socket, last-frame, and traffic-counter state
   unchanged.

- [x] Implementation completed in this repository.
- [x] Tests added or updated for every acceptance criterion.
- [x] Relevant static, unit, integration, documentation, and package checks passed.
- [x] Codex self-review completed against the approved contract and cross-language consistency requirements.
- [x] Live-PLC checks dispositioned: not required; these are deterministic pre-transport and parser boundaries.
- [x] Documentation, migration notes, changelog, and API reference agree with the implementation.
- [x] Final acceptance criteria verified and the item marked complete.

## CLPY-OVERHAUL-002 — One monotonic transaction deadline

Implementation scope: lazy connect, TCP/UDP transmit and receive, decode,
timeout, cancellation, and transport retirement.

Target contract: one admitted timeout snapshot and one monotonic deadline cover
lazy connection, transmit, receive, and decode. Timeout or cancellation retires
the transport. A request is never resent after any send attempt may have
occurred.

Compatibility impact: elapsed connect time is no longer reset before send or
receive, and read requests no longer retry after a post-send failure or PLC
retry-required response.

Acceptance criteria:

1. Remaining socket timeouts decrease against one monotonic deadline.
2. Only failures proven to precede a send attempt may use configured retries.
3. Timeout and cancellation retire the affected transport.
4. A state-changing post-send failure has a machine-readable unknown outcome.

- [x] Implementation completed in this repository.
- [x] Tests added or updated for every acceptance criterion.
- [x] Relevant static, unit, integration, documentation, and package checks passed.
- [x] Codex self-review completed against the approved contract and cross-language consistency requirements.
- [x] Live-PLC checks dispositioned: not required; fault-injected sockets verify deadline and retry state transitions.
- [x] Documentation, migration notes, changelog, and API reference agree with the implementation.
- [x] Final acceptance criteria verified and the item marked complete.

## CLPY-OVERHAUL-003 — Arrival-order FIFO and transport generations

Implementation scope: ordinary sync and async clients, lazy connection,
admission snapshots, waiting cancellation, close, and independent instances.

Target contract: each client serializes ordinary calls in arrival order. Async
uses one worker and sync uses a FIFO admission gate. Cancellation of a waiting
async call sends nothing. `close()` interrupts active work and invalidates work
already admitted in that generation; later admissions can lazily reconnect.
Instances never share queue or generation state.

Compatibility impact: concurrent sync use is now defined and serialized.
Closing a client no longer permits pre-close queued work to reconnect silently.

Acceptance criteria:

1. Sync and async call order equals admission order.
2. A waiting cancellation performs no send and does not cancel its predecessor.
3. Close retires active and queued work with `ToyopucClosedError` or unknown
   outcome reason `closed`, as appropriate.
4. A post-close admission uses a new generation and independent clients are
   unaffected.

- [x] Implementation completed in this repository.
- [x] Tests added or updated for every acceptance criterion.
- [x] Relevant static, unit, integration, documentation, and package checks passed.
- [x] Codex self-review completed against the approved contract and cross-language consistency requirements.
- [x] Live-PLC checks dispositioned: not required; queue and close behavior is local transport state.
- [x] Documentation, migration notes, changelog, and API reference agree with the implementation.
- [x] Final acceptance criteria verified and the item marked complete.

## CLPY-OVERHAUL-004 — Structured failure taxonomy and no post-send retry

Implementation scope: public exceptions, native causes, raw maintainer calls,
read/write retry policy, malformed frames, PLC NG, cancellation, and close.

Target contract: timeout, cancellation, close, explicit-not-connected,
transport, malformed response, and PLC NG are distinct. State-changing work
whose outcome cannot be known exposes `ToyopucOutcomeUnknownReason` and its
native cause. Raw operations are conservatively state-changing. No read or
write is automatically resent after a possible send.

Compatibility impact: callers must catch the dedicated error classes instead
of relying on broad socket errors or automatic read retry.

Acceptance criteria:

1. Every failure category has a distinct public type or unknown-outcome reason.
2. Exception chaining and `cause` retain the native failure.
3. Pre-send state-changing failure is not falsely classified outcome-unknown.
4. Raw, read, write, and relay paths send at most once after possible send.

- [x] Implementation completed in this repository.
- [x] Tests added or updated for every acceptance criterion.
- [x] Relevant static, unit, integration, documentation, and package checks passed.
- [x] Codex self-review completed against the approved contract and cross-language consistency requirements.
- [x] Live-PLC checks dispositioned: not required; injected failure position and send count are deterministic evidence.
- [x] Documentation, migration notes, changelog, and API reference agree with the implementation.
- [x] Final acceptance criteria verified and the item marked complete.

## CLPY-OVERHAUL-005 — Ordered read aggregation and explicit RMW

Implementation scope: `read`, `read_devices`, relay reads, typed reads,
`read_named`, write aggregation, and `write_bit_in_word`.

Target contract: explicit read aggregates preserve caller order, treat each
declared entry as indivisible, preflight the complete plan, split only when
required, hold one FIFO turn, and return all values or raise. Multi-request
snapshots are documented non-atomic. Writes reject multi-request plans.
`write_bit_in_word` remains an explicit non-atomic read-modify-write helper and
holds one exclusive turn; it is not automatic read aggregation.

Compatibility impact: read aggregates that previously rejected multi-request
plans now execute them safely. Their acquisition time can span requests. Write
aggregation remains strict. Multi-address `read_named` is newly supported.

Acceptance criteria:

1. Results and dictionary keys retain declaration order across split plans.
2. Typed 32-bit entries are never divided across request-family or PC10 block
   boundaries; an impossible indivisible entry fails before transport.
3. A later invalid read batch prevents every earlier batch from sending.
4. Multi-request writes fail before transport.
5. Explicit bit-in-word RMW holds one exclusive turn and is documented
   non-atomic relative to PLC logic and other connections.

- [x] Implementation completed in this repository.
- [x] Tests added or updated for every acceptance criterion.
- [x] Relevant static, unit, integration, documentation, and package checks passed.
- [x] Codex self-review completed against the approved contract and cross-language consistency requirements.
- [x] Live-PLC checks dispositioned: not required for release; plan/order/exclusivity are deterministic, while docs explicitly avoid claiming a PLC-atomic snapshot.
- [x] Documentation, migration notes, changelog, and API reference agree with the implementation.
- [x] Final acceptance criteria verified and the item marked complete.

## GOAL-SERIAL-DEFER-002-CONNECT — One absolute connection deadline

Implementation scope: the shared synchronous TCP/UDP engine and every explicit
or lazy synchronous/asynchronous wrapper path.

Target contract: one overflow-checked monotonic deadline is created after FIFO
admission and before IPv4 resolution or socket work. IPv4 DNS, established
first-IPv4 selection, TCP/UDP socket creation, bind/connect, TCP no-delay,
socket timeout configuration, cancellation/close checks, and final client-state
adoption share that deadline. Lazy connection uses the request's existing
deadline, so connection, send, receive, and decode never receive separate full
timeout budgets. A platform DNS or socket call may finish only in an isolated
daemon worker after public timeout/cancellation; that worker retains no client,
closes every abandoned socket, and cannot publish or mutate connected state.

Compatibility impact: no public signature or IPv4 policy changes. Connections
that formerly exceeded the configured timeout during DNS, UDP setup, or socket
configuration now return at the absolute bound. Deadline expiry remains
`ToyopucTimeoutError`; cancellation and close remain distinct; a native
connection failure completed before the deadline remains
`ToyopucTransportError` with its cause.

Acceptance criteria:

1. Explicit and lazy TCP/UDP paths create or receive exactly one monotonic
   deadline before IPv4 resolution and derive every later wait from it.
2. IPv4 literals bypass DNS; hostnames retain first-IPv4 selection with no IPv6,
   alternate-family, route, profile, or discovery fallback.
3. Delayed DNS, TCP connect/configuration, and UDP bind/connect return promptly
   at deadline, start no request, publish no connected state, and close any late
   socket result.
4. Async explicit/lazy wrappers use the synchronous engine's admitted deadline;
   cancellation waits for foreground cleanup but never waits for an abandoned
   platform resolver or socket call to finish.
5. Absolute expiry, caller cancellation, local close, and pre-deadline transport
   failure retain distinct stable public classifications and native causes.
6. Existing retry policy remains pre-send-only and every permitted retry shares
   the unchanged deadline; no late connection sends or replays a request.
7. Deterministic injected resolver/socket tests, full Python gates, documentation,
   and actual-diff self-review verify the contract without live PLC work.

Self-review findings:

- `CLCONNECT-R-1` — Accepted and corrected. A timeout could race a worker's
  successful queue publication and leave an unowned socket. One handoff lock now
  makes abandonment and publication mutually exclusive; timeout/cancellation
  also drains and closes any result already queued.
- `CLCONNECT-R-2` — Accepted and corrected. A native `TimeoutError` returned
  before the absolute deadline was previously converted to the library timeout
  class. Only `_remaining_time` expiry now creates `ToyopucTimeoutError`; an
  early native timeout remains a chained `ToyopucTransportError`.
- `CLCONNECT-R-3` — Accepted and corrected. Numeric IPv4 literals formerly
  entered `getaddrinfo`; they now bypass DNS while hostname selection remains
  first-IPv4-only.
- `CLCONNECT-R-4` — Rejected with rationale. No independent asyncio resolver or
  socket engine is added. Async explicit and lazy calls already preserve FIFO,
  cancellation, and timeout snapshots through the shared synchronous engine;
  a second implementation would create divergent adoption and retry behavior.
- `CLCONNECT-R-5` — Accepted and corrected during verification. After a
  cancelled or closed operation abandoned a blocked DNS worker, that worker
  could still start the socket phase before its result was discarded. The
  worker now checks the shared abandonment event immediately after resolution
  and before creating or binding a socket. The cancellation, deadline, and
  close regressions pass with warnings promoted to errors.

- [x] Implementation completed in this repository.
- [x] Tests added or updated for every acceptance criterion.
- [x] Relevant static, unit, integration, documentation, and package checks passed.
- [x] Codex self-review completed against the approved contract and cross-language consistency requirements.
- [x] Live-PLC checks are not required; deadline, cleanup, and adoption are deterministic local properties.
- [x] Documentation, migration notes, changelog, and API reference agree with the implementation.
- [x] Final acceptance criteria verified and the item marked complete.

## Verification evidence

- Windows Python 3.14 CI: Ruff lint and format, mypy, script/sample compile,
  public API documentation coverage (115 definitions and 165 methods), all 369
  tests without warnings, and PyInstaller executable build passed.
- Python 3.10.20: all 355 tests passed.
- `mkdocs build --strict` passed with all five standard user pages in site
  navigation.
- Wheel/sdist contract passed: 19 wheel files and 25 sdist files, with runtime,
  metadata, license, README, and `py.typed`, and without repository-only files.
- An isolated virtual environment installed the built wheel and verified the
  public error symbols, outcome enum, version API, and removed `retryable`
  parameter without importing the worktree.
- A synthetic worktree source archive containing modified, untracked, and
  deleted paths passed the complete non-hardware gate and package-consumer
  gate: 97 files, 16 sample files, 11 test files, and all 355 tests.
- `git diff --check` passed.

## Codex self-review findings

| Finding | Classification and disposition |
| --- | --- |
| Public `connect(_deadline=...)` leaked an internal keyword into subclass overrides. | Accepted and fixed with a public zero-argument wrapper plus private deadline-aware connect path. |
| The possible-send flag was set before socket timeout configuration. | Accepted and fixed; a pre-send configuration failure is now a transport error, not outcome-unknown. |
| Close could race connection assignment, leak the local socket, or allow stale queued work to reconnect. | Accepted and fixed with atomic generation validation, transport interruption, and queued-generation rejection. |
| Async queued calls retained mutable/one-shot arguments by reference. | Accepted and fixed with admission-time recursive snapshots. |
| PC10 explicit read aggregation could select a block request across a block boundary. | Accepted and fixed by block-aware read planning and indivisible-entry rejection. |
| Fixed write responses with trailing data were accepted. | Accepted and fixed; direct and relay state-changing responses now enforce exact command data and classify malformed post-send outcomes. |
| User documentation and public helper docstrings still called potentially multi-request read results snapshots, and the poll docstring still claimed exactly one address. | Accepted and fixed; aggregate results are named collections/results, non-atomic semantics remain explicit, and poll documents the supported non-empty unique address collection. |
| Existing fake sockets lacked `settimeout`, and tests expected the full configured timeout at every phase. | Rejected as obsolete test assumptions; fakes now implement socket timeout and assertions verify decreasing time against one deadline. |
| Existing read tests expected response/EOF retry after send. | Rejected because it contradicts the approved no-post-send-retry contract; send-count tests now require exactly one attempt. |
| Live PLC verification for queue, capacity, classification, and planning behavior. | Deferred with release disposition `not required`: these properties are deterministic and exhaustively fault-injected; no PLC compatibility claim was added. |

## CLPY-ARTIFACT-001 — Installable consumer and complete worktree source archive

Implementation scope: wheel/sdist contract checker, isolated consumer import,
source-archive worktree mode, extracted non-hardware checks, and CI/release
artifact evidence.

Target contract: the wheel gate installs the exact built wheel into a new
virtual environment with no checkout or `PYTHONPATH`, then verifies public
imports, `__all__`, callable signatures, docstrings, version identity, and the
installed module location. Worktree source archives are created from a
synthetic Git tree that includes every modified and untracked non-ignored file
and every tracked deletion, then the extracted archive alone passes the full
non-hardware gate and the same isolated package-consumer gate.

Compatibility impact: none; this strengthens artifact verification without
changing runtime behavior or the public Python API.

Acceptance criteria:

1. Wheel and sdist content rules still reject repository-only files and require
   metadata, license, README, and `py.typed`.
2. The exact wheel installs into a fresh venv, imports only from that venv, and
   exposes eight representative documented public entry points.
3. Worktree mode includes modifications, untracked files, and deletions in one
   synthetic archive rather than overlaying selected files onto `HEAD`.
4. The extracted archive passes Ruff, formatting, mypy, compilation, API-doc
   coverage, 355 tests, CLI construction, package rebuild, and isolated wheel
   consumption without referring to the checkout.

Self-review finding disposition: accepted. The former package checker inspected
filenames only, while the former worktree archive path retained `HEAD` content
and could not prove deletions or a complete consumer-valid snapshot.

- [x] Implementation completed in this repository.
- [x] Consumer and synthetic-worktree regression behavior added to permanent gates.
- [x] Full non-hardware, package, isolated-consumer, and extracted-source checks passed.
- [x] Codex self-review completed against archive completeness and checkout-independent import requirements.
- [x] Live PLC verification is not required; artifact construction and import behavior are deterministic.
- [x] Maintainer record and changelog agree with the implemented gates.
- [x] Final acceptance criteria verified and the item marked complete.

## GOAL-CROSS-OS-CI-001 — Required Windows representative contract smoke

Implementation scope: the repository CI workflow and the existing deterministic
transport-lifecycle tests. Runtime code, public API, packaging, release
workflows, and the Linux Python-version matrix are unchanged.

Target contract: the primary Ubuntu full gate remains authoritative. One
additional non-optional Windows job on Python 3.13 runs only representative
fake-socket contracts for late connect completion, native connect failure,
absolute connect timeout, fragmented TCP response assembly, terminal fixed-port
UDP timeout, close retirement of active/queued work, async generation
replacement, and a same-client explicit TCP reconnect followed by a successful
exchange. The job has a ten-minute bound and performs no package build or
hardware communication.

Compatibility impact: none; this adds CI evidence only.

Machine-verifiable acceptance criteria:

1. `.github/workflows/ci.yml` contains exactly one `windows-latest` contract-
   smoke job in addition to the unchanged Ubuntu full matrix.
2. The Windows job is required by workflow semantics: it has no conditional,
   failure suppression, or `continue-on-error` path.
3. The selected tests prove fragmented receive, connection failure, bounded
   timeout, late completion rejection, terminal UDP timeout, close retirement,
   and successful work on a new generation.
4. The Windows job installs only pytest, runs the explicit bounded test list,
   and does not build, package, publish, or contact a PLC.

- [x] Implementation completed in this repository.
- [x] Deterministic test code added or explicitly selected for every acceptance criterion.
- [x] The exact Windows smoke cases passed locally as part of the full 369-test Windows gate.
- [ ] The new Windows CI job passed on GitHub for the final source state.
- [x] Codex self-review completed after the requested verification run.
- [x] Live PLC checks are not required; all selected behavior uses fake sockets and local lifecycle state.
- [x] Maintainer CI documentation agrees with the workflow; no user migration note or changelog entry is required.
- [ ] Final acceptance criteria verified and the item marked complete.

Verification disposition: the Windows Python 3.14 worktree source-archive gate
passed Ruff, formatting, mypy, compilation, API-doc coverage, 369 tests,
PyInstaller, wheel/sdist construction, and isolated-wheel consumption. The
workflow's final GitHub-hosted Windows Python 3.13 result remains unchecked
until publication is separately authorized.

Self-review disposition:

- Accepted and corrected: the first selection covered connection and lifecycle
  retirement but no deliberately fragmented receive. A one-byte fake TCP
  response case now proves fixed header/body assembly and is selected directly.
- Accepted and corrected: operation-generation reuse alone did not prove a new
  socket connection. A timed-out transport is now closed, explicitly reconnected
  on the same client, and followed by a successful request/response.
- Rejected: copying existing deterministic cases into a Windows-only test file
  would create two sources of truth without adding coverage. The workflow uses
  exact repository-owned test node IDs instead.
- Duplicate findings: none. Deferred findings: none.
