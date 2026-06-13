# Samples

## What is in this directory

This directory contains runnable examples for the high-level TOYOPUC Computer Link API and one low-level numeric-address sample. Use the high-level samples first unless you are deliberately working with raw protocol addresses.

## How to run

```powershell
python samples/high_level_minimal.py --host 192.168.250.100 --port 1025
python samples/high_level_basic.py --host 192.168.250.100 --port 1025
python samples/high_level_all_sync.py --host 192.168.250.100 --port 1025
python samples/high_level_all_async.py --host 192.168.250.100 --port 1025 --poll-count 2
python samples/high_level_udp.py --host 192.168.250.100 --port 1035 --local-port 12000
python samples/fr_basic.py --host 192.168.250.100 --port 1025 --target FR000000 --value 0x1234
python samples/relay_basic.py --host 192.168.250.100 --port 1025 --hops "P1-L2:N2" --mode cpu-status
python samples/clock_and_status.py --host 192.168.250.100 --port 1025
python samples/low_level_basic.py --host 192.168.250.100 --port 1025
```

## Sample index

| File | What it demonstrates |
| --- | --- |
| `samples/high_level_minimal.py` | Smallest read, write, and readback workflow. |
| `samples/high_level_basic.py` | Daily high-level reads, writes, `read_many`, extension areas, and packed `W/H/L` notation. |
| `samples/high_level_all_sync.py` | Synchronous `ToyopucDeviceClient` cookbook. |
| `samples/high_level_all_async.py` | Async `ToyopucConnectionOptions`, `open_and_connect`, typed reads/writes, block reads, bit-in-word writes, named reads, and polling. |
| `samples/high_level_udp.py` | UDP transport with a fixed local port. |
| `samples/fr_basic.py` | FR read, staged write, and optional flash commit. |
| `samples/relay_basic.py` | Relay CPU status, clock, word, and FR operations. |
| `samples/clock_and_status.py` | PLC clock read and CPU status decode. |
| `samples/low_level_basic.py` | Low-level numeric-address reads and writes. |
