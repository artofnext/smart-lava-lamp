import time

class SafetyLatch:
    """Safety trip latch for over-temperature (cutoff)."""
    def __init__(self, cutoff_temp=200.0, timeout_s=0.0):
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

        # 2. Timeout check (only if timeout_s > 0)
        if self.timeout_s > 0:
            if last_valid_time is None or (now - last_valid_time) > self.timeout_s:
                self.fault = "Sensor timeout (>%ds without valid reading)" % int(self.timeout_s)
                return False

        return True

    def reset_fault(self, current_temp=None):
        self.fault = None
        return True

