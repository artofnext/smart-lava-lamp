# Assembly Instructions

> Work with the 12 V supply **unplugged** unless a step says otherwise. Keep the lamp's wax capsule away from any open flame or soldering tip.

## Tools and parts
Soldering iron, multimeter, wire strippers, heat-shrink, Kapton tape, thermal paste, USB-C cable, PC with Python and `uv` (`uvx mpremote`).

## Step 1: Bench-test the parts
1. Set the buck converter output to **5.0 V** with no load, then check under a load (e.g. a 10 Ω resistor).
2. Flash MicroPython onto the ESP32-C3 SuperMini: hold BOOT, plug in USB, then run `esptool` with the C3 MicroPython image. Check with `uvx mpremote` that the REPL answers.
3. Run `tools/bench/ds18b20_scan.py` with the sensor on a breadboard. It must find one device and read room temperature.
4. Wire the IRLZ44N MOSFET with a 12 V load (or the real heater). Run `tools/bench/pwm_ramp.py`. Confirm the load power rises smoothly and the MOSFET stays cool.
5. Record results in [bench-checklist.md](bench-checklist.md).

## Step 2: Build the board
1. Lay out on perfboard: ESP32-C3 SuperMini, buck module, IRLZ44N MOSFET, resistors, capacitor, flyback diode, terminal blocks.
2. Power wiring uses 22 AWG, signals use 28 AWG.
3. Solder:
   - 12 V jack → 100 µF (observe polarity) → buck input and heater `+` terminal.
   - Buck output (5 V) → ESP32 `5V` pin and WS2812B ring `5V`.
   - MOSFET (IRLZ44N): Source to GND, Drain to heater `-` return, Gate via 220 Ω to **GPIO4**, 10 kΩ from Gate to GND.
   - 1N4007 flyback diode across the heater terminals, **stripe (cathode) toward 12 V+**.
   - DS18B20 data to **GPIO5**, 4.7 kΩ pull-up from 3V3 to the data line.
   - WS2812B 16-LED ring DIN to **GPIO6**.
4. Join all grounds at a single common point.
5. Check with the multimeter before power: no short between 12 V and GND, between 5 V and GND, or between 3V3 and GND.

## Step 3: First power-up & firmware upload
1. Copy `firmware/config.example.json` to `firmware/config.json` and fill in your Wi-Fi credentials and access token.
2. Connect USB-C and deploy firmware + config:
   ```powershell
   .\tools\deploy.ps1 -Port COM9 -Config
   ```
3. Plug in 12 V and check 5 V at the MCU and 3.3 V on the sensor.

## Step 4: Install into the lamp
1. Fit the heater leads to the terminal block.
2. Position the DS18B20 sensor close to the bottom of the wax capsule and secure with Kapton tape.
3. Seat the 16-LED WS2812B ring in the base cavity facing up toward the bottle.
4. Secure the board and fit strain relief on the 12 V power cable.

## Step 5: Commissioning
1. Power up the lamp. It automatically starts warming at **100% heater power** with the LED ring in **Temperature Reactive** mode.
2. Open the web dashboard at the lamp's IP address and verify live temperature telemetry and the 1-hour sliding chart.
3. Once the sensor reaches **65 °C**, confirm the heater automatically drops to **75% power** and the LED ring switches to your last saved LED mode.

## Troubleshooting
| Symptom | Likely cause |
|---|---|
| Sensor reads `--.-°` / `-127` | Missing 4.7 kΩ pull-up, loose wire, or wrong pin |
| Heater never turns on | Gate wiring, non-logic-level MOSFET, or fault latched |
| Brownout / MCU resets when heater turns on | Flyback diode (1N4007) installed backwards (stripe must go to 12 V+) |
| MOSFET gets hot | Gate voltage below 3.3 V or wrong MOSFET part |
| Ring flickers or shows wrong colours | Shared ground missing between buck 5 V and ESP32 |
| `mpremote: failed to access COMx` | Another terminal has an open `mpremote` REPL session (`Ctrl + ]` to exit) |
