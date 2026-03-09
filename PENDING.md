# Pending Items

This file tracks items that are intentionally left open after the current round of implementation and hardware testing.

## Open Items

### 1. FR final confirmation

Status:

- code path remains in the project
- real hardware behavior is not finalized yet

Current note:

- `FR` is not part of the normal safe test path
- it should be verified separately before being treated as normal coverage

### 2. `CMD=60` relay command

Status:

- protocol summary exists in `COMPUTER_LINK_SPEC.md`
- real hardware test has not been performed

Open question:

- whether the current implementation matches the actual relay path used in the target environment

### 3. `CMD=C6` FR register

Status:

- protocol summary exists in `COMPUTER_LINK_SPEC.md`
- real hardware test has not been performed

Open question:

- whether the current implementation and actual FR behavior match on the target PLC

### 4. UDP verification note

Status:

- TCP-based checks have been verified
- UDP communication has also been confirmed on hardware when a fixed PC-side source port is used
- implementation supports fixed PC-side UDP source port via `local_port`
- basic/full/mixed/block/boundary UDP checks have been run on `TOYOPUC-Plus`
- UDP unplug/replug recovery has also been confirmed with `tools/recovery_write_loop.py`
- clock read/write and CPU status have also been checked over UDP on `TOYOPUC-Plus`

Suggested check:

- keep using a fixed local UDP port when the PLC requires one
- for `TOYOPUC-Plus`, UDP verification is effectively closed for supported areas
- if needed, repeat UDP verification on a non-Plus environment with wider device support

## Specification Re-check Items

### 5. `CMD=98/99` program-number interpretation

Status:

- current implementation is hardware-verified for the tested paths
- however, the exact scope of each program number should still be kept under review against the original specification

Re-check points:

- `00`: `EP/EK/EV/ET/EC/EL/EX/EY/EM`
- `07`: `GX/GY/GM`
- `01/02/03`: `P1/P2/P3`

### 6. Shared-area naming vs. user-facing naming

Status:

- project documents now use user-facing names
- internal implementation still keeps some shared-area aliases for address conversion

Re-check points:

- `X/Y`
- `T/C`
- `EX/EY`
- `ET/EC`
- `GX/GY`

### 7. `CMD=C4/C5` usage range

Status:

- current implementation uses `CMD=C4/C5` only on selected ranges
- this behavior is hardware-verified for current tests

Re-check points:

- `L1000-L2FFF`
- `M1000-M17FF`
- `U08000-U1FFFF`
- `EB00000-EB3FFFF`
- confirm whether any additional ranges should use `C4/C5`

### 8. FR handling policy

Status:

- `FR` support remains in code
- normal test flow treats it as separate and cautious

Re-check points:

- whether `FR` should stay opt-in only
- whether `FR` should have a dedicated read-only or guarded mode
- whether `FR` should remain excluded from standard coverage summaries

### 9. Manual write-check tail-end rejects

Status:

- manual write-and-check run exposed several end-point addresses that were rejected with `rc=0x10`
- these should be kept visible until the device-specific behavior is confirmed

Observed points:

- `D2FFF`
- `P1-D2FFF`
- `P3-D2FFF`
- `U1FFFF`
- `B` treated as unsupported on `TOYOPUC-Plus`

Open question:

- whether these are true unsupported tail addresses, mode-dependent restrictions, or areas that need narrower default ranges in manual checks

### 10. High-level grouped dispatch optimization

Status:

- `resolve_device()` and `ToyopucHighLevelClient` now exist
- high-level API is hardware-verified on supported TCP/UDP paths
- however, `read_many()` and `write_many()` still dispatch one item at a time

Open question:

- whether to group requests by `scheme / unit / No. / Program No.` and use multi-point or block commands automatically

Expected benefit:

- fewer protocol round-trips
- better performance for repeated `read_many()` / `write_many()` workloads
- better fit for UDP in high-frequency access patterns

Possible next step:

- group same-family requests first
- then add contiguous block coalescing for sequential ranges

## Notes

### Simulator status

Current state:

- `tools/run_sim_tests.bat 127.0.0.1 15000 tcp` passes
- `tools.sim_server` now covers:
  - high-level API smoke paths
  - packed access smoke paths
  - clock read/write
  - CPU status read

Current judgment:

- there is no separate simulator blocker item at the moment
- remaining simulator limitations are already documented in `TESTING.md` and are treated as design limits, not active defects

## Priority

Suggested order:

1. FR final confirmation
2. `CMD=C6` FR register
3. `CMD=60` relay command
4. `CMD=98/99` program-number interpretation
5. `CMD=C4/C5` usage range
6. shared-area naming vs. user-facing naming
7. FR handling policy
8. UDP verification on a non-Plus environment, if needed
9. manual write-check tail-end rejects
10. high-level grouped dispatch optimization

## Related documents

- overview: `README.md`
- testing: `TESTING.md`
- protocol: `COMPUTER_LINK_SPEC.md`
- release: `RELEASE.md`
