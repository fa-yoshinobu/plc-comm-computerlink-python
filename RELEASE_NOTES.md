# Release Notes

## v0.1.0

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

- `TOYOPUC-Plus CPU (TCC-6740)`

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
- `W/H/L` addressing

### Included Documents

- `README.md`
- `TESTING.md`
- `COMPUTER_LINK_SPEC.md`
- `MODEL_RANGES.md`
- `PENDING.md`
- `RELEASE.md`
- `examples/README.md`

### Known Limitations

- `FR` is not part of the normal safe test path
- `CMD=CA` is not hardware-verified
- `CMD=60` is not hardware-verified
- high-level `read_many()` / `write_many()` still use simple per-item dispatch
- model-specific unsupported areas exist

### Model Notes

For `TOYOPUC-Plus CPU (TCC-6740)`:

- `B` is unsupported
- `EB` is not present
- `U08000-U1FFFF` does not exist on this model
- prefixed upper ranges such as `P1/P2/P3-D1000+` are unsupported

### Packaging

Verified before release:

- `python -m py_compile ...`
- `python -m build`
- `python -m twine check dist/*`

