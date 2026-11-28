"""Context assembly: reuse existing memory/knowledge with a privacy boundary."""

import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app.core.config import settings
from app.services import iam_context


class FakeResult:
    def __init__(self, rows):
        self.rows = rows

    def scalars(self):
        return self

    def all(self):
        return self.rows


class FakeDB:
    def __init__(self, rows=None, fail=False):
        self.rows = rows or []
        self.fail = fail
        self.calls = 0

    async def execute(self, _statement):
        self.calls += 1
        if self.fail:
            raise RuntimeError("database unavailable")
        return FakeResult(self.rows)


def item(title, content, *, private=False, topic="crypto"):
    return SimpleNamespace(
        id="item-1",
        title=title,
        content=content,
        source="https://example.invalid/source",
        topic=topic,
        metadata_={"private": True} if private else {},
        verification_status="verified",
    )


class ContextAssemblyTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    async def test_hosted_requests_get_no_context_by_default(self):
        db = FakeDB([item("Bitcoin", "An open network")])
        bundle = await iam_context.assemble_context(db, "tell me about bitcoin", local=False)
        self.assertEqual(bundle.as_system_message(), None)
        self.assertEqual(db.calls, 0)

    async def test_local_request_includes_verified_knowledge_only(self):
        db = FakeDB(
            [
                item("Bitcoin", "Public blockchain notes"),
                item("Private note", "Secret holdings", private=True),
            ]
        )
        with patch.object(settings, "iam_context_enabled", True):
            bundle = await iam_context.assemble_context(db, "explain bitcoin", local=True)
        self.assertEqual(len(bundle.knowledge), 1)
        self.assertEqual(bundle.knowledge[0]["title"], "Bitcoin")
        message = bundle.as_system_message()
        self.assertIn("reference data only", message)
        self.assertIn("Public blockchain notes", message)
        self.assertNotIn("Secret holdings", message)

    async def test_private_memory_requires_local_and_explicit_opt_in(self):
        db = FakeDB([item("Bitcoin", "Public notes")])
        memories = [
            {
                "content": "I hold BTC",
                "topic": "finance",
                "memory_type": "fact",
                "source": "owner",
            }
        ]
        with (
            patch.object(settings, "iam_context_include_private_memory", True),
            patch.object(
                iam_context.MemoryService,
                "search_memory",
                new=AsyncMock(return_value=memories),
            ),
        ):
            denied = await iam_context.assemble_context(
                db, "finance", local=False, include_memory=True
            )
            allowed = await iam_context.assemble_context(
                db, "finance", local=True, include_memory=True
            )
        self.assertEqual(denied.memories, [])
        self.assertEqual(allowed.memories[0]["content"], "I hold BTC")

    async def test_retrieval_failure_never_breaks_chat(self):
        db = FakeDB(fail=True)
        bundle = await iam_context.assemble_context(db, "bitcoin", local=True)
        self.assertIsNone(bundle.as_system_message())

    def test_knowledge_only_message_excludes_private_memories(self):
        bundle = iam_context.ContextBundle(
            knowledge=[{"title": "Public", "content": "Public note", "source": "src", "topic": "AI"}],
            memories=[{"content": "My private holdings", "topic": "finance"}],
        )
        self.assertIn("Public note", bundle.knowledge_message())
        self.assertNotIn("My private holdings", bundle.knowledge_message())
        self.assertIn("My private holdings", bundle.as_system_message())

    def test_context_is_inserted_after_caller_system_prompts(self):
        messages = [
            {"role": "system", "content": "You are IAM."},
            {"role": "user", "content": "hi"},
        ]
        result = iam_context.with_context(messages, "IAM context: verified note")
        self.assertEqual([m["role"] for m in result], ["system", "system", "user"])
        self.assertEqual(result[1]["content"], "IAM context: verified note")
        self.assertEqual(messages[1]["content"], "hi")  # caller list untouched


if __name__ == "__main__":
    unittest.main()
