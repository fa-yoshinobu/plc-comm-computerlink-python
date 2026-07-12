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
- [x] `release_check.bat` passed Ruff, format, mypy, sample/script compilation, API docs, 251 tests, canonical profile parity, PyPI identity, and CLI packaging after the final diff on 2026-07-12.
- [x] Codex reviewed public signatures, sample/config parsing, and the no-fallback source scan.
- [x] Claude review completed (`CLAUDE-CL-20260712-01`; result and dispositions recorded).
- [x] Claude findings dispositioned and affected checks rerun (`CLAUDE-CL-20260712-01`).
- [x] No live communication is required for local endpoint validation; no PLC communication was performed.
- [x] Documentation, changelog, samples, and API coverage agree.
- [x] Final cross-language acceptance verified.

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
- [x] Claude review completed (`CLAUDE-CL-20260712-01`; result and dispositions recorded).
- [x] Claude findings dispositioned and affected checks rerun (`CLAUDE-CL-20260712-01`).
- [x] Live-PLC requirement dispositioned (no live PLC required; UDP bind-0, assigned source port, fixed-port collision, and TCP rejection are covered by local socket fixtures without claiming PLC compatibility).
- [x] Documentation, migration notes, changelog, samples, and generated API coverage agree with the implementation.
- [x] Final acceptance verified.

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
- [x] Claude review completed (`CLAUDE-CL-20260712-01`; result and dispositions recorded).
- [x] Claude findings dispositioned and checks rerun (`CLAUDE-CL-20260712-01`).
- [x] Live-PLC requirement dispositioned (no live PLC required; required transport parsing and pre-socket rejection are deterministic constructor/factory behavior).
- [x] Documentation, changelog, samples, migration notes, and generated API coverage agree with the implementation.
- [x] Final acceptance verified.

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
- [x] Claude review completed (`CLAUDE-CL-20260712-01`; result and dispositions recorded).
- [x] Claude findings dispositioned and checks rerun (`CLAUDE-CL-20260712-01`).
- [x] Live-PLC requirement dispositioned (no live PLC required; timeout default/validation and per-attempt session disposal are covered by deterministic local timeout fixtures).
- [x] Documentation, changelog, samples, migration notes, and generated API coverage agree with the implementation.
- [x] Final acceptance verified.

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
- [x] Claude review completed (`CLAUDE-CL-20260712-01`; result and dispositions recorded).
- [x] Claude findings dispositioned and checks rerun (`CLAUDE-CL-20260712-01`).
- [x] Live-PLC requirement dispositioned (no live PLC required; retry eligibility, send-count boundaries, delay, cancellation, and no-retry state transitions are covered by fault-injected transports).
- [x] Documentation, changelog, samples, migration notes, and generated API coverage agree with the implementation.
- [x] Final acceptance verified.

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
- [x] Claude review completed (`CLAUDE-CL-20260712-01`; result and dispositions recorded).
- [x] Claude findings dispositioned and checks rerun (`CLAUDE-CL-20260712-01`).
- [x] Live-PLC requirement dispositioned (no live PLC required; full-datagram receive and truncation/length handling are covered by local UDP fixtures).
- [x] Documentation, changelog, samples, migration notes, and generated API coverage agree with the implementation.
- [x] Final acceptance verified.

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
- [x] Claude review completed (`CLAUDE-CL-20260712-01`; result and dispositions recorded).
- [x] Claude findings dispositioned and checks rerun (`CLAUDE-CL-20260712-01`).
- [x] Live-PLC requirement dispositioned (no live PLC required; diagnostic copy ownership, ordering, exception isolation, and timing isolation do not depend on PLC behavior).
- [x] Documentation, changelog, samples, migration notes, and generated API coverage agree with the implementation.
- [x] Final acceptance verified.

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
- [x] Claude review completed (`CLAUDE-CL-20260712-01`; result and dispositions recorded).
- [x] Claude findings dispositioned and checks rerun (`CLAUDE-CL-20260712-01`).
- [x] Live-PLC requirement dispositioned (no live PLC required; canonical profile derivation, profile-bound object identity, and pre-transport mismatch rejection are deterministic resolver/vector properties).
- [x] Documentation, changelog, samples, migration notes, and generated API coverage agree with the implementation.
- [x] Final acceptance verified.

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
- [x] Claude review completed (`CLAUDE-CL-20260712-01`; result and dispositions recorded).
- [x] Claude findings dispositioned and checks rerun (`CLAUDE-CL-20260712-01`).
- [x] Live-PLC requirement dispositioned (no live PLC required; named-type grammar, width/range validation, and result decoding are covered by parser and protocol fixtures).
- [x] Documentation, changelog, samples, migration notes, and generated API coverage agree with the implementation.
- [x] Final acceptance verified.

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
- [x] Claude review completed (`CLAUDE-CL-20260712-01`; result and dispositions recorded).
- [x] Claude findings dispositioned and checks rerun (`CLAUDE-CL-20260712-01`).
- [x] Live-PLC requirement dispositioned (no live PLC required; scalar/list return shape, count limits, one-request enforcement, and zero-send rejection are deterministic API/mock-transport properties).
- [x] Documentation, changelog, samples, migration notes, and generated API coverage agree with the implementation.
- [x] Final acceptance verified.

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
- [x] Claude review completed (`CLAUDE-CL-20260712-01`; result and dispositions recorded).
- [x] Claude findings dispositioned and checks rerun (`CLAUDE-CL-20260712-01`).
- [x] Live-PLC requirement dispositioned (no live PLC required; Dword/float conversion, block/limit validation, and one-request/no-partial-write behavior are covered by exact frame and send-count fixtures).
- [x] Documentation, changelog, samples, migration notes, and generated API coverage agree with the implementation.
- [x] Final acceptance verified.

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
- [x] Claude review completed (`CLAUDE-CL-20260712-01`; result and dispositions recorded).
- [x] Claude findings dispositioned and checks rerun (`CLAUDE-CL-20260712-01`).
- [x] Live-PLC requirement dispositioned (no live PLC required; maintainer-only visibility, raw payload validation, exact frame construction, and post-send no-retry are deterministic).
- [x] Documentation, changelog, samples, migration notes, and generated API coverage agree with the implementation.
- [x] Final acceptance verified.

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
- [x] Claude review completed (`CLAUDE-CL-20260712-01`; result and dispositions recorded).
- [x] Claude findings dispositioned and checks rerun (`CLAUDE-CL-20260712-01`).
- [x] Live-PLC work-area check passed on 2026-07-12: Nano 10GX `192.168.250.100:1025` TCP Direct, `FR000000`, original `999`, test `0x7811` (`30737`), readback `30737`, write command `0xC3`, no CA call, restore command `0xC3`, final readback `999`.
- [x] Documentation, changelog, samples, migration notes, and generated API coverage agree with the implementation.
- [x] Final acceptance verified for D-080; durability remains the separate D-081 decision.

