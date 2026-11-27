"""Tests for Phase 2 repository-intelligence features."""

import sys
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))

from agent_api import plan  # noqa: E402
from intel_core import (  # noqa: E402
    HybridSearch,
    build_code_index,
    change_impact,
    import_cycles,
    load_code_index,
    symbol_report,
)


class CodeIntelligenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.index_path = build_code_index()
        cls.index = load_code_index()
        cls.search = HybridSearch()
        if not cls.search.db_path.is_file():
            cls.search.build()

    def test_index_extracts_definitions_calls_and_routes(self):
        self.assertTrue(self.index["definitions"])
        self.assertTrue(self.index["calls"])
        self.assertTrue(self.index["routes"])

    def test_symbol_report_connects_definition_callers_and_importers(self):
        report = symbol_report("IntelligenceRouter", self.index)
        self.assertTrue(report["definitions"])
        self.assertIn("modelrouter.py", str(report["call_sites"]))
        self.assertIn("modelrouter.py", str(report["importers"]))

    def test_search_prioritises_exact_filename(self):
        results = self.search.search("modelrouter", 10)
        self.assertTrue(any(
            r["source"] == "filename"
            and r["path"] == "backend/app/api/routes/modelrouter.py"
            for r in results
        ))

    def test_search_finds_hyphenated_document_token(self):
        results = self.search.search("OD-46", 10)
        self.assertTrue(any("PRIMARY_MODEL_UNIFICATION" in r["path"] for r in results))

    def test_change_impact_maps_changed_file_to_tests_and_specs(self):
        report = change_impact(["backend/app/api/routes/modelrouter.py"], self.index)
        self.assertIn("backend/app/api/routes/modelrouter.py", report["affected_files"])
        self.assertTrue(report["specs"])
        self.assertIn(report["risk"], ("low", "medium", "high"))

    def test_cycle_detection_returns_a_list(self):
        self.assertIsInstance(import_cycles(self.index), list)

    def test_search_planner_selects_strategy(self):
        self.assertEqual(plan("who calls IntelligenceRouter?")["strategy"], ["symbol", "impact"])
        self.assertEqual(plan("when was this introduced?")["strategy"], ["history"])


if __name__ == "__main__":
    unittest.main()
