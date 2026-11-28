"""Declared settings must actually reach the services that use them."""

import unittest
from pathlib import Path
from unittest.mock import patch

from app.core.config import settings
from app.services.browser_service import BrowserService
from app.services.creator_email import EmailTransportError, SmtpTransport
from app.services.free_sandboxes.manager import FreeSandboxManager
from app.workers.arq_iics_worker import _threat_feed_minutes


class ConfigWiringTests(unittest.TestCase):
    def test_quota_safety_margin_comes_from_settings(self):
        with patch.object(settings, "free_sandbox_quota_safety_margin", 0.35):
            manager = FreeSandboxManager()
        self.assertAlmostEqual(manager.guard.safety_margin, 0.35)

    def test_threat_feed_interval_drives_cron(self):
        with patch.object(settings, "iics_threat_feed_interval_minutes", 20):
            self.assertEqual(_threat_feed_minutes(), {0, 20, 40})

    def test_browser_profile_root_is_used(self):
        with patch.object(settings, "browser_profile_root", "iam-profiles"):
            path = BrowserService._profile_path(
                object.__new__(BrowserService), "session-1"
            )
        self.assertEqual(path.parent, Path("iam-profiles"))

    def test_creator_email_domain_is_enforced(self):
        with (
            patch.object(settings, "creator_email_domain", "iam.example"),
            patch.object(settings, "creator_email", "creator@iam.example"),
        ):
            SmtpTransport._assert_creator_domain("creator@iam.example")
            with self.assertRaises(EmailTransportError):
                SmtpTransport._assert_creator_domain("other@example.com")


if __name__ == "__main__":
    unittest.main()
