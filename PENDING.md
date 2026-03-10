# Pending Items

This file tracks items that are intentionally left open after the current round of implementation and hardware testing.

## Open Items

### Unverified Features

### 2. `CMD=60` relay command

Status:

- protocol summary exists in `COMPUTER_LINK_SPEC.md`
- real hardware test has not been performed

Open question:

- whether the current implementation matches the actual relay path used in the target environment

### Future Improvements


## Specification Re-check Items

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

1. `CMD=60` relay command

## Related documents

- overview: `README.md`
- testing: `TESTING.md`
- protocol: `COMPUTER_LINK_SPEC.md`
- release: `RELEASE.md`
