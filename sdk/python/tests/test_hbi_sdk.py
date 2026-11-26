"""Unit tests for the HBI SDK surface exposed to IAM's mainbrain.

No network calls: the transport request method is mocked.
"""

import unittest
from unittest.mock import AsyncMock, patch

from iam_sdk.client import IAM, _Transport


class HBISDKTests(unittest.IsolatedAsyncioTestCase):
    async def test_hbi_surface(self):
        iam = IAM("http://iam.test")
        with patch.object(
            _Transport, "request", new_callable=AsyncMock, return_value={"ok": True}
        ) as request:
            self.assertTrue((await iam.hbi.status())["ok"])
            await iam.hbi.research.search("community response", "research")
            await iam.hbi.knowledge.retrieve("trust", tier="T1")
            await iam.hbi.behaviour.predict({
                "question": "Will participation rise?", "target": "participation",
                "purpose": "research", "features": {"support": 1.0},
            })
            await iam.hbi.prediction.evaluate({"probability": {"positive": 0.7}}, 1)
            await iam.hbi.history.analogy({"similarities": {}}, {"event_id": "e1"})
            await iam.hbi.uncertainty("community response", "research")

        paths = [call.args[1] for call in request.await_args_list]
        self.assertEqual(paths[0], "/api/v1/hbi/status")
        self.assertIn("/api/v1/hbi/behaviour/forecast", paths)
        self.assertIn("/api/v1/hbi/history/analogy", paths)
        self.assertTrue(any(p.startswith("/api/v1/hbi/uncertainty/assess") for p in paths))
        self.assertTrue(any("tier=T1" in path for path in paths))

    async def test_hbi_is_versioned_namespace(self):
        iam = IAM("http://iam.test")
        self.assertTrue(hasattr(iam.hbi, "research"))
        self.assertTrue(hasattr(iam.hbi, "knowledge"))
        self.assertTrue(hasattr(iam.hbi, "behaviour"))
        self.assertTrue(hasattr(iam.hbi, "prediction"))
        self.assertTrue(hasattr(iam.hbi, "history"))


if __name__ == "__main__":
    unittest.main()
