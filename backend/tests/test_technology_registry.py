"""Unit tests for the Doc 20 Technology Capability Registry (no DB required)."""

import unittest
from datetime import datetime
from types import SimpleNamespace

from app.services.technology_registry_service import (
    TechnologyRegistryError,
    TechnologyRegistryService,
)


class TransitionTests(unittest.TestCase):
    def test_ordered_path(self):
        service = TechnologyRegistryService(None)
        self.assertTrue(service.is_valid_transition("researched", "tested"))
        self.assertTrue(service.is_valid_transition("tested", "approved"))
        self.assertTrue(service.is_valid_transition("approved", "integrated"))

    def test_no_direct_to_integrated(self):
        service = TechnologyRegistryService(None)
        self.assertFalse(service.is_valid_transition("researched", "integrated"))
        self.assertFalse(service.is_valid_transition("tested", "integrated"))

    def test_terminal_states(self):
        service = TechnologyRegistryService(None)
        self.assertFalse(service.is_valid_transition("integrated", "approved"))
        self.assertFalse(service.is_valid_transition("rejected", "tested"))
        self.assertFalse(service.is_valid_transition("deprecated", "researched"))

    def test_invalid_state(self):
        service = TechnologyRegistryService(None)
        self.assertFalse(service.is_valid_transition("researched", "deployed"))
        self.assertFalse(service.is_valid_transition("invented", "tested"))


class InputTests(unittest.IsolatedAsyncioTestCase):
    async def test_name_required(self):
        service = TechnologyRegistryService(None)
        with self.assertRaises(TechnologyRegistryError):
            await service.register({"name": ""})

    async def test_invalid_cost_status(self):
        service = TechnologyRegistryService(None)
        with self.assertRaises(TechnologyRegistryError):
            await service.register({"name": "Example", "cost_status": "unlimited"})


class SerialisationTests(unittest.TestCase):
    def test_registry_fields_present(self):
        record = SimpleNamespace(
            id="00000000-0000-0000-0000-000000000001",
            name="PydanticAI", version="0.1", official_source="github",
            source_url="https://example.invalid", language="python",
            architectures=["amd64", "arm64"], licence="MIT",
            commercial_use_ok=True, cost_status="open_source",
            hardware_requirements={}, capabilities=["agents"],
            limitations=["beta"], security_status=" reviewed ",
            maintenance_status="active", compatibility={},
            test_results=[], benchmarks=[], lifecycle_state="researched",
            notes=None, discovered_at=datetime(2026, 11, 27),
            last_reviewed_at=None,
        )
        payload = TechnologyRegistryService._to_dict(record)
        self.assertEqual(payload["cost_status"], "open_source")
        self.assertEqual(payload["lifecycle_state"], "researched")
        self.assertEqual(payload["architectures"], ["amd64", "arm64"])


if __name__ == "__main__":
    unittest.main()
