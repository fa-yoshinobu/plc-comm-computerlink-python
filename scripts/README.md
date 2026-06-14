
# Scripts

[![Documentation](https://img.shields.io/badge/docs-GitHub_Pages-blue.svg)](https://fa-yoshinobu.github.io/plc-comm-docs-site/computerlink/python/GETTING_STARTED/)

This directory contains Python helper programs only. The old per-device and
per-scenario batch wrappers were removed after the bring-up validation phase.

Use the repository-level entry points instead:

| Task | Command |
|---|---|
| Local CI gate | `run_ci.bat` |
| Release preflight | `release_check.bat` |

## Current Helpers

| Script | Purpose |
|---|---|
| `scripts/interactive_cli.py` | Manual read/write CLI for spot checks and protocol inspection. |
| `scripts/sim_server.py` | Local simulator for development tests without hardware. |
| `scripts/check_registry_duplicate.ps1` | Release helper used by `release_check.bat`. |

The remaining Python hardware helpers are kept as low-level investigation tools
for exceptional cases. They are not release gates, and new one-off batch files
should not be added for individual validation scenarios.



