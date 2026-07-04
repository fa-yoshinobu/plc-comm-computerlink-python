# Troubleshooting

Use this page for first-pass checks when a TOYOPUC Computerlink request does not behave as expected. For address-shape details, see [GOTCHAS.md](GOTCHAS.md).

## Connection checks

| Symptom | Check |
| --- | --- |
| Connection timeout | Confirm the PLC host address and the configured Computerlink port. TCP examples use `1025`. |
| TCP connection refused | Confirm Computerlink is enabled on the target PLC. |
| UDP requests do not return | Confirm the PLC UDP port configured for your target. |
| Intermittent timeouts | Increase timeout/retry settings and avoid reconnecting for every small request. |

## Addressing checks

| Symptom | Check |
| --- | --- |
| Profile rejected before communication | Use one exact canonical profile from [PROFILES.md](PROFILES.md). |
| Unknown device area | Confirm the selected profile supports that family. |
| Address out of range | Compare [PROFILES.md](PROFILES.md) with [SUPPORTED_REGISTERS.md](SUPPORTED_REGISTERS.md). |
| Basic address rejected | Use `P1-`, `P2-`, or `P3-` for basic families such as `D`, `M`, `X`, `Y`, `T`, `C`, `L`, `N`, `R`, and `S`. |
| Dword read returns a bit | Use `:D` for dword access and `.D` only for bit 13 inside a word. |

## Write checks

| Symptom | Check |
| --- | --- |
| A write appears to change the wrong value | Stop and confirm you are using a test address you control. |
| FR value does not survive power cycle | Stage with `write_fr(..., commit=False)` and then call `commit_fr()`. |
| Relay write or read does not reach the target PLC | Set the relay hop string explicitly. |

