"""Visual computer-use agent over an isolated browser session.

Default-off and permission-gated. Coordinates are bounded; screenshots go to
audit, never to a model prompt by default. No CAPTCHA or human verification is
solved — those must go through HAIS.
"""

import base64
from typing import Any, Dict

from app.core.config import settings
from app.models.security import AuditEvent
from app.services.browser_service import browser_service
from app.services.internetaccess_service import InternetAccessService

COMPUTER_ACTION = "uwai_computer_use"
ALLOWED_KEYS = {"Enter", "Tab", "Escape", "ArrowUp", "ArrowDown", "Backspace"}
MAX_COORDINATE = 4096
MAX_TEXT = 4096


class ComputerUseError(PermissionError):
    """Raised when a visual interaction is outside policy."""


class ComputerUseService:
    def __init__(self, db):
        self.db = db
        self.access = InternetAccessService(db)

    async def _permit(self) -> None:
        if not settings.uwai_computer_use_enabled:
            raise ComputerUseError("computer-use agent is disabled")
        permission = await self.access.check_permission(COMPUTER_ACTION)
        if not permission.get("permitted"):
            raise ComputerUseError(permission.get("reason", "signed authorization required"))

    @staticmethod
    def _coords(x: Any, y: Any) -> tuple[int, int]:
        try:
            ix, iy = int(x), int(y)
        except (TypeError, ValueError) as exc:
            raise ComputerUseError("coordinates must be integers") from exc
        if not (0 <= ix <= MAX_COORDINATE and 0 <= iy <= MAX_COORDINATE):
            raise ComputerUseError("coordinates are out of bounds")
        return ix, iy

    async def _audit(self, session_token: str, actor: str, action: str, details: Dict[str, Any]) -> None:
        self.db.add(
            AuditEvent(
                event_type="computer_use_action",
                actor=actor,
                target=session_token,
                details={"action": action, **details},
            )
        )
        await self.db.commit()

    async def screenshot(self, session_token: str, actor: str) -> Dict[str, Any]:
        await self._permit()
        page = await browser_service.get_persistent_page(session_token)
        data = await page.screenshot()
        await self._audit(session_token, actor, "screenshot", {"bytes": len(data)})
        return {
            "session_token": session_token,
            "image_base64": base64.b64encode(data).decode("ascii"),
        }

    async def click(self, session_token: str, x: Any, y: Any, actor: str) -> Dict[str, Any]:
        await self._permit()
        ix, iy = self._coords(x, y)
        page = await browser_service.get_persistent_page(session_token)
        await page.mouse.click(ix, iy)
        await self._audit(session_token, actor, "click", {"x": ix, "y": iy})
        return {"clicked": True, "x": ix, "y": iy}

    async def type_text(self, session_token: str, text: str, actor: str) -> Dict[str, Any]:
        await self._permit()
        if not isinstance(text, str) or not text or len(text) > MAX_TEXT:
            raise ComputerUseError("text must be 1–4096 characters")
        page = await browser_service.get_persistent_page(session_token)
        await page.keyboard.type(text)
        await self._audit(session_token, actor, "type", {"length": len(text)})
        return {"typed": True, "length": len(text)}

    async def press(self, session_token: str, key: str, actor: str) -> Dict[str, Any]:
        await self._permit()
        if key not in ALLOWED_KEYS:
            raise ComputerUseError(f"key is not allowed: {key}")
        page = await browser_service.get_persistent_page(session_token)
        await page.keyboard.press(key)
        await self._audit(session_token, actor, "press", {"key": key})
        return {"pressed": key}

    async def scroll(self, session_token: str, x: Any, y: Any, delta: Any, actor: str) -> Dict[str, Any]:
        await self._permit()
        ix, iy = self._coords(x, y)
        try:
            step = int(delta)
        except (TypeError, ValueError) as exc:
            raise ComputerUseError("delta must be an integer") from exc
        if abs(step) > 2000:
            raise ComputerUseError("scroll delta is too large")
        page = await browser_service.get_persistent_page(session_token)
        await page.mouse.move(ix, iy)
        await page.mouse.wheel(0, step)
        await self._audit(session_token, actor, "scroll", {"x": ix, "y": iy, "delta": step})
        return {"scrolled": True, "delta": step}