Self-review finding (2026-07-12): Python `write_fr_words` and `relay_write_fr_words` converted each input with `int(value) & 0xFFFF`, so invalid public values could become valid but different PLC values. The high-level FR methods also called `int(...)` before the low-level path. This was accepted as a contract violation, corrected with one shared strict FR-word validator, and covered for direct and relay paths before the final release check.

GitHub CI follow-up (2026-07-12): the first published correction at `a141dfc752fab685fe139bda73bb78808ec05765` passed local `release_check.bat` but its Python 3.10／3.11／3.12／3.13 matrix failed only the five parameter cases of the new async FR rejection test. The test had introduced `pytest.mark.asyncio` even though CI intentionally does not install `pytest-asyncio`; 228 other tests passed in every job. The test was changed to the repository's existing `asyncio.run()` pattern without adding a dependency. All five cases pass with pytest plugin autoload disabled, and the full 233-test release check passes after the correction. GitHub rerun evidence is recorded after the corrected commit is published.

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
- [x] Claude review completed (`CLAUDE-CL-20260712-01`; result and dispositions recorded).
- [x] Claude findings dispositioned and checks rerun (`CLAUDE-CL-20260712-01`).
- [x] Live-PLC CA acceptance/durability passed on 2026-07-12: after a clean PLC restart, Python changed `FR000000` from `999` to `0x74E6`, read it back, sent one CA, and used explicit application-level A0 reads to observe writing clear without an abnormal flag. A restart preserved `0x74E6`; .NET restored and committed `999`; a second restart returned `999` through both Python and .NET.
- [x] Documentation, changelog, samples, migration notes, and generated API coverage agree with the implementation.
- [x] Final acceptance verified for D-081 on the tested Nano 10GX profile, endpoint, block, and current Python/.NET builds; no result is generalized to other FR blocks or profiles.

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
- [x] Claude review completed (`CLAUDE-CL-20260712-01`; result and dispositions recorded).
- [x] Claude findings dispositioned and checks rerun (`CLAUDE-CL-20260712-01`).
- [x] Live-PLC requirement dispositioned (no live PLC required; fixed hexadecimal parsing, normalization, formatting, and wire round trips are deterministic vectors).
- [x] Documentation, changelog, samples, migration notes, and generated API coverage agree with the implementation.
- [x] Final acceptance verified.

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
- [x] Claude review completed (`CLAUDE-CL-20260712-01`; result and dispositions recorded).
- [x] Claude findings dispositioned and checks rerun (`CLAUDE-CL-20260712-01`).
- [x] Live-PLC clock-write check passed on 2026-07-12 for Nano 10GX `192.168.250.100:1025` TCP Direct: Python wrote `2026-07-12 12:34:56` with `year_base=2000`; a new .NET session read the advancing test time; .NET restored the captured clock plus elapsed time; new Python and .NET sessions read the advancing restored time.
- [x] Documentation, changelog, samples, migration notes, and generated API coverage agree with the implementation.
- [x] Final acceptance verified. One Nano 10GX showed a short PLC-side clock visibility difference; the user approved keeping only concise maintainer evidence, without generalizing it in GOTCHAS, PROFILES, or the shared docs-site. No automatic wait, reconnect, or retry is added.

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
- [x] Claude review completed (`CLAUDE-CL-20260712-01`; result and dispositions recorded).
- [x] Claude findings dispositioned and checks rerun (`CLAUDE-CL-20260712-01`).
- [x] Live/release disposition recorded. D-084-A passed in Python and .NET: each changed `P1-D0000` through `P1-L1:N2` from `0xFFFF` to `0x3DA4`, read it back, restored `0xFFFF`, and read the restoration back over TCP `192.168.250.100:1025`; both used outer `CMD=60`, link `0x11`, station `0x0002`, and fixed ENQ `0x05`. D-084-B has no available real multi-hop topology or exact route/target and remains explicitly `unverified`; the user approved release with that TODO on 2026-07-12. Exact nested frames, all-hop validation, response unwrap tests, mandatory explicit hops, and no route discovery/fallback contain the unverified scope. Multi-hop live compatibility is not claimed.
- [x] Documentation, changelog, samples, migration notes, and generated API coverage agree with the implementation.
- [x] Final acceptance verified under the recorded D-084-B unverified release disposition; multi-hop live compatibility is not claimed.

