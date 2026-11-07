import json
import os

CONFIG_FILE = "config.json"
DEFAULT_CONFIG = {
    "wifi": {"ssid": "", "password": ""},
    "token": "change-me",
    "hostname": "lavalamp",
    "power_pct": 100,
    "max_duty": 100,
    "pwm_freq": 10,
    "limits": {"min": 0.0, "max": 100.0, "cutoff": 100.0},
    "led": {
        "on": True,
        "brightness": 50,
        "mode": "temp",
        "color": [255, 60, 0],
        "speed": 30
    }
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
        self.data["limits"] = dict(DEFAULT_CONFIG["limits"])

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
