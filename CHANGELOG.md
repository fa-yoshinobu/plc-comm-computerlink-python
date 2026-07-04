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

### Changed
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
