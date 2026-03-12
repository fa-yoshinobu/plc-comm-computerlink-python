# Python Porting Notes

This document records the mapping between the original Python implementation in
[`fa-yoshinobu/pytoyopuc-computerlink`](https://github.com/fa-yoshinobu/pytoyopuc-computerlink)
and the current .NET implementation in `Toyopuc`, and also lists the
intentional changes made during the port.

The .NET implementation is a port of
[`fa-yoshinobu/pytoyopuc-computerlink`](https://github.com/fa-yoshinobu/pytoyopuc-computerlink).
This note only records the porting decisions made in this repository. For
protocol background, detailed behavior, and finer reference material, read the
Python repository first.

Related checklist:

- [`PYTHON_DERIVED_ACCESS_CHECKLIST.md`](d:/Github/toyopucdriver/docs/internal/PYTHON_DERIVED_ACCESS_CHECKLIST.md)
- [`PYTHON_PYTEST_CASE_MATRIX.md`](d:/Github/toyopucdriver/docs/internal/PYTHON_PYTEST_CASE_MATRIX.md)

## Scope

Python source:

- [`toyopuc/client.py`](https://github.com/fa-yoshinobu/pytoyopuc-computerlink/blob/main/toyopuc/client.py)
- [`toyopuc/high_level.py`](https://github.com/fa-yoshinobu/pytoyopuc-computerlink/blob/main/toyopuc/high_level.py)
- [`toyopuc/protocol.py`](https://github.com/fa-yoshinobu/pytoyopuc-computerlink/blob/main/toyopuc/protocol.py)
- [`toyopuc/address.py`](https://github.com/fa-yoshinobu/pytoyopuc-computerlink/blob/main/toyopuc/address.py)
- [`toyopuc/relay.py`](https://github.com/fa-yoshinobu/pytoyopuc-computerlink/blob/main/toyopuc/relay.py)

.NET source:

- [`src/Toyopuc/ToyopucClient.cs`](d:/Github/toyopucdriver/src/Toyopuc/ToyopucClient.cs)
- [`src/Toyopuc/ToyopucHighLevelClient.cs`](d:/Github/toyopucdriver/src/Toyopuc/ToyopucHighLevelClient.cs)
- [`src/Toyopuc/ToyopucProtocol.cs`](d:/Github/toyopucdriver/src/Toyopuc/ToyopucProtocol.cs)
- [`src/Toyopuc/ToyopucAddress.cs`](d:/Github/toyopucdriver/src/Toyopuc/ToyopucAddress.cs)
- [`src/Toyopuc/ToyopucDeviceResolver.cs`](d:/Github/toyopucdriver/src/Toyopuc/ToyopucDeviceResolver.cs)
- [`src/Toyopuc/ToyopucRelay.cs`](d:/Github/toyopucdriver/src/Toyopuc/ToyopucRelay.cs)

## Porting Policy

- Preserve the original wire protocol and core addressing behavior where practical.
- Add .NET-specific usability features only where they improve packaging, validation, logging, or model-specific compatibility.
- Treat direct `TOYOPUC-Plus` and relay `Nano 10GX` as different real hardware targets when their address behavior differs.

## Mapping

- `toyopuc/client.py`
  - low-level transport, FR access, clock, CPU status
  - mapped to [`ToyopucClient.cs`](d:/Github/toyopucdriver/src/Toyopuc/ToyopucClient.cs)
- `toyopuc/high_level.py`
  - string address resolution, high-level read/write, FR helpers
  - mapped to [`ToyopucHighLevelClient.cs`](d:/Github/toyopucdriver/src/Toyopuc/ToyopucHighLevelClient.cs)
- `toyopuc/protocol.py`
  - frame construction and response parsing
  - mapped to [`ToyopucProtocol.cs`](d:/Github/toyopucdriver/src/Toyopuc/ToyopucProtocol.cs)
- `toyopuc/address.py`
  - address parsing and encoding helpers
  - mapped to [`ToyopucAddress.cs`](d:/Github/toyopucdriver/src/Toyopuc/ToyopucAddress.cs)
- `toyopuc/high_level.py:resolve_device()`
  - high-level device classification
  - mapped to [`ToyopucDeviceResolver.cs`](d:/Github/toyopucdriver/src/Toyopuc/ToyopucDeviceResolver.cs)
- `toyopuc/relay.py`
  - relay hop parsing
  - mapped to [`ToyopucRelay.cs`](d:/Github/toyopucdriver/src/Toyopuc/ToyopucRelay.cs)

## Intentional Differences

### 1. Addressing Profiles Were Added

The Python implementation assumes one device resolution policy. The .NET port adds [`ToyopucAddressingOptions.cs`](d:/Github/toyopucdriver/src/Toyopuc/ToyopucAddressingOptions.cs) together with named device profiles such as:

- `TOYOPUC-Plus:Plus Extended mode`
- `Nano 10GX:Compatible mode`

These profiles change how the following families are resolved:

- upper `U`
- `EB`
- `FR`

Why this was added:

- On the verified direct `TOYOPUC-Plus` path, `U08000`, `EB00000`, and `FR000000` must not always be treated as PC10.
- On the verified relay `Nano 10GX` path, `U08000`, `EB00000`, and `FR000000` do work through the PC10 path.

Relevant .NET files:

- [`ToyopucAddressingOptions.cs`](d:/Github/toyopucdriver/src/Toyopuc/ToyopucAddressingOptions.cs)
- [`ToyopucDeviceResolver.cs`](d:/Github/toyopucdriver/src/Toyopuc/ToyopucDeviceResolver.cs)

### 2. FR High-Level Access Now Follows the Resolved Scheme

In Python, `read_fr()` and `write_fr()` are dedicated FR helpers:

- [`toyopuc/high_level.py:517`](https://github.com/fa-yoshinobu/pytoyopuc-computerlink/blob/main/toyopuc/high_level.py#L517)
- [`toyopuc/high_level.py:532`](https://github.com/fa-yoshinobu/pytoyopuc-computerlink/blob/main/toyopuc/high_level.py#L532)

In .NET, FR access can follow either of these paths depending on the resolved scheme:

- `pc10-word`
  - `C2` / `C3` / `CA`
- `ext-word`
  - `94` / `95` fallback

Relevant .NET files:

- [`ToyopucHighLevelClient.cs`](d:/Github/toyopucdriver/src/Toyopuc/ToyopucHighLevelClient.cs#L132)
- [`ToyopucHighLevelClient.cs`](d:/Github/toyopucdriver/src/Toyopuc/ToyopucHighLevelClient.cs#L176)

### 3. A Dedicated .NET Validation CLI Was Added

The Python repository contains many focused scripts under
[`tools/`](https://github.com/fa-yoshinobu/pytoyopuc-computerlink/tree/main/tools).
The .NET port consolidates most operational validation into [`examples/Toyopuc.SmokeTest/Program.cs`](d:/Github/toyopucdriver/examples/Toyopuc.SmokeTest/Program.cs).

Added CLI features:

- `--verbose`
- `--log`
- `--suite`
- `--restore-after-write`
- `--profile`
- `--hops`
- `--fr-commit`

This is not a protocol change. It is a .NET-side validation and troubleshooting layer.

### 4. Safe Write and Restore Flow Was Added

The Python repository provides many standalone write-check tools. The .NET port adds a unified safe flow through `--restore-after-write`:

- read original value
- write test value
- verify
- restore original value
- recheck

Relevant file:

- [`examples/Toyopuc.SmokeTest/Program.cs`](d:/Github/toyopucdriver/examples/Toyopuc.SmokeTest/Program.cs)

### 5. Multi-Frame Trace Was Added

The Python implementation exposes `last_tx` and `last_rx`. The .NET port adds `TraceFrames` so multi-step operations can be inspected in order.

Typical use:

- relay wrapped requests
- FR write
- FR commit
- completion wait polling

Relevant file:

- [`ToyopucClient.cs`](d:/Github/toyopucdriver/src/Toyopuc/ToyopucClient.cs#L82)

### 6. .NET Packaging and Samples Were Added

The Python side has package metadata and multiple scripts. The .NET side adds:

- solution and project files
- xUnit tests
- NuGet package metadata
- minimal read-only sample
- scripted validation runner

Relevant files:

- [`Toyopuc.sln`](d:/Github/toyopucdriver/Toyopuc.sln)
- [`Toyopuc.csproj`](d:/Github/toyopucdriver/src/Toyopuc/Toyopuc.csproj)
- [`examples/run_validation.ps1`](d:/Github/toyopucdriver/examples/run_validation.ps1)

### 7. Bit-Device Derived Access Must Use Shorter Addresses

This is a hardware manual rule and must be treated as the supported behavior.

For every bit-device family, derived word/byte notation uses a shorter
hexadecimal address than the bit form.

Examples:

- bit `GMFFFF` -> word `GMFFFW` -> byte `GMFFFL` / `GMFFFH`
- bit `M17FF` -> word `M17FW` -> byte `M17FL` / `M17FH`
- bit `EP0FFF` -> word `EP0FFW` -> byte `EP0FFL` / `EP0FFH`

Interpretation rule:

- bit-device direct notation keeps the bit index width
- derived `W` / `L` / `H` notation uses one fewer hex digit
- derived word/byte ranges are therefore the bit ranges shifted right by 4

This means the earlier shared-range assumption is wrong:

- wrong: bit `GM0000-FFFF` and derived `GM0000W-GMFFFFW`, `GM0000L-GMFFFFL`
- correct: bit `GM0000-GMFFFF` and derived `GM000W-GMFFFW`, `GM000L-GMFFFH`

Affected families:

- basic bit: `P`, `K`, `V`, `T`, `C`, `L`, `X`, `Y`, `M`
- ext bit: `EP`, `EK`, `EV`, `ET`, `EC`, `EL`, `EX`, `EY`, `EM`, `GM`, `GX`, `GY`

Python-side changes required if the Python port copied the old .NET behavior:

- parser:
  - keep the original hex digit count from the input string
  - reject derived forms that use bit-width notation such as `M0000W` or `M0000L`
- model:
  - do not treat `SupportsPackedWord` or byte access as "same range, same width with suffix"
  - store or derive `W` / `L` / `H` ranges separately from bit ranges
  - store or derive derived-access width separately from bit width
- validation:
  - validate derived `W` / `L` / `H` addresses against derived ranges, not bit ranges
  - validate derived digit count against the shorter manual width
- formatting:
  - when converting parsed devices back to text, use derived width
  - do not emit forms like `GM0FFFW`, `GM0FFFL`, or `M0000W` if the manual form is `GMFFFW`, `GMFFFL`, or `M000W`
- tests:
  - add positive cases such as `GMFFFW`, `GMFFFL`, `M17FW`, `M17FL`, `EP0FFW`, `EP0FFL`
  - add negative cases such as `GM1000W`, `GM1000L`, `M0000W`, `EP0000L`

This is not a UI-only issue. It affects:

- parser acceptance
- profile/range validation
- suggested address generation
- canonical device string formatting
- round-trip tests between text and encoded address

### 8. Profile-Enforced Basic Families Are Prefixed-Only

When a device profile is enforced, the current .NET behavior treats these
families as program access only:

- `P`, `K`, `V`, `T`, `C`, `L`, `X`, `Y`, `M`
- `S`, `N`, `R`, `D`

Supported profile-side notation is therefore:

- `P1-D0000`, `P2-D0000`, `P3-D0000`
- `P1-M0000`, `P2-M0000`, `P3-M0000`
- `P1-D0000L`, `P1-M000W`

Unprefixed forms such as `D0000` or `M0000` are now treated as legacy
compatibility behavior only when no profile is enforced.

Python-side changes required if the Python port copied the earlier .NET
profile behavior:

- resolver:
  - when a profile/matrix is active, reject unprefixed `P/K/V/T/C/L/X/Y/M/S/N/R/D`
  - continue to allow them only in the no-profile compatibility path if desired
- profile data:
  - model those families as prefixed-only in the reviewed matrix
  - do not expose direct ranges for them in profile-backed validation
- tools and examples:
  - update validation examples and smoke tools to use `P1-*`, `P2-*`, or `P3-*`
  - update default sample devices from `D0000` to `P1-D0000` where a profile is supplied
- tests:
  - add positive cases such as `P1-D0000`, `P1-M0000`, `P1-D0000L`, `P1-M000W`
  - add negative cases such as profile-backed `D0000`, `M0000`, `D0000L`, `M000W`

This affects more than parser acceptance. It also affects:

- profile matrix consistency
- catalog or dropdown generation
- validation scripts
- user-facing examples

### 9. `GX` And `GY` Must Stay Explicit; Do Not Introduce `GXY`

The current .NET implementation no longer normalizes `GX` and `GY` into an
internal synthetic area such as `GXY`.

Required interpretation:

- `GX` and `GY` remain explicit area names in parser, resolver, formatter, and profile data
- if a target behaves like shared underlying storage for some derived access, that is a target behavior note, not a synthetic area name
- user-facing strings, logs, and internal canonical names should stay `GX` or `GY`

Python-side changes required if the Python port copied the earlier .NET alias:

- parser/model:
  - remove any synthetic `GXY` area name
  - keep `GX` and `GY` as separate supported areas
- resolver/encoding:
  - encode `GX` and `GY` directly, even if they currently map to the same `No` and base offset
- formatting:
  - never emit `GXY...`
- tests:
  - `GX000W` resolves as `GX`
  - `GY000W` resolves as `GY`
  - no round-trip or canonical formatting path emits `GXY`

This is a naming and modeling rule, not a protocol behavior change.

## Behavior Preserved From Python

The following areas were intentionally kept aligned with the Python implementation:

- basic word, bit, and byte read/write behavior
- program address handling
- relay wrapping through `CMD=60`
- FR `C2` / `C3` / `CA` sequence
- clock read/write
- CPU status read

## Same FR Completion Strategy As Python

The .NET port did not invent a new FR completion strategy. It preserves the Python approach used in `wait_fr_write_complete()`:

- try `A0 / 01 10` first
- if unsupported, fall back to normal CPU status polling

Python reference:

- [`toyopuc/client.py:861`](https://github.com/fa-yoshinobu/pytoyopuc-computerlink/blob/main/toyopuc/client.py#L861)

.NET references:

- [`ToyopucClient.cs`](d:/Github/toyopucdriver/src/Toyopuc/ToyopucClient.cs#L691)
- [`ToyopucClient.cs`](d:/Github/toyopucdriver/src/Toyopuc/ToyopucClient.cs#L582)

## Python Tools Not Ported One-to-One

The .NET repository does not include a direct one-to-one port of every Python utility under the upstream `tools/` directory.

Examples not ported as separate .NET tools:

- `high_level_api_test.py`
- `auto_rw_test.py`
- `fr_probe.py`
- `device_read_scan.py`
- `interactive_cli.py`
- `device_monitor_gui.py`

Replacement approach in .NET:

- use [`Toyopuc.SmokeTest`](d:/Github/toyopucdriver/examples/Toyopuc.SmokeTest/Program.cs)
- use [`examples/run_validation.ps1`](d:/Github/toyopucdriver/examples/run_validation.ps1)
- use [`docs/internal/VALIDATION.md`](d:/Github/toyopucdriver/docs/internal/VALIDATION.md)

## Hardware-Driven Changes

Real hardware validation directly affected the port:

- direct `TOYOPUC-Plus`
  - `U08000`, `EB00000`, and `FR000000` were not available through the verified path
- relay target `Nano 10GX`
  - `U08000`, `EB00000`, and `FR000000` were available and verified

Recorded results:

- [`TESTRESULTS.md`](d:/Github/toyopucdriver/docs/internal/TESTRESULTS.md)

## Summary

The short version is:

- the core protocol logic was preserved from Python
- model-specific compatibility required profile-based address resolution
- .NET-specific validation, logging, packaging, and tracing were added
- the Python tool collection was consolidated into a smaller .NET validation workflow
