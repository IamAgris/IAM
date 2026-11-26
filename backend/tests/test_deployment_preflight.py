"""Unit tests for deployment configuration checks."""

import base64
import os
import tempfile
import unittest
from unittest.mock import patch

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from app.core.config import Settings, settings
from app.services.deployment_preflight import check_deployment


class PreflightTests(unittest.TestCase):
    def test_missing_creator_config_is_blocking(self):
        with (
            patch.object(settings, "creator_email", ""),
            patch.object(settings, "creator_public_key", ""),
            patch.object(settings, "creator_gateway_secret", ""),
            patch.object(settings, "creator_email_transport", "log"),
            patch.object(settings, "artex_enabled", False),
        ):
            report = check_deployment()
        self.assertFalse(report["ready"])
        for name in ("creator_email", "creator_public_key", "creator_gateway_secret"):
            self.assertIn(name, report["blockers"])

    def test_configured_deployment_is_ready_and_redacted(self):
        key = base64.b64encode(
            Ed25519PrivateKey.generate().public_key().public_bytes_raw()
        ).decode()
        secret = "super-secret-gateway-value"
        with (
            patch.object(settings, "creator_email", "creator@iam.example"),
            patch.object(settings, "creator_public_key", key),
            patch.object(settings, "creator_gateway_secret", secret),
            patch.object(settings, "creator_email_transport", "log"),
            patch.object(settings, "artex_enabled", False),
            patch.dict(os.environ, {"IAM_BOOTSTRAP_API_KEY": "bootstrap-secret"}),
        ):
            report = check_deployment()
        self.assertTrue(report["ready"], report)
        serialised = repr(report)
        self.assertNotIn(secret, serialised)
        self.assertNotIn("bootstrap-secret", serialised)

    def test_docker_secret_file_is_loaded(self):
        with tempfile.NamedTemporaryFile("w", delete=False, encoding="utf-8") as tmp:
            tmp.write("secret-from-file\n")
            path = tmp.name
        try:
            with patch.dict(os.environ, {"APP_SECRET_KEY_FILE": path}):
                loaded = Settings()
            self.assertEqual(loaded.app_secret_key, "secret-from-file")
        finally:
            os.unlink(path)

    def test_smtp_requires_password_environment(self):
        with (
            patch.object(settings, "creator_email", "creator@iam.example"),
            patch.object(
                settings,
                "creator_public_key",
                base64.b64encode(
                    Ed25519PrivateKey.generate().public_key().public_bytes_raw()
                ).decode(),
            ),
            patch.object(settings, "creator_gateway_secret", "secret"),
            patch.object(settings, "creator_email_transport", "smtp"),
            patch.object(settings, "creator_smtp_host", "smtp.example.com"),
            patch.object(settings, "creator_email_from", "iam@example.com"),
            patch.dict(os.environ, {}, clear=True),
        ):
            report = check_deployment()
        self.assertFalse(report["ready"])
        self.assertIn("creator_smtp_password", report["blockers"])


if __name__ == "__main__":
    unittest.main()
