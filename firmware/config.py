import json
import os

CONFIG_FILE = "config.json"
DEFAULT_CONFIG = {
    "wifi": {"ssid": "", "password": ""},
    "token": "change-me",
    "hostname": "lavalamp",
    "setpoint": 50.0,
    "pid": {"kp": 8.0, "ki": 0.05, "kd": 40.0},
    "max_duty": 100,
    "pwm_freq": 10,
    "limits": {"min": 45.0, "max": 80.0, "cutoff": 100.0},
    "tz_dst": True,
    "led": {"brightness": 40, "palette": "lava"},
    "schedule": [],
    "patterns": {
        "calm": [[0, 50]],
        "lively": [[0, 54], [20, 48], [40, 54]]
    },
    "heat_rate": 0.15
}

class Config:
    def __init__(self, filename=CONFIG_FILE):
        self.filename = filename
        self.data = dict(DEFAULT_CONFIG)
        self.load()

    def load(self):
        try:
            with open(self.filename, "r") as f:
                loaded = json.load(f)
                if isinstance(loaded, dict):
                    self.data.update(loaded)
        except Exception as e:
            print("Config load note:", e)

    def save(self):
        # Atomic-like replace using a temp file to avoid corrupting on power loss
        tmp = self.filename + ".tmp"
        try:
            with open(tmp, "w") as f:
                json.dump(self.data, f)
            try:
                os.remove(self.filename)
            except Exception:
                pass
            os.rename(tmp, self.filename)
            return True
        except Exception as e:
            print("Config save error:", e)
            return False

    def get(self, key, default=None):
        return self.data.get(key, default)

    def set(self, key, value):
        self.data[key] = value

    def setpoint(self):
        sp = float(self.data.get("setpoint", 50.0))
        limits = self.data.get("limits", {})
        low = float(limits.get("min", 45.0))
        high = float(limits.get("max", 80.0))
        return max(low, min(high, sp))

