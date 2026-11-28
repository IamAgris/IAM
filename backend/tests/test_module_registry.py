"""The module registry is the single declaration of dispatchable capabilities."""

import unittest

from app.orchestration import dispatch
from app.services.module_registry import (
    action_for_objective,
    available_actions,
    contract,
    discover,
)


class ModuleRegistryTests(unittest.IsolatedAsyncioTestCase):
    def test_discovery_exposes_structured_contracts(self):
        modules = discover()
        self.assertGreaterEqual(len(modules), 10)
        for item in modules:
            self.assertIn("action", item)
            self.assertIn("service", item)
            self.assertIn("authority", item)
            self.assertIn("side_effect", item)

    def test_dispatch_allowlist_comes_from_registry(self):
        self.assertEqual(set(dispatch.AVAILABLE), set(available_actions()))
        self.assertIsNotNone(contract("research"))
        self.assertIsNone(contract("not_a_module"))

    def test_objective_keywords_use_declared_contracts(self):
        self.assertEqual(action_for_objective("Research the market"), "research")
        self.assertEqual(action_for_objective("recall memory"), "memory_recall")
        self.assertIsNone(action_for_objective("something unrecognised"))

    async def test_unknown_action_fails_closed(self):
        result = await dispatch.dispatch(None, "not_a_module", {})
        self.assertEqual(result["status"], "failure")
        self.assertEqual(result["error"], "unknown_action")


if __name__ == "__main__":
    unittest.main()
