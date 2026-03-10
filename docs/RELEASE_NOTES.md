# Release Notes

Related documents:

- [../README.md](../README.md)
- [TESTING.md](TESTING.md)
- [MODEL_RANGES.md](MODEL_RANGES.md)
- [COMPUTER_LINK_SPEC.md](COMPUTER_LINK_SPEC.md)
- [RELEASE.md](RELEASE.md)

## v1.0.0

Initial public release of `toyopuc-computerlink`.

### Included

- low-level client: `ToyopucClient`
- high-level client: `ToyopucHighLevelClient`
- address parsing and encoding helpers
- TCP support
- UDP support with optional fixed local source port
- clock read / write
- CPU status read
- `W/H/L` addressing for bit-device word/byte access
- examples
- simulator smoke test tools
- generated API docs via `pdoc`

### Verified

Real hardware verified on:

- `TOYOPUC-Plus CPU (TCC-6740) + Plus EX2 (TCU-6858)`

Verified communication paths:

- TCP
- UDP with fixed `local_port`

Verified feature groups:

- basic device read / write
- prefixed `P1/P2/P3`
- extension bit / word access
- mixed `CMD=98/99`
- block access
- boundary checks
- recovery write / read checks
- high-level API
- clock read / write
- CPU status read
- relay command read / write
- `W/H/L` addressing

### Included Documents

- [../README.md](../README.md)
- [TESTING.md](TESTING.md)
- [COMPUTER_LINK_SPEC.md](COMPUTER_LINK_SPEC.md)
- [MODEL_RANGES.md](MODEL_RANGES.md)
- [PENDING.md](PENDING.md)
- [RELEASE.md](RELEASE.md)
- [../examples/README.md](../examples/README.md)

### Known Limitations

- `FR` is not part of the normal safe test path
- `CMD=60` is verified for single-hop read / write / FR commit on `P1-L2:N2`; selected two-hop / three-hop read paths; three-hop basic word write `CMD=1D` with readback; three-hop contiguous 8-word relay write/readback on `D0000-D0007`; three-hop relay `FR000000` read / write / commit path (`P1-L2:N4 -> P1-L2:N6 -> P1-L2:N2`); a three-hop relay high-level API sweep (`TOTAL: 24/24`); a broader three-hop relay matrix (`D/R/U` passed for counts `16/32`, `S` did not retain written patterns); relay low-level sweeps on both UDP and TCP; and relay abnormal-case sweeps showing timeout/no-reply behavior for missing station, broken path, out-of-range `D3000`, and relay write to `S0000`. Standalone relay `CMD=A0 / 01 10` still returned NAK on the verified Plus relay paths.
- high-level `read_many()` / `write_many()` still use simple per-item dispatch
- model-specific unsupported areas exist

### Model Notes

For `TOYOPUC-Plus CPU (TCC-6740) + Plus EX2 (TCU-6858)`:

- `B` is unsupported
- `EB` is not present
- `U08000-U1FFFF` does not exist on this model
- prefixed upper ranges such as `P1/P2/P3-D1000+` are unsupported

### Packaging

Verified before release:

- `python -m py_compile ...`
- `python -m build`
- `python -m twine check dist/*`

