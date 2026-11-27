"""Doc 29 P6 tests: onion intelligence, safe files, Creator controls, emergency."""

import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from app.core.config import settings
from app.services.tor_privacy import (
    OnionServiceIntelligence,
    TorCreatorControls,
    TorEmergencyController,
    TorFilePipeline,
    TorPrivacyError,
    validate_onion_address,
)

VALID = "a" * 56 + ".onion"


class FakeResult:
    def __init__(self, rows):
        self.rows = rows

    def scalar_one_or_none(self):
        return self.rows[0] if self.rows else None

    def scalars(self):
        return self

    def all(self):
        return self.rows


class FakeDB:
    def __init__(self):
        self.rows = []

    def add(self, obj):
        if obj not in self.rows:
            self.rows.append(obj)

    async def commit(self):
        return None

    async def execute(self, statement):
        entity = statement.column_descriptions[0]["entity"]
        return FakeResult([r for r in self.rows if isinstance(r, entity)])


def intelligence_with_db():
    db = FakeDB()
    service = OnionServiceIntelligence(db)
    service.evidence = MagicMock()
    service.evidence.append_audit = AsyncMock(return_value="audit-1")
    return service, db


class AddressTests(unittest.TestCase):
    def test_v3_validation(self):
        self.assertTrue(validate_onion_address(VALID))
        self.assertTrue(validate_onion_address(("B" * 56) + ".ONION"))
        self.assertFalse(validate_onion_address("a" * 16 + ".onion"))
        self.assertFalse(validate_onion_address("not-an-address"))


class OnionTests(unittest.IsolatedAsyncioTestCase):
    async def test_observe_and_assess_never_confirm_operator(self):
        service, db = intelligence_with_db()
        await service.observe(
            VALID,
            claimed_operator="Example Hosting",
            source_urls=["https://alpha.example/report", "https://beta.example/report"],
            actor="iam",
        )
        with patch.object(
            service, "check_availability",
            new_callable=AsyncMock,
            return_value={"reachable": True, "status_code": 200},
        ):
            result = await service.assess(VALID, actor="iam")
        self.assertEqual(result["status"], "observed")
        self.assertNotEqual(result["status"], "confirmed")
        self.assertEqual(result["confidence"], "low")

    async def test_impersonation_marks_suspicious(self):
        service, _ = intelligence_with_db()
        await service.observe(VALID, claimed_operator="PayPal Support")
        with patch.object(
            service, "check_availability",
            new_callable=AsyncMock,
            return_value={"reachable": True},
        ):
            result = await service.assess(VALID)
        self.assertEqual(result["status"], "suspicious")
        self.assertIn("paypal", result["impersonation_terms"])

    async def test_availability_fails_closed_when_disabled(self):
        service, _ = intelligence_with_db()
        with patch.object(settings, "tor_onion_access_enabled", False):
            result = await service.check_availability(VALID)
        self.assertFalse(result["reachable"])


class FilePipelineTests(unittest.IsolatedAsyncioTestCase):
    async def test_quarantine_and_legal_gate(self):
        service = TorFilePipeline(object())
        service.gateway = MagicMock()
        service.gateway.quarantine_download = AsyncMock(return_value={
            "status": "quarantined", "sha256": "abc", "executed": False,
        })
        service.gateway.evidence = MagicMock()
        service.gateway.evidence.append_audit = AsyncMock(return_value="audit-1")
        with patch(
            "app.services.tor_privacy.IPLCIService"
        ) as iplci_cls:
            iplci_cls.return_value.gate_check = AsyncMock(
                return_value={"decision": "BLOCKED"}
            )
            result = await service.process(
                "/tmp/download.pdf", original_name="download.pdf", task_id="task-1"
            )
        self.assertEqual(result["status"], "quarantined")
        self.assertEqual(result["licence_decision"], "BLOCKED")
        self.assertFalse(result["executed"])


class ControlTests(unittest.IsolatedAsyncioTestCase):
    def _manager(self):
        manager = MagicMock()
        manager.sessions = {"s1": {"session_id": "s1", "is_tor": True, "handle": object()}}
        manager.privacy.kill_switch = True
        manager.evidence = MagicMock()
        manager.evidence.append_audit = AsyncMock(return_value="audit-1")
        manager.monitor = MagicMock()
        manager.monitor.health = AsyncMock(return_value={
            "control_port": True, "socks_port": False,
        })
        return manager

    async def test_creator_controls_and_policy(self):
        manager = self._manager()
        controls = TorCreatorControls(manager)
        with patch.object(settings, "tor_onion_access_enabled", False), \
             patch.object(settings, "tor_bandwidth_limit_kbps", 0):
            policy = controls.policy()
            self.assertTrue(policy["kill_switch"])
            controls.set_onion_access(True, "creator")
            self.assertTrue(settings.tor_onion_access_enabled)
            controls.set_bandwidth_limit(100, "creator")
            self.assertEqual(settings.tor_bandwidth_limit_kbps, 100)
            with self.assertRaises(TorPrivacyError):
                controls.set_session_duration(5, "creator")
        self.assertEqual(len(controls.view_sessions()), 1)

    async def test_emergency_stop_engages_all_guards(self):
        manager = self._manager()
        manager.terminate_all = AsyncMock(return_value={"terminated": 1})
        controller = TorEmergencyController(manager)
        with patch.object(settings, "tor_onion_access_enabled", True):
            result = await controller.stop("creator")
        self.assertEqual(result["terminated"], 1)
        self.assertFalse(result["onion_access"])
        self.assertTrue(result["credential_isolation"])
        self.assertFalse(result["fallback_to_standard_browser"])

    async def test_suspicious_connection_detection(self):
        manager = self._manager()
        result = await TorEmergencyController(manager).suspicious_connections()
        self.assertTrue(result["suspicious"])
        self.assertIn("control port reachable but SOCKS port unavailable", result["reasons"])

    async def test_crash_cleanup_removes_stale_profiles(self):
        manager = self._manager()
        with tempfile.TemporaryDirectory() as tmp:
            stale = Path(tmp) / "old-session"
            stale.mkdir()
            old = datetime.now(timezone.utc) - timedelta(days=2)
            import os
            os.utime(stale, (old.timestamp(), old.timestamp()))
            manager._profile_root = lambda: Path(tmp)
            manager._reap_expired = AsyncMock()
            result = await TorEmergencyController(manager).cleanup_after_crash()
            self.assertEqual(result["profiles_removed"], 1)
            self.assertFalse(stale.exists())


if __name__ == "__main__":
    unittest.main()
