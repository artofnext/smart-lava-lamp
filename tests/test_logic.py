import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "firmware")))

from pid import PID
from safety import SafetyLatch
from dst import is_dst_london, _last_sunday
from patterns import evaluate_pattern
from config import Config
from web_server import constant_time_compare

class TestControllerLogic(unittest.TestCase):
    def test_pid_clamping_and_response(self):
        pid = PID(kp=10.0, ki=1.0, kd=0.0, out_min=0.0, out_max=100.0)
        # Big error (50 - 40 = 10) -> P term = 100 -> clamped to 100
        out = pid.update(setpoint=50.0, measurement=40.0, dt=1.0)
        self.assertEqual(out, 100.0)

        # Above setpoint (50 - 60 = -10) -> clamped to 0
        pid.reset()
        out = pid.update(setpoint=50.0, measurement=60.0, dt=1.0)
        self.assertEqual(out, 0.0)

    def test_safety_latch(self):
        safety = SafetyLatch(cutoff_temp=200.0, timeout_s=5.0)

        # Normal condition
        self.assertTrue(safety.check(temp=100.0, last_valid_time=100.0, current_time=102.0))
        self.assertIsNone(safety.fault)

        # Cutoff exceeded (200C)
        self.assertFalse(safety.check(temp=200.5, last_valid_time=102.0, current_time=102.5))
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

    def test_dst_boundaries(self):
        # 2026: March 29 is the last Sunday of March
        sun_mar_2026 = _last_sunday(2026, 3)
        self.assertEqual(sun_mar_2026, 29)

        # March 29 at 00:00 UTC -> Winter (False)
        self.assertFalse(is_dst_london(2026, 3, 29, 0))
        # March 29 at 01:00 UTC -> Summer (True)
        self.assertTrue(is_dst_london(2026, 3, 29, 1))

        # July -> Summer (True)
        self.assertTrue(is_dst_london(2026, 7, 15, 12))

        # October 25 is the last Sunday of October 2026
        sun_oct_2026 = _last_sunday(2026, 10)
        self.assertEqual(sun_oct_2026, 25)
        # October 25 at 00:59 UTC -> Summer (True)
        self.assertTrue(is_dst_london(2026, 10, 25, 0))
        # October 25 at 01:00 UTC -> Winter (False)
        self.assertFalse(is_dst_london(2026, 10, 25, 1))

    def test_pattern_interpolation(self):
        points = [[0, 50.0], [20, 54.0]]
        self.assertAlmostEqual(evaluate_pattern(points, 0), 50.0)
        self.assertAlmostEqual(evaluate_pattern(points, 10), 52.0)
        self.assertAlmostEqual(evaluate_pattern(points, 20), 54.0)

    def test_token_auth(self):
        self.assertTrue(constant_time_compare("secret123", "secret123"))
        self.assertFalse(constant_time_compare("secret123", "wrong"))
        self.assertFalse(constant_time_compare("secret123", None))
        self.assertFalse(constant_time_compare("", ""))

    def test_heater_clamping(self):
        import unittest.mock as mock
        sys.modules["machine"] = mock.MagicMock()
        from heater import Heater
        h = Heater(4, max_duty=80, freq=10)
        h.set_duty(100.0)
        self.assertEqual(h.duty_pct, 80.0)
        h.set_duty(-10.0)
        self.assertEqual(h.duty_pct, 0.0)
        h.off()
        self.assertEqual(h.duty_pct, 0.0)

if __name__ == "__main__":
    unittest.main()
