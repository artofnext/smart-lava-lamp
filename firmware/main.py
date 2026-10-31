# Phase 0 smoke test: blink the onboard blue LED. Replaced in later phases.
import time
from machine import Pin
import pins

led = Pin(pins.LED_ONBOARD, Pin.OUT, value=1)
while True:
    led.value(0)  # active low: on
    time.sleep(0.5)
    led.value(1)  # off
    time.sleep(0.5)
