"""TIPS foundation — Tor Intelligence & Privacy System (Doc 29 P5).

Official Tor Browser only: a normal Chromium with a SOCKS proxy is not a Tor
Browser session and is never used as a fallback. Every component fails closed
when Tor is disabled, the binary is absent, or the control port is unreachable.
Tor does not guarantee anonymity; no code here claims it does.
"""

from __future__ import annotations

import asyncio
import shutil
import socket
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from app.core.config import settings
from app.services.browser_evidence_service import BrowserEvidenceService

DEFAULT_LOCATIONS = (
    "/opt/tor-browser/Browser/start-tor-browser",
    "/opt/tor-browser/Browser/firefox",
    "/Applications/Tor Browser.app/Contents/MacOS/TorBrowser",
    r"C:\Program Files\Tor Browser\Browser\start-tor-browser.exe",
    r"C:\Program Files\Tor Browser\Browser\firefox.exe",
)


class TorUnavailable(RuntimeError):
    """Raised when a Tor operation cannot be performed safely."""


class TorBrowserNotFound(TorUnavailable):
    """Raised when the official Tor Browser binary is not present."""


class OfficialTorBrowser:
    """Locates the official Tor Browser; never substitutes another browser."""

    def executable(self) -> Optional[Path]:
        candidates = [settings.tor_browser_executable] if settings.tor_browser_executable else []
        candidates.extend(DEFAULT_LOCATIONS)
        for candidate in candidates:
            if not candidate:
                continue
            path = Path(candidate).expanduser()
            if path.is_file():
                return path
        return None

    def launch_config(self) -> Dict[str, Any]:
        """Proxy plus DNS-leak-prevention prefs; used only with Tor Browser."""
        return {
            "proxy": {"server": f"socks5://127.0.0.1:{settings.tor_socks_port}"},
            "prefs": {
                "network.proxy.socks_remote_dns": True,
                "media.peerconnection.enabled": False,
            },
        }


class PlaywrightTorLauncher:
    """Launcher using Playwright against the official Tor Browser binary."""

    async def open(self, profile_dir: Path) -> Dict[str, Any]:
        executable = OfficialTorBrowser().executable()
        if not executable:
            raise TorBrowserNotFound(
                "official Tor Browser executable not found; refusing proxy-only fallback"
            )
        from playwright.async_api import async_playwright

        config = OfficialTorBrowser().launch_config()
        playwright = await async_playwright().start()
        try:
            context = await playwright.firefox.launch_persistent_context(
                user_data_dir=str(profile_dir),
                executable_path=str(executable),
                headless=False,  # Tor Browser is not supported headless
                proxy=config["proxy"],
                firefox_user_prefs=config["prefs"],
            )
        except Exception:
            await playwright.stop()
            raise
        return {"playwright": playwright, "context": context, "executable": str(executable)}

    async def close(self, handle: Dict[str, Any]) -> None:
        context = handle.get("context")
        playwright = handle.get("playwright")
        if context:
            await context.close()
        if playwright:
            await playwright.stop()


class TorCircuitManager:
    """Tor control-port circuit inspection and New Identity handling via stem."""

    @staticmethod
    def _controller():
        from stem import Signal
        from stem.control import Controller

        controller = Controller.from_port(
            host=settings.tor_control_host, port=settings.tor_control_port
        )
        controller.authenticate()
        return controller, Signal

    async def status(self) -> Dict[str, Any]:
        try:
            controller, _ = await asyncio.to_thread(self._controller)
        except Exception as exc:
            return {"connected": False, "reason": type(exc).__name__}
        try:
            circuits = await asyncio.to_thread(controller.get_circuits)
            entries = [
                {"id": getattr(circuit, "id", None),
                 "path": [getattr(node, "nickname", None) for node in getattr(circuit, "path", [])]}
                for circuit in circuits
            ]
            return {"connected": True, "circuit_count": len(entries), "circuits": entries}
        finally:
            controller.close()

    async def new_identity(self) -> Dict[str, Any]:
        try:
            controller, signal = await asyncio.to_thread(self._controller)
        except Exception as exc:
            raise TorUnavailable(f"Tor control port unavailable: {type(exc).__name__}") from exc
        try:
            await asyncio.to_thread(controller.signal, signal.NEWNYM)
            return {"signal": "NEWNYM", "issued_at": datetime.now(timezone.utc).isoformat()}
        finally:
            controller.close()


class TorNetworkMonitor:
    """Connection health checks. Port reachability is not an anonymity claim."""

    @staticmethod
    def _open(port: int) -> bool:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(1.5)
            return sock.connect_ex((settings.tor_control_host, port)) == 0

    async def health(self) -> Dict[str, Any]:
        control = await asyncio.to_thread(self._open, settings.tor_control_port)
        socks = await asyncio.to_thread(self._open, settings.tor_socks_port)
        return {
            "control_port": control,
            "socks_port": socks,
            "healthy": control and socks,
            "anonymity_guaranteed": False,
        }


