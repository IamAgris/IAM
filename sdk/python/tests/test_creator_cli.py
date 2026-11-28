"""Unit tests for the Creator CLI signing contract (no network required)."""

import unittest

from iam_sdk.creator_cli import build_parser, clean_signature, signing_message
from iam_sdk.types import IAMOptions

CHALLENGE = {
    "request_id": "cr_test",
    "challenge_hash": "abc123def456",
    "signer_id": "creator-hardware-signer",
}


class SigningMessageTests(unittest.TestCase):
    def test_exact_bytes(self):
        self.assertEqual(signing_message(CHALLENGE, "approved"), "abc123def456|approved")
        self.assertEqual(signing_message(CHALLENGE, "rejected"), "abc123def456|rejected")

    def test_invalid_decision_rejected(self):
        with self.assertRaises(ValueError):
            signing_message(CHALLENGE, "maybe")

    def test_missing_hash_rejected(self):
        with self.assertRaises(ValueError):
            signing_message({"request_id": "cr_test"}, "approved")

    def test_challenge_for_another_request_rejected(self):
        with self.assertRaises(ValueError):
            signing_message(CHALLENGE, "approved", "cr_other")

    def test_matching_request_id_accepted(self):
        self.assertEqual(
            signing_message(CHALLENGE, "approved", "cr_test"), "abc123def456|approved"
        )


class SignatureTests(unittest.TestCase):
    def test_valid_base64_with_whitespace(self):
        value = "dGVzdHNpZ25hdHVyZWxvbmVub3VnaA=="
        self.assertEqual(clean_signature(f"  {value}\n"), value)

    def test_invalid_base64_rejected(self):
        with self.assertRaises(ValueError):
            clean_signature("not-base64!")

    def test_short_signature_rejected(self):
        with self.assertRaises(ValueError):
            clean_signature("YQ==")


class CloudflareAccessTests(unittest.TestCase):
    def test_service_token_fields_are_supported(self):
        options = IAMOptions(
            endpoint="https://core.example.com",
            access_client_id="access-id",
            access_client_secret="access-secret",
        )
        self.assertEqual(options.access_client_id, "access-id")
        self.assertEqual(options.access_client_secret, "access-secret")


class ParserTests(unittest.TestCase):
    def test_decide_requires_explicit_decision(self):
        with self.assertRaises(SystemExit):
            build_parser().parse_args(["decide", "cr_test", "--signature", "x", "--signer-id", "s"])

    def test_sign_supports_dry_run(self):
        args = build_parser().parse_args([
            "sign", "cr_test", "--approve", "--signer", "python sign.py", "--dry-run"
        ])
        self.assertTrue(args.dry_run)
        self.assertTrue(args.approve)


if __name__ == "__main__":
    unittest.main()
