"""Phase 10 Module C tests: AI Communication & Collaboration."""

import unittest
import uuid
from unittest.mock import patch

from app.models.ai_communication import (
    AICommunicationPermission,
    AICommunicationAudit,
    AIConversationMessage,
    AIConversationThread,
    AIContextExchange,
    AIIdentityRegistry,
    AIReputationRecord,
    AIResponseVerification,
    HumanCommunicationBridge,
)
from app.models.security import AuditEvent
from app.services.ai_communication import (
    AICommunicationError,
    AICommunicationService,
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

    async def refresh(self, obj):
        return None

    async def execute(self, statement):
        entity = statement.column_descriptions[0]["entity"]
        return FakeResult([row for row in self.rows if isinstance(row, entity)])


class IdentityRegistryTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.db = FakeDB()
        self.service = AICommunicationService(self.db)

    async def test_register_ai_identity(self):
        result = await self.service.register_ai_identity(
            name="ChatGPT",
            provider="OpenAI",
            model_id="gpt-4",
            communication_channel="human_mediated",
            is_local=False,
            communication_permitted=True,
            trust_level="trusted",
            description="OpenAI's ChatGPT assistant",
            actor="iam",
        )
        self.assertEqual(result["name"], "ChatGPT")
        self.assertEqual(result["provider"], "OpenAI")
        self.assertEqual(result["model_id"], "gpt-4")
        self.assertEqual(result["communication_channel"], "human_mediated")
        self.assertTrue(result["communication_permitted"])
        self.assertEqual(result["trust_level"], "trusted")

        fetched = await self.service.get_identity(str(result["id"]))
        self.assertEqual(fetched["name"], "ChatGPT")
        self.assertTrue(fetched["communication_permitted"])

    async def test_list_identities(self):
        await self.service.register_ai_identity(
            name="ChatGPT",
            provider="OpenAI",
            model_id="gpt-4",
            communication_channel="human_mediated",
            is_local=False,
            communication_permitted=True,
            trust_level="trusted",
            actor="iam",
        )
        await self.service.register_ai_identity(
            name="Claude",
            provider="Anthropic",
            model_id="claude-3",
            communication_channel="browser",
            is_local=False,
            communication_permitted=False,
            trust_level="untrusted",
            actor="iam",
        )
        identities = await self.service.list_identities()
        self.assertEqual(len(identities), 2)

    async def test_update_identity_trust_level(self):
        wk = await self.service.register_ai_identity(
            name="Test AI",
            provider="TestProvider",
            model_id="test-1",
            communication_channel="browser",
            is_local=True,
            communication_permitted=False,
            trust_level="untrusted",
            actor="iam",
        )
        updated = await self.service.update_identity(
            str(wk["id"]),
            communication_permitted=True,
            trust_level="trusted",
            actor="iam",
        )
        self.assertTrue(updated["communication_permitted"])
        self.assertEqual(updated["trust_level"], "trusted")


class CapabilityRegistryTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.db = FakeDB()
        self.service = AICommunicationService(self.db)

    async def test_register_capability(self):
        wk_service = AICommunicationService(self.db)
        identity = await wk_service.register_ai_identity(
            name="Test AI",
            provider="TestProvider",
            model_id="test-1",
            communication_channel="browser",
            is_local=True,
            communication_permitted=False,
            trust_level="trusted",
            actor="iam",
        )

        cap = await self.service.register_capability(
            ai_identity_id=str(identity["id"]),
            capability="code_review",
            confidence_score=85,
            evidence=[{"source": "benchmark", "score": 85}],
            actor="iam",
        )
        self.assertEqual(cap["capability"], "code_review")
        self.assertEqual(cap["confidence_score"], 85)

    async def test_list_capabilities(self):
        wk_service = AICommunicationService(self.db)
        identity = await wk_service.register_ai_identity(
            name="Test AI",
            provider="TestProvider",
            model_id="test-1",
            communication_channel="browser",
            is_local=True,
            communication_permitted=False,
            trust_level="trusted",
            actor="iam",
        )
        await self.service.register_capability(
            ai_identity_id=str(identity["id"]),
            capability="code_review",
            confidence_score=85,
            evidence=[],
            actor="iam",
        )
        await self.service.register_capability(
            ai_identity_id=str(identity["id"]),
            capability="research",
            confidence_score=70,
            evidence=[],
            actor="iam",
        )
        caps = await self.service.list_capabilities()
        self.assertEqual(len(caps), 2)

        ai_caps = await self.service.list_capabilities(str(identity["id"]))
        self.assertEqual(len(ai_caps), 2)


class ConversationThreadTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.db = FakeDB()
        self.service = AICommunicationService(self.db)

    async def test_create_conversation_and_add_message(self):
        wk_service = AICommunicationService(self.db)
        identity = await wk_service.register_ai_identity(
            name="Test AI",
            provider="TestProvider",
            model_id="test-1",
            communication_channel="browser",
            is_local=True,
            communication_permitted=False,
            trust_level="trusted",
            actor="iam",
        )

        thread = await self.service.create_conversation(
            ai_identity_id=str(identity["id"]),
            title="Architecture Discussion",
            topic="system design",
            is_human_mediated=False,
            actor="iam",
        )
        self.assertEqual(thread["title"], "Architecture Discussion")
        self.assertEqual(thread["status"], "active")

        msg = await self.service.add_message(
            conversation_id=str(thread["id"]),
            sender="iam",
            content="Can you review this architecture?",
            message_type="question",
            confidence_score=90,
            actor="iam",
        )
        self.assertEqual(msg["sender"], "iam")
        self.assertEqual(msg["content"], "Can you review this architecture?")
        self.assertEqual(msg["confidence_score"], 90)

        messages = await self.service.list_messages(str(thread["id"]))
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0]["sender"], "iam")

    async def test_invalid_sender(self):
        wk_service = AICommunicationService(self.db)
        identity = await wk_service.register_ai_identity(
            name="Test AI",
            provider="TestProvider",
            model_id="test-1",
            communication_channel="browser",
            is_local=True,
            communication_permitted=False,
            trust_level="trusted",
            actor="iam",
        )
        thread = await self.service.create_conversation(
            ai_identity_id=str(identity["id"]),
            title="Test",
            topic=None,
            is_human_mediated=False,
            actor="iam",
        )
        with self.assertRaises(AICommunicationError):
            await self.service.add_message(
                conversation_id=str(thread["id"]),
                sender="invalid_sender",
                content="test",
                actor="iam",
            )


class HumanBridgeTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.db = FakeDB()
        self.service = AICommunicationService(self.db)

    async def test_create_and_complete_human_bridge(self):
        wk_service = AICommunicationService(self.db)
        identity = await wk_service.register_ai_identity(
            name="ChatGPT",
            provider="OpenAI",
            model_id="gpt-4",
            communication_channel="human_mediated",
            is_local=False,
            communication_permitted=True,
            trust_level="trusted",
            actor="iam",
        )

        bridge = await self.service.create_human_bridge(
            ai_identity_id=str(identity["id"]),
            iam_message="Can you review my architecture?",
            actor="iam",
        )
        self.assertEqual(bridge["status"], "pending")
        self.assertEqual(bridge["iam_message"], "Can you review my architecture?")

        completed = await self.service.complete_bridge(
            str(bridge["id"]),
            human_response="I've reviewed your architecture.",
            ai_response="Thank you, I will incorporate your feedback.",
            status="completed",
            actor="iam",
        )
        self.assertEqual(completed["status"], "completed")
        self.assertEqual(completed["human_response"], "I've reviewed your architecture.")
        self.assertEqual(completed["ai_response"], "Thank you, I will incorporate your feedback.")

    async def test_list_bridges(self):
        wk_service = AICommunicationService(self.db)
        identity = await wk_service.register_ai_identity(
            name="Test AI",
            provider="TestProvider",
            model_id="test-1",
            communication_channel="human_mediated",
            is_local=False,
            communication_permitted=True,
            trust_level="trusted",
            actor="iam",
        )
        await self.service.create_human_bridge(
            ai_identity_id=str(identity["id"]),
            iam_message="Test message 1",
            actor="iam",
        )
        await self.service.create_human_bridge(
            ai_identity_id=str(identity["id"]),
            iam_message="Test message 2",
            actor="iam",
        )
        bridges = await self.service.list_bridges()
        self.assertEqual(len(bridges), 2)


class ContextExchangeTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.db = FakeDB()
        self.service = AICommunicationService(self.db)

    async def test_exchange_context(self):
        wk_service = AICommunicationService(self.db)
        identity = await wk_service.register_ai_identity(
            name="Test AI",
            provider="TestProvider",
            model_id="test-1",
            communication_channel="browser",
            is_local=True,
            communication_permitted=False,
            trust_level="trusted",
            actor="iam",
        )

        context = await self.service.exchange_context(
            ai_identity_id=str(identity["id"]),
            context_type="architecture",
            content={"system": "web app", "stack": ["python", "postgres"]},
            actor="iam",
        )
        self.assertEqual(context["context_type"], "architecture")
        self.assertEqual(context["content"]["system"], "web app")

        contexts = await self.service.list_context_exchanges(str(identity["id"]))
        self.assertEqual(len(contexts), 1)
        self.assertEqual(contexts[0]["context_type"], "architecture")


if __name__ == "__main__":
    unittest.main()