## Current verification evidence

- `release_check.bat`: passed on 2026-07-12 after all live-verification dispositions and maintainer-record updates.
- Canonical profile fixture: unchanged against `plc-comm-computerlink-profiles` v1.0.1.
- Ruff lint/format: passed; Mypy: passed for 13 source files.
- Public API docstring coverage: 108 definitions and 164 methods.
- Unit tests: `251 passed`; all maintained samples/scripts compiled.
- PyInstaller CLI executable build: passed.
- PyInstaller spec is generated under ignored `build/toyopuc.spec`; the final release check leaves no root-level `toyopuc.spec` artifact.
- Claude: `CLAUDE-CL-20260712-01` was run by the user; all 11 findings were accepted, corrected, reverified, committed, and pushed.
- Live PLC: D-080, D-081, D-083, and D-084-A passed on 2026-07-12 for the recorded Nano 10GX routes. D-083-LIVE-01 is closed as maintainer-only profile-specific evidence. D-084-B remains `unverified` under its explicit release disposition.

## Live verification evidence and remaining TODO

No command below is authorized merely by appearing here. Confirm the currently connected PLC and the physical route, present the selected exact row again, and wait for explicit user `OK` before communication.

| ID | Exact candidate target | Operation and evidence | Restoration / risk | Status |
|---|---|---|---|---|
| D-080 | Nano 10GX TUC-1157; `toyopuc:nano-10gx:compatible`; `192.168.250.100:1025` TCP; Direct; `FR000000` | `pass`（2026-07-12）。Python／.NETで元値`999`、work-area test `0x7811`、readback `30737`、write command `0xC3`、CA未実行を確認。 | 両実装とも元値`999`をC3で復元しreadback済み。.NET一時project／生成物削除済み。 |
| D-081 | Nano 10GX TUC-1157; `toyopuc:nano-10gx:compatible`; `192.168.250.100:1025` TCP; Direct; `FR000000` | `pass`（2026-07-12）。再起動直後の元値`999`からPythonで`0x74E6`を書込み・readbackしCAを1回実行。明示A0 readで約1秒後に書込み中解除・異常なし。再起動後.NETが`0x74E6`を確認した。 | .NETでC3により`999`へ戻してCAを1回実行し、明示A0 readで約1.5秒後に書込み中解除・異常なし。再々起動後Python／.NETとも`999`。libraryによるpoll／retry／fallbackなし。一時.NET project／生成物削除済み。 |
| D-083 | Nano 10GX TUC-1157; `toyopuc:nano-10gx:compatible`; `192.168.250.100:1025` TCP; Direct; PLC clock | `pass`（2026-07-12）。Python／.NETとも明示century付きwrite、確認read、元時刻復元に成功。 | Profile固有の短い反映差はAPI契約へ一般化しない。自動wait／reconnect／retryなし。一時.NET project／生成物削除済み。 |
| D-084-A | Nano 10GX; `toyopuc:nano-10gx:compatible`; TCP `192.168.250.100:1025`; `P1-L1:N2`; `P1-D0000` | `pass`（2026-07-12）。Python／.NETとも`0xFFFF → 0x3DA4 → 0xFFFF`、outer `CMD=60`、link `0x11`、station `0x0002`、ENQ `0x05`、response unwrap成功。 | 両実装とも元値復元・readback済み。一時.NET project／生成物削除済み。 |
| D-084-B | Real multi-hop topology, endpoint, route, target PLC/device unavailable | `unverified; release permitted`（2026-07-12）。Exact nested-frame, all-hop validation, and response-unwrap tests pass; D-084-A one-hop live behavior passes in Python/.NET. No multi-hop live-pass claim is made. | TODO remains until exact hardware/topology exists. Explicit hops are mandatory; no route discovery, route mutation, or fallback. Any future live command still requires the exact route/target and user `OK`. |

