# Model-Specific Writable Ranges

This document records writable device ranges confirmed per hardware model.

The intent is practical:
- where writes are accepted
- where writes are rejected
- whether there are holes inside the accepted span

Evidence types used in this file:

- `exhaustive scan`
  Confirmed by `tools/exhaustive_writable_scan.py`.
- `runtime tests`
  Confirmed by the normal runtime test set in `TESTING.md`.

These ranges are based primarily on `tools/exhaustive_writable_scan.py`.

## TOYOPUC-Plus CPU (TCC-6740)

Source command:

```bash
python -m tools.exhaustive_writable_scan --host <HOST> --port <PORT> --protocol tcp --targets all --log exhaustive.log
```

Evidence:

- exhaustive scan
- runtime tests also agree with the supported/unsupported split for the tested paths

### Basic Bit

| Device | Writable range |
| --- | --- |
| `P` | `P0000-P17FF` |
| `K` | `K0000-K02FF` |
| `V` | `V0000-V17FF` |
| `T` | `T0000-T17FF` |
| `C` | `C0000-C17FF` |
| `L` | `L0000-L2FFF` |
| `X` | `X0000-X07FF` |
| `Y` | `Y0000-Y07FF` |
| `M` | `M0000-M17FF` |

Evidence:

| Scope | Source |
| --- | --- |
| final range | exhaustive scan |
| supported behavior | runtime tests |

### Basic Word

| Device | Writable range |
| --- | --- |
| `S` | `S0000-S13FF` |
| `N` | `N0000-N17FF` |
| `R` | `R0000-R07FF` |
| `D` | `D0000-D0FFF` |
| `B` | unsupported |

Evidence:

| Scope | Source |
| --- | --- |
| final range | exhaustive scan |
| supported behavior | runtime tests |

### Prefixed Bit (`P1/P2/P3`)

| Device | Writable range |
| --- | --- |
| `P` | `P000-P1FF` |
| `K` | `K000-K2FF` |
| `V` | `V000-V0FF` |
| `T` | `T000-T1FF` |
| `C` | `C000-C1FF` |
| `L` | `L000-L7FF` |
| `X` | `X000-X7FF` |
| `Y` | `Y000-Y7FF` |
| `M` | `M000-M7FF` |

Evidence:

| Scope | Source |
| --- | --- |
| final range | exhaustive scan |
| supported behavior | runtime tests |

Not writable on this model:
- `P1000-P17FF`
- `V1000-V17FF`
- `T1000-T17FF`
- `C1000-C17FF`
- `L1000-L2FFF`
- `M1000-M17FF`

### Prefixed Word (`P1/P2/P3`)

| Device | Writable range |
| --- | --- |
| `S` | `S0000-S03FF` |
| `N` | `N0000-N01FF` |
| `R` | `R0000-R07FF` |
| `D` | `D0000-D0FFF` |
| `B` | unsupported |

Evidence:

| Scope | Source |
| --- | --- |
| final range | exhaustive scan |
| supported behavior | runtime tests |

Not writable on this model:
- `S1000-S13FF`
- `N1000-N17FF`
- `D1000-D2FFF`

### Extension Bit

| Device | Writable range |
| --- | --- |
| `EP` | `EP0000-EP0FFF` |
| `EK` | `EK0000-EK0FFF` |
| `EV` | `EV0000-EV0FFF` |
| `ET` | `ET0000-ET07FF` |
| `EC` | `EC0000-EC07FF` |
| `EL` | `EL0000-EL1FFF` |
| `EX` | `EX0000-EX07FF` |
| `EY` | `EY0000-EY07FF` |
| `EM` | `EM0000-EM1FFF` |
| `GX` | `GX0000-GXFFFF` |
| `GY` | `GY0000-GYFFFF` |
| `GM` | `GM0000-GMFFFF` |

Evidence:

| Scope | Source |
| --- | --- |
| final range | exhaustive scan |
| supported behavior | runtime tests |

### Extension Word

| Device | Writable range |
| --- | --- |
| `ES` | `ES0000-ES07FF` |
| `EN` | `EN0000-EN07FF` |
| `H` | `H0000-H07FF` |
| `U` | `U00000-U07FFF` |
| `EB` | not present on this model |

Evidence:

| Scope | Source |
| --- | --- |
| final range | exhaustive scan |
| supported behavior | runtime tests |

Does not exist on this model:
- `U08000-U1FFFF`

### Notes

- No holes were observed inside the writable spans above.
- Unsupported spans were contiguous in the observed scan.
- This is a write-acceptance result. It does not imply readback validation.
- For this model, the exhaustive scan is the primary source for final upper bounds such as `D0000-D0FFF` and `U00000-U07FFF`.

## Nano 10GX (TUC-1157)

Source commands:

