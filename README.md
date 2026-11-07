# Smart Lava Lamp Controller

Wi-Fi controller for a 12 V DC lava lamp built on the **ESP32-C3 SuperMini** running **MicroPython**, with an **IRLZ44N** low-frequency PWM heater driver, **DS18B20** capsule-bottom temperature telemetry, and a **16-LED WS2812B** addressable RGB ring.

---

## User Manual

### 1. Automatic Boot & Warmup Behavior
When you plug in or power on the lamp:
1. **Warmup Phase (`< 65 °C`)**:
   - The heater automatically starts **ON at 100% power** to melt the wax as quickly as possible.
   - The LED ring turns **ON** in **Temp (Temperature Reactive)** mode so you can see the lamp's warm-up progress across the room.
2. **Cruise Transition (`≥ 65 °C`)**:
   - As soon as the DS18B20 sensor reaches **65 °C**, the heater automatically reduces power to **75%** for steady lava flow.
   - The LED ring switches to your **last manually selected LED mode** saved in flash memory (defaults to `Temp` if you haven't chosen another mode).
3. **Manual Override**:
   - Adjusting the heater power or toggling the heater button at any time overrides the automatic 65 °C heater transition.
   - Selecting any LED mode on the dashboard immediately switches to that mode, saves it to flash as your new post-warmup default, and overrides the 65 °C LED transition.

### 2. Web Dashboard Controls
Open `http://<lamp-ip>` in your phone or desktop browser (enter your access token on first visit; it is saved in `localStorage`).

#### Heater Card (`🔥 Lava Lamp`)
- **Status Badge**:
  - `HEATING` (orange): Heater is active.
  - `COOLING` (blue): Heater is off while the base is still warm (`> 35 °C`).
  - `OFF` (grey): Heater is off and base is cool.
  - `FAULT` (pulsing red): Safety cutoff tripped (`≥ 100 °C`).
- **Temperature Readout & 1-Hour Diagram**:
  - Displays live DS18B20 temperature updated once per second (`1 Hz`).
  - The chart plots a **1-hour (`-60m` to `now`) sliding window** over a `10 °C – 80 °C` range with a dashed reference line at `63 °C` (wax melting point). Up to 1 hour of history is buffered in ESP32 RAM (`10 s` intervals) so refreshing the page preserves the curve.
- **Heater Power Slider & Presets**:
  - Adjust heater duty cycle from `0%` to `100%` using the slider, `-5` / `+5` step buttons, or quick preset buttons (`25%`, `50%`, `75%`, `100%`).
- **Heater ON / OFF & Clear Fault**:
  - **Heater ON / OFF** toggles the heater element.
  - **Clear Fault** resets the safety latch if it ever trips.

#### LED Ring Card (`💡 LED Ring`)
- **LED ON / OFF Button**:
  - Toggles the LED ring when the heater is off.
  - Whenever the **heater is active**, the LED ring is forced **ON** (`ON (Heater)`) and the button is disabled.
- **Brightness Slider (`5% – 80%`)**:
  - Controls overall ring brightness across all modes (capped at `80%` to limit current and base heat).
- **Lighting Modes**:
  1. **Solid**: Fills all 16 LEDs with a single static color chosen via the **Solid Color** picker.
  2. **Temp (Temperature Reactive)**: Smoothly blends all 16 LEDs based on live sensor temperature:
     - `≤ 25 °C`: Cool Blue
     - `40 °C`: Purple
     - `55 °C`: Orange
     - `≥ 60 °C`: Lava Red
  3. **Rainbow**: Smoothly cycles all 16 LEDs in unison through the full color spectrum. Use the **Animation Speed** slider (`1% – 100%`) to set cycle speed.
  4. **🔥 Flame**: Per-pixel fire simulation with neighbor heat diffusion and random ember flares around the ring. Use the **Animation Speed** slider (`1% – 100%`) to control flame turbulence.

---

## Developer Manual

### 1. Hardware & Pinout (`ESP32-C3 SuperMini`)
All pin definitions live in [`firmware/pins.py`](firmware/pins.py):

| Function | GPIO | Hardware Notes |
|---|---|---|
| Heater MOSFET Gate | `GPIO4` | Via `220 Ω` series resistor, `10 kΩ` pull-down to `GND`, drives `IRLZ44N` |
| DS18B20 Data (1-Wire) | `GPIO5` | `4.7 kΩ` pull-up resistor between `3V3` and `DATA` |
| WS2812B Ring Data (16 px) | `GPIO6` | Powered from `5V` buck rail, data from `GPIO6` |
| Onboard Blue LED | `GPIO8` | Active-low (`0 = ON`, `1 = OFF`) |

#### Circuit Summary
```text
12V+ ──┬─ 100µF ─ GND
       ├─────────── Heater (+) ──┬── Drain (IRLZ44N)
       │                         └── 1N4007 across heater (stripe/cathode to 12V+)
       └── Buck IN                     Source ── GND
Buck OUT (5V) ── ESP32-C3 5V pin & WS2812B Ring 5V
ESP32 3V3 ──┬─ 4.7kΩ ─┬─ DS18B20 DATA ── GPIO5
            └─ DS18B20 VDD (GND to common GND)
GPIO4 ── 220Ω ──┬── Gate (IRLZ44N)
                └── 10kΩ ── GND
GPIO6 ── WS2812B Ring DIN
```
See [`docs/ASSEMBLY.md`](docs/ASSEMBLY.md) and [`docs/bench-checklist.md`](docs/bench-checklist.md) for build and bench-testing steps.

### 2. Project Structure
```text
firmware/
├── boot.py              # Runs on reset: forces GPIO4 (heater) LOW immediately
├── main.py              # AppState, 1 Hz control/sensor loop, 25 FPS LED task
├── pins.py              # Hardware GPIO map
├── config.py            # Atomic JSON config loader/saver
├── config.example.json  # Template configuration
├── heater.py            # 10 Hz PWM driver with max_duty clamp
├── sensor.py            # Non-blocking async DS18B20 1-Wire reader (750ms conversion)
├── safety.py            # Over-temperature safety latch (100 °C cutoff)
├── leds.py              # WS2812B driver (solid, temp, rainbow, flame)
├── web_server.py        # Async HTTP server & constant-time Bearer token auth
└── web/
    └── index.html       # Single-file dark-mode web UI & 1-hour canvas chart
tests/
└── test_logic.py        # Host-side unit test suite (unittest)
tools/
├── deploy.ps1           # USB deployment script using uvx mpremote
└── bench/               # Hardware bring-up scripts (ds18b20_scan.py, pwm_ramp.py)
```

### 3. Configuration (`firmware/config.json`)
Copy [`firmware/config.example.json`](firmware/config.example.json) to `firmware/config.json`:
```json
{
  "wifi": {
    "ssid": "your-ssid",
    "password": "your-password"
  },
  "token": "change-me",
  "hostname": "lavalamp",
  "power_pct": 100,
  "max_duty": 100,
  "pwm_freq": 10,
  "limits": {
    "min": 0,
    "max": 100,
    "cutoff": 100
  },
  "led": {
    "on": true,
    "brightness": 50,
    "mode": "temp",
    "color": [255, 60, 0],
    "speed": 30
  }
}
```

### 4. HTTP REST API
All `/api/*` endpoints require header `Authorization: Bearer <token>` (or query param `?token=<token>`).

| Method | Path | Payload / Response |
|---|---|---|
| `GET` | `/api/status` | Returns `temp`, `power_pct`, `duty`, `state`, `fault`, `power`, `led`, `limits`, `ip`, `uptime` |
| `GET` | `/api/history` | Returns `{"interval_s": 10, "temps": [...]}` (up to 360 samples = 1 hour) |
| `POST` | `/api/power` | `{"on": true\|false}` — turns heater ON/OFF |
| `POST` | `/api/power-level` | `{"power_pct": 0..100}` — sets manual heater power % |
| `POST` | `/api/reset-fault` | Clears safety fault latch |
| `GET/POST` | `/api/led` | Reads or updates `{"on", "brightness", "mode", "color", "speed"}` |

### 5. Deploying & Testing

#### Run Unit Tests (Host PC)
```powershell
python -m unittest tests/test_logic.py
```

#### Deploy Firmware to ESP32-C3 over USB
Ensure no `mpremote` REPL session is holding the serial port (`Ctrl + ]` to exit), then run:
```powershell
# Deploy code + web UI (preserves on-device config.json)
.\tools\deploy.ps1 -Port COM9

# Deploy code + web UI AND overwrite config.json on device
.\tools\deploy.ps1 -Port COM9 -Config
```

#### View Live Serial Telemetry
```powershell
uvx mpremote connect COM9
```
Outputs 0.5 Hz status lines:
```text
T: 58.4 C | PwrLvl: 100% | Duty: 100% | State: HEATING | Pwr: ON
```
