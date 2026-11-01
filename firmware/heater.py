from machine import Pin, PWM

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
        self.duty_pct = pct
        self.pwm.duty_u16(int(pct * 65535 / 100))

    def off(self):
        self.duty_pct = 0.0
        self.pwm.duty_u16(0)

