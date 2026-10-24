# Assembly Instructions

> Work with the 12 V supply **unplugged** unless a step says otherwise. Keep the lamp's wax capsule away from any open flame or soldering tip.

## Tools and parts
Soldering iron, multimeter, wire strippers, heat-shrink, Kapton tape, thermal paste, USB-C cable, PC with Python and `mpremote` (`pip install mpremote`). Parts are in the BOM in [PROJECT.md](PROJECT.md).

## Step 1: Bench-test the parts (Phase 1)
1. Set the buck converter output to **5.0 V** with no load, then check under a load (e.g. a 10 Ω resistor).
2. Flash MicroPython onto the ESP32-S3-Zero: hold BOOT, plug in USB, then run `esptool` with the S3 MicroPython image. Check with `mpremote` that the REPL answers.
3. Run `tools/bench/ds18b20_scan.py` with the sensor on a breadboard. It must find exactly one device and read about room temperature.
4. Wire the MOSFET with a 12 V, 7 Ω load (or the real heater). Run `tools/bench/pwm_ramp.py`. Confirm the load power rises smoothly and the MOSFET only gets slightly warm.
5. Record results in `docs/bench-checklist.md`.

## Step 2: Build the board
1. Lay out on perfboard: ESP32-S3-Zero, buck module, MOSFET, resistors, capacitor, diode, terminal blocks.
2. Power wiring uses 22 AWG, signals use 28 AWG.
3. Solder:
   - 12 V jack → 100 µF (observe polarity) → buck input and heater terminal.
   - Buck output (5 V) → ESP32 `5V` pin and ring `5V`.
   - MOSFET: source to GND, drain to heater return, gate via 220 Ω to **GPIO4**, 10 kΩ from gate to GND.
   - 1N4007 across the heater terminals, **stripe toward 12 V+**.
   - DS18B20 data to **GPIO5**, 4.7 kΩ from 3V3 to the data line, close to the MCU.
   - Ring DIN to **GPIO6**.
4. Join all grounds at a single point.
5. Check with the multimeter before power: no short between 12 V and GND, between 5 V and GND, or between 3V3 and GND.

## Step 3: First power-up (no heater, no ring)
1. Plug in USB only (disconnect the buck output from the MCU if you have no Schottky diode, see PROJECT.md 5.2).
2. Upload firmware: `./tools/deploy.ps1`.
3. Create `config.json` from `config.example.json` with your Wi-Fi and a long random token.
4. Plug in 12 V and check 5 V at the MCU and 3.3 V on the sensor.

## Step 4: Install into the lamp
1. Disconnect the lamp's original heater supply from its mains/adapter wiring.
2. Fit the heater to the new board (heater leads to the terminal block).
3. **Sensor:** spread thermal paste on the sensor, press it flat at the **centre of the capsule base**, and secure it with Kapton tape. Cover with foam or Kapton so lamp air does not skew the reading.
4. Seat the LED ring below the capsule, in the base cavity, facing up, away from the heater coil.
5. Secure the board with standoffs. Keep signal wires away from heater wires. Fit strain relief on the barrel jack.

## Step 5: Commissioning
1. With the lamp cold, power up. Open the dashboard (see [USER_GUIDE.md](USER_GUIDE.md)). The temperature should read room temperature.
2. Start manual mode at 45 °C. Watch the temperature rise and the duty settle. Warm-up usually takes 30-60 min.
3. Unplug the sensor once. The heater must switch off within 5 s and the ring must turn red. Replug and reset the fault.
4. Tune PID (see user guide) until it holds ±1 °C.
5. Measure the current at 12 V during warm-up and at full LED brightness. It should stay under 3 A.

## Troubleshooting
| Symptom | Likely cause |
|---|---|
| Sensor reads -127 | Missing pull-up, wiring, or the wrong pin |
| Sensor reads 85.0 | Power-on default, conversion not run or the sensor is not powered |
| Heater never turns on | Gate wiring, wrong MOSFET (not logic-level), the diode reversed |
| MOSFET hot | Not fully on (check gate voltage at 100 % duty, should be about 3.3 V) |
| Ring flickers or shows wrong colours | Level mismatch (see PROJECT.md 5.2) or ground not shared |
| MCU resets when the heater switches | Weak supply or the 100 µF capacitor missing or too far from the load |
| Cannot flash | Hold BOOT while plugging in USB |
