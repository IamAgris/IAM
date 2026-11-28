"""Phase 10 tests: Website Knowledge Base, Account Lifecycle, Digital Reputation,
Website Consent, Digital Security Incidents, Autonomous Web Tasks, Browser Infrastructure."""

import unittest
import uuid
from unittest.mock import patch

from app.models.web_knowledge import (
    WebsiteKnowledge, WebsiteSession, WebsiteAccountLifecycle,
    DigitalReputation, WebsiteConsent, DigitalSecurityIncident,
    AutonomousWebTask, BrowserInfrastructure,
)
from app.models.security import AuditEvent
from app.services.web_knowledge_service import (
    WebsiteKnowledgeError,
    WebsiteKnowledgeService,
)
from app.services.web_account_service import (
    WebsiteAccountError,
    WebsiteAccountService,
)
from app.services.digital_reputation_service import (
    DigitalReputationError,
    DigitalReputationService,
)
from app.services.web_consent_service import (
    WebsiteConsentError,
    WebsiteConsentService,
)
from app.services.digital_security_service import (
    DigitalSecurityIncidentError,
    DigitalSecurityService,
)
from app.services.autonomous_web_task_service import (
    AutonomousWebTaskError,
    AutonomousWebTaskService,
)
from app.services.browser_infrastructure_service import (
    BrowserInfrastructureError,
    BrowserInfrastructureService,
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
    def __init__(self):
        self.rows = []

    def add(self, obj):
        if obj not in self.rows:
            if getattr(obj, "id", None) is None:
                obj.id = uuid.uuid4()
            self.rows.append(obj)

    async def delete(self, obj):
        if obj in self.rows:
            self.rows.remove(obj)

    async def flush(self):
        return None

    async def commit(self):
        return None

    async def refresh(self, obj):
        return None

    async def execute(self, statement):
        entity = statement.column_descriptions[0]["entity"]
        return FakeResult([row for row in self.rows if isinstance(row, entity)])


class WebsiteKnowledgeTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.db = FakeDB()
        self.service = WebsiteKnowledgeService(self.db)

    async def test_create_and_get_knowledge(self):
        knowledge = await self.service.create(
            domain="example.com",
            display_name="Example Corp",
            homepage_url="https://example.com",
            login_procedure=[{"step": 1, "action": "navigate", "target": "/login"}],
            auth_methods=["password", "passkey"],
            supported_passkeys=True,
            known_restrictions=["captcha"],
            browser_compatibility=["chromium", "firefox"],
            actor="iam",
        )
        self.assertEqual(knowledge["domain"], "example.com")
        self.assertEqual(knowledge["is_active"], True)

        fetched = await self.service.get(str(knowledge["id"]))
        self.assertEqual(fetched["domain"], "example.com")
        self.assertTrue(fetched["supported_passkeys"])

    async def test_list_and_update(self):
        await self.service.create(
            domain="example.com",
            display_name="Example Corp",
            homepage_url="https://example.com",
            actor="iam",
        )
        all_knowledge = await self.service.list()
        self.assertEqual(len(all_knowledge), 1)

        updated = await self.service.update(
            str(all_knowledge[0]["id"]),
            supported_passkeys=True,
            actor="iam",
        )
        self.assertTrue(updated["supported_passkeys"])

    async def test_delete_knowledge(self):
        created = await self.service.create(
            domain="example.com",
            display_name="Example Corp",
            homepage_url="https://example.com",
            actor="iam",
        )
        deleted = await self.service.delete(str(created["id"]))
        self.assertEqual(deleted["status"], "deleted")
        remaining = await self.service.list()
        self.assertEqual(len(remaining), 0)

    async def test_duplicate_domain_denied(self):
        await self.service.create(
            domain="example.com",
            display_name="Example Corp",
            homepage_url="https://example.com",
            actor="iam",
        )
        with self.assertRaises(WebsiteKnowledgeError):
            await self.service.create(
                domain="example.com",
                display_name="Example Corp 2",
                homepage_url="https://example2.com",
                actor="iam",
            )


class WebsiteAccountTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.db = FakeDB()
        self.service = WebsiteAccountService(self.db)

    async def test_create_account_lifecycle(self):
        # First create website knowledge
        wk_service = WebsiteKnowledgeService(self.db)
        wk = await wk_service.create(
            domain="example.com",
            display_name="Example Corp",
            homepage_url="https://example.com",
            actor="iam",
        )

        account = await self.service.create(
            website_knowledge_id=str(wk["id"]),
            account_type="owned_by_iam",
            username="iam_user",
            owner_entity="Aura Holdings",
            is_owned_by_iam=True,
            actor="iam",
        )
        self.assertEqual(account["account_type"], "owned_by_iam")
        self.assertEqual(account["username"], "iam_user")
        self.assertTrue(account["is_owned_by_iam"])

    async def test_invalid_account_type(self):
        wk_service = WebsiteKnowledgeService(self.db)
        wk = await wk_service.create(
            domain="example.com",
            display_name="Example Corp",
            homepage_url="https://example.com",
            actor="iam",
        )
        with self.assertRaises(WebsiteAccountError):
            await self.service.create(
                website_knowledge_id=str(wk["id"]),
                account_type="invalid_type",
                username="user",
                owner_entity="Aura Holdings",
                actor="iam",
            )

    async def test_ownership_validation(self):
        wk_service = WebsiteKnowledgeService(self.db)
        wk = await wk_service.create(
            domain="example.com",
            display_name="Example Corp",
            homepage_url="https://example.com",
            actor="iam",
        )
        with self.assertRaises(WebsiteAccountError):
            await self.service.create(
                website_knowledge_id=str(wk["id"]),
                account_type="owned_by_iam",
                username="user",
                owner_entity="Aura Holdings",
                is_owned_by_iam=True,
                is_owned_by_creator=True,
                actor="iam",
            )


class DigitalReputationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.db = FakeDB()
        self.service = DigitalReputationService(self.db)

    async def test_create_reputation(self):
        wk_service = WebsiteKnowledgeService(self.db)
        wk = await wk_service.create(
            domain="example.com",
            display_name="Example Corp",
            homepage_url="https://example.com",
            actor="iam",
        )

        rep = await self.service.create(
            website_knowledge_id=str(wk["id"]),
            account_username="iam_user",
            verification_status="verified",
            service_reliability_score=85,
            account_security_score=90,
            actor="iam",
        )
        self.assertEqual(rep["account_username"], "iam_user")
        self.assertEqual(rep["service_reliability_score"], 85)

    async def test_invalid_score(self):
        wk_service = WebsiteKnowledgeService(self.db)
        wk = await wk_service.create(
            domain="example.com",
            display_name="Example Corp",
            homepage_url="https://example.com",
            actor="iam",
        )
        with self.assertRaises(DigitalReputationError):
            await self.service.create(
                website_knowledge_id=str(wk["id"]),
                account_username="user",
                service_reliability_score=150,
                actor="iam",
            )


class DigitalSecurityIncidentTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.db = FakeDB()
        self.service = DigitalSecurityService(self.db)

    async def test_create_incident(self):
        wk_service = WebsiteKnowledgeService(self.db)
        wk = await wk_service.create(
            domain="example.com",
            display_name="Example Corp",
            homepage_url="https://example.com",
            actor="iam",
        )

        incident = await self.service.create(
            website_knowledge_id=str(wk["id"]),
            incident_type="credential_leak",
            title="Credential leak detected",
            severity="high",
            actor="iam",
        )
        self.assertEqual(incident["incident_type"], "credential_leak")
        self.assertEqual(incident["severity"], "high")
        self.assertEqual(incident["status"], "open")

    async def test_invalid_incident_type(self):
        wk_service = WebsiteKnowledgeService(self.db)
        wk = await wk_service.create(
            domain="example.com",
            display_name="Example Corp",
            homepage_url="https://example.com",
            actor="iam",
        )
        with self.assertRaises(DigitalSecurityIncidentError):
            await self.service.create(
                website_knowledge_id=str(wk["id"]),
                incident_type="invalid_type",
                title="Test",
                actor="iam",
            )


class AutonomousWebTaskTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.db = FakeDB()
        self.service = AutonomousWebTaskService(self.db)

    async def test_create_and_retry(self):
        wk_service = WebsiteKnowledgeService(self.db)
        wk = await wk_service.create(
            domain="example.com",
            display_name="Example Corp",
            homepage_url="https://example.com",
            actor="iam",
        )

        task = await self.service.create(
            title="Register account",
            task_type="registration",
            website_knowledge_id=str(wk["id"]),
            priority=5,
            actor="iam",
        )
        self.assertEqual(task["status"], "pending")
        self.assertEqual(task["task_type"], "registration")
        self.assertEqual(task["progress_percentage"], 0)

        # Manually set status to failed
        task_row = await self.service._task(str(task["id"]))
        task_row.status = "failed"
        for row in self.db.rows:
            if isinstance(row, AutonomousWebTask) and str(row.id) == str(task["id"]):
                row.status = "failed"
        await self.db.commit()

        retried = await self.service.retry(str(task["id"]), actor="iam")
        self.assertEqual(retried["status"], "pending")

    async def test_schedule_at_is_persisted(self):
        scheduled = await self.service.create(
            title="Scheduled monitoring",
            task_type="monitoring",
            schedule_at="2026-11-29T10:30:00Z",
            actor="iam",
        )
        self.assertEqual(scheduled["schedule_at"], "2026-11-29T10:30:00+00:00")
        row = await self.service._task(str(scheduled["id"]))
        self.assertIsNotNone(row.schedule_at)
        self.assertEqual(row.schedule_at.tzinfo.utcoffset(row.schedule_at).total_seconds(), 0)

        unscheduled = await self.service.create(
            title="Immediate task",
            task_type="research",
            actor="iam",
        )
        self.assertIsNone(unscheduled["schedule_at"])

    async def test_schedule_at_rejects_naive_and_invalid(self):
        with self.assertRaises(AutonomousWebTaskError):
            await self.service.create(
                title="Naive timestamp",
                task_type="research",
                schedule_at="2026-11-29T10:30:00",
                actor="iam",
            )
        with self.assertRaises(AutonomousWebTaskError):
            await self.service.create(
                title="Invalid timestamp",
                task_type="research",
                schedule_at="not-a-timestamp",
                actor="iam",
            )

    async def test_max_retries_exceeded(self):
        wk_service = WebsiteKnowledgeService(self.db)
        wk = await wk_service.create(
            domain="example.com",
            display_name="Example Corp",
            homepage_url="https://example.com",
            actor="iam",
        )

        task = await self.service.create(
            title="Test task",
            task_type="login",
            website_knowledge_id=str(wk["id"]),
            max_retries=0,
            actor="iam",
        )
        # Manually set status to failed in FakeDB rows
        task_row = await self.service._task(str(task["id"]))
        task_row.status = "failed"
        for row in self.db.rows:
            if isinstance(row, AutonomousWebTask) and str(row.id) == str(task["id"]):
                row.status = "failed"
        await self.db.commit()

        # Verify status is failed
        task_row2 = await self.service._task(str(task["id"]))
        assert task_row2.status == "failed", f"Expected failed, got {task_row2.status}"

        with self.assertRaises(AutonomousWebTaskError):
            await self.service.retry(str(task["id"]), actor="iam")


class BrowserInfrastructureTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.db = FakeDB()
        self.service = BrowserInfrastructureService(self.db)

    async def test_create_and_list(self):
        browser = await self.service.create(
            name="Chromium Worker 1",
            browser_type="chromium",
            mode="headless",
            concurrent_session_limit=3,
            actor="iam",
        )
        self.assertEqual(browser["browser_type"], "chromium")
        self.assertEqual(browser["health_status"], "healthy")

        browsers = await self.service.list()
        self.assertEqual(len(browsers), 1)

    async def test_invalid_browser_type(self):
        with self.assertRaises(BrowserInfrastructureError):
            await self.service.create(
                name="Invalid Browser",
                browser_type="invalid_browser",
                actor="iam",
            )


if __name__ == "__main__":
    unittest.main()
