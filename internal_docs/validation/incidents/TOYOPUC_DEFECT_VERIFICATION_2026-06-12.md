# Toyopuc Defect Verification - 2026-06-12

This note preserves the useful information from the workspace-level
Toyopuc/ComputerLink defect investigation. The root workspace report can be
deleted after this information is committed.

## Conclusion

No release-blocking Toyopuc / ComputerLink defect remains for the Python
library as of 2026-06-12.

The following defect candidates were fixed and verified:

- Program packed-word sparse `ReadMany` all-zero behavior.
- Program packed-word sparse write address encoding.
- `CMD=A0` CPU status request frame layout.
- `FR` `CMD=C2/C3` max byte count and helper split behavior.
- Fail-fast guards for protocol max counts instead of silent semantic
  auto-splitting.
- `EB` extended-No guard for the `CMD=94..99` route.

Remaining Python TODO work is coverage expansion only:

- newer Toyopuc model ranges
- extended-device edge cases

Those are not known release-blocking defects.

## Program Packed-Word Sparse `ReadMany`

Root cause:

- For `CMD=98/99`, word-point addresses in program/extended multi access use
  monitor byte addresses.
- The old implementation sent the word address used by `CMD=94/95`.
- Example: `P1-V000W` should use byte address `0x00A0`; the old frame used
  `0x0050`.
- The PLC interpreted the old sparse request as a different area and returned
  genuine zeros.

Verified fix:

- Python and .NET were both fixed for direct and relay read/write paths.
- Cross-verify frame parity confirmed the corrected sparse frame.
- Live verification showed sparse packed-word reads no longer collapse to
  all-zero.

Representative corrected frame:

```text
request : 00 00 0A 00 98 00 00 02 01 A0 00 01 A4 00
response: 80 00 05 00 98 50 00 40 00
```

Representative live result:

- contiguous `P1-V000W..P1-V003W`: `0x0050, 0x0000, 0x0040, 0x0100`
- sparse `P1-V000W,P1-V002W`: `0x0050, 0x0040`

## Manual Audit Fixes

The following Python/.NET mismatches were checked against the Toyopuc
Computer Link manual and fixed.

### `CMD=A0` CPU Status

- Correct request payload is `A0 00 11 00`.
- Old request `A0 01 10` returned `rc=0x10 / error_code=0x24`.
- Correct request returned a normal CPU status response on live hardware.

### `FR` `CMD=C2/C3` Limit

- Manual limit: `n <= 0x03F0` bytes.
- Helper limit is now `0x01F8` words.
- `0x01F9` words are split by the explicit FR helper route.
- Low-level `CMD=C2/C3` calls reject `0x03F1` bytes before sending.

### Max Count Policy

Silent semantic auto-splitting is intentionally avoided. A request that exceeds
one protocol-defined telegram limit fails before sending unless the API is an
explicit helper whose name and contract already imply chunking.

Reason:

- reads can be split across time and lose snapshot consistency
- writes can partially succeed or fail across multiple telegrams
- hiding that semantic change behind a normal read/write call is a defect risk

### `EB` Extended-No Guard

For `CMD=94..99`, `EB` extended-No access is limited to the manual-defined
`EB00000..EB1FFFF` range. Wider `EB` access is only allowed through the PC10
route when the selected profile supports it.

## FR Visible Nano 10GX Verification

Target:

- `192.168.250.100:1025/tcp`
- Nano 10GX with `FR` visible

Verified in Python and .NET:

- `FR000000` read
- exact max `CMD=C2` read at `0x03F0` bytes
- `CMD=C2` over-limit guard at `0x03F1` bytes
- `read_fr_words(..., 0x01F8)` exact max
- `read_fr_words(..., 0x01F9)` helper split
- `write_fr(..., commit=False)` write/readback/restore
- exact max `CMD=C3` write/readback/restore
- split `CMD=C3` write/readback/restore
- `CMD=CA` commit/wait/readback
- restore original values and commit
- power cycle / CPU reset persistence check

Final persistence result:

- marker `FR000200..FR000203 = 0xCA10..0xCA13` survived reset after commit
- original values `0x57AB,0x57AC,0x57AD,0x57AE` were restored and committed

## Relay `P1-L1:N2` Verification

Target:

- host: `192.168.250.100`
- TCP port: `1025`
- UDP port: `1027`
- relay target: Nano 10GX
- hops: `P1-L1:N2`

Python:

- relay CPU status: OK
- relay `P1-D0000` read: OK
- relay `P1-D0000` write/readback: OK

.NET:

- relay CPU status: OK
- relay `P1-D0000` read: OK
- relay `P1-D0000` count probe `1/8/16/32/64/128/256`: OK

Stress:

- single TCP client sequential read-only: 100 iterations OK
- single UDP client sequential read-only with PC local port `12000`: 500
  iterations OK
- TCP + UDP simultaneous read-only: 500 iterations each OK
- 30-minute relay write/readback soak: 1029 alternating writes to `P1-D0000`
  (`0x1111` / `0x2222`), 0 failures, final restore to `0x270F` OK

Observed limitation:

- two simultaneous TCP clients against the same relay hop reproduced a socket
  error on one client at the first request
- an immediate single-client post-check succeeded
- classify this as same-hop simultaneous-use contention, not a relay frame
  generation bug

Manual note:

- relay `0x73` means duplicate relay commands against the same link module
  and is a retryable target condition
- if relay communication fails, confirm target power/RUN state, path idleness,
  host/port/protocol, and competing clients before logging it as a defect

## Remaining Work Classification

Release blockers:

- none known

Future coverage only:

- newer Toyopuc model ranges
- extended-device edge cases
- deferred profile read-only sweeps
