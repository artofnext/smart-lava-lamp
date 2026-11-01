import time
import asyncio
import network
import machine
import pins
from config import Config
from pid import PID
from safety import SafetyLatch
from sensor import Sensor
from heater import Heater
from leds import LEDController
from scheduler import Scheduler
from patterns import evaluate_pattern
from web_server import WebServer

class AppState:
    def __init__(self, config, heater, pid, safety, leds, scheduler):
        self.config = config
        self.heater = heater
        self.pid = pid
        self.safety = safety
        self.leds = leds
        self.scheduler = scheduler

        self.power_on = False
        self.state = "OFF"
        self.current_temp = None
        self.power_pct = float(config.get("power_pct", 100))
        self.setpoint = self.power_pct
        self.active_pattern = None
        self.pattern_start_time = None
        self.ip_address = "0.0.0.0"
        self.start_time = time.time()
        self.last_valid_time = None

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
        self.setpoint = val
        self.config.set("power_pct", val)
        self.config.save()
        if self.power_on and self.state != "FAULT":
            self.heater.set_duty(val)
        return val

    def set_setpoint(self, val):
        return self.set_power_pct(val)

    def update_pid(self, p_dict):
        pid_cfg = self.config.get("pid", {})
        if "kp" in p_dict: pid_cfg["kp"] = float(p_dict["kp"])
        if "ki" in p_dict: pid_cfg["ki"] = float(p_dict["ki"])
        if "kd" in p_dict: pid_cfg["kd"] = float(p_dict["kd"])
        self.pid.kp = pid_cfg["kp"]
        self.pid.ki = pid_cfg["ki"]
        self.pid.kd = pid_cfg["kd"]
        self.config.set("pid", pid_cfg)
        self.config.save()

    def reset_fault(self):
        self.last_valid_time = time.time()
        self.safety.reset_fault()
        if self.state == "FAULT":
            self.state = "OFF"
            self.heater.off()
        return True

    def set_led_brightness(self, pct):
        pct = max(5, min(80, int(pct)))
        self.leds.set_brightness(pct)
        led_cfg = self.config.get("led", {})
        led_cfg["brightness"] = pct
        self.config.set("led", led_cfg)
        self.config.save()

    def set_led_palette(self, pal):
        self.leds.palette = pal
        led_cfg = self.config.get("led", {})
        led_cfg["palette"] = pal
        self.config.set("led", led_cfg)
        self.config.save()

    def get_status(self):
        return {
            "temp": self.current_temp,
            "power_pct": round(self.power_pct, 1),
            "setpoint": round(self.power_pct, 1),
            "duty": round(self.heater.duty_pct, 1),
            "state": self.state,
            "fault": self.safety.fault,
            "power": self.power_on,
            "active_pattern": self.active_pattern,
            "palette": self.leds.palette,
            "limits": self.config.get("limits", {"min": 0, "max": 100, "cutoff": 200}),
            "ip": self.ip_address,
            "uptime": int(time.time() - self.start_time),
            "pid": {"kp": self.pid.kp, "ki": self.pid.ki, "kd": self.pid.kd}
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

    pid_cfg = config.get("pid", {})
    pid = PID(
        kp=pid_cfg.get("kp", 8.0),
        ki=pid_cfg.get("ki", 0.05),
        kd=pid_cfg.get("kd", 40.0),
        out_min=0.0,
        out_max=float(config.get("max_duty", 100))
    )

    safety = SafetyLatch(cutoff_temp=cutoff, timeout_s=0.0)
    sensor = Sensor(pins.ONEWIRE)
    pwm_freq = int(config.get("pwm_freq", 10))
    heater = Heater(pins.HEATER, max_duty=config.get("max_duty", 100), freq=pwm_freq)

    led_cfg = config.get("led", {})
    leds = LEDController(
        ring_pin=pins.LED_RING,
        onboard_pin=pins.LED_ONBOARD,
        brightness_pct=led_cfg.get("brightness", 40),
        palette=led_cfg.get("palette", "status")
    )

    scheduler = Scheduler(config)
    app_state = AppState(config, heater, pid, safety, leds, scheduler)

    # Wi-Fi & Web Server
    app_state.ip_address = await connect_wifi(config)
    if app_state.ip_address != "0.0.0.0":
        asyncio.create_task(scheduler.sync_ntp())

    web = WebServer(app_state, port=80)
    await web.start()

    # Hardware Watchdog (30 seconds timeout)
    # shortcut: WDT disabled during development on some soft-reboots, active on production hardware
    try:
        wdt = machine.WDT(timeout=30000)
    except Exception:
        wdt = None

    # Main 1 Hz Control Loop
    last_loop_time = time.time()
    loop_count = 0
    while True:
        try:
            loop_count += 1
            if wdt:
                wdt.feed()

            now = time.time()
            dt = max(0.5, min(2.0, now - last_loop_time))
            last_loop_time = now

            # 1. Read temperature sensor
            temp = await sensor.read()
            app_state.current_temp = temp
            if sensor.last_valid_time:
                app_state.last_valid_time = sensor.last_valid_time

            # 2. Safety evaluation
            is_safe = safety.check(temp, app_state.last_valid_time, now)
            if not is_safe:
                app_state.state = "FAULT"
                app_state.power_on = False
                heater.off()
                leds.update("FAULT", duty_pct=0.0)
                await asyncio.sleep(1)
                continue

            # 3. Direct heater power control (sensor provides safety cutoff + telemetry)
            if app_state.power_on:
                app_state.state = "HEATING"
                heater.set_duty(app_state.power_pct)
            else:
                heater.off()
                if temp and temp > 35.0:
                    app_state.state = "COOLING"
                else:
                    app_state.state = "OFF"

            # 4. Update LEDs
            progress = 0.0
            if app_state.state == "HEATING" and temp is not None:
                progress = max(0.0, min(1.0, (temp - 20.0) / (cutoff - 20.0)))
            elif app_state.state == "COOLING" and temp is not None:
                progress = max(0.0, min(1.0, (temp - 25.0) / (cutoff - 25.0)))

            wifi_ok = (app_state.ip_address != "0.0.0.0")
            leds.update(app_state.state, progress=progress, duty_pct=heater.duty_pct, wifi_connected=wifi_ok)

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

        await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(main())
