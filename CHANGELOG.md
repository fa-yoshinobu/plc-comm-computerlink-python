# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

**Entry labels**

- `Release`: Package/version metadata and publishing preparation.
- `Library`: Runtime behavior, public API, protocol handling, or validation in the distributed library.
- `Docs`: README, user guides, generated API docs, or other documentation-only changes.
- `Samples`: Examples, sample flows, sample scripts, or sample applications.
- `Tests`: Test suites, test fixtures, golden vectors, or verification data.
- `Tooling`: Developer/operator command-line tools and helper utilities.
- `CI`: Release checks, workflow scripts, or automation-only changes.

## [Unreleased]

## [3.0.0] - 2026-07-10

### Changed
- Release: Bumped package metadata and `toyopuc.__version__` to `3.0.0`.
- Docs: Replaced relative README links with absolute URLs so they resolve on package registry pages.

### BREAKING
- Library: Breaking: `ToyopucConnectionOptions` and the direct `open_and_connect` helper now require an explicit `plc_profile`.
- Migration: Pass a canonical `plc_profile` to `ToyopucConnectionOptions` and direct `open_and_connect` calls; use the profile `name` for storage and `display_name` for UI labels.
- Library: `ToyopucPlcProfile` now includes `display_name`; use `display_name` for UI labels and the canonical `name` for storage.

### Docs
- Docs: Clarified required profile selection and the separation between canonical names and display names.

## [2.0.0] - 2026-07-06

### BREAKING
- Release: Renamed the PyPI install package while keeping the Python import name unchanged.

| Old install name | New install name | Import name |
| --- | --- | --- |
| `toyopuc-computerlink` | `plc-comm-toyopuc` | `toyopuc` |

### Added
- Docs: Added `docsrc/user/API_REFERENCE.md` as the standard user-facing API index and linked it from the README.

### Changed
- Release: Bumped package metadata to `2.0.0`.
- Docs: Added the plc-comm family package matrix link to the README.
- Tests: Added package-rename import-name coverage for `import toyopuc`.
- Tooling: Updated release duplicate checks to query `plc-comm-toyopuc`.

## [1.2.0] - 2026-07-05

### Changed
- Release: Bumped package metadata to `1.2.0`.
- Tooling: Normalized line-ending handling in the canonical profile JSON update script so `-SourceRoot` runs no longer report false changes.
- Release: Synced `__version__` with the package version.
- Library: Synced the embedded TOYOPUC profile fixture to `plc-comm-computerlink-profiles` `v1.0.1`, including canonical `display_name` labels.
- Library: Added `display_name(profile)` and `ToyopucPlcProfiles.display_name(profile)` as public UI-label helpers while keeping stored PLC profile values canonical.
- Docs: Documented the profile display-name helpers and canonical-ID storage guidance.
- Tests: Added canonical fixture parity coverage for profile `display_name` values.
- Samples: Added read-only `multi_plc_monitor.py` and `config_polling.py` operational recipes with dry-run validation and reconnect backoff.
- Docs: Added public API docstrings for the Computerlink Python package and a CI coverage check for public API documentation.
- Docs: Added a Gotchas entry clarifying that `read_named()` accepts one address per call and should not be used as a multi-address snapshot helper.
- Docs: Removed the per-library troubleshooting/code page; shared Computerlink troubleshooting and code guidance now lives in the PLC Setup Guide.
- Docs: Removed the per-library latest communication verification page and links so user docs stay focused on usage, not verification logs.
- Docs: Removed the manual page-navigation block from Getting Started and rely on site navigation instead.
- Docs: Moved shared supported-register, model-range, and troubleshooting guidance to the common PLC Setup Guide and kept the user docs to Getting Started, Usage Guide, PLC Profiles, and Gotchas.

## [1.1.0] - 2026-06-29

### Changed
- Release: Bumped package metadata to `1.1.0`.
- Library: Made byte-unit parsing require explicit `L` / `H` suffixes and made `read_many` / `write_many` / `read_named` reject implicit multi-request splitting before communication.
- Docs: Documented explicit request-boundary behavior for multi-address helpers.
- Samples: Updated high-level samples to keep `read_many`, `write_many`, `read_named`, and `poll` request boundaries explicit.
- Tests: Added coverage for explicit byte suffix requirements and rejected implicit multi-request named reads.

### Fixed
- Library: Made `BIT_IN_WORD` helper addresses require an explicit bit index such as `P1-D0100.0` through `P1-D0100.F`; `P1-D0100:BIT_IN_WORD` now fails in `parse_device_address`, `try_parse_device_address`, and `read_named` instead of silently reading bit 0.
- Tests: Added coverage for rejecting `BIT_IN_WORD` addresses without an explicit bit index.

## [1.0.1] - 2026-06-25

### Changed
- Release: Bumped Python package metadata to `1.0.1`.
- Docs: Documented that `plc_profile` must be an explicit canonical profile name: missing values, aliases, abbreviations, case variants, and implicit `toyopuc:generic` fallback are rejected.
- Samples: Updated Computerlink sample scripts and guidance to use safer write/restore patterns.

## [1.0.0] - 2026-06-24

### Changed
- Release: Bumped package metadata to `1.0.0` for the first stable release line.

### Fixed
- Library: Added factory-level validation for `ToyopucConnectionOptions` host, port, local port, and receive-buffer size so Python rejects invalid connection settings at the same layer as the .NET factory.
