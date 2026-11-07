from machine import Pin
import neopixel

NUM_LEDS = 16
MAX_BRIGHTNESS = 80
VALID_MODES = ("solid", "temp", "rainbow", "flame")

TEMP_STOPS = (
    (25.0, (0, 100, 255)),   # Cool blue
    (40.0, (160, 0, 220)),   # Purple
    (55.0, (255, 110, 0)),   # Orange
    (60.0, (255, 15, 0)),    # Lava red
)

def temp_to_rgb(temp):
    if temp is None or temp <= TEMP_STOPS[0][0]:
        return TEMP_STOPS[0][1]
    if temp >= TEMP_STOPS[-1][0]:
        return TEMP_STOPS[-1][1]
    for i in range(len(TEMP_STOPS) - 1):
        t0, c0 = TEMP_STOPS[i]
        t1, c1 = TEMP_STOPS[i + 1]
        if t0 <= temp <= t1:
            f = (temp - t0) / (t1 - t0)
            return (
                int(c0[0] + (c1[0] - c0[0]) * f),
                int(c0[1] + (c1[1] - c0[1]) * f),
                int(c0[2] + (c1[2] - c0[2]) * f),
            )
    return TEMP_STOPS[-1][1]

def hsv_to_rgb(hue):
    h = (hue % 360.0) / 60.0
    i = int(h)
    f = h - i
    q = int(255 * (1.0 - f))
    t = int(255 * f)
    if i == 0: return (255, t, 0)
    if i == 1: return (q, 255, 0)
    if i == 2: return (0, 255, t)
    if i == 3: return (0, q, 255)
    if i == 4: return (t, 0, 255)
    return (255, 0, q)

def heat_to_flame_rgb(h):
    h = max(0.0, min(1.0, h))
    if h < 0.5:
        f = h / 0.5
        return (int(120 + 135 * f), int(8 + 47 * f), 0)
    if h < 0.85:
        f = (h - 0.5) / 0.35
        return (255, int(55 + 80 * f), 0)
    f = (h - 0.85) / 0.15
    return (255, int(135 + 75 * f), int(35 * f))

class LEDController:
    def __init__(self, pin_num, cfg=None):
        cfg = cfg or {}
        self.np = neopixel.NeoPixel(Pin(pin_num, Pin.OUT), NUM_LEDS)
        self.on = bool(cfg.get("on", True))
        self.brightness = max(1, min(MAX_BRIGHTNESS, int(cfg.get("brightness", 50))))
        self.mode = cfg.get("mode", "temp")
        if self.mode not in VALID_MODES:
            self.mode = "temp"
        c = cfg.get("color", [255, 60, 0])
        self.color = (int(c[0]), int(c[1]), int(c[2]))
        self.speed = max(1, min(100, int(cfg.get("speed", 30))))
        self.hue = 0.0
        self.heat = [0.35] * NUM_LEDS
        self._rng = 0x12345678
        self._last_out = None

    def _rand_float(self):
        self._rng = (self._rng * 1664525 + 1013904223) & 0xFFFFFFFF
        return (self._rng >> 8) / 16777216.0

    def _step_flame(self, dt, scale):
        rate = min(0.45, dt * (1.2 + self.speed * 0.08))
        new_heat = [0.0] * NUM_LEDS
        # 1. Cool down & diffuse across neighboring pixels on the ring
        for i in range(NUM_LEDS):
            prev_h = self.heat[(i - 1) % NUM_LEDS]
            curr_h = self.heat[i]
            next_h = self.heat[(i + 1) % NUM_LEDS]
            blended = curr_h * (1.0 - rate) + (prev_h + curr_h + next_h) / 3.0 * rate
            cool = rate * (0.18 + 0.35 * self._rand_float())
            new_heat[i] = max(0.08, blended - cool)

        # 2. Random ember sparks / flame tongues
        if self._rand_float() < (0.35 + self.speed * 0.005):
            idx = int(self._rand_float() * NUM_LEDS) % NUM_LEDS
            flare = 0.65 + 0.35 * self._rand_float()
            new_heat[idx] = max(new_heat[idx], flare)
            new_heat[(idx - 1) % NUM_LEDS] = max(new_heat[(idx - 1) % NUM_LEDS], flare * 0.65)
            new_heat[(idx + 1) % NUM_LEDS] = max(new_heat[(idx + 1) % NUM_LEDS], flare * 0.65)

        self.heat = new_heat
        for i in range(NUM_LEDS):
            r, g, b = heat_to_flame_rgb(self.heat[i])
            self.np[i] = (int(r * scale), int(g * scale), int(b * scale))
        self.np.write()
        self._last_out = None

    def step(self, dt, current_temp, heater_on):
        effective_on = True if heater_on else self.on
        if not effective_on:
            out = (0, 0, 0)
        else:
            scale = self.brightness / 100.0
            if self.mode == "flame":
                self._step_flame(dt, scale)
                return
            if self.mode == "solid":
                r, g, b = self.color
            elif self.mode == "rainbow":
                # Speed 1..100 maps to ~3..120 deg/sec across the hue wheel
                self.hue = (self.hue + dt * (2.0 + self.speed * 1.18)) % 360.0
                r, g, b = hsv_to_rgb(self.hue)
            else:
                r, g, b = temp_to_rgb(current_temp)

            out = (int(r * scale), int(g * scale), int(b * scale))

        if out != self._last_out:
            self.np.fill(out)
            self.np.write()
            self._last_out = out

    def to_dict(self, heater_on=False):
        return {
            "on": True if heater_on else self.on,
            "brightness": self.brightness,
            "mode": self.mode,
            "color": list(self.color),
            "speed": self.speed
        }
