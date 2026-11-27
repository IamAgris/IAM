"""Unit tests for Creator email transports and gateway authentication."""

import asyncio
import json
import unittest

from app.core.config import settings
from app.services.creator_email import (
    EmailTransportError,
    LogTransport,
    transport_from_settings,
)
from app.services.creator_gateway import (
    verify_gateway_signature,
)

BODY = json.dumps(
    {
        "request_id": "cr_test",
        "decision": "approved",
        "signature": "abc",
        "signer_id": "signer-1",
    }
).encode("utf-8")


class GatewaySignatureTests(unittest.TestCase):
    def setUp(self):
        self.secret = "gateway-secret"

    def _sign(self, body: bytes, secret: str = None) -> str:
        import hashlib
        import hmac

        return hmac.new(
            (secret or self.secret).encode("utf-8"), body, hashlib.sha256
        ).hexdigest()

    def test_valid_signature(self):
        self.assertTrue(
            verify_gateway_signature(BODY, self._sign(BODY), self.secret)
        )

    def test_wrong_secret_rejected(self):
        self.assertFalse(
            verify_gateway_signature(BODY, self._sign(BODY, "other"), self.secret)
        )

    def test_tampered_body_rejected(self):
        self.assertFalse(
            verify_gateway_signature(BODY + b" ", self._sign(BODY), self.secret)
        )

    def test_empty_secret_disables_gateway(self):
        self.assertFalse(verify_gateway_signature(BODY, self._sign(BODY), ""))

    def test_missing_header_rejected(self):
        self.assertFalse(verify_gateway_signature(BODY, "", self.secret))


class TransportTests(unittest.TestCase):
    def test_log_transport_sends_nothing(self):
        result = asyncio.run(
            LogTransport().send(
                {"request_id": "cr_test", "to": "creator@iam.example", "subject": "Test"}
            )
        )
        self.assertEqual(result["status"], "sent")
        self.assertFalse(result["delivered_externally"])

    def test_default_transport_is_log(self):
        previous = settings.creator_email_transport
        try:
            settings.creator_email_transport = "log"
            self.assertIsInstance(transport_from_settings(), LogTransport)
        finally:
            settings.creator_email_transport = previous

    def test_unknown_transport_rejected(self):
        previous = settings.creator_email_transport
        try:
            settings.creator_email_transport = "carrier-pigeon"
            with self.assertRaises(EmailTransportError):
                transport_from_settings()
        finally:
            settings.creator_email_transport = previous


if __name__ == "__main__":
    unittest.main()
