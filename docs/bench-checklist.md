# Bench Checklist (Phase 1)

Date: ____  Board: ESP32-C3 SuperMini  Supply: 12 V ___ A

| # | Check | Expected | Result |
|---|---|---|---|
| 1 | Buck output, no load | 5.0 V | |
| 2 | Buck output, 10 Ω load (0.5 A) | 5.0 V ±0.1 | |
| 3 | Buck output, LED ring full white | 5.0 V ±0.15, no MCU reset | |
| 4 | 3V3 rail | 3.3 V ±0.1 | |
| 5 | `ds18b20_scan.py`: devices found | exactly 1 | |
| 6 | Sensor reads | room temp ±1 °C, no 85/-127, 0 errors in 5 min | |
| 7 | Sensor warms under a finger | rises smoothly | |
| 8 | Gate at 100 % duty | about 3.3 V | |
| 9 | Heater off at boot/reset | no heating during reset | |
| 10 | `pwm_ramp.py` with the real heater | load voltage rises with duty, MOSFET only warm | |
| 11 | Total 12 V current at 100 % heater | about 1.95 A | |
| 12 | Ctrl-C during ramp | heater off immediately | |

Notes:
