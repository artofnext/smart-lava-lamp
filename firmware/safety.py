import time

class SafetyLatch:
    """Safety trip latch for over-temperature or persistent sensor loss (>5s)."""
    def __init__(self, cutoff_temp=100.0, timeout_s=5.0):
        self.cutoff_temp = float(cutoff_temp)
        self.timeout_s = float(timeout_s)
        self.fault = None

    def check(self, temp, last_valid_time, current_time=None):
        if self.fault:
            return False
        now = time.time() if current_time is None else current_time

        # 1. Over-temperature check (immediate trip)
        if temp is not None and temp >= self.cutoff_temp:
            self.fault = "Over-temperature: %.1f C exceeds cutoff %.1f C" % (temp, self.cutoff_temp)
            return False

        # 2. Timeout check: no valid reading for timeout_s (5s)
        if last_valid_time is None or (now - last_valid_time) > self.timeout_s:
            self.fault = "Sensor timeout (>%ds without valid reading)" % int(self.timeout_s)
            return False

        return True

    def reset_fault(self, current_temp):
        if not self.fault:
            return True
        # Only allow reset if current temperature is safely below cutoff
        if current_temp is not None and current_temp < (self.cutoff_temp - 5.0):
            self.fault = None
            return True
        return False

