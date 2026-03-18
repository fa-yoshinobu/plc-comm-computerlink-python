# TODO: Toyopuc Computer Link Python

This file tracks the remaining tasks and known issues for the Toyopuc Computer Link Python library.

## 1. Protocol and Model Coverage
- [ ] **Extended Device Validation**: Expand verified coverage for newer Toyopuc model ranges and unresolved extended-device edge cases.
- [ ] **Addressing Matrix**: Convert the current probe knowledge into a maintained device/profile matrix that is easy to review before releases.

## 2. Testing and Validation
- [ ] **Formal Hardware Evidence**: Add validation reports for `ToyopucDeviceClient`, `AsyncToyopucDeviceClient`, relay paths, and 32-bit helper behavior.
- [ ] **Regression Automation**: Promote the current `scripts/` probes into a repeatable regression workflow with clear pass/fail outputs.

## 3. Documentation and Quality
- [ ] **Naming Sweep**: Audit the remaining docs and maintainer notes for stale wording after the `ToyopucDeviceClient` rename.
- [ ] **Static Analysis Scope**: Decide the target `ruff` / `mypy` coverage for package code versus scripts and samples, then close the gap.
