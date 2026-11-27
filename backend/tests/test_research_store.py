"""Artifact store selection: local by default, durable S3 when configured."""

import unittest
from unittest.mock import MagicMock, patch

from app.core.config import settings
from app.services.ai_research import release_gate
from app.services.ai_research.artifacts import FileSystemArtifactStore


class ResearchStoreTests(unittest.TestCase):
    def test_local_default(self):
        with patch.object(settings, "research_artifact_store", "local"):
            store = release_gate.default_release_store()
        self.assertIsInstance(store, FileSystemArtifactStore)

    def test_s3_selection_uses_existing_bucket_and_prefix(self):
        fake = MagicMock()
        with (
            patch.object(settings, "research_artifact_store", "s3"),
            patch.object(settings, "s3_bucket", "aura-storage"),
            patch.object(settings, "research_artifact_prefix", "research"),
            patch(
                "app.services.ai_research.s3_store.S3ArtifactStore", return_value=fake
            ),
        ):
            store = release_gate.default_release_store()
        self.assertIs(store, fake)


if __name__ == "__main__":
    unittest.main()
