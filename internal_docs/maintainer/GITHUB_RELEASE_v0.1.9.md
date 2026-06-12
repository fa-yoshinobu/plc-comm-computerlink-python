# GitHub Release Template: v0.1.9

Use this file as a copy-paste template for the GitHub Releases form.

## Release Settings

- Title: `Release v0.1.9`
- Tag: `v0.1.9`
- Target: `main`
- Set as latest release: `yes`
- Pre-release: `no`

## Release Body

TOYOPUC Computer Link Python maintenance release.

## Highlights

- Records the 2026-06-12 defect verification results for PC10 sparse reads, FR commit/persistence, and relay-hop access.
- Keeps generic FR writes guarded; use explicit `write_fr(..., commit=False|True)` or `commit_fr()`.
- Keeps single-request and chunked APIs explicit so the caller decides when protocol splitting is acceptable.
- Refreshes release dependencies and MkDocs release-build instructions.
- Brings GitHub Releases back in sync after the repository release list stopped at `v0.1.5` while PyPI had `0.1.8`.

## Verification

- `release_check.bat` -> passed
- `python -m build` -> passed
- `python -m twine check dist/*` -> passed
- PyPI duplicate check for `toyopuc-computerlink` `0.1.9` -> not already published

## Assets

- `dist/toyopuc_computerlink-0.1.9-py3-none-any.whl`
- `dist/toyopuc_computerlink-0.1.9.tar.gz`

## Upload Checklist

- attach `toyopuc_computerlink-0.1.9-py3-none-any.whl`
- attach `toyopuc_computerlink-0.1.9.tar.gz`
- confirm the tag is `v0.1.9`
- confirm release notes match `CHANGELOG.md`
