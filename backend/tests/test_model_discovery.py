"""OD-52 Phase B: dual discovery, merge precedence and conservative persistence."""

import unittest
import uuid
from unittest.mock import patch

from app.models.modelrouter import AIProvider, DiscoveredModel
from app.services.model_discovery import ModelDiscoveryService
from app.services.providers.base import ModelSpec
from app.services.providers.models_dev import ModelsDevClient
from app.services.providers.nvidia import NvidiaProvider


class FakeResult:
    def __init__(self, rows):
        self.rows = list(rows)

    def scalars(self):
        return self

    def all(self):
        return self.rows

    def scalar_one_or_none(self):
        return self.rows[0] if self.rows else None


class FakeDB:
    def __init__(self, rows=None):
        self.rows = list(rows or [])

    async def execute(self, statement):
        try:
            froms = list(statement.froms)
            name = getattr(froms[0], "name", "") if froms else ""
        except Exception:
            name = str(statement)
        return FakeResult(
            [r for r in self.rows if getattr(r.__class__, "__tablename__", "") in name]
        )

    def add(self, obj):
        if getattr(obj, "id", None) is None:
            obj.id = uuid.uuid4()
        self.rows.append(obj)

    async def flush(self):
        return None

    async def commit(self):
        return None


class FakeResponse:
    def __init__(self, data, status_code=200):
        self._data = data
        self.status_code = status_code

    def json(self):
        return self._data


class FakeClient:
    def __init__(self, response):
        self.response = response

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def get(self, *args, **kwargs):
        return self.response


class FakeProvider:
    name = "nvidia"

    async def discover(self):
        return [
            ModelSpec(
                provider="nvidia",
                model_id="nvidia/free",
                display_name="catalogue name",
                access_type="free",
                context_length=100,
                metadata_source="nvidia_catalog",
            ),
            ModelSpec(
                provider="nvidia",
                model_id="nvidia/paid",
                display_name="paid",
                access_type="paid",
                metadata_source="nvidia_catalog",
            ),
        ]

    async def metadata(self):
        return {
            "nvidia/free": ModelSpec(
                provider="nvidia",
                model_id="nvidia/free",
                display_name="metadata name",
                access_type="paid",
                context_length=262144,
                tool_calling=True,
                reasoning=True,
                structured_output=True,
                metadata_source="models.dev",
            )
        }


class ModelDiscoveryTests(unittest.IsolatedAsyncioTestCase):
    async def test_merge_uses_live_access_and_metadata_capabilities(self):
        specs = ModelDiscoveryService.merge(
            await FakeProvider().discover(), await FakeProvider().metadata(), "nvidia"
        )
        self.assertEqual(len(specs), 1)  # paid model filtered in free-only mode
        spec = specs[0]
        self.assertEqual(spec.access_type, "free")
        self.assertEqual(spec.context_length, 262144)
        self.assertTrue(spec.tool_calling and spec.reasoning and spec.structured_output)
        self.assertEqual(spec.endpoint_status, "unknown")
        self.assertIn("nvidia_catalog", spec.metadata_source)

    async def test_persistence_never_claims_availability(self):
        db = FakeDB([AIProvider(id=uuid.uuid4(), name="nvidia", provider_type="nvidia")])
        with patch("app.services.model_discovery._provider", return_value=FakeProvider()):
            written = await ModelDiscoveryService(db).discover("nvidia")
        row = [r for r in db.rows if isinstance(r, DiscoveredModel)][0]
        self.assertEqual(len(written), 1)
        self.assertEqual(row.model_type, "llm")
        self.assertEqual(row.endpoint_status, "unknown")
        self.assertTrue(row.tool_calling)
        self.assertEqual(row.access_type, "free")
        self.assertTrue(row.is_free)
        self.assertTrue(row.alias.startswith("nv-"))
        self.assertEqual(row.last_known_good["model_ids"], [])
        self.assertIsNone(row.last_tested)

    async def test_models_dev_specifications_are_normalised(self):
        data = {
            "nvidia": {
                "models": {
                    "nvidia/nemotron-3.5-lightning-30b-a3b": {
                        "name": "Nemotron Lightning",
                        "modalities": {"input": ["text"], "output": ["text"]},
                        "limit": {"context": 262144},
                        "cost": {"input": 0, "output": 0},
                        "tool_call": True,
                        "reasoning": True,
                        "structured_output": True,
                    }
                }
            }
        }
        with patch("app.services.providers.models_dev.httpx.AsyncClient",
                   return_value=FakeClient(FakeResponse(data))):
            specs = await ModelsDevClient().fetch("nvidia")
        spec = specs["nvidia/nemotron-3.5-lightning-30b-a3b"]
        self.assertEqual(spec.access_type, "free")
        self.assertEqual(spec.context_length, 262144)
        self.assertTrue(spec.tool_calling)
        self.assertEqual(spec.metadata_source, "models.dev")

    async def test_nvidia_catalogue_respects_free_only(self):
        data = {
            "data": [
                {"id": "nvidia/nemotron-3.5-lightning-30b-a3b"},
                {"id": "openai/gpt-4o-mini"},
            ]
        }
        with patch("app.services.providers.nvidia.httpx.AsyncClient",
                   return_value=FakeClient(FakeResponse(data))), \
             patch("app.services.providers.nvidia.settings.nvidia_api_key", "key"):
            specs = await NvidiaProvider().discover()
        self.assertEqual([s.model_id for s in specs], ["nvidia/nemotron-3.5-lightning-30b-a3b"])
        self.assertTrue(all(s.endpoint_status == "unknown" for s in specs))


if __name__ == "__main__":
    unittest.main()
