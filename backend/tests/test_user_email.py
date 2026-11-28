"""Unit tests for the opt-in user email carrier (OD-59 / Doc 39).

No database, network or real credentials are used. Secrets are never printed.
"""

import hashlib
import hmac
import unittest
from unittest.mock import patch

from app.api.routes.user_email import SIGNATURE_HEADER, verify_webhook_signature
from app.core.config import settings
from app.services.user_email_service import (
    UserEmailError,
    UserEmailService,
    _email_hash,
    _token_hash,
)


class WebhookSignatureTests(unittest.TestCase):
    def test_valid_signature(self):
        raw = b'{"message_id":"m1","email":"user@example.com","body":"hi"}'
        secret = "test-secret"
        provided = hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()
        self.assertTrue(verify_webhook_signature(raw, provided, secret))

    def test_tampered_body_rejected(self):
        raw = b'{"message_id":"m1","body":"hi"}'
        secret = "test-secret"
        provided = hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()
        self.assertFalse(verify_webhook_signature(raw + b" ", provided, secret))

    def test_missing_secret_or_signature_rejected(self):
        self.assertFalse(verify_webhook_signature(b"x", "", "secret"))
        self.assertFalse(verify_webhook_signature(b"x", "abc", ""))

    def test_header_constant(self):
        self.assertEqual(SIGNATURE_HEADER, "X-User-Email-Signature")


class HelperTests(unittest.TestCase):
    def test_hashes_are_one_way_and_normalised(self):
        self.assertEqual(_email_hash(" User@Example.COM "), _email_hash("user@example.com"))
        self.assertNotEqual(_email_hash("a@example.com"), _email_hash("b@example.com"))
        self.assertEqual(_token_hash("abc"), hashlib.sha256(b"abc").hexdigest())

    def test_address_mask_never_returns_full_local_part(self):
        masked = UserEmailService._mask("alice@example.com")
        self.assertEqual(masked, "al***@example.com")
        self.assertNotIn("alice", masked)


class ValidationTests(unittest.TestCase):
    def setUp(self):
        self.service = UserEmailService(db=None)
        self.patches = [
            patch.object(settings, "user_email_enabled", True),
            patch.object(settings, "user_email_domain", "iamagris.co.za"),
            patch.object(settings, "user_email_max_body_chars", 50),
        ]
        for item in self.patches:
            item.start()
        self.addCleanup(self._stop)

    def _stop(self):
        for item in reversed(self.patches):
            item.stop()

    def test_rejects_public_mailbox_outside_domain(self):
        with self.assertRaises(UserEmailError):
            self.service._normalise_address("someone@gmail.com")

    def test_accepts_subdomain_of_permitted_domain(self):
        self.assertEqual(
            self.service._normalise_address(" User@Chat.IAMagris.co.za "),
            "user@chat.iamagris.co.za",
        )

    def test_rejects_malformed_address(self):
        with self.assertRaises(UserEmailError):
            self.service._normalise_address("not-an-address")

    def test_body_is_bounded_and_non_empty(self):
        with self.assertRaises(UserEmailError):
            self.service._clean_body("   ")
        self.assertEqual(len(self.service._clean_body("x" * 500)), 50)


class DisabledByDefaultTests(unittest.TestCase):
    def test_no_external_action_while_disabled(self):
        with patch.object(settings, "user_email_enabled", False):
            service = UserEmailService(db=None)
            with self.assertRaises(UserEmailError):
                service._require_enabled()
            with self.assertRaises(UserEmailError):
                import asyncio

                asyncio.run(service._deliver("user@example.com", "subject", "body"))


if __name__ == "__main__":
    unittest.main()
