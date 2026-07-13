# Release Checklist

Related documents:

- [README.md](../../README.md)
- [CHANGELOG.md](../../CHANGELOG.md)
- [TESTING_GUIDE.md](TESTING_GUIDE.md)
- [Computerlink Device Ranges](https://fa-yoshinobu.github.io/plc-comm-docs-site/plc-setup/computerlink/device-ranges/)

This document is a practical checklist for releasing the library as a package.

Naming used by this project:

- GitHub repository: `plc-comm-computerlink-python`
- GitHub URL: `https://github.com/fa-yoshinobu/plc-comm-computerlink-python`
- Docs site: `https://fa-yoshinobu.github.io/plc-comm-docs-site/computerlink/python/GETTING_STARTED/`
- package name: `plc-comm-toyopuc`
- import name: `toyopuc`

## 1. Scope

Confirm what is part of the release.

- keep:
  - `toyopuc/`
  - `README.md`
  - `internal_docs/maintainer/TESTING_GUIDE.md`
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

Decide the semantic version before packaging and tagging.

- increment the major version for incompatible public API changes
- increment the minor version for backward-compatible features
- increment the patch version for backward-compatible fixes
- keep `pyproject.toml` and `toyopuc/__init__.py` synchronized
- never retarget a published tag; use a new version

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

## Final Publication Integrity Gate

Before final publication, enumerate every unchecked repository TODO and maintainer checkbox and
give each item a result or explicit release disposition. Build the shared docs site in a fresh
virtual environment using the registry package and require its version/symbol check plus
`mkdocs build --strict`. Compare the published PyPI wheel and sdist byte-for-byte with the inspected
GitHub Release assets. Finally verify the immutable tag target, Release assets/state, docs
deployment, open release PR count, and clean working tree.

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
- [Computerlink Device Ranges](https://fa-yoshinobu.github.io/plc-comm-docs-site/plc-setup/computerlink/device-ranges/)
  - model-specific writable ranges
- [TODO.md](../../TODO.md)
  - active open items only

## 6. Hardware Notes

Keep release notes focused on changed support. Latest profile facts live in the profile data and shared docs, not in release-process notes.

## 7. Safety Notes

Confirm caution notes are present before release.

- `FR` is not part of the normal safe path
- `V` bit mismatch may be tolerated due to PLC-side overwrite
- `S` word mismatch may be tolerated depending on model / behavior
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

Recommended release order:

1. `release_check.bat`
2. `python -m build`
3. `python -m twine check dist/*`
4. create and push the matching immutable version tag
5. let the tag workflow rebuild, test, and attach the checked distributions
6. publish the same checked files to PyPI

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

Prepare a short release note in `CHANGELOG.md` and the GitHub Releases body with:

- version
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

## 12. Post-Release

After release:

- verify that the immutable tag, package metadata, GitHub Release, and PyPI version all match
- keep [Computerlink Device Ranges](https://fa-yoshinobu.github.io/plc-comm-docs-site/plc-setup/computerlink/device-ranges/) updated when new hardware is tested
- keep [TODO.md](../../TODO.md) limited to active items

