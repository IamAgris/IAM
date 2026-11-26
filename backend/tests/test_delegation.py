"""Delegation gates: signed authority, independent review, fail-closed storage."""

import json
import unittest
import uuid
from unittest.mock import AsyncMock, patch

from app.core.config import settings
from app.models.memory import KnowledgeItem
from app.models.security import AuditEvent
from app.services import delegation


class FakeInference:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    async def chat(self, messages, *, model=None, temperature=0.7, **_kwargs):
        self.calls.append({"messages": messages, "model": model, "temperature": temperature})
        return {"choices": [{"message": {"content": self.responses.pop(0)}}]}


class FakeDB:
    def __init__(self):
        self.added = []
        self.commits = 0
        self.rollbacks = 0

    def add(self, obj):
        self.added.append(obj)
        if getattr(obj, "id", None) is None:
            obj.id = uuid.uuid4()

    async def flush(self):
        return None

    async def commit(self):
        self.commits += 1

    async def rollback(self):
        self.rollbacks += 1


def authorized(value=True):
    if value:
        return {
            "authorized": True,
            "authorization_id": "auth-123",
            "signer_id": "creator",
        }
    return {"authorized": False, "reason": "no signature"}


ACCEPT = json.dumps(
    {
        "verdict": "accept",
        "confidence": 0.8,
        "reason": "claim supported by context",
        "findings": ["Finding one", "Finding two"],
    }
)


class DelegationTests(unittest.IsolatedAsyncioTestCase):
    async def test_unauthorized_delegation_never_calls_a_provider(self):
        db = FakeDB()
        service = FakeInference(["specialist answer", ACCEPT])
        with patch.object(
            delegation.CreatorApprovalService,
            "check_authorization",
            new=AsyncMock(return_value=authorized(False)),
        ):
            result = await delegation.run(db, "analyse this", service=service)
        self.assertEqual(result.status, "rejected")
        self.assertEqual(service.calls, [])
        self.assertEqual(db.added, [])

    async def test_accepted_findings_are_stored_unverified_with_provenance(self):
        db = FakeDB()
        service = FakeInference(["specialist answer", ACCEPT])
        with patch.object(
            delegation.CreatorApprovalService,
            "check_authorization",
            new=AsyncMock(return_value=authorized()),
        ):
            result = await delegation.run(
                db, "analyse this", model="qwen3.5-9b", service=service
            )
        self.assertEqual(result.status, "accepted")
        self.assertEqual(result.verdict, "accept")
        self.assertEqual(len(result.knowledge_ids), 2)
        items = [item for item in db.added if isinstance(item, KnowledgeItem)]
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0].verification_status, "unverified")
        self.assertEqual(items[0].source, "delegate:qwen3.5-9b")
        self.assertTrue(items[0].metadata_["delegation"]["private_content_excluded"])
        self.assertTrue(any(isinstance(item, AuditEvent) for item in db.added))
        self.assertEqual(db.commits, 1)
        self.assertIn("Finding one", result.context_message())

    async def test_rejected_verification_stores_nothing(self):
        db = FakeDB()
        rejection = json.dumps(
            {"verdict": "reject", "reason": "unsupported", "findings": ["bad claim"]}
        )
        service = FakeInference(["specialist answer", rejection])
        with patch.object(
            delegation.CreatorApprovalService,
            "check_authorization",
            new=AsyncMock(return_value=authorized()),
        ):
            result = await delegation.run(db, "analyse this", service=service)
        self.assertEqual(result.status, "rejected")
        self.assertEqual(result.findings, [])
        self.assertEqual(db.added, [])
        self.assertEqual(db.commits, 0)

    async def test_malformed_review_fails_closed(self):
        db = FakeDB()
        service = FakeInference(["specialist answer", "this is not json"])
        with patch.object(
            delegation.CreatorApprovalService,
            "check_authorization",
            new=AsyncMock(return_value=authorized()),
        ):
            result = await delegation.run(db, "analyse this", service=service)
        self.assertEqual(result.status, "rejected")
        self.assertEqual(db.added, [])

    async def test_local_model_cannot_be_used_as_external_delegate(self):
        db = FakeDB()
        service = FakeInference(["unused", ACCEPT])
        with patch.object(
            delegation.CreatorApprovalService,
            "check_authorization",
            new=AsyncMock(return_value=authorized()),
        ):
            result = await delegation.run(
                db, "analyse this", model=settings.iam_primary_model, service=service
            )
        self.assertEqual(result.status, "rejected")
        self.assertEqual(service.calls, [])


if __name__ == "__main__":
    unittest.main()
