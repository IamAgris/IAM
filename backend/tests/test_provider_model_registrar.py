"""OD-52 Phase C: runtime LiteLLM registration with one key and no secret leak."""

import json
import unittest
from unittest.mock import patch

from app.services.provider_model_registrar import ProviderModelRegistrar
from app.services.providers.base import ModelSpec


class FakeResponse:
    def __init__(self, data, status_code=200):
        self._data = data
        self.status_code = status_code
        self.content = json.dumps(data).encode()

    def json(self):
        return self._data


class FakeClient:
    calls = []

    def __init__(self, responses):
        self.responses = list(responses)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def request(self, method, url, headers=None, json=None):
        FakeClient.calls.append({"method": method, "url": url, "headers": headers, "json": json})
        return self.responses.pop(0)


def _spec(alias="nv-nvidia-free", model_id="nvidia/free"):
    return ModelSpec(
        provider="nvidia", model_id=model_id, display_name="Free", alias=alias
    )


class ProviderModelRegistrarTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        FakeClient.calls = []

    async def test_disabled_does_not_call_gateway(self):
        with patch(
            "app.services.provider_model_registrar.settings.model_catalog_registration_enabled",
            False,
        ), patch("app.services.provider_model_registrar.httpx.AsyncClient") as client:
            result = await ProviderModelRegistrar().sync([_spec()])
        self.assertFalse(result["enabled"])
        client.assert_not_called()

    async def test_registers_free_model_with_env_reference_and_retires_stale(self):
        existing = {
            "data": [
                {"model_name": "nvidia-nemotron-3.5-lightning", "id": "static-1", "model_info": {}},
                {"model_name": "nv-old", "id": "managed-1", "model_info": {"iam_managed": True}},
            ]
        }
        responses = [FakeResponse(existing), FakeResponse({"id": "new"}), FakeResponse({"deleted": True})]
        with patch(
            "app.services.provider_model_registrar.settings.model_catalog_registration_enabled",
            True,
        ), patch(
            "app.services.provider_model_registrar.httpx.AsyncClient",
            side_effect=lambda *a, **k: FakeClient(responses),
        ):
            result = await ProviderModelRegistrar().sync([_spec()])
        creates = [c for c in FakeClient.calls if c["url"].endswith("/model/new")]
        deletes = [c for c in FakeClient.calls if c["url"].endswith("/model/delete")]
        self.assertEqual(len(creates), 1)
        payload = creates[0]["json"]
        self.assertEqual(payload["litellm_params"]["api_key"], "os.environ/NVIDIA_API_KEY")
        self.assertTrue(payload["model_info"]["iam_managed"])
        self.assertEqual(len(deletes), 1)
        self.assertEqual(deletes[0]["json"]["id"], "managed-1")
        self.assertEqual(result["created"], ["nv-nvidia-free"])
        self.assertEqual(result["retired"], ["nv-old"])

    async def test_no_literal_key_in_any_request(self):
        responses = [FakeResponse({"data": []}), FakeResponse({"id": "new"})]
        with patch(
            "app.services.provider_model_registrar.settings.model_catalog_registration_enabled",
            True,
        ), patch(
            "app.services.provider_model_registrar.httpx.AsyncClient",
            side_effect=lambda *a, **k: FakeClient(responses),
        ):
            await ProviderModelRegistrar().sync([_spec()])
        serialized = json.dumps(FakeClient.calls)
        self.assertNotIn("nvapi-", serialized)
        self.assertNotIn("literally-secret", serialized)


class RegistrarEligibilityTests(unittest.TestCase):
    def test_chat_llm_is_eligible(self):
        spec = ModelSpec(
            provider="nvidia",
            model_id="nvidia/nemotron-3-5-lightning-30b-a3b",
            display_name="Nemotron 3.5 Lightning",
            alias="nv-nemotron",
            access_type="free",
            model_type="llm",
            api_protocol="chat_completions",
        )
        self.assertTrue(ProviderModelRegistrar._eligible(spec))

    def test_db_backed_entry_id_is_read_from_model_info(self):
        entry = {"model_name": "nv-free", "model_info": {"id": "db-id-1"}}
        self.assertEqual(ProviderModelRegistrar._entry_id(entry), "db-id-1")

    def test_non_chat_catalogue_models_are_ineligible(self):
        for model_id in (
            "openai/whisper-large-v3",
            "nvidia/active-speaker-detection",
            "nvidia/bevformer",
            "nvidia/streampetr",
            "nvidia/sparsedrive",
            "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning",
        ):
            spec = ModelSpec(
                provider="nvidia",
                model_id=model_id,
                display_name=model_id,
                alias="nv-model",
                access_type="free",
                model_type="llm",
                api_protocol="chat_completions",
            )
            with self.subTest(model_id=model_id):
                self.assertFalse(ProviderModelRegistrar._eligible(spec))


if __name__ == "__main__":
    unittest.main()
