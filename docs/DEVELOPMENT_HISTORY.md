# Development History

## 2026-06-11 Archived Refactor Plan

The previous `refactor-instructions.md` was archived into this history file.

### Scope

- Library: Python Toyopuc Computer Link package.
- Primary task: split responsibilities from `toyopuc/high_level.py` using move-only internal modules.
- Extracted pure logic was to receive direct unit tests while preserving all existing public exports.

### Contracts To Preserve

- Public exports from `toyopuc/__init__.py`, `toyopuc.high_level`, and related public modules.
- Exact transmitted frame bytes from packing functions.
- Batch planning rules for PC10 boundaries, continuous ranges, FR handling, bit/word behavior, and semantic atomicity.
- Profile validation rejection conditions and exception messages.
- Recent UDP response truncation fix behavior.
- Dependency-free package metadata, `pyproject.toml`, and version `0.1.8`.

### Debt Notes

- D1: PC10 payload packing and batching logic lacked direct characterization tests.
- D2: `high_level.py` mixed address resolution, packing, batching, transport-facing high-level behavior, and public API compatibility in one large module.
- D3: `utils.py` and `high_level.py` role boundaries were noted but left unchanged.
- D4: large maintenance scripts were report-only.

### Planned Verification

- Record baseline results, including simulator smoke checks when available.
- Add characterization tests for packing and planning cases using current output.
- Split pure helpers into private modules such as `_pc10.py` and `_batching.py`, with re-export compatibility retained.
- Run pytest and smoke checks after each split.

### Out Of Scope

- Public module path changes.
- Frame-byte changes.
- Dependency, version, changelog, PyInstaller, or release work.
