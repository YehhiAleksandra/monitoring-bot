import unittest
from datetime import datetime, timedelta, timezone

from monitoring.core import (
    agent_token,
    http_ok,
    resource_level,
    ssl_days_left,
    ssl_level,
    token_matches,
)


class AgentTokenTest(unittest.TestCase):
    def test_token_is_stable_and_hex(self):
        token = agent_token("secret")
        self.assertEqual(token, agent_token("secret"))
        self.assertEqual(len(token), 64)
        int(token, 16)

    def test_empty_or_foreign_token_is_rejected(self):
        self.assertTrue(token_matches("secret", agent_token("secret")))
        self.assertFalse(token_matches("secret", ""))
        self.assertFalse(token_matches("secret", agent_token("other")))


class HttpStatusTest(unittest.TestCase):
    def test_server_errors_and_missing_status_fail(self):
        self.assertTrue(http_ok(200))
        self.assertTrue(http_ok(404))
        self.assertFalse(http_ok(500))
        self.assertFalse(http_ok(503))
        self.assertFalse(http_ok(None))


class SslTest(unittest.TestCase):
    NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)

    def test_days_left_rounds_down_and_never_negative(self):
        later = (self.NOW + timedelta(days=29, hours=23)).strftime(
            "%b %d %H:%M:%S %Y GMT"
        )
        self.assertEqual(ssl_days_left(later, self.NOW), 29)
        past = (self.NOW - timedelta(days=5)).strftime("%b %d %H:%M:%S %Y GMT")
        self.assertEqual(ssl_days_left(past, self.NOW), 0)

    def test_levels_follow_thresholds(self):
        self.assertEqual(ssl_level(None, 30, 14), "unknown")
        self.assertEqual(ssl_level(7, 30, 14), "critical")
        self.assertEqual(ssl_level(14, 30, 14), "critical")
        self.assertEqual(ssl_level(15, 30, 14), "warn")
        self.assertEqual(ssl_level(30, 30, 14), "warn")
        self.assertEqual(ssl_level(31, 30, 14), "ok")


class ResourceTest(unittest.TestCase):
    def test_free_percent_equal_to_threshold_warns(self):
        self.assertEqual(resource_level(21, 20), "ok")
        self.assertEqual(resource_level(20, 20), "warn")
        self.assertEqual(resource_level(5, 20), "warn")


if __name__ == "__main__":
    unittest.main()
