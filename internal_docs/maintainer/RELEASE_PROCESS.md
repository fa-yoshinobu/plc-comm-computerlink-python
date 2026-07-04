# Release Checklist

Related documents:

- [README.md](../../README.md)
- [RELEASE_NOTES.md](RELEASE_NOTES.md)
- [TESTING_GUIDE.md](TESTING_GUIDE.md)
- [Computerlink Device Ranges](https://fa-yoshinobu.github.io/plc-comm-docs-site/plc-setup/computerlink/device-ranges/)
- [PROTOCOL_SPEC.md](PROTOCOL_SPEC.md)

This document is a practical checklist for releasing the library as a package.

Naming used by this project:

- GitHub repository: `plc-comm-computerlink-python`
- GitHub URL: `https://github.com/fa-yoshinobu/plc-comm-computerlink-python`
- Docs site: `https://fa-yoshinobu.github.io/plc-comm-docs-site/computerlink/python/`
- package name: `toyopuc-computerlink`
- import name: `toyopuc`

## 1. Scope

Confirm what is part of the release.

- keep:
  - `toyopuc/`
  - `README.md`
  - `internal_docs/maintainer/TESTING_GUIDE.md`
  - `internal_docs/maintainer/PROTOCOL_SPEC.md`
  - [Computerlink Device Ranges](https://fa-yoshinobu.github.io/plc-comm-docs-site/plc-setup/computerlink/device-ranges/)
  - `TODO.md`
  - `LICENSE`
  - `pyproject.toml`
- exclude:
  - `logs/`
  - `manual/`
  - ad-hoc local output files

## 2. Public API

Confirm which names are treated as public and stable enough to document.

- low-level:
  - `ToyopucClient`
  - `parse_address()`
  - `parse_prefixed_address()`
  - `encode_bit_address()`
  - `encode_word_address()`
  - `encode_byte_address()`
  - `encode_program_bit_address()`
  - `encode_program_word_address()`
  - `encode_program_byte_address()`
  - `encode_ext_no_address()`
  - `encode_exno_bit_u32()`
  - `encode_exno_byte_u32()`
- high-level:
  - `ToyopucDeviceClient`
  - `resolve_device()`

Decide whether any current helpers should remain internal-only.

## 3. Versioning

Decide release version before packaging.

- choose `0.x` if API may still change
- choose `1.0.0` only if public API is intended to be stable
- update version in `pyproject.toml`

## 4. Package Metadata

Check `pyproject.toml`.

- package name
- version
- description
- readme
- license
- authors / maintainers
- `requires-python`
- keywords
- classifiers
- project URLs

## 5. Documentation

Verify that the docs match the code.

- `README.md`
  - install
  - basic usage
  - high-level usage
  - UDP `local_port` note
  - supported / unsupported behavior notes
- [TESTING_GUIDE.md](TESTING_GUIDE.md)
  - test tools usage
  - verified results
- [PROTOCOL_SPEC.md](PROTOCOL_SPEC.md)
  - protocol summary
  - example messages
- [Computerlink Device Ranges](https://fa-yoshinobu.github.io/plc-comm-docs-site/plc-setup/computerlink/device-ranges/)
  - model-specific writable ranges
- [TODO.md](../../TODO.md)
  - open items clearly separated from verified behavior

## 6. Verified Hardware Notes

Keep tested hardware explicit in release notes.

Currently verified:

- `TOYOPUC-Plus CPU (TCC-6740) + Plus EX2 (TCU-6858)`
- TCP
- UDP with fixed `local_port`
- low-level API
- high-level API
- mixed / block / boundary / recovery tests

State clearly that unsupported areas depend on model.

## 7. Safety Notes

Confirm caution notes are present before release.

- `FR` is not part of the normal safe path
- `V` bit mismatch may be tolerated due to PLC-side overwrite
- `S` word mismatch may be tolerated depending on model / behavior
- `TOYOPUC-Plus` has unsupported areas such as `B`
- some UDP environments require fixed PC-side source port

## 8. Code Checks

Install release dependencies before running checks:

```bash
python -m pip install -e .[dev]
```

Run syntax checks:

```bash
cmd /c run_ci.bat
```

Optional import smoke test:

```bash
python - <<'PY'
from toyopuc import ToyopucClient, ToyopucDeviceClient, resolve_device
print("import ok")
PY
```

## 9. Build Check

Canonical pre-release entry point:

```bat
release_check.bat
```

This runs:

1. PyPI registry duplicate check
2. `run_ci.bat`

Build the package locally before publishing.

```bash
python -m build
```

If using Twine:

```bash
python -m twine check dist/*
```

Current status:

- `release_check.bat`: completed for `toyopuc-computerlink` `0.1.9`
- `python -m build`: completed for `toyopuc-computerlink` `0.1.9`
- `python -m twine check dist/*`: completed for `toyopuc-computerlink` `0.1.9`

Recommended release order:

1. `python -m build`
2. `python -m twine check dist/*`

## 10. Final Git Check

Before tagging or uploading:

```bash
git status
git diff --stat
```

Confirm:

- no accidental local files
- no manual/vendor files
- no logs

## 11. Release Notes

Prepare a short release note with:

- version
- confirmed hardware
- main features
  - low-level client
  - high-level client
  - TCP / UDP
  - model notes
- known limitations
  - `FR`
  - `CMD=CA`
  - `CMD=60`
  - model-specific unsupported ranges

Current release note file:

- [RELEASE_NOTES.md](RELEASE_NOTES.md)
- GitHub Releases body:
  - [GITHUB_RELEASE_v1.0.3.md](GITHUB_RELEASE_v1.0.3.md)
  - includes title, tag, target, body, and upload checklist

## 12. Post-Release

After release:

- record tag / version
- keep [Computerlink Device Ranges](https://fa-yoshinobu.github.io/plc-comm-docs-site/plc-setup/computerlink/device-ranges/) updated when new hardware is tested
- move completed items out of [TODO.md](../../TODO.md)

