# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed
- Documented that `plc_profile` must be an explicit canonical profile name: missing values, aliases, abbreviations, case variants, and implicit `toyopuc:generic` fallback are rejected.

## [1.0.0] - 2026-06-24

### Changed
- Bumped package metadata to `1.0.0` for the first stable release line.

### Fixed
- Added factory-level validation for `ToyopucConnectionOptions` host, port, local port, and receive-buffer size so Python rejects invalid connection settings at the same layer as the .NET factory.

## [0.8.0] - 2026-06-14

### Changed
- Renamed profile-facing APIs from `DeviceProfile` to `PlcProfile` (`ToyopucPlcProfile` / `ToyopucPlcProfiles`) to align with the other PLC communication libraries.
- Replaced display-style profile names with canonical lower-case `toyopuc:<model>:<mode>` values such as `toyopuc:plus:extended` and `toyopuc:pc10g:pc10`.
- Removed legacy profile-name aliases; callers must use the canonical PLC profile strings.
- Removed implicit Generic fallback for blank or missing PLC profiles; high-level clients and profile-aware address resolution now require an explicit canonical profile string.
- Enabled `TCP_NODELAY` for TCP sessions to match the other PLC communication libraries and reduce latency for small request/response cycles.

## [0.1.9] - 2026-06-12

### Fixed
- Fixed `CMD=98`/`CMD=99` multi-point word addressing: word points now carry monitor byte addresses (manual 3-60/3-61 "byte address N") instead of `CMD=94/95` word addresses. Sparse `read_many()` of word devices (including packed bit-device words such as `P1-V000W`) previously read the wrong area and returned incorrect (typically all-zero) data, and sparse `write_many()` of word devices previously wrote to the wrong area. Verified against real hardware where `read_many(["P1-V000W", "P1-V002W"])` returned all-zero before the fix.
- `read_ext_multi()` / `write_ext_multi()` word-point addresses are now documented as monitor byte addresses; callers passing `CMD=94/95` word addresses must double them.
- The protocol simulator now interprets `CMD=98/99` word points as byte addresses, sharing storage with `CMD=94/95`, so the original defect is reproducible against the simulator.
- Fixed `CMD=A0` CPU-status read to send `A0 00 11 00` and parse `00 11 00` plus the 8 status bytes, matching the manual and R08CPU hardware verification.
- Reduced FR PC10 block I/O chunks to `0x01F8` words (`0x03F0` bytes) so `CMD=C2/C3` requests stay within the documented byte-count limit.
- Added fail-fast protocol guards for oversized single-frame requests instead of silently producing out-of-range or count-wrapped frames. This covers continuous read/write, basic multi-point, extended multi-point, PC10 block, and PC10 multi-point commands.
- Restricted `CMD=94-99` EB extended-No addressing to `EB00000-EB1FFFF`; wider EB access remains on the PC10 route when enabled.

## [0.1.8] - 2026-05-02

### Added
- Added public device-address parse/try-parse/format helpers for typed and bit-in-word address notation.
- Added `ToyopucDeviceCatalog.get_device_matrix()` and `ToyopucDeviceMatrixRow` for maintained profile/device range review.
- Expanded `ToyopucConnectionOptions` and `open_and_connect()` so transport, local port, retry delay, receive buffer size, and trace hooks remain explicit in async helper code.
- Added TOYOPUC scan control helpers for scan resume, scan stop, and scan stop release, including relay and async wrapper support.
- Added `ToyopucDeviceCatalog.format_address_range()` and `format_address_ranges()` using `..` as the explicit endpoint separator for split ranges.
- Verified the Python PC10G direct API smoke on hardware for split-range formatting, split-range reads, and scan stop/release/resume.

## [0.1.7] - 2026-04-27

### Fixed
- Fixed TOYOPUC address parsing so single-letter areas such as `D` and `U` are not misread as unknown two-letter areas when the address starts with a hexadecimal `A-F` digit.
- Kept unsupported areas as hard errors instead of falling back to another device interpretation.

## [0.1.6] - 2026-04-14

### Changed
- Reorganized the public docs around beginner-first getting-started and supported-register guides while keeping maintainer notes under `internal_docs`.
- Separated local and publish docs builds so publication settings no longer affect local MkDocs verification.

## [0.1.5] - 2026-04-01

## [0.1.4] - 2026-03-29

### Changed
- `read_many()` / `write_many()` and `relay_read_many()` / `relay_write_many()` now route through the high-level batching path where grouped relay/direct commands are available, while preserving input order.
- Direct high-level batching now uses `CMD=98` sparse extended reads, `CMD=99` sparse extended writes, `CMD=C4` sparse PC10 word reads, and `CMD=C5` sparse PC10 word writes where available.
- Extended multi-bit batch reads now unpack packed bit payloads correctly for batches larger than 8 points.
- `read_named()` bit-in-word helper parsing now accepts hexadecimal bit indices `A-F` as well as `0-9`, matching the .NET helper-layer behavior.
- Async helper wrappers now use per-client dedicated workers instead of the shared default executor.
- Transport and high-level layers cache relay hops, resolved devices, and compiled run plans to reduce repeated parsing and dispatch overhead.
- TCP receive and trace hot paths now allocate less during repeated polling.
- `run_ci.bat` now lint-checks `toyopuc/tests/scripts/samples`, compile-checks all `scripts/` and `samples/` entry points, runs the pytest suite, and builds the CLI executable without per-scenario batch wrappers.
- Added `release_check.bat` to run CI and docs generation as one pre-release entry point.
- Added file-level regression tests that keep `samples/`, `scripts/`, and historical release templates aligned with the current repository layout.
- Documentation now consistently uses the current `scripts/` and `samples/` directories and points open-item references at `TODO.md`.

## [0.1.2] - 2026-03-22

### Changed
- Fixed Python version badge in `README.md` to match `requires-python = ">=3.10"`.
- Added `License :: OSI Approved :: MIT License` classifier consistency.

## [0.1.0] - 2026-03-19

### Added
- Initial Python client library for JTEKT TOYOPUC computer-link communication.
- `ToyopucDeviceClient` with TCP and UDP transport support.
- Model-aware addressing profiles and device catalog support.
- High-level `read`/`write` API for bit and word devices.
- Validation CLI and scripted hardware verification.
- Hardware verified against TOYOPUC-Plus and Nano 10GX targets.

### Notes
- First release under the `toyopuc-computerlink` PyPI package name.
