# TODO: Toyopuc Computer Link Python

This file tracks the remaining tasks and known issues for the Toyopuc Computer Link Python library.

## 1. Protocol Implementation Gaps
- [ ] **Extended Device Support**: Investigate and implement full support for newer Toyopuc model extended device ranges.
- [ ] **Async Support**: Consider implementing an asynchronous client similar to the SLMP library.

## 2. Testing & Validation
- [ ] **Hardware QA Reports**: Migrate and formalize existing validation results into `docs/validation/reports/`.
- [ ] **Automated Regression**: Integrate existing tools in `scripts/` into a unified automated test suite.

## 3. Documentation & Maintenance
- [ ] **Modern Docs Finalization**: Review all migrated documents in `docs/` and ensure they follow the unified style.
- [ ] **Distribution Configuration**: Update `pyproject.toml` to exclude non-user folders from the distribution package.
- [ ] **Static Analysis**: Achieve 100% compliance with `ruff` and `mypy`.
