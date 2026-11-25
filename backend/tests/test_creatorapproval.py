"""Unit tests for email-based Creator approval challenge format and signatures."""

import base64
import unittest

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from app.services.creatorapproval_service import canonical_payload, hash_payload

CHALLENGE = {
    "request_id": "cr_test",
    "action_type": "skillforge.publish",
    "target_ref": "iam.native.research.demo",
    "risk_level": "3",
    "summary": "Publish skill",
    "consequences": ["Skill can be activated"],
    "nonce": "nonce-value",
    "expires_at": "2026-11-25T12:00:00+00:00",
    "creator_email": "creator@iam.example",
}


class ChannelTests(unittest.IsolatedAsyncioTestCase):
    async def test_unknown_channel_rejected(self):
        from app.services.creatorapproval_service import (
            CreatorApprovalError,
            CreatorApprovalService,
        )

        service = CreatorApprovalService(None)
        with self.assertRaises(CreatorApprovalError):
            await service.create_request(
                action_type="test.action", summary="test", channel="carrier_pigeon"
            )


class ChallengeTests(unittest.TestCase):
    def test_canonical_payload_is_deterministic(self):
        other_order = dict(reversed(list(CHALLENGE.items())))
        self.assertEqual(canonical_payload(CHALLENGE), canonical_payload(other_order))

    def test_hash_changes_with_nonce(self):
        changed = dict(CHALLENGE, nonce="different-nonce")
        self.assertNotEqual(hash_payload(CHALLENGE), hash_payload(changed))

    def test_hash_is_lowercase_hex(self):
        value = hash_payload(CHALLENGE)
        self.assertEqual(len(value), 64)
        self.assertEqual(value, value.lower())


class SignatureTests(unittest.TestCase):
    def setUp(self):
        self.private = Ed25519PrivateKey.generate()
        self.public_bytes = self.private.public_key().public_bytes_raw()
        self.encoded_public = base64.b64encode(self.public_bytes).decode()
        self.digest = hash_payload(CHALLENGE)

    def _sign(self, decision: str) -> str:
        message = f"{self.digest}|{decision}".encode("utf-8")
        return base64.b64encode(self.private.sign(message)).decode()

    def test_signed_approval_verifies(self):
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

        signature = base64.b64decode(self._sign("approved"))
        Ed25519PublicKey.from_public_bytes(
            base64.b64decode(self.encoded_public)
        ).verify(signature, f"{self.digest}|approved".encode("utf-8"))

    def test_signature_cannot_be_reused_for_other_decision(self):
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

        key = Ed25519PublicKey.from_public_bytes(self.public_bytes)
        signature = base64.b64decode(self._sign("approved"))
        with self.assertRaises(InvalidSignature):
            key.verify(signature, f"{self.digest}|rejected".encode("utf-8"))

    def test_signature_cannot_be_reused_for_other_challenge(self):
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

        key = Ed25519PublicKey.from_public_bytes(self.public_bytes)
        signature = base64.b64decode(self._sign("approved"))
        other_digest = hash_payload(dict(CHALLENGE, nonce="other"))
        with self.assertRaises(InvalidSignature):
            key.verify(signature, f"{other_digest}|approved".encode("utf-8"))


if __name__ == "__main__":
    unittest.main()
