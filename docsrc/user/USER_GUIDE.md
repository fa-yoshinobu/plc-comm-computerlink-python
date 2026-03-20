# User Guide: TOYOPUC Computer Link Python

High-performance Python client for JTEKT TOYOPUC PLCs using the Computer Link protocol.

## 1. Installation
```bash
pip install .
```

## 2. Basic Usage
```python
from toyopuc import ToyopucClient

with ToyopucClient("192.168.1.5", 1025) as plc:
    # Read Program 1, Data Register 0
    val = plc.read_word(1, "D0000")
    print(f"Value: {val}")
```

## 3. Supported Devices
- **Data Registers**: D
- **Internal Relays**: M
- **Inputs/Outputs**: X, Y
- **Special Registers**: S
- **Timers/Counters**: T, C
