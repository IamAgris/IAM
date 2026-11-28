"""OD-03/OD-04 tests: legacy owner grants are historical, never authority."""

import unittest
import uuid
from unittest.mock import patch

from fastapi import HTTPException

from app.api.routes.ownerauth import GrantRequest, grant
from app.models.ownerauth import OwnerAuthorization
from app.orchestration.autonomy_graph import check_authority
from app.services.ownerauth_service import (
    LegacyAuthorityError,
    OwnerAuthService,
)


class FakeResult:
    def __init__(self, rows):
        self.rows = rows

    def scalars(self):
        return self

    def all(self):
        return self.rows

    def scalar_one_or_none(self):
        return self.rows[0] if self.rows else None


class FakeDB:
    def __init__(self, rows=None):
        self.rows = list(rows or [])

    def add(self, obj):
        if obj not in self.rows:
            if getattr(obj, "id", None) is None:
                obj.id = uuid.uuid4()
            self.rows.append(obj)

    async def commit(self):
        return None

    async def execute(self, statement):
        entity = statement.column_descriptions[0]["entity"]
        return FakeResult([row for row in self.rows if isinstance(row, entity)])


def legacy_grant():
    return OwnerAuthorization(
        id=uuid.uuid4(),
        action_type="spend_approved_budget",
        max_authority_level="4",
        spending_limit_usd=1000,
        can_create_accounts=True,
        can_publish_externally=True,
        can_modify_own_security=True,
        scope={"legacy": True},
        is_active=True,
        granted_by="owner",
    )


class ReconciliationTests(unittest.IsolatedAsyncioTestCase):
    async def test_existing_grant_cannot_authorise(self):
        service = OwnerAuthService(FakeDB([legacy_grant()]))
        result = await service.check_authorization("spend_approved_budget", "4")
        self.assertFalse(result["authorized"])
        self.assertEqual(result["legacy_grants_found"], 1)
        self.assertEqual(result["authority_source"], "creator_signed_request_only")

    async def test_new_grants_rejected(self):
        service = OwnerAuthService(FakeDB())
        with self.assertRaises(LegacyAuthorityError):
            await service.grant_authorization("spend_approved_budget", "4", 100)

    async def test_route_returns_gone(self):
        with self.assertRaises(HTTPException) as caught:
            await grant(GrantRequest(action_type="spend_approved_budget"), FakeDB())
        self.assertEqual(caught.exception.status_code, 410)

    async def test_listing_marks_records_as_non_authoritative(self):
        rows = await OwnerAuthService(FakeDB([legacy_grant()])).list_authorizations()
        self.assertFalse(rows[0]["authority_source"])

    async def test_revocation_still_works(self):
        row = legacy_grant()
        service = OwnerAuthService(FakeDB([row]))
        self.assertTrue(await service.revoke_authorization(row.id))
        self.assertFalse(row.is_active)

    async def test_autonomy_graph_uses_governance_not_legacy_grants(self):
        class FakeGovernance:
            def __init__(self, _db):
                pass

            async def check_authority(self, action, level):
                return {"permitted": True, "required_level": level}

        class SessionContext:
            async def __aenter__(self):
                return FakeDB()

            async def __aexit__(self, *_args):
                return None

        with patch("app.core.database.get_session_factory", lambda: lambda: SessionContext()), patch(
            "app.services.governance_service.GovernanceService", FakeGovernance
        ):
            result = await check_authority({})
        self.assertTrue(result["authority_check"]["permitted"])
        self.assertEqual(
            result["authority_check"]["authority_source"],
            "governance_boundary_or_signed_creator",
        )


if __name__ == "__main__":
    unittest.main()
