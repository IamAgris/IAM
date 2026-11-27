"""Doc 29 P5 tests: TIPS fail-closed behaviour, kill switch and leak guards."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from app.api.routes import tor as tor_routes
from app.core.config import settings
from app.services.tor_intelligence import (
    OfficialTorBrowser,
    TorBrowserNotFound,
    TorCircuitManager,
    TorManager,
    TorNetworkMonitor,
    TorPrivacyGateway,
    TorUnavailable,
)


class FakeLauncher:
    def __init__(self):
        self.opened = []
        self.closed = []

    async def open(self, profile_dir):
        self.opened.append(profile_dir)
        return {"context": MagicMock(close=AsyncMock()), "playwright": MagicMock(stop=AsyncMock())}

    async def close(self, handle):
        self.closed.append(handle)


class GuardTests(unittest.TestCase):
    def test_launch_config_prevents_standard_browser_fallback(self):
        config = OfficialTorBrowser().launch_config()
        self.assertTrue(config["proxy"]["server"].startswith("socks5://"))
        self.assertTrue(config["prefs"]["network.proxy.socks_remote_dns"])
        self.assertFalse(config["prefs"]["media.peerconnection.enabled"])


class ManagerTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.patches = [
            patch.object(settings, "tor_enabled", True),
            patch.object(settings, "tor_data_root", self.tempdir.name),
            patch.object(settings, "tor_max_concurrent_sessions", 1),
        ]
        for item in self.patches:
            item.start()

    async def asyncTearDown(self):
        for item in reversed(self.patches):
            item.stop()
        self.tempdir.cleanup()

    async def test_disabled_tor_fails_closed(self):
        with patch.object(settings, "tor_enabled", False):
            manager = TorManager(object(), launcher=FakeLauncher())
            with self.assertRaises(TorUnavailable):
                await manager.open_session("s1")

    async def test_missing_official_browser_fails_closed(self):
        with patch.object(OfficialTorBrowser, "executable", return_value=None):
            manager = TorManager(object(), launcher=FakeLauncher())
            with self.assertRaises(TorBrowserNotFound):
                await manager.open_session("s2")
        self.assertEqual(manager.sessions, {})

    async def test_tor_session_and_killswitch(self):
        executable = Path(self.tempdir.name) / "tor-browser"
        executable.write_text("fake")
        with patch.object(OfficialTorBrowser, "executable", return_value=executable):
            launcher = FakeLauncher()
            manager = TorManager(object(), launcher=launcher)
            manager.evidence = MagicMock()
            manager.evidence.append_audit = AsyncMock(return_value="audit-1")
            session = await manager.open_session(
                "s3", actor="iam", task_id="tor-task-1"
            )
            self.assertTrue(session["is_tor"])
            allowed = manager.privacy.check_egress("s3", "https://example.com")
            self.assertTrue(allowed["permitted"])
            self.assertTrue(allowed["via_tor"])
            manager.privacy.engage()
            denied = manager.privacy.check_egress(None, "https://example.com")
            self.assertFalse(denied["permitted"])
            self.assertIn("kill switch", denied["reason"])
            await manager.terminate_all()
            self.assertEqual(len(launcher.closed), 1)
            self.assertEqual(manager.sessions, {})
            self.assertTrue(manager.privacy.kill_switch)

    async def test_privacy_gateway_rejects_non_tor_session(self):
        sessions = {"std": {"is_tor": False}}
        gateway = TorPrivacyGateway(sessions)
        self.assertFalse(gateway.check_egress("std", "https://example.com")["permitted"])


class ControlTests(unittest.IsolatedAsyncioTestCase):
    async def test_circuit_status_and_new_identity_via_stem(self):
        controller = MagicMock()
        circuit = MagicMock()
        circuit.id = "c1"
        circuit.path = [MagicMock(nickname="GuardA")]
        controller.get_circuits.return_value = [circuit]
        with patch("stem.control.Controller.from_port", return_value=controller):
            manager = TorCircuitManager()
            status = await manager.status()
            self.assertTrue(status["connected"])
            self.assertEqual(status["circuit_count"], 1)
            identity = await manager.new_identity()
        self.assertEqual(identity["signal"], "NEWNYM")
        controller.signal.assert_called_once()
        controller.close.assert_called()

    async def test_monitor_reports_no_anonymity_guarantee(self):
        with patch.object(TorNetworkMonitor, "_open", staticmethod(lambda port: True)):
            health = await TorNetworkMonitor().health()
        self.assertTrue(health["healthy"])
        self.assertFalse(health["anonymity_guaranteed"])


class RouteTests(unittest.IsolatedAsyncioTestCase):
    async def test_killswitch_route_uses_shared_manager(self):
        fake = MagicMock()
        fake.privacy.engage = MagicMock(return_value={"kill_switch": True})
        with patch.object(tor_routes, "_manager", fake):
            result = await tor_routes.engage_killswitch(manager=fake)
        self.assertTrue(result["kill_switch"])


if __name__ == "__main__":
    unittest.main()
