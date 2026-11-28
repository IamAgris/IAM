"""Legal authorisation must verify signed Creator authority, not trust a string."""

import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app.services.legal_service import LegalError, LegalService


class FakeResult:
    def __init__(self, value=None, values=None):
        self.value = value
        self.values = values or []

    def scalar_one_or_none(self):
        return self.value

    def scalars(self):
        return SimpleNamespace(all=lambda: self.values)


class FakeDB:
    def __init__(self, change, impacts=None):
        self.change = change
        self.impacts = impacts or []
        self.added = []
        self.commits = 0
        self.calls = 0

    async def execute(self, statement):
        self.calls += 1
        if self.calls == 1:
            return FakeResult(value=self.change)
        return FakeResult(values=self.impacts)

    def add(self, obj):
        self.added.append(obj)

    async def commit(self):
        self.commits += 1


def change(stage="recommend"):
    return SimpleNamespace(
        id="change-1",
        lifecycle_stage=stage,
        creator_approval_reference=None,
        professional_review_reference=None,
        evidence={},
    )


AUTH_ID = "11111111-1111-4111-8111-111111111111"


def authority(authorized=True):
    if authorized:
        return {"authorized": True, "authorization_id": AUTH_ID, "signer_id": "creator"}
    return {"authorized": False, "reason": "no active authorization"}


class LegalAuthorityTests(unittest.IsolatedAsyncioTestCase):
    async def test_authorise_rejects_missing_signed_authority(self):
        db = FakeDB(change())
        with patch(
            "app.services.creatorapproval_service.CreatorApprovalService.check_authorization",
            new_callable=AsyncMock,
            return_value=authority(False),
        ):
            with self.assertRaisesRegex(LegalError, "no active signed Creator authorization"):
                await LegalService(db).authorise("change-1", "fake-reference")

    async def test_authorise_rejects_reference_that_does_not_match_signed_authority(self):
        db = FakeDB(change())
        with patch(
            "app.services.creatorapproval_service.CreatorApprovalService.check_authorization",
            new_callable=AsyncMock,
            return_value=authority(True),
        ) as check:
            with self.assertRaisesRegex(LegalError, "does not match"):
                await LegalService(db).authorise("change-1", "some-other-reference")
        check.assert_awaited_once()
        self.assertTrue(any(kwargs.get("target_ref") == "legal_change:change-1" for _, kwargs in check.await_args_list))

    async def test_authorise_stores_verified_reference_and_audits(self):
        item = change()
        db = FakeDB(item)
        with patch(
            "app.services.creatorapproval_service.CreatorApprovalService.check_authorization",
            new_callable=AsyncMock,
            return_value=authority(True),
        ):
            result = await LegalService(db).authorise("change-1", AUTH_ID)
        self.assertEqual(result["lifecycle_stage"], "authorise")
        self.assertEqual(item.creator_approval_reference, AUTH_ID)
        self.assertTrue(any(getattr(obj, "event_type", "") == "legal_change_authorised" for obj in db.added))

    async def test_high_risk_still_requires_professional_review(self):
        impact = SimpleNamespace(risk_level="critical")
        db = FakeDB(change(), impacts=[impact])
        with patch(
            "app.services.creatorapproval_service.CreatorApprovalService.check_authorization",
            new_callable=AsyncMock,
            return_value=authority(True),
        ):
            with self.assertRaisesRegex(LegalError, "qualified professional review"):
                await LegalService(db).authorise("change-1", AUTH_ID)


if __name__ == "__main__":
    unittest.main()
