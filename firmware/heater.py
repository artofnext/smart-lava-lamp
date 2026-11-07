import time
from machine import Pin, PWM

def _sleep_ms(ms):
    if hasattr(time, "sleep_ms"):
        time.sleep_ms(ms)

class Heater:
    def __init__(self, pin_num, max_duty=100, freq=10):
        self.pin_num = pin_num
        self.max_duty = max_duty
        self.freq = freq
        # Low frequency (10 Hz) avoids EMI / crosstalk into 1-Wire and NeoPixel lines
        self.pwm = PWM(Pin(pin_num), freq=freq, duty_u16=0)
        self.duty_pct = 0.0

    def set_duty(self, pct):
        pct = max(0.0, min(float(self.max_duty), float(pct)))
        # Soft-step large current changes (>40%) to prevent 12V supply load-dump / ground bounce
        if abs(pct - self.duty_pct) > 40.0:
            mid = (self.duty_pct + pct) * 0.5
            self.pwm.duty_u16(int(mid * 65535 / 100))
            _sleep_ms(15)
        self.duty_pct = pct
        self.pwm.duty_u16(int(pct * 65535 / 100))

    def off(self):
        if self.duty_pct > 40.0:
            self.pwm.duty_u16(int(self.duty_pct * 0.4 * 65535 / 100))
            _sleep_ms(15)
        self.duty_pct = 0.0
        self.pwm.duty_u16(0)
