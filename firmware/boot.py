# Runs first on every reset: force the heater off before anything else.
from machine import Pin
import pins

Pin(pins.HEATER, Pin.OUT, value=0)
