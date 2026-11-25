"""Unit tests for IAM→Creator email communication (no DB or network required)."""

import unittest

from app.models.creatorapproval import CreatorMessage
from app.services.creator_communication import (
    CreatorCommunicationError,
    CreatorCommunicationService,
)


class PurposeTests(unittest.TestCase):
    def test_question_and_status_allowed(self):
        self.assertEqual(CreatorCommunicationService.classify_purpose("question"), "question")
        self.assertEqual(
            CreatorCommunicationService.classify_purpose("status_update"), "status_update"
        )

    def test_approval_purpose_rejected(self):
        for purpose in ("approval", "decision", "authorization", "signed_request"):
            with self.assertRaises(CreatorCommunicationError):
                CreatorCommunicationService.classify_purpose(purpose)


class AuthorityBoundaryTests(unittest.TestCase):
    def test_message_is_not_authority_bearing_by_default(self):
        self.assertFalse(CreatorMessage().authority_bearing)

    def test_database_constraint_forbids_authority(self):
        names = {c.name for c in CreatorMessage.__table_args__}
        self.assertIn("ck_creator_message_no_authority", names)

    def test_communication_service_has_no_decision_method(self):
        self.assertFalse(hasattr(CreatorCommunicationService, "decide"))
        self.assertFalse(hasattr(CreatorCommunicationService, "create_authorization"))


if __name__ == "__main__":
    unittest.main()
