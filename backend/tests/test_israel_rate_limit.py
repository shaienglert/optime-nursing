"""Owner 2026-11-19: public family actions are rate limited so nobody can flood a facility."""
import os
import unittest
from unittest import mock

from app.services import israel_rate_limit as rl


class RateLimitUnitTests(unittest.TestCase):
    def setUp(self):
        rl.reset()

    def test_per_address_hour_and_day(self):
        t = 1_000_000.0
        for i in range(5):
            self.assertTrue(rl.check([("inquiry_ip", "1.1.1.1")], now=t + i))
        self.assertFalse(rl.check([("inquiry_ip", "1.1.1.1")], now=t + 10))
        self.assertTrue(rl.check([("inquiry_ip", "2.2.2.2")], now=t + 10))  # other families unaffected
        later = t + rl.HOUR + 1
        for i in range(5):
            self.assertTrue(rl.check([("inquiry_ip", "1.1.1.1")], now=later + i))
        for i in range(5):
            self.assertTrue(rl.check([("inquiry_ip", "1.1.1.1")], now=later + rl.HOUR + 1 + i))
        self.assertFalse(rl.check([("inquiry_ip", "1.1.1.1")], now=later + 2 * rl.HOUR + 2))  # 15 per day

    def test_refused_request_is_not_counted_on_any_key(self):
        t = 2_000_000.0
        for i in range(3):
            self.assertTrue(rl.check([("inquiry_ip_facility", "a|F1"), ("inquiry_facility", "F1")], now=t + i))
        self.assertFalse(rl.check([("inquiry_ip_facility", "a|F1"), ("inquiry_facility", "F1")], now=t + 5))
        self.assertEqual(len(rl._hits[("inquiry_facility", "F1")]), 3)

    def test_address_prefers_site_proxy_header(self):
        self.assertEqual(rl.client_address({"x-oomnik-client-ip": "9.9.9.9", "x-forwarded-for": "10.0.0.1"}, "x"), "9.9.9.9")
        self.assertEqual(rl.client_address({"x-forwarded-for": "8.8.8.8, 10.0.0.1"}, "x"), "8.8.8.8")
        self.assertEqual(rl.client_address({}, "7.7.7.7"), "7.7.7.7")

    def test_can_be_disabled_for_load_tests(self):
        with mock.patch.dict(os.environ, {"OOMNIK_RATE_LIMIT_DISABLED": "1"}):
            for _ in range(50):
                self.assertTrue(rl.check([("inquiry_ip", "z")]))


def test_allowed_counts_nothing_and_record_counts():
    rl.reset()
    keys = [("inquiry_ip_facility", "q|F")]
    for _ in range(10):
        assert rl.allowed(keys)
    for _ in range(3):
        rl.record(keys)
    assert not rl.allowed(keys)
