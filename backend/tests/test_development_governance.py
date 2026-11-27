"""WS-04 tests: protected deployments require tested changes and signed authority."""

import unittest
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from app.services.development_governance import (
    DeploymentGateDenied,
    is_protected_environment,
    verify_protected_deployment,
)

PROJECT_ID = uuid.uuid4()


class FakeResult:
    def __init__(self, rows):
        self.rows = rows

    def scalars(self):
        return self

    def all(self):
        return self.rows


class QueuedDB:
    """Returns query results in call order: code changes, then authorizations."""

    def __init__(self, *results):
        self.results = list(results)

    async def execute(self, _statement):
        return self.results.pop(0)


def change(status="tested", project_id=PROJECT_ID, change_id=None):
    return type(
        "CodeChange",
        (),
        {
            "id": change_id or uuid.uuid4(),
            "project_id": project_id,
            "status": status,
        },
    )()


def authorization(**overrides):
    values = dict(
        id=uuid.uuid4(),
        is_active=True,
        revoked_at=None,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        target_ref=str(PROJECT_ID),
        signer_id="creator-signer",
    )
    values.update(overrides)
    return type("Authorization", (), values)()


def approvals_for(row):
    class Approvals:
        def __init__(self, _db):
            pass

        async def check_authorization(self, _action, target_ref=None):
            return {
                "authorized": True,
                "authorization_id": str(row.id),
                "expires_at": row.expires_at.isoformat(),
            }

    return Approvals


class EnvironmentTests(unittest.TestCase):
    def test_protected_environments(self):
        for value in ("production", "PROD", "core", " protected "):
            self.assertTrue(is_protected_environment(value), value)
        for value in ("staging", "development", "", "production-copy"):
            self.assertFalse(is_protected_environment(value), value)


class DeploymentGateTests(unittest.IsolatedAsyncioTestCase):
    async def test_tested_change_with_signed_authority_allowed(self):
        row = authorization()
        tested = change()
        db = QueuedDB(FakeResult([tested]), FakeResult([row]))
        with patch(
            "app.services.development_governance.CreatorApprovalService", approvals_for(row)
        ):
            result = await verify_protected_deployment(
                db, str(PROJECT_ID), [str(tested.id)]
            )
        self.assertTrue(result["authorized"])
        self.assertEqual(result["authorization_id"], str(row.id))
        self.assertEqual(result["tested_changes"], [str(tested.id)])

    async def test_missing_change_ids_denied(self):
        with self.assertRaises(DeploymentGateDenied):
            await verify_protected_deployment(QueuedDB(), str(PROJECT_ID), [])

    async def test_untested_change_denied(self):
        proposed = change(status="proposed")
        db = QueuedDB(FakeResult([proposed]), FakeResult([]))
        with self.assertRaises(DeploymentGateDenied):
            await verify_protected_deployment(db, str(PROJECT_ID), [str(proposed.id)])

    async def test_foreign_project_change_denied(self):
        foreign = change(project_id=uuid.uuid4())
        db = QueuedDB(FakeResult([]), FakeResult([]))
        with self.assertRaises(DeploymentGateDenied):
            await verify_protected_deployment(db, str(PROJECT_ID), [str(foreign.id)])

    async def test_expired_and_revoked_authority_denied(self):
        tested = change()
        for row in (
            authorization(expires_at=datetime.now(timezone.utc) - timedelta(minutes=1)),
            authorization(revoked_at=datetime.now(timezone.utc)),
            authorization(target_ref=str(uuid.uuid4())),
        ):
            db = QueuedDB(FakeResult([tested]), FakeResult([row]))
            with patch(
                "app.services.development_governance.CreatorApprovalService",
                approvals_for(row),
            ):
                with self.assertRaises(DeploymentGateDenied):
                    await verify_protected_deployment(
                        db, str(PROJECT_ID), [str(tested.id)]
                    )


if __name__ == "__main__":
    unittest.main()