class TorPrivacyGateway:
    """Kill switch and egress enforcement for Tor sessions."""

    def __init__(self, sessions: Dict[str, Dict[str, Any]]):
        self.sessions = sessions
        self.kill_switch = False

    def engage(self) -> Dict[str, Any]:
        self.kill_switch = True
        return {"kill_switch": True, "engaged_at": datetime.now(timezone.utc).isoformat()}

    def release(self, actor: str) -> Dict[str, Any]:
        if not self.kill_switch:
            return {"kill_switch": False, "note": "already released"}
        self.kill_switch = False
        return {"kill_switch": False, "released_by": actor}

    def check_egress(self, session_id: Optional[str], url: str) -> Dict[str, Any]:
        session = self.sessions.get(str(session_id or ""))
        if not session:
            return {
                "permitted": False,
                "reason": "no active Tor session; egress denied by kill switch"
                if self.kill_switch else "no active Tor session",
            }
        if not session.get("is_tor"):
            return {"permitted": False, "reason": "session is not a Tor session"}
        if self.kill_switch and not str(url).lower().startswith(("https://", "http://")):
            return {"permitted": False, "reason": "non-http egress denied"}
        return {"permitted": True, "session_id": session_id, "via_tor": True}


class TorManager:
    """Single facade for TIPS P5 operations."""

    def __init__(self, db: Any, *, launcher: Optional[PlaywrightTorLauncher] = None):
        self.db = db
        self.launcher = launcher or PlaywrightTorLauncher()
        self.circuit_manager = TorCircuitManager()
        self.monitor = TorNetworkMonitor()
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self.privacy = TorPrivacyGateway(self.sessions)
        self.evidence = BrowserEvidenceService(db)

    @staticmethod
    def _require_enabled() -> None:
        if not settings.tor_enabled:
            raise TorUnavailable("Tor is disabled by policy")

    def _profile_root(self) -> Path:
        root = Path(
            settings.tor_data_root
            or str(Path(tempfile.gettempdir()) / "iam-tor-profiles")
        ).resolve()
        root.mkdir(parents=True, exist_ok=True)
        return root

    async def status(self) -> Dict[str, Any]:
        health = await self.monitor.health()
        health.update({
            "enabled": settings.tor_enabled,
            "official_browser_present": OfficialTorBrowser().executable() is not None,
            "active_sessions": len(self.sessions),
            "kill_switch": self.privacy.kill_switch,
        })
        return health

    async def open_session(
        self,
        session_id: str,
        *,
        actor: str = "sdk",
        actor_type: str = "agent",
        task_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        self._require_enabled()
        await self._reap_expired()
        if session_id in self.sessions:
            return dict(self.sessions[session_id])
        if len(self.sessions) >= settings.tor_max_concurrent_sessions:
            raise TorUnavailable("Tor session concurrency limit reached")
        executable = OfficialTorBrowser().executable()
        if not executable:
            raise TorBrowserNotFound(
                "official Tor Browser executable not found; refusing proxy-only fallback"
            )
        profile = self._profile_root() / session_id
        profile.mkdir(parents=True, exist_ok=True)
        try:
            handle = await self.launcher.open(profile)
        except Exception:
            shutil.rmtree(profile, ignore_errors=True)
            raise
        self.sessions[session_id] = {
            "session_id": session_id,
            "is_tor": True,
            "owner": actor,
            "actor_type": actor_type,
            "executable": str(executable),
            "profile": str(profile),
            "handle": handle,
            "created_at": datetime.now(timezone.utc),
        }
        if task_id:
            await self.evidence.append_audit(
                task_id, actor=actor, actor_type=actor_type,
                action="tor.session.open", target=session_id,
                outcome={"official_browser": True, "is_tor": True},
            )
        return {
            key: value for key, value in self.sessions[session_id].items()
            if key != "handle"
        }

    async def close_session(
        self,
        session_id: str,
        *,
        actor: str = "sdk",
        task_id: Optional[str] = None,
    ) -> bool:
        session = self.sessions.pop(str(session_id), None)
        if not session:
            return False
        await self.launcher.close(session["handle"])
        shutil.rmtree(session["profile"], ignore_errors=True)
        if task_id:
            await self.evidence.append_audit(
                task_id, actor=actor, action="tor.session.close",
                target=session_id, outcome={"destroyed": True},
            )
        return True

    async def terminate_all(self, actor: str = "creator") -> Dict[str, Any]:
        ids = list(self.sessions)
        for session_id in ids:
            await self.close_session(session_id, actor=actor)
        self.privacy.engage()
        return {"terminated": len(ids), "kill_switch": True}

    async def _reap_expired(self) -> None:
        now = datetime.now(timezone.utc)
        expired = [
            session_id for session_id, session in self.sessions.items()
            if (now - session["created_at"]).total_seconds()
            > settings.tor_session_ttl_seconds
        ]
        for session_id in expired:
            await self.close_session(session_id)

    async def circuits(self) -> Dict[str, Any]:
        self._require_enabled()
        return await self.circuit_manager.status()

    async def new_identity(self, *, actor: str = "sdk") -> Dict[str, Any]:
        self._require_enabled()
        result = await self.circuit_manager.new_identity()
        await self.evidence.append_audit(
            "tor-control", actor=actor, action="tor.identity.new",
            target="tor-control", outcome=result,
        )
        return result
