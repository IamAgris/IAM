"""OD-52 Phase A: live catalogue registry schema evidence."""

import json
import unittest
from pathlib import Path

from app.models.modelrouter import DiscoveredModel

REPO = Path(__file__).resolve().parents[2]
MIGRATIONS = REPO / "backend" / "app" / "db" / "migrations"


class ModelCatalogSchemaTests(unittest.TestCase):
    def test_registry_fields_exist(self):
        columns = set(DiscoveredModel.__table__.columns.keys())
        expected = {
            "model_type", "access_type", "endpoint_status", "alias",
            "input_capabilities", "output_capabilities", "tool_calling",
            "reasoning", "structured_output", "api_protocol", "last_tested",
            "test_result", "restrictions", "metadata_source", "last_known_good",
        }
        self.assertTrue(expected.issubset(columns), sorted(expected - columns))

    def test_catalogue_entry_does_not_claim_availability(self):
        column = DiscoveredModel.__table__.c.endpoint_status
        self.assertFalse(column.nullable)
        self.assertEqual(column.default.arg, "unknown")

    def test_capabilities_are_false_until_tested(self):
        for name in ("tool_calling", "reasoning", "structured_output"):
            column = DiscoveredModel.__table__.c[name]
            self.assertFalse(column.default.arg, name)

    def test_free_access_is_the_safe_default(self):
        self.assertEqual(DiscoveredModel.__table__.c.access_type.default.arg, "free")
        self.assertEqual(
            DiscoveredModel.__table__.c.api_protocol.default.arg, "chat_completions"
        )

    def test_constraints_present(self):
        names = {constraint.name for constraint in DiscoveredModel.__table__.constraints}
        expected = {
            "ck_discovered_model_type", "ck_discovered_model_access",
            "ck_discovered_model_endpoint_status", "ck_discovered_model_protocol",
        }
        self.assertTrue(expected.issubset(names), sorted(expected - names))

    def test_migration_is_registered_and_includes_backfill(self):
        manifest = json.loads((MIGRATIONS / "MIGRATION_ORDER.json").read_text(encoding="utf-8"))
        entries = [item["path"] for item in manifest["files"]]
        self.assertIn("060_model_catalog.sql", entries)
        sql = (MIGRATIONS / "060_model_catalog.sql").read_text(encoding="utf-8")
        self.assertIn("endpoint_status", sql)
        self.assertIn("metadata_source = COALESCE", sql)
        self.assertIn("WHERE metadata_source IS NULL OR metadata_source = 'legacy'", sql)


if __name__ == "__main__":
    unittest.main()
