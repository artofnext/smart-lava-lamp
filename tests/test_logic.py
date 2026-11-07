import unittest
import unittest.mock as mock
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "firmware")))

from safety import SafetyLatch
from config import Config
from web_server import constant_time_compare

class TestControllerLogic(unittest.TestCase):
    def test_safety_latch(self):
        safety = SafetyLatch(cutoff_temp=100.0, timeout_s=5.0)

        # Normal condition
        self.assertTrue(safety.check(temp=80.0, last_valid_time=100.0, current_time=102.0))
        self.assertIsNone(safety.fault)

        # Cutoff exceeded (100C)
        self.assertFalse(safety.check(temp=100.5, last_valid_time=102.0, current_time=102.5))
        self.assertIsNotNone(safety.fault)
        self.assertIn("Over-temperature", safety.fault)

        # Reset unconditionally clears the fault latch
        self.assertTrue(safety.reset_fault())
        self.assertIsNone(safety.fault)

        # Timeout trips latch if timeout_s > 0
        self.assertFalse(safety.check(temp=48.0, last_valid_time=100.0, current_time=106.0))
        self.assertIn("timeout", safety.fault.lower())

        # Single None within timeout window does NOT trip latch
        safety.fault = None
        self.assertTrue(safety.check(temp=None, last_valid_time=100.0, current_time=102.0))
        self.assertIsNone(safety.fault)

    def test_token_auth(self):
        self.assertTrue(constant_time_compare("secret123", "secret123"))
        self.assertFalse(constant_time_compare("secret123", "wrong"))
        self.assertFalse(constant_time_compare("secret123", None))
        self.assertFalse(constant_time_compare("", ""))

    def test_heater_clamping(self):
        sys.modules["machine"] = mock.MagicMock()
        from heater import Heater
        h = Heater(4, max_duty=80, freq=10)
        h.set_duty(100.0)
        self.assertEqual(h.duty_pct, 80.0)
        h.set_duty(-10.0)
        self.assertEqual(h.duty_pct, 0.0)
        h.off()
        self.assertEqual(h.duty_pct, 0.0)

    def test_led_modes_and_heater_override(self):
        sys.modules["machine"] = mock.MagicMock()
        sys.modules["neopixel"] = mock.MagicMock()
        from leds import LEDController, temp_to_rgb

        # Temperature keyframes
        self.assertEqual(temp_to_rgb(8.0), (220, 235, 255))   # <= 10C cold white
        self.assertEqual(temp_to_rgb(15.0), (0, 255, 50))     # 15C green
        self.assertEqual(temp_to_rgb(25.0), (0, 100, 255))    # 25C cool blue
        self.assertEqual(temp_to_rgb(40.0), (160, 0, 220))    # 40C purple
        self.assertEqual(temp_to_rgb(55.0), (255, 110, 0))    # 55C orange
        self.assertEqual(temp_to_rgb(65.0), (255, 15, 0))     # >= 60C lava red

        # Heater-active forces LED ring ON even if user set on=False
        leds = LEDController(6, {"on": False, "brightness": 50, "mode": "solid", "color": [200, 100, 0]})
        leds.step(0.04, 30.0, heater_on=False)
        self.assertEqual(leds._last_out, (0, 0, 0))
        leds.step(0.04, 30.0, heater_on=True)
        self.assertEqual(leds._last_out, (100, 50, 0))
        self.assertTrue(leds.to_dict(heater_on=True)["on"])

        # Flame mode updates per-pixel buffer and writes
        leds.mode = "flame"
        leds.step(0.04, 30.0, heater_on=True)
        self.assertIsNone(leds._last_out)
        self.assertEqual(len(leds.heat), 16)

    def test_boot_warmup_and_manual_override(self):
        sys.modules["machine"] = mock.MagicMock()
        sys.modules["network"] = mock.MagicMock()
        sys.modules["neopixel"] = mock.MagicMock()
        sys.modules["onewire"] = mock.MagicMock()
        sys.modules["ds18x20"] = mock.MagicMock()
        from heater import Heater
        from leds import LEDController
        from main import AppState

        cfg = mock.MagicMock()
        cfg.get.side_effect = lambda k, d=None: {"mode": "rainbow", "brightness": 50} if k == "led" else d

        heater = Heater(4, max_duty=100, freq=10)
        safety = SafetyLatch(cutoff_temp=200.0)
        leds = LEDController(6, {"mode": "rainbow", "brightness": 50})

        # 1. Boot state: heater ON at 100%, LED forced to "temp" while remembering "rainbow"
        state = AppState(cfg, heater, safety, leds)
        self.assertTrue(state.power_on)
        self.assertEqual(state.power_pct, 100.0)
        self.assertEqual(heater.duty_pct, 100.0)
        self.assertEqual(leds.mode, "temp")

        # Below 65C: stays in warmup
        state.check_warmup(60.0)
        self.assertEqual(state.power_pct, 100.0)
        self.assertEqual(leds.mode, "temp")

        # Reaching 65C: switches heater to 75% and LED mode to saved "rainbow"
        state.check_warmup(65.0)
        self.assertEqual(state.power_pct, 75.0)
        self.assertEqual(heater.duty_pct, 75.0)
        self.assertEqual(leds.mode, "rainbow")

        # 2. Manual override before 65C prevents 65C transition from overwriting manual choices
        leds2 = LEDController(6, {"mode": "rainbow", "brightness": 50})
        state2 = AppState(cfg, heater, safety, leds2)
        state2.set_power_pct(50.0)
        state2.update_led({"mode": "solid"})
        state2.check_warmup(66.0)
        self.assertEqual(state2.power_pct, 50.0)
        self.assertEqual(leds2.mode, "solid")

if __name__ == "__main__":
    unittest.main()
