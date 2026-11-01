"""Phase 1: ramp heater PWM duty up and down. Run:
uvx mpremote run tools/bench/pwm_ramp.py
Measure the voltage across the load and the MOSFET temperature as duty rises.
Duty is capped by MAX_DUTY and the run is time-limited. The heater is always
switched off on exit or Ctrl-C. Start with a dummy load, then the real heater."""
import time
from machine import Pin, PWM
import pins

MAX_DUTY = 50     # percent; raise gradually
STEP = 10         # percent per step
HOLD_S = 20       # seconds per step (watch the MOSFET/load temperature)
FREQ = 10         # Hz (low frequency prevents EMI/interference into 1-Wire sensor)

pwm = PWM(Pin(pins.HEATER), freq=FREQ, duty_u16=0)

def set_pct(p):
    pwm.duty_u16(p * 65535 // 100)
    print("duty %d%%" % p)

try:
    steps = list(range(STEP, MAX_DUTY + 1, STEP))
    for p in steps + steps[-2::-1]:
        set_pct(p)
        time.sleep(HOLD_S)
finally:
    pwm.duty_u16(0)
    pwm.deinit()
    Pin(pins.HEATER, Pin.OUT, value=0)
    print("heater off")
