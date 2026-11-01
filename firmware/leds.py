import time
import math
from machine import Pin
import neopixel

class LEDController:
    MAX_BRIGHTNESS = 80

    def __init__(self, ring_pin, onboard_pin, num_leds=16, brightness_pct=40, palette="status"):
        self.num_leds = num_leds
        self.brightness = max(5, min(self.MAX_BRIGHTNESS, int(brightness_pct))) / 100.0
        self.ring = neopixel.NeoPixel(Pin(ring_pin), num_leds)
        self.onboard = Pin(onboard_pin, Pin.OUT, value=1)  # Active low: 1=off
        self.tick = 0
        self.palette = palette
        self.off()

    def set_brightness(self, pct):
        self.brightness = max(5, min(self.MAX_BRIGHTNESS, int(pct))) / 100.0

    def _scale(self, r, g, b, factor=1.0):
        scale = self.brightness * max(0.0, min(1.0, factor))
        return (int(r * scale), int(g * scale), int(b * scale))

    def _wheel(self, pos):
        pos = pos % 256
        if pos < 85:
            return (255 - pos * 3, pos * 3, 0)
        elif pos < 170:
            pos -= 85
            return (0, 255 - pos * 3, pos * 3)
        else:
            pos -= 170
            return (pos * 3, 0, 255 - pos * 3)

    def off(self):
        for i in range(self.num_leds):
            self.ring[i] = (0, 0, 0)
        self.ring.write()
        self.onboard.value(1)

    def update(self, state, progress=0.0, duty_pct=0.0, wifi_connected=True):
        self.tick += 1

        # Onboard LED: slow blink normally, solid in fault, fast blink if disconnected
        if state == "FAULT":
            self.onboard.value(0)
        elif not wifi_connected:
            self.onboard.value(0 if (self.tick % 4 < 2) else 1)
        else:
            self.onboard.value(0 if (self.tick % 10 < 2) else 1)

        # 1. Wi-Fi connection indicator (Cyan chase)
        if not wifi_connected:
            pos = self.tick % self.num_leds
            for i in range(self.num_leds):
                dist = (i - pos) % self.num_leds
                b = max(0.0, 1.0 - (dist / 4.0)) if dist < 4 else 0.0
                self.ring[i] = self._scale(0, 180, 255, b)
            self.ring.write()
            return

        # 2. Hardware Fault (Red pulse)
        if state == "FAULT":
            fade = 0.5 + 0.5 * math.sin(self.tick * 0.4)
            c = self._scale(255, 0, 0, fade)
            for i in range(self.num_leds):
                self.ring[i] = c
            self.ring.write()
            return

        # 3. Active Heating (WARMING state)
        if state == "WARMING":
            lit = max(2, int(progress * self.num_leds))
            pulse = 0.7 + 0.3 * math.sin(self.tick * 0.4)
            p = max(0.0, min(1.0, progress))
            # Color transitions from deep blue/cyan to fiery amber/orange
            r = int(255 * (0.2 + 0.8 * p))
            g = int(70 * p + 30 * (1 - p))
            b = int(240 * (1 - p))
            c_lit = self._scale(r, g, b, pulse)
            c_dim = self._scale(r * 0.06, g * 0.06, b * 0.06)

            runner = self.tick % self.num_leds
            for i in range(self.num_leds):
                if i == runner:
                    self.ring[i] = self._scale(255, 200, 80, 1.0)
                elif i < lit:
                    self.ring[i] = c_lit
                else:
                    self.ring[i] = c_dim
            self.ring.write()
            return

        # 4. Holding Target Temperature (Breathing glow scaled with duty %)
        if state == "HOLDING":
            speed = 0.15 + (duty_pct / 100.0) * 0.25
            val = 0.35 + 0.65 * (0.5 + 0.5 * math.sin(self.tick * speed))
            c = self._scale(255, 85, 8, val)
            for i in range(self.num_leds):
                self.ring[i] = c
            self.ring.write()
            return

        # 5. Cooling State
        if state == "COOLING":
            fade = max(0.0, 1.0 - progress)
            c = self._scale(50, 100, 255, fade * 0.4)
            for i in range(self.num_leds):
                self.ring[i] = c
            self.ring.write()
            return

        # 6. Standby / OFF - check if manual ambient palette is selected
        if self.palette == "lava":
            val = 0.3 + 0.7 * (0.5 + 0.5 * math.sin(self.tick * 0.2))
            c = self._scale(255, 60, 5, val)
            for i in range(self.num_leds):
                self.ring[i] = c
            self.ring.write()
            return

        if self.palette == "rainbow":
            for i in range(self.num_leds):
                rc = self._wheel((i * 256 // self.num_leds + self.tick * 6) % 256)
                self.ring[i] = self._scale(rc[0], rc[1], rc[2])
            self.ring.write()
            return

        if self.palette == "white":
            c = self._scale(255, 175, 110, 0.75)
            for i in range(self.num_leds):
                self.ring[i] = c
            self.ring.write()
            return

        # Default: all off in standby
        self.off()