```bash
tools\run_quick_test.bat 192.168.250.101 1025 tcp 4 5 0
tools\run_full_test.bat 192.168.250.101 1025 tcp 4 5 0
python -m tools.whl_addressing_test --host 192.168.250.101 --port 1025 --protocol tcp --timeout 5 --retries 0 --log whl_nano10gx_tcp.log
python -m tools.high_level_api_test --host 192.168.250.101 --port 1025 --protocol tcp --timeout 5 --retries 0 --log high_level_nano10gx_tcp.log
python -m tools.clock_test --host 192.168.250.101 --port 1025 --protocol tcp --timeout 5 --retries 0
python -m tools.cpu_status_test --host 192.168.250.101 --port 1025 --protocol tcp --timeout 5 --retries 0
tools\run_full_test.bat 192.168.250.101 1027 udp 4 5 2 12000
python -m tools.whl_addressing_test --host 192.168.250.101 --port 1027 --protocol udp --local-port 12000 --timeout 5 --retries 2 --skip-errors --log whl_nano10gx.log
python -m tools.high_level_api_test --host 192.168.250.101 --port 1027 --protocol udp --local-port 12000 --timeout 5 --retries 2 --skip-errors --log high_level_nano10gx.log
python -m tools.clock_test --host 192.168.250.101 --port 1027 --protocol udp --local-port 12000 --timeout 5 --retries 2
python -m tools.clock_test --host 192.168.250.101 --port 1027 --protocol udp --local-port 12000 --timeout 5 --retries 2 --set "2026-03-09 20:00:10"
python -m tools.cpu_status_test --host 192.168.250.101 --port 1027 --protocol udp --local-port 12000 --timeout 5 --retries 2
tools\run_device_range_scan.bat 192.168.250.101 1027 udp 12000 16 32
```

Evidence:

- runtime tests
- coarse device-range scan
- TCP and UDP runtime results agree on the tested families

### Basic Bit

| Device | Writable range |
| --- | --- |
| `P` | `P0000-P17FF` |
| `K` | `K0000-K02FF` |
| `V` | `V0000-V17FF` |
| `T` | `T0000-T17FF` |
| `C` | `C0000-C17FF` |
| `L` | `L0000-L2FFF` |
| `X` | `X0000-X07FF` |
| `Y` | `Y0000-Y07FF` |
| `M` | `M0000-M17FF` |

Evidence:

| Scope | Source |
| --- | --- |
| supported behavior | runtime tests |
| coarse upper-bound observation | device-range scan |

### Basic Word

| Device | Writable range |
| --- | --- |
| `S` | `S0000-S13FF` |
| `N` | `N0000-N17FF` |
| `R` | `R0000-R07FF` |
| `D` | `D0000-D2FFF` |
| `B` | `B0000-B1FFF` |

Evidence:

| Scope | Source |
| --- | --- |
| supported behavior | runtime tests |
| coarse upper-bound observation | device-range scan |

### Prefixed Bit (`P1/P2/P3`)

| Device | Writable range |
| --- | --- |
| `P` | `P000-P17FF` |
| `K` | `K000-K2FF` |
| `V` | `V000-V17FF` |
| `T` | `T000-T17FF` |
| `C` | `C000-C17FF` |
| `L` | `L000-L2FFF` |
| `X` | `X000-X7FF` |
| `Y` | `Y000-Y7FF` |
| `M` | `M000-M17FF` |

Evidence:

| Scope | Source |
| --- | --- |
| supported behavior | runtime tests |
| coarse upper-bound observation | device-range scan |

### Prefixed Word (`P1/P2/P3`)

| Device | Writable range |
| --- | --- |
| `S` | `S0000-S13FF` |
| `N` | `N0000-N17FF` |
| `R` | `R0000-R07FF` |
| `D` | `D0000-D2FFF` |

Evidence:

| Scope | Source |
| --- | --- |
| supported behavior | runtime tests |
| coarse upper-bound observation | device-range scan |

Note:

- prefixed `B` is not part of the current documented default range set for this project and is not treated as a confirmed family yet

### Extension Bit

| Device | Writable range |
| --- | --- |
| `EP` | `EP0000-EP0FFF` |
| `EK` | `EK0000-EK0FFF` |
| `EV` | `EV0000-EV0FFF` |
| `ET` | `ET0000-ET07FF` |
| `EC` | `EC0000-EC07FF` |
| `EL` | `EL0000-EL1FFF` |
| `EX` | `EX0000-EX07FF` |
| `EY` | `EY0000-EY07FF` |
| `EM` | `EM0000-EM1FFF` |
| `GX` | `GX0000-GXFFFF` |
| `GY` | `GY0000-GYFFFF` |
| `GM` | `GM0000-GMFFFF` |

Evidence:

| Scope | Source |
| --- | --- |
| supported behavior | runtime tests |
| coarse upper-bound observation | device-range scan |

### Extension Word

| Device | Writable range |
| --- | --- |
| `ES` | `ES0000-ES07FF` |
| `EN` | `EN0000-EN07FF` |
| `H` | `H0000-H07FF` |
| `U` | `U00000-U1FFFF` |
| `EB` | runtime-tested across lower and upper ranges; coarse scan observed at least `EB00000-EB41FF0` |

Evidence:

| Scope | Source |
| --- | --- |
| supported behavior | runtime tests |
| coarse upper-bound observation | device-range scan |

### Notes

- TCP `1025` and UDP `1027` were both verified on this model.
- `tools\run_full_test.bat` completed with `TOTAL: 818/818` on this model over TCP and UDP.
- `W/H/L` addressing completed with `TOTAL: 35/35` on this model over TCP and UDP.
- High-level API completed with `TOTAL: 21/21` on this model over TCP and UDP.
- Clock read was confirmed over TCP and clock read/write were confirmed over UDP on this model.
- CPU status was confirmed over both TCP and UDP on this model.
- Coarse device-range scan showed continuous acceptance for the documented runtime-tested families with no holes.
- `EB` was observed continuously at least through `EB41FF0` before repeated upper-range errors stopped the helper.
- `FR` is still separate and was excluded from the default follow-up range scan after the scan helper was corrected.
