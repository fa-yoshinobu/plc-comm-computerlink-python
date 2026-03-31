# TODO: Toyopuc Computer Link Python

This file tracks the remaining tasks and known issues for the Toyopuc Computer Link Python library.

## 1. Protocol and Model Coverage
- [ ] **Extended Device Validation**: Expand verified coverage for newer Toyopuc model ranges and unresolved extended-device edge cases.
- [ ] **Addressing Matrix**: Convert the current probe knowledge into a maintained device/profile matrix that is easy to review before releases.

## 2. Testing and Validation
- [x] **Regression Automation**: Promoted the current `scripts/` probes into `run_ci.bat` with simulator-backed smoke coverage and explicit pass/fail handling.

## 3. Documentation and Quality
- [x] **Naming Sweep**: Audit the remaining docs and maintainer notes for stale wording after the `ToyopucDeviceClient` rename.
- [x] **Static Analysis Scope**: Keep `mypy` focused on `toyopuc/`, run `ruff` across `toyopuc/tests/scripts/samples`, and compile-check `scripts/` plus `samples/` in CI.

## 4. Cross-Stack API Alignment

- [ ] **Keep helper naming aligned with the managed stacks**: Preserve the shared high-level contract around `open_and_connect`, `read_typed`, `write_typed`, `write_bit_in_word`, `read_named`, and `poll`.
- [ ] **Review public address helper exposure**: Decide whether Toyopuc address parse/normalize/format helpers should be promoted into a documented utility API so applications do not need private copies.
- [ ] **Keep protocol-specific options explicit**: Preserve Toyopuc-specific settings such as profile selection, relay hops, local port, retries, and retry delay as first-class options instead of hiding them behind ambiguous defaults.
- [ ] **Preserve semantic atomicity by default**: Allow segmentation only on protocol-defined boundaries such as FR or PC10 block limits. Do not silently split one logical value or one user-visible logical block into different semantics.
- [ ] **Preserve semantic atomicity by default**: Allow segmentation only on protocol-defined boundaries such as FR or PC10 block limits. Do not silently split one logical value or one user-visible logical block into different semantics.

## 4. Cross-Stack API Alignment

- [ ] **Keep helper naming aligned with the managed stacks**: Preserve the shared high-level contract around `open_and_connect`, `read_typed`, `write_typed`, `write_bit_in_word`, `read_named`, and `poll`.
- [ ] **Review public address helper exposure**: Decide whether Toyopuc address parse/normalize/format helpers should be promoted into a documented utility API so applications do not need private copies.
- [ ] **Keep protocol-specific options explicit**: Preserve Toyopuc-specific settings such as profile selection, relay hops, local port, retries, and retry delay as first-class options instead of hiding them behind ambiguous defaults.


