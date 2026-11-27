"""HTTP-level conversation ownership and chat persistence tests.

No frontend is involved: ownership comes from a server-issued HttpOnly cookie,
so the existing browser client scopes itself automatically.
"""

import json
import unittest
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.api.routes import conversations as conversation_routes
from app.api.routes import models as model_routes
from app.core.config import settings
from app.core.database import get_db_session
from app.main import app
from app.models.memory import Conversation, ConversationMessage


class MemoryDB:
    """Minimal async session backed by a list, enough for conversation CRUD."""

    def __init__(self):
        self.rows = []

    def add(self, obj):
        if getattr(obj, "id", None) is None:
            obj.id = uuid.uuid4()
        self.rows.append(obj)

    async def commit(self):
        return None

    async def flush(self):
        return None

    async def refresh(self, _obj):
        return None

    async def delete(self, obj):
        self.rows = [row for row in self.rows if row is not obj]

    async def execute(self, statement):
        descriptions = getattr(statement, "column_descriptions", None) or []
        entity = descriptions[0].get("entity") if descriptions else None
        rows = [row for row in self.rows if isinstance(row, entity)] if entity else []

        class Result:
            def scalars(self_inner):
                return SimpleNamespace(all=lambda: rows)

            def scalar_one_or_none(self_inner):
                return rows[0] if rows else None

        return Result()


class ConversationOwnershipTests(unittest.TestCase):
    def setUp(self):
        self.db = MemoryDB()

        async def override():
            yield self.db

        app.dependency_overrides[get_db_session] = override
        app.dependency_overrides[conversation_routes.get_db_session] = override
        app.dependency_overrides[model_routes.get_db_session] = override
        self.settings_patch = patch.object(settings, "auth_enabled", False)
        self.settings_patch.start()
        self.client = TestClient(app)
        self.addCleanup(self._cleanup)

    def _cleanup(self):
        app.dependency_overrides.clear()
        self.settings_patch.stop()

    def _client(self, token=None):
        client = TestClient(app)
        if token:
            client.cookies.set("iam_conversation_owner", token)
        return client

    def test_cookie_is_issued_and_scopes_conversations(self):
        owner_a, owner_b = str(uuid.uuid4()), str(uuid.uuid4())
        client_a = self._client(owner_a)
        client_b = self._client(owner_b)

        created = client_a.post(
            "/api/v1/conversations/", json={"title": "Private chat"}
        )
        self.assertEqual(created.status_code, 200)
        conversation_id = created.json()["id"]

        self.assertEqual(len(client_a.get("/api/v1/conversations/").json()), 1)
        self.assertEqual(client_b.get("/api/v1/conversations/").json(), [])
        self.assertEqual(
            client_b.get(f"/api/v1/conversations/{conversation_id}").status_code, 404
        )
        self.assertEqual(
            client_b.delete(f"/api/v1/conversations/{conversation_id}").status_code, 404
        )
        self.assertEqual(
            client_a.get(f"/api/v1/conversations/{conversation_id}").status_code, 200
        )

    def test_new_browser_gets_an_httponly_cookie(self):
        response = self.client.get("/api/v1/conversations/")
        self.assertEqual(response.status_code, 200)
        cookie = response.headers.get("set-cookie", "")
        self.assertIn("iam_conversation_owner", cookie)
        self.assertIn("httponly", cookie.lower())

    def test_invalid_uuid_returns_404(self):
        response = self.client.get("/api/v1/conversations/not-a-uuid")
        self.assertEqual(response.status_code, 404)

    def test_chat_turn_is_persisted_and_scoped(self):
        owner = str(uuid.uuid4())
        client = self._client(owner)
        status = SimpleNamespace(
            available=True, mode="ollama", model=settings.iam_primary_model,
            reason="", provider="ollama",
        )
        bundle = SimpleNamespace(as_system_message=lambda: None)
        with (
            patch.object(model_routes.inference_service, "resolve", new=AsyncMock(return_value=status)),
            patch.object(
                model_routes.inference_service,
                "chat",
                new=AsyncMock(return_value={
                    "choices": [{"message": {"content": "Hello from IAM"}}]
                }),
            ),
            patch.object(
                model_routes, "assemble_context", new=AsyncMock(return_value=bundle)
            ),
        ):
            response = client.post(
                "/api/v1/models/chat",
                json={
                    "messages": [
                        {"role": "user", "content": "Hello IAM"},
                    ],
                    "idempotency_key": "turn-1",
                },
            )
        self.assertEqual(response.status_code, 200)
        conversation_id = response.json()["conversation_id"]

        messages = client.get(f"/api/v1/conversations/{conversation_id}/messages").json()
        contents = [item["content"] for item in messages]
        self.assertIn("Hello IAM", contents)
        self.assertIn("Hello from IAM", contents)

        # A retry with the same key must not duplicate the user turn.
        with (
            patch.object(model_routes.inference_service, "resolve", new=AsyncMock(return_value=status)),
            patch.object(
                model_routes.inference_service,
                "chat",
                new=AsyncMock(return_value={
                    "choices": [{"message": {"content": "Hello from IAM"}}]
                }),
            ),
            patch.object(
                model_routes, "assemble_context", new=AsyncMock(return_value=bundle)
            ),
        ):
            client.post(
                "/api/v1/models/chat",
                json={
                    "conversation_id": conversation_id,
                    "messages": [{"role": "user", "content": "Hello IAM"}],
                    "idempotency_key": "turn-1",
                },
            )
        messages_again = client.get(
            f"/api/v1/conversations/{conversation_id}/messages"
        ).json()
        self.assertEqual(
            [m["content"] for m in messages_again].count("Hello IAM"), 1
        )


class ClaimTests(unittest.IsolatedAsyncioTestCase):
    async def test_anonymous_conversation_can_be_claimed_after_login(self):
        from app.api.routes.conversations import claim_conversation

        db = MemoryDB()
        anon = str(uuid.uuid4())
        conv = Conversation(title="Mine", metadata_={"owner_token": anon})
        db.add(conv)
        request = SimpleNamespace(
            state=SimpleNamespace(
                conversation_owner=anon,
                credential={"id": "credential-1"},
            )
        )
        result = await claim_conversation(str(conv.id), request, db)
        self.assertEqual(result.metadata["owner_token"], "credential:credential-1")

        # Once claimed, the anonymous cookie no longer owns it.
        request.state.credential = None
        with self.assertRaises(Exception):
            await claim_conversation(str(conv.id), request, db)


if __name__ == "__main__":
    unittest.main()
