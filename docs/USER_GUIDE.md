# User Guide

## First-time setup
1. Plug in the 12 V supply. The ring shows a **cyan chase** while it looks for Wi-Fi.
2. If no Wi-Fi is configured, the lamp starts its own access point `LavaLamp-XXXX`. Join it and open `http://192.168.4.1` to enter the SSID, the password and a **token** (this is your dashboard password). The lamp reboots and joins your network.
3. Open `http://lavalamp.local` (or the IP shown on your router) and enter the token. The browser remembers it.

## Daily use
- **Power**: starts or stops heating. A cold lamp needs about 30-60 min to flow.
- **Setpoint**: 45-55 °C. Around 48-50 °C gives large slow blobs, higher gives smaller lively ones.
- **Ring colours**: see the table below.

| Ring | Meaning |
|---|---|
| Orange-blue sweep | Warming. Fill level shows progress |
| Breathing colour | Holding temperature. Faster breath means the heater is working harder |
| Slow fade | Cooling |
| Red pulse | Fault, heater is off |
| Cyan chase | No Wi-Fi |

## Schedule
Add windows with days, start and end time, and a pattern. The lamp starts heating early so that the wax is ready at the start time. The lead time is learned automatically from past warm-ups. Times are London/Lisbon local time, with summer time handled.

## Patterns
A pattern is a list of steps: minutes from the start and a temperature. The lamp moves smoothly between steps. Presets: **calm** (constant 50 °C), **lively** (swings 48-54 °C), **cycle** (slow 20 min up/down swing). Temperatures are always kept within 45-55 °C.

## Faults
The heater is switched off and the ring pulses red when the temperature reaches 65 °C, the sensor is missing or reads wrong, or readings stop for 5 s. Check the sensor connection, then tap **Reset fault**. If it repeats, unplug the lamp and check the wiring (see ASSEMBLY.md).

## PID tuning (advanced)
Defaults are starting points.
1. Raise **Kp** until the temperature oscillates slightly around the setpoint, then reduce it by about 40 %.
2. Add **Ki** slowly to remove the steady offset.
3. Add **Kd** to cut overshoot (the glass reacts slowly).
4. Use the live chart to confirm ±1 °C over 30 min.

## Security
Keep the token secret and long (16+ random characters). The lamp is meant for your IoT WLAN only. It does not use HTTPS, so do not expose it to the internet.

## Updating firmware
Connect USB-C, then run `./tools/deploy.ps1`. Your `config.json` is preserved.
