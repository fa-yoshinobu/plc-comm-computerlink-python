# Latest Communication Verification

This page keeps the current public summary only. Older detailed notes are not kept in the public documentation set.

## Current Retained Summary

- verified model groups: `TOYOPUC-Plus CPU`, `Nano 10GX`, `PC10G-CPU`
- verified public surface: plain reads/writes, typed reads/writes, mixed snapshots, FR helpers, relay helpers
- recommended first public test: `P1-D0000` and `P1-M0000`
- latest PC10G direct check: `2026-04-30`, `PC10G:PC10 mode`, TCP `192.168.250.100:1025`

## Practical Public Conclusions

- `TOYOPUC-Plus` is the cleanest first-run path for prefixed word and bit access
- `Nano 10GX` remains a supported public path, but relay and profile-specific differences matter
- `PC10G` remains supported, but exact range limits differ from `TOYOPUC-Plus` and `Nano 10GX`
- PC10G direct Python API smoke on `2026-04-30` confirmed:
  - split-range formatting: `P1-P0000..P1-P01FF, P1-P1000..P1-P17FF`
  - direct reads for `P1-D0000`, `P1-P01F0`, `P1-P1000`, `P1-S03F0`, `P1-S1000`, and `EB00000`
  - scan control sequence: `stop_scan()`, `release_scan_stop()`, `resume_scan()`

## Current Cautions

- exact writable ranges depend on profile and hardware
- the tested `PC10G` notes include model-specific unsupported areas such as missing `B` support on the tested unit
- `FR` exposure is profile-dependent and should not be the first smoke test

## Where Older Evidence Went

Public historical validation clutter was removed. Maintainer-only retained evidence now belongs under `internal_docs/`.
