# Smart Lava Lamp Controller

Closed-loop PID heating, scheduling and a web dashboard for a 12 V lava lamp. ESP32-C3 SuperMini, MicroPython, DS18B20, IRLZ44N, WS2812B ring.

## Docs
- [Project spec and design](docs/PROJECT.md)
- [Assembly](docs/ASSEMBLY.md)
- [User guide](docs/USER_GUIDE.md)
- [App plan](docs/APP_PLAN.md)

## Quick start
1. Flash MicroPython for ESP32-C3 onto the board (hold BOOT while plugging in USB).
2. No install needed: the scripts use `uvx mpremote` (uv downloads it on first run).
3. Copy `firmware/config.example.json` to `firmware/config.json` and fill it in. Upload it once with `uvx mpremote fs cp firmware/config.json :config.json`.
4. `./tools/deploy.ps1`. The onboard blue LED should blink (Phase 0 smoke test).

## Layout
`firmware/` runs on the board, `tools/` runs on the PC, `tests/` is host-side pytest, `docs/` has the documentation.
