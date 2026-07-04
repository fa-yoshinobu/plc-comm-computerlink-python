# Samples

## What is here

This directory contains runnable high-level Python examples for TOYOPUC Computerlink.

Use only test addresses that are safe for your PLC program before you run any write example.

| Sample | What it shows |
| --- | --- |
| `high_level_minimal.py` | One connection, one word read, one word write, and readback. |
| `high_level_basic.py` | Common high-level reads, writes, `read_many`, and packed `W/H/L` access. |
| `high_level_all_sync.py` | Synchronous cookbook for `ToyopucDeviceClient`. |
| `high_level_all_async.py` | Async cookbook for `ToyopucConnectionOptions`, `open_and_connect`, typed helpers, named reads, and polling. |
| `polling_reconnect.py` | Read-only polling loop with automatic reconnect and backoff after transport loss. |
| `multi_plc_monitor.py` | Read-only multi-PLC polling with reconnect state transitions and long-form CSV output. |
| `config_polling.py` | Read-only polling from JSON or YAML configuration, with `--dry-run` validation before connection. |
| `high_level_udp.py` | UDP connection with a fixed local port. |
| `fr_basic.py` | FR read/write and optional flash commit. |
| `relay_basic.py` | Relay CPU status, clock, word, and FR operations. |
| `clock_and_status.py` | PLC clock and CPU status decode. |
| [`../scripts/README.md`](../scripts/README.md) | Script index for simulation and support utilities. |

## How to run

Run commands from the repository root. Use an exact canonical profile string from [profiles](../docsrc/user/PROFILES.md).

| Transport | Host | Port |
| --- | --- | --- |
| TCP | `192.168.250.100` | `1025` |
| UDP | `192.168.250.100` | `1035` |

```powershell
python samples/high_level_minimal.py --host 192.168.250.100 --port 1025 --profile toyopuc:plus:extended
python samples/high_level_basic.py --host 192.168.250.100 --port 1025 --profile toyopuc:plus:extended
python samples/high_level_all_sync.py --host 192.168.250.100 --port 1025 --profile toyopuc:plus:extended
python samples/high_level_all_async.py --host 192.168.250.100 --port 1025 --poll-count 2 --profile toyopuc:plus:extended
python samples/polling_reconnect.py --host 192.168.250.100 --port 1025 --profile toyopuc:plus:extended
python samples/multi_plc_monitor.py --plc line-a=192.168.250.100,toyopuc:plus:extended,1025,tcp --tag d0100=P1-D0100:U --cycles 1 --dry-run
python samples/config_polling.py --config samples/config_polling.example.json --dry-run
python samples/high_level_udp.py --host 192.168.250.100 --port 1035 --local-port 12000 --profile toyopuc:plus:extended
python samples/fr_basic.py --host 192.168.250.100 --port 1035 --protocol udp --local-port 12000 --profile toyopuc:pc10g:pc10 --target FR000000 --value 0x1234
python samples/relay_basic.py --host 192.168.250.100 --port 1035 --protocol udp --local-port 12000 --profile toyopuc:nano-10gx:compatible --hops "P1-L2:N2" --mode cpu-status
python samples/clock_and_status.py --host 192.168.250.100 --port 1025 --profile toyopuc:plus:extended
```

## Index

| Task | Command |
| --- | --- |
| First TCP read/write | `python samples/high_level_minimal.py --host 192.168.250.100 --port 1025 --profile toyopuc:plus:extended` |
| Daily high-level operations | `python samples/high_level_basic.py --host 192.168.250.100 --port 1025 --profile toyopuc:plus:extended` |
| Full synchronous walkthrough | `python samples/high_level_all_sync.py --host 192.168.250.100 --port 1025 --profile toyopuc:plus:extended` |
| Full async walkthrough | `python samples/high_level_all_async.py --host 192.168.250.100 --port 1025 --poll-count 2 --profile toyopuc:plus:extended` |
| Read-only polling with reconnect | `python samples/polling_reconnect.py --host 192.168.250.100 --port 1025 --profile toyopuc:plus:extended` |
| Multi-PLC read-only monitor | `python samples/multi_plc_monitor.py --plc line-a=192.168.250.100,toyopuc:plus:extended,1025,tcp --tag d0100=P1-D0100:U --cycles 1 --dry-run` |
| Config-driven read-only polling | `python samples/config_polling.py --config samples/config_polling.example.json --dry-run` |
| UDP with a fixed local port | `python samples/high_level_udp.py --host 192.168.250.100 --port 1035 --local-port 12000 --profile toyopuc:plus:extended` |
| FR read/write without commit | `python samples/fr_basic.py --host 192.168.250.100 --port 1035 --protocol udp --local-port 12000 --profile toyopuc:pc10g:pc10 --target FR000000 --value 0x1234` |
| FR read/write with commit | `python samples/fr_basic.py --host 192.168.250.100 --port 1035 --protocol udp --local-port 12000 --profile toyopuc:pc10g:pc10 --target FR000000 --value 0x1234 --commit` |
| Relay CPU status | `python samples/relay_basic.py --host 192.168.250.100 --port 1035 --protocol udp --local-port 12000 --profile toyopuc:nano-10gx:compatible --hops "P1-L2:N2" --mode cpu-status` |
| Relay word read | `python samples/relay_basic.py --host 192.168.250.100 --port 1035 --protocol udp --local-port 12000 --profile toyopuc:nano-10gx:compatible --hops "P1-L2:N2,P1-L2:N4" --mode word-read --device P1-D0000 --count 4` |
| Clock and CPU status | `python samples/clock_and_status.py --host 192.168.250.100 --port 1025 --profile toyopuc:plus:extended` |

## Address notes

| Rule | Example |
| --- | --- |
| Basic families require a program prefix. | `P1-D0000`, `P1-M0000` |
| Data type suffixes use `:`. | `P1-D0100:D`, `P1-D0100:F` |
| Bit-in-word uses `.`. | `P1-D0100.3` |
| Packed bit-family views use `W`, `L`, or `H`. | `P1-M0010W`, `P1-M0010L` |
| FR writes are two-phase. | `write_fr(..., commit=False)` then `commit_fr()` when needed. |
