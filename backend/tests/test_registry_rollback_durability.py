"""Rollback must survive process restart (registry hydration evidence)."""

import tempfile
import unittest
from pathlib import Path

from app.services.ai_research.artifacts import FileSystemArtifactStore
from app.services.ai_research.base import ResearchError
from app.services.ai_research.registry import ModelRegistry, ModelVersion


def version(name: str, score: float) -> ModelVersion:
    return ModelVersion(
        model="local-qwen-coder-3b",
        version=name,
        checkpoint_ref=f"ckpt-{name}",
        capability_profile={"coding": score},
        benchmark_score=score,
    )


class RollbackDurabilityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = FileSystemArtifactStore(Path(self.tmp.name) / "store")

    def _deploy(self, registry, name, score):
        registry.register(version(name, score))
        registry.approve("local-qwen-coder-3b", name)
        registry.deploy("local-qwen-coder-3b", name)

    def test_rollback_active_version_survives_hydration(self):
        registry = ModelRegistry(self.store)
        self._deploy(registry, "v1", 0.6)
        self._deploy(registry, "v2", 0.9)

        registry.rollback("local-qwen-coder-3b", "v1")
        self.assertEqual(registry.active("local-qwen-coder-3b"), "v1")
        self.assertEqual(
            registry.get("local-qwen-coder-3b", "v1").status, "deployed"
        )
        self.assertEqual(
            registry.get("local-qwen-coder-3b", "v2").status, "rolled_back"
        )

        restarted = ModelRegistry(self.store)
        restarted.hydrate()
        self.assertEqual(restarted.active("local-qwen-coder-3b"), "v1")

    def test_unknown_target_is_controlled_error(self):
        registry = ModelRegistry(self.store)
        self._deploy(registry, "v1", 0.6)
        with self.assertRaises(ResearchError):
            registry.rollback("local-qwen-coder-3b", "missing")


if __name__ == "__main__":
    unittest.main()
