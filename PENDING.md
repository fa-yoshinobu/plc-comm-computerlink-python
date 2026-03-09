# Pending Items

This file tracks items that are intentionally left open after the current round of implementation and hardware testing.

## Open Items

### Unverified Features

### 1. FR final confirmation

Status:

- confirmed on `Nano 10GX (TUC-1157)` over UDP on `2026-03-10`
- on that model, full-range `FR000000-FR1FFFFF` read/write/commit persistence is also confirmed
- still open for other models until separately checked

Current note:

- `FR` is not part of the normal safe test path
- on `Nano 10GX (TUC-1157)`:
  - read path is `CMD=C2`
  - write path is `CMD=C3`
  - commit path is `CMD=CA`
  - each committed FR block must wait for flash-write completion before the next `CA`
  - practical wait path is `CMD=32 / 11 00` `Data7.bit4/bit5`
  - persistence after CPU reset has been confirmed for the full FR range
- the generic coarse range scan treated `FR` as unsupported only because it was using the old direct mapping assumption

### 2. `CMD=60` relay command

Status:

- protocol summary exists in `COMPUTER_LINK_SPEC.md`
- real hardware test has not been performed

Open question:

- whether the current implementation matches the actual relay path used in the target environment

### 3. `CMD=CA` FR register

Status:

- confirmed on `Nano 10GX (TUC-1157)` as the FR commit path
- confirmed on that model only when each `CA` is followed by completion wait
- still open for other models until separately checked

Open question:

- whether any model-specific differences exist outside the confirmed `Nano 10GX (TUC-1157)` path

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

### Future Improvements

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

## Specification Re-check Items

### 5. `CMD=98/99` program-number interpretation

Status:

- confirmed on `Nano 10GX (TUC-1157)` on `2026-03-10`
- current mapping was probed against candidate `no` values `00/01/02/03/07`
- `EX/GX/P1/P2/P3` showed no alias across the tested candidates
- still open for other models until separately checked

Re-check points:

- `00`: `EP/EK/EV/ET/EC/EL/EX/EY/EM`
- `07`: `GX/GY/GM`
- `01/02/03`: `P1/P2/P3`

### 6. Shared-area naming vs. user-facing naming

Status:

- documents, examples, and test labels now use user-facing paired names
- internal aliases remain only as implementation details for address conversion
- no active hardware question remains on `Nano 10GX (TUC-1157)`

Re-check points:

- keep future outward-facing text on `X/Y`, `T/C`, `EX/EY`, `ET/EC`, and `GX/GY`

### 7. `CMD=C4/C5` usage range

Status:

- confirmed on `Nano 10GX (TUC-1157)` on `2026-03-10`
- `L1000-L2FFF` and `M1000-M17FF` should stay on `CMD=C4/C5`
- basic `CMD=20/21` did not alias the same points for those upper `L/M` ranges
- `CMD=C4/C5` also reached the same points for `U00000-U1FFFF` and `EB00000-EB3FFFF`
- current implementation still keeps normal `U/EB` word-byte paths on `CMD=94/95` or `CMD=C2/C3`
- still open only as a design choice for other models or future dispatch changes

Re-check points:

- whether `U/EB` should remain on the current normal path or be widened to `CMD=C4/C5`
- whether any other model shows a different split

### 8. FR handling policy

Status:

- `FR` support remains in code
- normal test flow treats it as separate and cautious
- current high-level policy rejects generic `write("FR...")` and `write_many()` entries that target `FR`
- explicit `write_fr(..., commit=...)` / `commit_fr()` remains the supported path

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
2. `CMD=CA` FR register
3. `CMD=60` relay command
4. `CMD=98/99` program-number interpretation
5. `CMD=C4/C5` usage range
6. FR handling policy
7. UDP verification on a non-Plus environment, if needed
8. manual write-check tail-end rejects
9. high-level grouped dispatch optimization

## Related documents

- overview: `README.md`
- testing: `TESTING.md`
- protocol: `COMPUTER_LINK_SPEC.md`
- release: `RELEASE.md`
