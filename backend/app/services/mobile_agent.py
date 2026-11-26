"""ADB-based mobile interaction agent — fail-closed and allowlisted.

No device is contacted unless enabled, the serial is explicitly allowed, and
the action uses a fixed argument list (never a shell). Screenshots are saved
inside the configured transfer root.
"""

import asyncio
import subprocess
from pathlib import Path
from typing import Any, Dict, List

from app.core.config import settings
from app.models.security import AuditEvent

ALLOWED_ACTIONS = ("list_devices", "tap", "swipe", "type", "screenshot")
MAX_COORDINATE = 4096
MAX_TEXT = 2048
TIMEOUT_SECONDS = 15


class MobileAgentError(PermissionError):
    """Raised when a mobile action is outside policy."""


class MobileAgentService:
    def __init__(self, db):
        self.db = db
        self.root = Path(
            settings.uwai_upload_root or "/tmp/iam-web-uploads"
        ).resolve()

    def _devices(self) -> List[str]:
        return [
            item.strip()
            for item in settings.mobile_allowed_devices.split(",")
            if item.strip()
        ]

    def _device(self, serial: str) -> str:
        if serial not in self._devices():
            raise MobileAgentError("device serial is not allowlisted")
        return serial

    @staticmethod
    def _coords(x: Any, y: Any) -> tuple[int, int]:
        try:
            ix, iy = int(x), int(y)
        except (TypeError, ValueError) as exc:
            raise MobileAgentError("coordinates must be integers") from exc
        if not (0 <= ix <= MAX_COORDINATE and 0 <= iy <= MAX_COORDINATE):
            raise MobileAgentError("coordinates are out of bounds")
        return ix, iy

    async def _run(self, args: List[str]) -> str:
        if not settings.mobile_agent_enabled:
            raise MobileAgentError("mobile agent is disabled")
        try:
            result = await asyncio.to_thread(
                subprocess.run,
                [settings.mobile_adb_path, *args],
                capture_output=True,
                text=True,
                timeout=TIMEOUT_SECONDS,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise MobileAgentError(f"adb unavailable: {type(exc).__name__}") from exc
        if result.returncode != 0:
            raise MobileAgentError(f"adb command failed: {result.returncode}")
        return result.stdout.strip()

    async def _run_to_file(self, args: List[str], destination: Path) -> None:
        if not settings.mobile_agent_enabled:
            raise MobileAgentError("mobile agent is disabled")
        try:
            with destination.open("wb") as handle:
                result = await asyncio.to_thread(
                    subprocess.run,
                    [settings.mobile_adb_path, *args],
                    stdout=handle,
                    stderr=subprocess.PIPE,
                    timeout=TIMEOUT_SECONDS,
                    check=False,
                )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise MobileAgentError(f"adb unavailable: {type(exc).__name__}") from exc
        if result.returncode != 0:
            raise MobileAgentError(f"adb command failed: {result.returncode}")

    async def _audit(self, actor: str, action: str, details: Dict[str, Any]) -> None:
        self.db.add(
            AuditEvent(
                event_type="mobile_agent_action",
                actor=actor,
                target=details.get("device", ""),
                details={"action": action, **details},
            )
        )
        await self.db.commit()

    async def list_devices(self, actor: str) -> Dict[str, Any]:
        output = await self._run(["devices"])
        devices = [
            line.split("\t")[0]
            for line in output.splitlines()
            if "\tdevice" in line
        ]
        await self._audit(actor, "list_devices", {"count": len(devices)})
        return {"devices": devices, "allowlisted": self._devices()}

    async def tap(self, serial: str, x: Any, y: Any, actor: str) -> Dict[str, Any]:
        device = self._device(serial)
        ix, iy = self._coords(x, y)
        await self._run(["-s", device, "shell", "input", "tap", str(ix), str(iy)])
        await self._audit(actor, "tap", {"device": device, "x": ix, "y": iy})
        return {"tapped": True, "x": ix, "y": iy}

    async def swipe(
        self, serial: str, x1: Any, y1: Any, x2: Any, y2: Any, actor: str
    ) -> Dict[str, Any]:
        device = self._device(serial)
        a, b = self._coords(x1, y1), self._coords(x2, y2)
        await self._run(
            ["-s", device, "shell", "input", "swipe", *map(str, a), *map(str, b)]
        )
        await self._audit(actor, "swipe", {"device": device, "from": a, "to": b})
        return {"swiped": True}

    async def type_text(self, serial: str, text: str, actor: str) -> Dict[str, Any]:
        device = self._device(serial)
        if not text or len(text) > MAX_TEXT or "\n" in text:
            raise MobileAgentError("text must be a single line of at most 2048 characters")
        await self._run(["-s", device, "shell", "input", "text", text])
        await self._audit(actor, "type", {"device": device, "length": len(text)})
        return {"typed": True, "length": len(text)}

    async def screenshot(self, serial: str, filename: str, actor: str) -> Dict[str, Any]:
        device = self._device(serial)
        name = Path(filename).name
        if not name.endswith(".png"):
            raise MobileAgentError("screenshot filename must end in .png")
        self.root.mkdir(parents=True, exist_ok=True)
        destination = self.root / name
        await self._run_to_file(["-s", device, "exec-out", "screencap", "-p"], destination)
        await self._audit(actor, "screenshot", {"device": device, "filename": name})
        return {"filename": str(destination), "saved": True}
