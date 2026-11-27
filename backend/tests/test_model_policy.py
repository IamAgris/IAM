"""Signed authority gates for paid inference and chat actions."""

import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException

from app.api.routes import modelrouter, models
from app.core.config import settings
from app.services import model_policy


class FakeDB:
    pass


def authority(authorized=True):
    if authorized:
        return {"authorized": True, "authorization_id": "auth-1", "signer_id": "creator"}
    return {"authorized": False, "reason": "no signed authorization"}


class ModelPolicyTests(unittest.IsolatedAsyncioTestCase):
    async def test_require_authorization_passes_with_signed_approval(self):
        with patch.object(
            model_policy.CreatorApprovalService,
            "check_authorization",
            new=AsyncMock(return_value=authority()),
        ):
            result = await model_policy.require_authorization(
                FakeDB(), model_policy.PAID_ACTION
            )
        self.assertEqual(result["authorization_id"], "auth-1")

    async def test_require_authorization_raises_without_approval(self):
        with patch.object(
            model_policy.CreatorApprovalService,
            "check_authorization",
            new=AsyncMock(return_value=authority(False)),
        ):
            with self.assertRaises(model_policy.ModelPolicyDenied):
                await model_policy.require_authorization(FakeDB(), model_policy.PAID_ACTION)

    async def test_router_rejects_allow_paid_without_signed_authorization(self):
        request = modelrouter.SelectRequest(task_type="coding", allow_paid=True)
        with patch.object(
            model_policy.CreatorApprovalService,
            "check_authorization",
            new=AsyncMock(return_value=authority(False)),
        ):
            with self.assertRaises(HTTPException) as caught:
                await modelrouter.select_model(request, FakeDB())
        self.assertEqual(caught.exception.status_code, 403)

    async def test_chat_rejects_allow_paid_before_any_provider_call(self):
        request = models.ChatRequest(
            messages=[models.ChatMessage(role="user", content="hi")],
            allow_paid=True,
        )
        status = SimpleNamespace(mode="ollama", model=settings.iam_primary_model)
        with (
            patch.object(
                model_policy.CreatorApprovalService,
                "check_authorization",
                new=AsyncMock(return_value=authority(False)),
            ),
            patch.object(
                models.inference_service, "resolve", new=AsyncMock(return_value=status)
            ),
            patch.object(
                models.inference_service,
                "chat",
                new=AsyncMock(side_effect=AssertionError("must not be called")),
            ),
        ):
            with self.assertRaises(HTTPException) as caught:
                await models.chat_completion(request, FakeDB())
        self.assertEqual(caught.exception.status_code, 403)

    async def test_skill_invocation_without_authorization_is_recorded_not_executed(self):
        request = models.ChatRequest(
            messages=[models.ChatMessage(role="user", content="hi")],
            skill="demo-skill",
        )
        status = SimpleNamespace(mode="ollama", model=settings.iam_primary_model)
        with (
            patch.object(
                model_policy.CreatorApprovalService,
                "check_authorization",
                new=AsyncMock(return_value=authority(False)),
            ),
            patch.object(
                models.SkillRuntimeService,
                "invoke",
                new=AsyncMock(side_effect=AssertionError("must not be called")),
            ),
            patch.object(
                models,
                "assemble_context",
                new=AsyncMock(return_value=SimpleNamespace(as_system_message=lambda: None)),
            ),
        ):
            _messages, delegation, action = await models._prepare_messages(
                request, FakeDB(), status
            )
        self.assertIsNone(delegation)
        self.assertEqual(action["status"], "denied")
        self.assertEqual(action["skill"], "demo-skill")


if __name__ == "__main__":
    unittest.main()
