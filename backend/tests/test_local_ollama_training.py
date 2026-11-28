"""Local Ollama development path.

The driver creates a real servable model through /api/create and writes a
versioned checkpoint artifact. It is prompt/template adaptation, not weight
fine-tuning; tests assert it never claims otherwise.
"""

import json
import tempfile
import unittest
import uuid
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app.core.config import settings
from app.orchestration.model_development import CapabilityAssessment, FoundationModelDeveloper
from app.services.ai_research.artifacts import FileSystemArtifactStore
from app.services.ai_research.local_ollama_training import (
    LocalOllamaTrainingDriver,
    local_training_adapters,
)


class FakeResponse:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = payload or {}
        self.text = json.dumps(self._payload)

    def json(self):
        return self._payload


class FakeClient:
    posts = []
    tags = []

    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def post(self, url, json=None):
        FakeClient.posts.append((url, json))
        return FakeResponse()

    async def get(self, url):
        return FakeResponse(payload={"models": FakeClient.tags})


class LocalOllamaDriverTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        FakeClient.posts = []
        FakeClient.tags = []
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = FileSystemArtifactStore(Path(self.tmp.name))
        self.driver = LocalOllamaTrainingDriver(
            base_model="qwen2.5:3b",
            candidate_model="qwen2.5:3b-candidate",
            weakness="reasoning is weak",
            store=self.store,
            client_factory=FakeClient,
        )

    async def test_driver_creates_model_and_checkpoint_artifact(self):
        external_id = await self.driver.provision(SimpleNamespace(task_id="exp_local"))
        await self.driver.start(external_id)

        url, payload = FakeClient.posts[0]
        self.assertTrue(url.endswith("/api/create"))
        self.assertEqual(payload["name"], "qwen2.5:3b-candidate")
        self.assertIn("FROM qwen2.5:3b", payload["modelfile"])

        FakeClient.tags = [{"name": "qwen2.5:3b-candidate"}]
        from app.services.free_sandboxes.base import EnvironmentState

        self.assertEqual(
            await self.driver.status(external_id), EnvironmentState.COMPLETED
        )

        checkpoint = await self.driver.collect(external_id)
        self.assertEqual(checkpoint["method"], "ollama_create")
        self.assertFalse(checkpoint["weight_fine_tuning"])
        stored = json.loads(self.store.get(checkpoint["checkpoint_ref"]).decode())
        self.assertEqual(stored["model"], "qwen2.5:3b-candidate")

    async def test_start_fails_closed_when_ollama_rejects(self):
        class RejectingClient(FakeClient):
            async def post(self, url, json=None):
                return FakeResponse(status_code=400)

        driver = LocalOllamaTrainingDriver(
            base_model="qwen2.5:3b",
            candidate_model="candidate",
            store=self.store,
            client_factory=RejectingClient,
        )
        external_id = await driver.provision(SimpleNamespace(task_id="exp_local"))
        with self.assertRaises(Exception):
            await driver.start(external_id)


class DeveloperLocalPathTests(unittest.IsolatedAsyncioTestCase):
    async def test_developer_creates_checkpoint_before_delegation(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        store = FileSystemArtifactStore(Path(tmp.name) / "chain")
        adapters = local_training_adapters(
            base_model="qwen2.5:3b",
            candidate_model="qwen2.5:3b-candidate",
            store=store,
            client_factory=FakeClient,
        )
        developer = FoundationModelDeveloper(
            SimpleNamespace(),
            adapters=[],
            evaluate=lambda _spec, _model: 0.8,
            store=store,
            licence="CC-BY-4.0",
        )
        weakness = CapabilityAssessment(
            model_id="qwen2.5:3b",
            capability="reasoning",
            score=0.5,
            confidence=0.5,
            evidence="held-out evaluation",
            dataset="held_out_eval",
            assessed_at="2026-11-28T10:00:00+00:00",
        )
        outcome = {"status": "candidate", "model": "qwen2.5:3b-candidate", "version": "v1"}
        with (
            patch.object(settings, "model_development_local_training", True),
            patch.object(settings, "training_consent_types", ["public_knowledge"]),
            patch(
                "app.services.ai_research.local_ollama_training.local_training_adapters",
                return_value=adapters,
            ),
            patch(
                "app.services.ai_research.self_improvement.prepare_candidate",
                new=AsyncMock(return_value=outcome),
            ) as prepare,
        ):
            result = await developer.prepare_candidate(weakness)

        request = prepare.await_args.args[1]
        self.assertIn("checkpoint", request.checkpoint_ref)
        self.assertEqual(request.consent_types, frozenset({"public_knowledge"}))
        self.assertEqual(result["training_method"], "ollama_create")
        self.assertFalse(result["weight_fine_tuning"])


if __name__ == "__main__":
    unittest.main()
