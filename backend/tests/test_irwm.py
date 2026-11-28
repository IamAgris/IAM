"""OD-39 IRWM runtime enforcement tests."""

import asyncio
import unittest
from unittest.mock import patch

from app.core.config import settings
from app.services.adaptive_model_selector import ResourceSnapshot
from app.services.irwm import IRWM


class IRWMTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.unloaded = []
        self.irwm = IRWM(
            ResourceSnapshot(8192, 6000, 4, False, source="test"),
            unloader=lambda model: self.unloaded.append(model) or True,
        )

    async def test_single_resident_and_request(self):
        with patch.object(settings, "adaptive_reserved_ram_mb", 1500), patch.object(
            settings, "irwm_max_concurrent", 1
        ):
            first = await self.irwm.admit("local-qwen-3b", 2500, 8192)
            self.assertEqual(first["decision"], "admit")
            self.assertEqual(first["context_tokens"], 4096)
            second = await self.irwm.admit("local-qwen-3b", 2500)
            self.assertEqual(second["decision"], "queue")
            self.assertEqual(second["queue_depth"], 1)
            self.assertEqual(second["resident_model"], "local-qwen-3b")

    async def test_different_model_queued_while_busy(self):
        with patch.object(settings, "adaptive_reserved_ram_mb", 1500):
            await self.irwm.admit("model-a", 2000)
            decision = await self.irwm.admit("model-b", 2000)
            self.assertEqual(decision["decision"], "queue")
            self.assertEqual(self.irwm.resident.model, "model-a")

    async def test_oversized_model_delegated(self):
        with patch.object(settings, "irwm_hard_ceiling_mb", 6000), patch.object(
            settings, "adaptive_reserved_ram_mb", 1500
        ):
            decision = await self.irwm.admit("huge", 7000)
            self.assertEqual(decision["decision"], "delegate")
            self.assertIsNone(self.irwm.resident)

    async def test_release_promotes_queued_request(self):
        with patch.object(settings, "adaptive_reserved_ram_mb", 1500):
            await self.irwm.admit("model-a", 2000)
            await self.irwm.admit("model-a", 2000)
            result = await self.irwm.release("model-a")
            self.assertTrue(result["released"])
            self.assertEqual(result["promoted"]["model"], "model-a")
            self.assertEqual(self.irwm.status()["queue_depth"], 0)

    async def test_idle_unload_and_status(self):
        with patch.object(settings, "irwm_keep_alive_seconds", 0):
            await self.irwm.admit("model-a", 2000)
            await self.irwm.release("model-a")
            self.assertEqual(self.irwm.sweep_idle(), "model-a")
            self.assertEqual(self.unloaded, ["model-a"])
        status = self.irwm.status()
        self.assertIsNone(status["resident"])
        self.assertEqual(status["limits"]["max_concurrent"], settings.irwm_max_concurrent)
        self.assertTrue(status["recent_decisions"])

    async def test_core_reserve_never_sacrificed(self):
        with patch.object(settings, "adaptive_reserved_ram_mb", 5000):
            decision = await self.irwm.admit("model-a", 2000)
            self.assertEqual(decision["decision"], "delegate")
            self.assertIn("reserve", decision["reason"])

    async def test_auto_snapshot_refreshes_after_memory_is_freed(self):
        stale = ResourceSnapshot(4096, 1000, 4, False, source="auto")
        fresh = ResourceSnapshot(4096, 6000, 4, False, source="auto")
        with patch("app.services.irwm.detect_resources", return_value=stale):
            irwm = IRWM()  # auto-detected snapshot, not an injected fixed one
        with patch.object(settings, "adaptive_reserved_ram_mb", 1500), patch(
            "app.services.irwm.detect_resources", return_value=fresh
        ):
            decision = await irwm.admit("model-a", 2000)
            self.assertEqual(decision["decision"], "admit")
            self.assertGreaterEqual(irwm.usable_ram_mb, 2000)

    async def test_cancelled_request_releases_its_lease(self):
        manager = IRWM(ResourceSnapshot(8192, 6000, 4, False, source="test"))
        with patch.object(settings, "adaptive_reserved_ram_mb", 1500):
            admitted = await manager.admit("model-a", 2000, enqueue=False)
        lease_id = admitted["lease_id"]
        from app.services.model_inference import _register_lease_release

        async def abandoned():
            _register_lease_release("model-a", "ollama", lease_id)
            raise asyncio.CancelledError()

        with patch("app.services.irwm.irwm", manager):
            task = asyncio.create_task(abandoned())
            with self.assertRaises(asyncio.CancelledError):
                await task
            await asyncio.sleep(0.05)
        self.assertEqual(manager.resident.in_flight, 0)
        self.assertEqual(manager.resident.leases, {})

    async def test_user_chat_preempts_internal_lease(self):
        manager = IRWM(ResourceSnapshot(8192, 6000, 4, False, source="test"))
        cancelled = []

        class FakeTask:
            def done(self):
                return False

            def cancel(self):
                cancelled.append(True)

        with patch.object(settings, "adaptive_reserved_ram_mb", 1500):
            internal = await manager.admit(
                "model-a", 2000, enqueue=False, purpose="internal", task=FakeTask()
            )
            self.assertEqual(internal["decision"], "admit")
            user = await manager.admit(
                "model-a", 2000, enqueue=False, purpose="user", preemptible=False
            )

        self.assertEqual(user["decision"], "admit")
        self.assertEqual(len(cancelled), 1)
        self.assertEqual(manager.resident.in_flight, 1)
        self.assertIn(
            "preempted_internal",
            [d.get("decision") for d in manager.status()["recent_decisions"]],
        )

    async def test_lease_release_is_idempotent(self):
        with patch.object(settings, "adaptive_reserved_ram_mb", 1500):
            admitted = await self.irwm.admit("model-a", 2000)
        lease_id = admitted["lease_id"]
        first = await self.irwm.release("model-a", lease_id)
        second = await self.irwm.release("model-a", lease_id)
        self.assertTrue(first["released"])
        self.assertFalse(second["released"])
        self.assertEqual(self.irwm.status()["resident"]["in_flight"], 0)


if __name__ == "__main__":
    unittest.main()
