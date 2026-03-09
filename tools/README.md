# Tools

Use this file as a short index for the `tools/` directory.

## Main scripts

- `tools/run_tcc6740_all.bat`
  Recommended broad validation batch for `TOYOPUC-Plus CPU (TCC-6740)`.
- `tools/run_device_range_scan.bat`
  Two-pass coarse/fine writable-range scan batch for all documented device families except `FR`.
- `tools/run_fr_range_scan.bat`
  `FR`-only coarse/fine writable-range scan batch.
- `tools/run_fr_read_scan.bat`
  `FR`-only read-only full/range scan batch using `CMD=C2`.
- `tools/run_fr_write_scan.bat`
  `FR`-only write/verify scan batch using `CMD=C3`, with a final commit phase.
- `tools/run_fr_probe.bat`
  `FR` candidate access probe batch using `CMD=CA` and several read-path guesses.
- `tools/run_relay_test.bat`
  `CMD=60` relay-command hardware test batch with outer/inner frame dump.
- `tools/run_fr_commit_test.bat`
  Simple `FR` read / write+commit batch for direct hardware confirmation.
- `tools/run_program_no_probe.bat`
  `CMD=98/99` program-number probe that compares current mapping against candidate `no` values.
- `tools/run_c4c5_range_probe.bat`
  Probe for current-vs-alternate `CMD=C4/C5` usage on selected `L/M/U/EB` ranges.
- `tools/auto_rw_test.py`
  Automated read/write test against a real PLC.
- `tools/high_level_api_test.py`
  Verification tool for `ToyopucHighLevelClient` and `resolve_device()`.
- `tools/whl_addressing_test.py`
  Verification tool for `W/H/L` addressing on bit-device families.
- `tools/clock_test.py`
  Dedicated command-line helper for PLC clock read/set tests.
- `tools/cpu_status_test.py`
  Dedicated command-line helper for CPU status read/decode tests.
- `tools/interactive_cli.py`
  Manual read/write CLI for spot checks and protocol inspection.
- `tools/manual_device_write_check.py`
  Stepwise helper for human verification: writes one fixed test value, waits for manual confirmation, then advances.
- `tools/recovery_write_loop.py`
  Repeated write/read loop for unplug/replug recovery checks with interval logging.
- `tools/find_last_writable.py`
  Downward write probe to find the last writable address near a range end.
- `tools/exhaustive_writable_scan.py`
  Exhaustive full-range write scan that reports the true last writable address and any holes.
- `tools/run_auto_tests.bat`
  Runs the standard automated test sequence and writes logs plus `summary.txt`.
- `tools/run_quick_test.bat`
  Runs the basic-area test only.
- `tools/run_full_test.bat`
  Runs the PC10G full test set.
- `tools/run_block_test.bat`
  Runs the block-length test.
- `tools/run_validation_all.bat`
  Runs full + mixed + block + boundary + recovery write/read + last-writable probe in one batch.
- `tools/run_sim_tests.bat`
  Runs a small simulator-oriented smoke test set against `tools.sim_server`.
- `tools/build_api_docs.bat`
  Generates API HTML documentation with `pdoc` into `docs/api`.
- `tools/sim_server.py`
  Local simulator for protocol testing without hardware.

## Documents

- Project overview: `README.md`
- Test usage and verified results: `TESTING.md`
- Model-specific writable ranges: `MODEL_RANGES.md`
- Communication protocol and address tables: `COMPUTER_LINK_SPEC.md`
- Remaining open items: `PENDING.md`

## Batch usage summary

Use this section as a quick picker:

- `run_tcc6740_all.bat`: recommended broad validation sweep for `TCC-6740`
- `run_auto_tests.bat`: standard end-to-end sweep
- `run_quick_test.bat`: fast basic communication check
- `run_full_test.bat`: broad device coverage check
- `run_block_test.bat`: contiguous transfer length check
- `run_validation_all.bat`: broad validation sweep including recovery and tail-end probes
- `run_device_range_scan.bat`: forward coarse-to-fine range scan for all documented device families except `FR`; unsupported families are skipped automatically
- `run_fr_range_scan.bat`: `FR`-only forward coarse-to-fine range scan
- `run_fr_read_scan.bat`: `FR`-only read-only range scan with chunked `CMD=C2` reads
- `run_fr_write_scan.bat`: `FR`-only write/readback range scan with chunked `CMD=C3/C2` and end-of-range commit phase
- `run_fr_probe.bat`: direct `FR` probe using current mapping plus `CMD=CA` candidate paths
- `run_relay_test.bat`: `CMD=60` relay-command test with `cpu-status`, `clock-read`, `word-read`, or raw inner frames
- `run_fr_commit_test.bat`: direct `FR` read or write+commit check with `A0` status output
- `run_program_no_probe.bat`: targeted `CMD=98/99` mapping probe for `EX/GX/P1/P2/P3`
- `run_c4c5_range_probe.bat`: targeted `CMD=C4/C5` range probe for `L/M/U/EB`
- `run_sim_tests.bat`: simulator smoke test for high-level API, `W/H/L` addressing, clock, and CPU status
