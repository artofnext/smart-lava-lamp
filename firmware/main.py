# Phase 0 smoke test: blink the onboard RGB LED. Replaced in later phases.
import time
import neopixel
from machine import Pin
import pins

led = neopixel.NeoPixel(Pin(pins.LED_ONBOARD), 1)
while True:
    led[0] = (0, 20, 0)
    led.write()
    time.sleep(0.5)
    led[0] = (0, 0, 0)
    led.write()
    time.sleep(0.5)