If hardware is unavailable, each item needs an explicit release disposition. The proposed dispositions are recorded in workspace `quality_overhaul_goal_20260711.md`; no proposal is approved merely by being documented.

## Claude review batch `CLAUDE-CL-20260712-01`

- [x] Review package prepared and explicit user authorization obtained for this batch.
- [x] Claude independently reviewed the stated Python/.NET diff read-only; the result is preserved in workspace `Close/instructions/claude_review_result_computerlink_20260712.md`.
- [x] Codex independently reproduced and accepted all eleven findings; no finding was rejected, duplicated, or deferred.
- [x] Accepted findings were corrected with deterministic regression coverage.
- [x] Final full release checks and post-fix Codex diff review recorded (251 tests and complete `release_check.bat`, 2026-07-12).

Finding dispositions:

| Finding | Disposition and acceptance evidence |
| --- | --- |
| 1 | Accepted. FR/dword/float/word helper paths use strict unsigned value validation, restore the dedicated FR work-area route, and reject coercion before transport. |
| 2 | Accepted. Sequence `write` and `relay_write` compile one batch request or reject before send; no element loop remains. |
| 3 | Accepted. Each async worker call owns a start/cancel state; canceling a queued call cancels only that future and does not close the running call's socket. |
| 4 | Accepted, .NET scope. Typed U/S/D/L/F validation and finite float32 reads are aligned with Python. |
| 5 | Accepted as a contract completion. Generic bit/byte/word/dword writes reject truth conversion, masking, fractional conversion, numeric strings, and out-of-range values. |
| 6 | Accepted with stronger correction. UDP sockets connect to the configured endpoint. A fixed-local-port UDP session becomes terminal after an uncertain post-send transport failure because same-endpoint stale responses cannot be identified without a protocol serial. |
| 7 | Accepted. Python exposes `ToyopucOperationOutcomeUnknownError` for state-changing post-send timeout/disconnect/cancellation. |
| 8 | Accepted. Relay reads may retry retry-required outer response `0x73`; relay state-changing operations do not retry after send. |
| 9 | Accepted, .NET scope. Timeout and retry-delay values exceeding `int.MaxValue` milliseconds fail during configuration. |
| 10 | Accepted. The polling example uses a required named dtype. |
| 11 | Accepted. Python direct/relay read/write collection APIs reject empty inputs before transport, matching .NET. |

Machine-verifiable acceptance criteria for the Claude corrections:

1. Invalid bit/byte/word/dword/float/FR values and empty collections send zero requests in both affected implementations.
2. One public sequence write produces exactly one protocol request or fails before transport.
3. Canceling a queued Python async call does not cancel, close, or alter the running call and the queued call sends zero requests.
4. State-changing Python post-send failure has a distinct unknown-outcome exception; relay reads and writes retain different retry eligibility.
5. UDP accepts only the configured endpoint, and a fixed-port session cannot issue another request after an uncertain post-send transport failure.
6. Source, tests, samples, generated/public API documentation, changelog, and maintainer records pass each repository's full release check.

Prepared batch scope: all changes on `quality/2026-07-overhaul` relative to its merge base, with emphasis on `toyopuc/client.py`, `toyopuc/high_level.py`, async wrappers, transport/retry/cancellation state, generated/public API surface, D-066 through D-084 tests and documentation, and the 2026-07-12 strict FR-value correction.

Review purpose: independently identify contract violations, unsafe retry/cancellation transitions, hidden multi-request behavior, validation after transport, public compatibility remnants, direct/relay or sync/async divergence, FR/clock semantic errors, value coercion/masking, and missing tests.

Inputs provided for the completed review: approved contracts and acceptance criteria in this file; repository diff; public API reference; `release_check.bat` result; Ruff/format/mypy evidence; test result; sample/script compilation and PyInstaller evidence; the self-review FR finding and correction; canonical profile parity; and deferred live-verification scope.

Expected output: findings only, each with severity, affected contract identifier, exact file/line evidence, failure scenario, recommended correction, and missing-test recommendation. A general quality score or approval is not a substitute for concrete findings.
