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

if __name__ == "__main__":
    unittest.main()
