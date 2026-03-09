# Examples

These examples show practical usage of `toyopuc`.

Run them from the repository root or after installing the package.

## Start Here

If you want the shortest path:

- minimal basic read/write: `examples/high_level_minimal.py`
- broader high-level example: `examples/high_level_basic.py`
- UDP example: `examples/high_level_udp.py`
- clock/status: `examples/clock_and_status.py`
- GUI monitor: `examples/device_monitor_gui.py`

`examples/low_level_basic.py` is an advanced example.
It is for users who want to work directly with:

- `ToyopucClient`
- explicit numeric addresses
- parser/encoder aware low-level usage

Quick copy/paste commands:

```powershell
python examples/high_level_minimal.py --host 192.168.250.101 --port 1025
python examples/high_level_basic.py --host 192.168.250.101 --port 1025
python examples/high_level_udp.py --host 192.168.250.101 --port 1027 --local-port 12000
python examples/clock_and_status.py --host 192.168.250.101 --port 1025
python examples/device_monitor_gui.py --host 192.168.250.101 --port 1025
```

## Files

- `examples/low_level_basic.py`
  Advanced low-level read/write example using `ToyopucClient`
- `examples/high_level_minimal.py`
  Shortest high-level example for a single word read/write
- `examples/high_level_basic.py`
  Broader high-level example, including `W/H/L` addressing on bit-device families
- `examples/high_level_udp.py`
  High-level read/write over UDP with a fixed local port
- `examples/clock_and_status.py`
  CPU clock read and full CPU status decode
- `examples/device_monitor_gui.py`
  Tkinter GUI monitor for watch/read/write/clock/status with changed-cell highlight

GUI example:

```powershell
python examples/device_monitor_gui.py --host 192.168.250.101 --port 1025
```

UDP example:

```powershell
python examples/device_monitor_gui.py --host 192.168.250.101 --port 1027 --protocol udp --local-port 12000
```
