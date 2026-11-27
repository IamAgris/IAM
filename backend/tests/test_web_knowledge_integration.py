"""Doc 29 P4 tests: governed research proposals, verification and legal gates."""

import unittest
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from app.api.routes import browser_knowledge as knowledge_routes
from app.models.web_knowledge import BrowserKnowledgeProposal
from app.services.web_knowledge_integration import (
    WebKnowledgeIntegrationError,
    WebKnowledgeIntegrationService,
    domain_of,
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

    async def flush(self):
        return None

    async def commit(self):
        return None

    async def execute(self, statement):
        entity = statement.column_descriptions[0]["entity"]
        rows = [row for row in self.rows if isinstance(row, entity)]
        where = getattr(statement, "whereclause", None)
        if where is not None and hasattr(where, "left") and hasattr(where.left, "key"):
            key = where.left.key
            value = getattr(where.right, "value", None)
            rows = [row for row in rows if getattr(row, key, None) == value]
        return FakeResult(rows)


EVIDENCE = [
    {"evidence_id": "e1", "url": "https://alpha.example/report"},
    {"evidence_id": "e2", "url": "https://beta.example/report"},
]
SOURCES = [
    {"url": "https://alpha.example/report", "evidence_id": "e1"},
    {"url": "https://beta.example/report", "evidence_id": "e2"},
]


class ServiceTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.db = FakeDB()
        self.service = WebKnowledgeIntegrationService(self.db)
        self.service.evidence = MagicMock()
        self.service.evidence.evidence_for = AsyncMock(return_value=EVIDENCE)
        self.service.evidence.append_audit = AsyncMock(return_value="audit-1")

    async def test_domain_helper_and_single_source(self):
        self.assertEqual(domain_of("https://Alpha.Example/a"), "alpha.example")
        result = await self.service.verify_sources(
            "claim", [SOURCES[0]], "task-1"
        )
        self.assertEqual(result["state"], "single_source")
        self.assertFalse(result["verified"])

    async def test_two_independent_sources_verified(self):
        result = await self.service.verify_sources("claim", SOURCES, "task-1")
        self.assertTrue(result["verified"])
        self.assertEqual(result["independent_count"], 2)

    async def test_unpreserved_source_is_unverified(self):
        result = await self.service.verify_sources(
            "claim", [{"url": "https://unknown.example", "evidence_id": "e9"}], "task-1"
        )
        self.assertEqual(result["state"], "unverified")

    async def test_propose_quarantines_when_legal_gate_blocks(self):
        with patch(
            "app.services.web_knowledge_integration.IPLCIService"
        ) as iplci_cls:
            iplci_cls.return_value.gate_check = AsyncMock(
                return_value={"decision": "BLOCKED", "reason": "no rights record"}
            )
            proposal = await self.service.propose(
                task_id="task-1", claim="hosting prices", sources=SOURCES,
                created_by="iam",
            )
        self.assertEqual(proposal["status"], "quarantined")
        self.assertEqual(proposal["legal_decision"], "BLOCKED")
        self.assertEqual(proposal["verification_state"], "verified")

    async def test_propose_pending_review_when_cleared(self):
        with patch(
            "app.services.web_knowledge_integration.IPLCIService"
        ) as iplci_cls:
            iplci_cls.return_value.gate_check = AsyncMock(
                return_value={"decision": "ALLOWED", "policy_version": "1"}
            )
            proposal = await self.service.propose(
                task_id="task-1", claim="hosting prices", sources=SOURCES,
                created_by="iam",
            )
        self.assertEqual(proposal["status"], "pending_review")

    async def test_approval_requires_signed_authorization(self):
        with patch(
            "app.services.web_knowledge_integration.IPLCIService"
        ) as iplci_cls, patch(
            "app.services.web_knowledge_integration.CreatorApprovalService"
        ) as approval_cls:
            iplci_cls.return_value.gate_check = AsyncMock(
                return_value={"decision": "ALLOWED"}
            )
            proposal = await self.service.propose(
                task_id="task-1", claim="c", sources=SOURCES, created_by="iam"
            )
            approval_cls.return_value.check_authorization = AsyncMock(
                return_value={"authorized": False}
            )
            with self.assertRaises(WebKnowledgeIntegrationError):
                await self.service.approve(proposal["id"], "creator")

    async def test_approved_proposal_returns_promotion_not_a_write(self):
        with patch(
            "app.services.web_knowledge_integration.IPLCIService"
        ) as iplci_cls, patch(
            "app.services.web_knowledge_integration.CreatorApprovalService"
        ) as approval_cls:
            iplci_cls.return_value.gate_check = AsyncMock(
                return_value={"decision": "ALLOWED"}
            )
            proposal = await self.service.propose(
                task_id="task-1", claim="c", sources=SOURCES, created_by="iam"
            )
            approval_cls.return_value.check_authorization = AsyncMock(
                return_value={
                    "authorized": True, "authorization_id": "a1", "signer_id": "creator"
                }
            )
            result = await self.service.approve(proposal["id"], "creator")
        self.assertEqual(result["status"], "approved")
        self.assertEqual(result["promotion"]["authorization_id"], "a1")
        self.assertIn("explicitly", result["promotion"]["note"])
        stored = [r for r in self.db.rows if isinstance(r, BrowserKnowledgeProposal)]
        self.assertEqual(stored[0].status, "approved")
        self.assertEqual(stored[0].evidence_refs, ["e1", "e2"])


class RouteTests(unittest.IsolatedAsyncioTestCase):
    async def test_proposal_route_delegates(self):
        payload = knowledge_routes.ProposalRequest(
            task_id="task-1", claim="c", sources=SOURCES
        )
        request = SimpleNamespace(state=SimpleNamespace(credential=None))
        with patch.object(knowledge_routes, "WebKnowledgeIntegrationService") as service_cls:
            service_cls.return_value.propose = AsyncMock(return_value={"status": "quarantined"})
            result = await knowledge_routes.create_proposal(payload, request, object())
        self.assertEqual(result["status"], "quarantined")


if __name__ == "__main__":
    unittest.main()
