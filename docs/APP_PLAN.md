# Control App Plan

## Approach
A **single-page web app served by the lamp** (no native app, no cloud). It works on phones and desktops, can be added to the home screen (small `manifest.json`), and uses the REST/WS API in [PROJECT.md](PROJECT.md) section 7.

Constraints: assets are served from flash and gzip-compressed, kept to about 40 KB total. They are vanilla HTML/CSS/JS with no framework and no CDN, so they work offline on the IoT VLAN.

## Files
```
firmware/web/static/
├── index.html
├── app.js        # API client, WS, views
├── style.css     # dark theme
├── chart.js      # tiny canvas line chart (own code)
└── manifest.json
```

## Screens
| Screen | Content |
|---|---|
| **Login** | Token field, stored in `localStorage`. A 401 sends the user back here |
| **Dashboard** | Large current temp, setpoint slider (45-55) with +/- buttons, power button, state badge, duty bar, live chart (last 30 min), ring colour preview |
| **Schedule** | List of windows. Add/edit sheet: day chips, time pickers, pattern select, enable toggle. Shows the next planned start and the estimated warm-up lead time |
| **Patterns** | Preset list plus an editor: step table (minutes, °C), a small preview chart, run and stop buttons. Values clamped in the UI and again on the device |
| **Lighting** | Brightness slider (capped), palette picker, LED on/off |
| **Settings** | PID gains with the live chart alongside, Wi-Fi, token change, limits (read-only cutoff), device info (IP, RSSI, uptime, free memory), reset fault |

## Behaviour
- Telemetry arrives over the WebSocket every second. If it drops, the app shows a "reconnecting" banner and falls back to polling `/api/status` every 5 s.
- Writes are optimistic, then confirmed by the next status message. Errors show a toast with the device's message.
- The fault state shows a full-width red banner with the cause and a **Reset fault** button, disabled until the temperature is safe.
- Changing PID gains or schedule needs a confirm step. Changing the token or Wi-Fi shows a warning that the connection will be lost.
- Mobile-first layout, large touch targets, dark theme with a warm lava gradient accent. Supports `prefers-reduced-motion`.

## Device side
- Microdot with one route per endpoint, a token check middleware, JSON validation helper.
- Static files served with `Content-Encoding: gzip` and cache headers.
- Memory: max 2 simultaneous clients (1 WS plus 1 HTTP in practice). Extra WS clients are refused with a 503.
- Token comparison is constant-time. A short delay follows 5 failed attempts.

## Milestones
1. API skeleton and token auth, tested with `curl`.
2. Dashboard with live telemetry and chart.
3. Setpoint/power control, fault banner.
4. Schedule and pattern editors.
5. Lighting and settings screens, AP provisioning page.
6. Polish: PWA manifest, reconnect handling, tests on phone, with a measured loop-jitter check under load.

## Testing
- API: `pytest` against a host build of the route handlers with a fake thermal module.
- UI: manual test matrix (iOS Safari, Android Chrome, desktop) and a Playwright smoke test against a mock server (`tools/mock_server.py`).
