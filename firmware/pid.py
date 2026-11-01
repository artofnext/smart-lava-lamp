class PID:
    """PID controller with anti-windup clamping and derivative-on-measurement."""
    def __init__(self, kp=8.0, ki=0.05, kd=40.0, out_min=0.0, out_max=100.0):
        self.kp = float(kp)
        self.ki = float(ki)
        self.kd = float(kd)
        self.out_min = float(out_min)
        self.out_max = float(out_max)
        self._integral = 0.0
        self._last_meas = None

    def reset(self):
        self._integral = 0.0
        self._last_meas = None

    def update(self, setpoint, measurement, dt=1.0):
        if dt <= 0:
            dt = 1.0
        error = setpoint - measurement
        p = self.kp * error

        # Integral with clamping
        self._integral += self.ki * error * dt
        if self._integral > self.out_max:
            self._integral = self.out_max
        elif self._integral < self.out_min:
            self._integral = self.out_min

        # Derivative on measurement (avoids setpoint kick)
        if self._last_meas is not None:
            d = -self.kd * (measurement - self._last_meas) / dt
        else:
            d = 0.0
        self._last_meas = measurement

        out = p + self._integral + d
        if out > self.out_max:
            return self.out_max
        if out < self.out_min:
            return self.out_min
        return out

