import unittest
from datetime import datetime, timedelta, timezone
from scripts.collect import should_check_feed, RETRY_DAYS

class FeedRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.feed = {"feed_url": "https://example.org/rss"}
        self.now = datetime(2026, 11, 2, tzinfo=timezone.utc)

    def test_healthy_feed_runs(self):
        self.assertTrue(should_check_feed(self.feed, {self.feed["feed_url"]: {"fail_count": 2}}, self.now))

    def test_paused_feed_waits_for_cooldown(self):
        state = {self.feed["feed_url"]: {"fail_count": 3, "checked_at": (self.now - timedelta(days=1)).isoformat()}}
        self.assertFalse(should_check_feed(self.feed, state, self.now))

    def test_paused_feed_recovers_after_cooldown(self):
        state = {self.feed["feed_url"]: {"fail_count": 3, "checked_at": (self.now - timedelta(days=RETRY_DAYS)).isoformat()}}
        self.assertTrue(should_check_feed(self.feed, state, self.now))

    def test_old_state_without_timestamp_is_retried(self):
        self.assertTrue(should_check_feed(self.feed, {self.feed["feed_url"]: {"fail_count": 3}}, self.now))

if __name__ == "__main__":
    unittest.main()
