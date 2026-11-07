import time
import asyncio
import network
import machine
import pins
from config import Config
from safety import SafetyLatch
from sensor import Sensor
from heater import Heater
from web_server import WebServer

class AppState:
    def __init__(self, config, heater, safety):
        self.config = config
        self.heater = heater
        self.safety = safety

        self.power_on = False
        self.state = "OFF"
        self.current_temp = None
        self.power_pct = float(config.get("power_pct", 100))
        self.ip_address = "0.0.0.0"
        self.start_time = time.time()
        self.last_valid_time = None
        self.history = []  # 1-hour sliding window (1 sample / 10s = max 360 samples)

    def record_temp(self, temp):
        if temp is not None:
            self.history.append(round(temp, 1))
            if len(self.history) > 360:
                self.history.pop(0)

    def set_power(self, on):
        if on and self.safety.fault:
            self.reset_fault()
        if on and self.safety.fault:
            print("Cannot power on: fault latched:", self.safety.fault)
            self.power_on = False
            return False
        self.power_on = bool(on)
        if self.power_on:
            self.state = "HEATING"
            self.heater.set_duty(self.power_pct)
        else:
            if self.state != "FAULT":
                self.state = "COOLING" if (self.current_temp and self.current_temp > 35) else "OFF"
            self.heater.off()
        print("Power set to:", "ON" if self.power_on else "OFF", "at %d%%" % int(self.power_pct))
        return True

    def set_power_pct(self, val):
        val = max(0.0, min(100.0, float(val)))
        self.power_pct = val
        self.config.set("power_pct", val)
        self.config.save()
        if self.power_on and self.state != "FAULT":
            self.heater.set_duty(val)
        return val

    def reset_fault(self):
        self.last_valid_time = time.time()
        self.safety.reset_fault()
        if self.state == "FAULT":
            self.state = "OFF"
            self.heater.off()
        return True

    def get_status(self):
        return {
            "temp": self.current_temp,
            "power_pct": round(self.power_pct, 1),
            "duty": round(self.heater.duty_pct, 1),
            "state": self.state,
            "fault": self.safety.fault,
            "power": self.power_on,
            "limits": self.config.get("limits", {"min": 0, "max": 100, "cutoff": 200}),
            "ip": self.ip_address,
            "uptime": int(time.time() - self.start_time)
        }


async def connect_wifi(cfg):
    w = network.WLAN(network.STA_IF)
    w.active(True)
    wifi_cfg = cfg.get("wifi", {})
    ssid = wifi_cfg.get("ssid", "")
    pwd = wifi_cfg.get("password", "")
    if ssid:
        print("Connecting to Wi-Fi:", ssid)
        w.connect(ssid, pwd)
        for _ in range(15):
            if w.isconnected():
                print("Wi-Fi connected! IP:", w.ifconfig()[0])
                return w.ifconfig()[0]
            await asyncio.sleep(1)
    print("Wi-Fi not connected (running in standalone mode)")
    return w.ifconfig()[0] if w.isconnected() else "0.0.0.0"


async def main():
    config = Config()
    limits = config.get("limits", {})
    cutoff = float(limits.get("cutoff", 200.0))

    safety = SafetyLatch(cutoff_temp=cutoff, timeout_s=0.0)
    sensor = Sensor(pins.ONEWIRE)
    pwm_freq = int(config.get("pwm_freq", 10))
    heater = Heater(pins.HEATER, max_duty=config.get("max_duty", 100), freq=pwm_freq)

    app_state = AppState(config, heater, safety)

    # Wi-Fi & Web Server
    app_state.ip_address = await connect_wifi(config)
    web = WebServer(app_state, port=80)
    await web.start()

    # Hardware Watchdog (30 seconds timeout)
    # shortcut: WDT disabled during development on some soft-reboots, active on production hardware
    try:
        wdt = machine.WDT(timeout=30000)
    except Exception:
        wdt = None

    # Main 1 Hz Control Loop
    loop_count = 0
    while True:
        try:
            loop_count += 1
            if wdt:
                wdt.feed()

            now = time.time()

            # 1. Read temperature sensor (~750ms conversion)
            temp = await sensor.read()
            app_state.current_temp = temp
            if sensor.last_valid_time:
                app_state.last_valid_time = sensor.last_valid_time
            if loop_count % 10 == 1:
                app_state.record_temp(temp)

            # 2. Safety evaluation
            is_safe = safety.check(temp, app_state.last_valid_time, now)
            if not is_safe:
                app_state.state = "FAULT"
                app_state.power_on = False
                heater.off()
                await asyncio.sleep_ms(250)
                continue

            # 3. Direct manual heater power control
            if app_state.power_on:
                app_state.state = "HEATING"
                heater.set_duty(app_state.power_pct)
            else:
                heater.off()
                if temp and temp > 35.0:
                    app_state.state = "COOLING"
                else:
                    app_state.state = "OFF"

            # Live serial logging over USB every 2 seconds
            if loop_count % 2 == 0:
                t_str = ("%.1f C" % temp) if temp is not None else "--.- C"
                f_str = (" | FAULT: %s" % safety.fault) if safety.fault else ""
                print("T: %s | PwrLvl: %d%% | Duty: %d%% | State: %s | Pwr: %s%s" % (
                    t_str, int(app_state.power_pct), int(heater.duty_pct), app_state.state,
                    "ON" if app_state.power_on else "OFF", f_str
                ))

        except Exception as e:
            print("Control loop iteration error:", e)

        # 750ms conversion + 250ms sleep = 1.0s (1 Hz) measurement rate
        await asyncio.sleep_ms(250)

if __name__ == "__main__":
    asyncio.run(main())
