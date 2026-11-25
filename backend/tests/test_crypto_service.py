"""Unit tests for field-level encryption."""

import base64
import os
import unittest
from unittest.mock import patch

from app.core.config import settings
from app.services.crypto_service import PREFIX, CryptoService


class CryptoTests(unittest.TestCase):
    def test_round_trip(self):
        crypto = CryptoService()
        encrypted = crypto.encrypt("private message")
        self.assertTrue(encrypted.startswith(PREFIX))
        self.assertEqual(crypto.decrypt(encrypted), "private message")

    def test_encryption_is_non_deterministic(self):
        crypto = CryptoService()
        self.assertNotEqual(crypto.encrypt("same"), crypto.encrypt("same"))

    def test_legacy_plaintext_is_readable(self):
        self.assertEqual(CryptoService().decrypt("old plaintext"), "old plaintext")

    def test_placeholder_key_is_flagged(self):
        with patch.object(settings, "encryption_key", "change-me-to-a-32-byte-base64-key"):
            self.assertFalse(CryptoService().key_is_secure)

    def test_real_key_is_accepted(self):
        key = base64.b64encode(os.urandom(32)).decode()
        with patch.object(settings, "encryption_key", key):
            self.assertTrue(CryptoService().key_is_secure)
