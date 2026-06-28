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

## [Unreleased] - 2026-06-28

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
