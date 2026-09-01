# TODO: Toyopuc Computerlink Python

Current active TODOs only.

## Current Status

One high-level API naming candidate is currently tracked. Library implementation has not started.

## CL-NAME-004: Explicit FR work-area and block-commit names

### Target State Candidate

Make the two different FR operations explicit in the Python high-level API:

- writing only to the FR work area;
- committing one FR block.

The current `write_fr` / `relay_write_fr` and `commit_fr` / `relay_commit_fr` names do not express that distinction as clearly as the .NET `WriteFrWorkArea` and `CommitFrBlock` names. The final Python names must also avoid collision with the existing numeric low-level `commit_fr_block` API.

Preferred candidates for later specification discussion are:

- `write_fr_work_area`
- `relay_write_fr_work_area`
- `commit_fr_block_by_device`
- `relay_commit_fr_block_by_device`

These are candidates only. The exact canonical names are not approved by this TODO entry.

This reopens a previously approved language-specific naming decision, so the exact canonical names and transition behavior require separate approval before implementation.

### Acceptance Criteria

1. Exact canonical Python names are approved before implementation.
2. Work-area write and block commit cannot be confused by their public names or documentation.
3. High-level device-address APIs remain distinguishable from numeric low-level APIs.
4. Direct and relay variants use the same naming rule.
5. Existing names follow the separately approved transition and removal policy.
6. Tests prove that work-area write does not commit and block commit uses the intended block.

- [ ] Target contract approved.
- [ ] Implementation completed.
- [ ] Tests added or updated for every acceptance criterion.
- [ ] Relevant static, unit, package, and documentation checks passed.
- [ ] Codex self-review completed.
- [ ] Documentation, migration notes, changelog, and API reference agree.
- [ ] Required live-PLC checks passed or given an explicit disposition.
- [ ] Final acceptance criteria verified.
