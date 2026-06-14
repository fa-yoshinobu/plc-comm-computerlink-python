# Testing Guide

This repository no longer keeps per-device or per-scenario batch wrappers for
individual hardware validation. That bring-up phase is complete.

Current testing has two supported entry points:

| Task | Command |
|---|---|
| Local CI gate | `run_ci.bat` |
| Release preflight | `release_check.bat` |

## Local CI Gate

Run from the repository root:

```bat
run_ci.bat
```

The local gate checks:

1. Ruff lint
2. Ruff format
3. mypy for the library package
4. Python compilation for scripts and samples
5. pytest
6. PyInstaller build for the `toyopuc` CLI helper

## GitHub Actions

The GitHub Actions CI mirrors the library-quality part of the local gate:

1. Ruff lint
2. Ruff format
3. mypy
4. pytest

The PyInstaller build remains local/release-oriented because it is a Windows
operator convenience artifact, not the library package itself.

## Hardware Checks

Do not add new one-off `.bat` files for hardware checks. If a new field issue
requires live confirmation, run the relevant Python helper directly and record
only the conclusion in a stable maintainer document.

Examples:

```bat
python scripts\interactive_cli.py --host 192.168.250.100 --port 1025 --protocol tcp
python scripts\clock_test.py --host 192.168.250.100 --port 1025 --protocol tcp
python scripts\cpu_status_test.py --host 192.168.250.100 --port 1025 --protocol tcp
```

Hardware-specific logs, packet captures, and temporary scan outputs are local
debugging artifacts and must not be committed.

## Release Gate

Run from the repository root:

```bat
release_check.bat
```

The release gate checks the PyPI version and delegates the implementation gate
to `run_ci.bat`.
