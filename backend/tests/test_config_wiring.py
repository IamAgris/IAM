"""Declared settings must actually reach the services that use them."""

import unittest
from unittest.mock import patch

from app.core.config import settings
from app.services.free_sandboxes.manager import FreeSandboxManager


class ConfigWiringTests(unittest.TestCase):
    def test_quota_safety_margin_comes_from_settings(self):
        with patch.object(settings, "free_sandbox_quota_safety_margin", 0.35):
            manager = FreeSandboxManager()
        self.assertAlmostEqual(manager.guard.safety_margin, 0.35)


if __name__ == "__main__":
    unittest.main()
