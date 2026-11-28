"""Browser & Device Infrastructure service.

Manages browser profiles, remote browser workers, mobile devices,
health monitoring and resource allocation for web automation.
"""

from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.web_knowledge import BrowserInfrastructure


class BrowserInfrastructureError(PermissionError):
    """Raised when a browser infrastructure operation fails."""


class BrowserInfrastructureService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _browser(self, browser_id: str) -> BrowserInfrastructure:
        try:
            identifier = UUID(str(browser_id))
        except (ValueError, TypeError) as exc:
            raise ValueError("Invalid browser ID") from exc
        result = await self.db.execute(
            select(BrowserInfrastructure).where(BrowserInfrastructure.id == identifier)
        )
        row = result.scalar_one_or_none()
        if not row:
            raise ValueError("Browser infrastructure record not found")
        return row

    async def create(
        self,
        *,
        name: str,
        browser_type: str,
        mode: str = "headless",
        profile_name: Optional[str] = None,
        remote_endpoint: Optional[str] = None,
        device_serial: Optional[str] = None,
        resource_allocation: Optional[Dict[str, Any]] = None,
        concurrent_session_limit: int = 1,
        actor: str,
    ) -> Dict[str, Any]:
        """Create a new browser infrastructure record."""
        valid_types = ("chromium", "firefox", "webkit", "android_adb", "remote_desktop")
        if browser_type not in valid_types:
            raise BrowserInfrastructureError(f"Invalid browser type: {browser_type}")
        valid_modes = ("headless", "visible")
        if mode not in valid_modes:
            raise BrowserInfrastructureError(f"Invalid mode: {mode}")
        if not 1 <= concurrent_session_limit <= 100:
            raise BrowserInfrastructureError("Concurrent session limit must be between 1 and 100")

        row = BrowserInfrastructure(
            name=name,
            browser_type=browser_type,
            mode=mode,
            profile_name=profile_name,
            remote_endpoint=remote_endpoint,
            device_serial=device_serial,
            health_status="healthy",
            last_health_check_at=None,
            resource_allocation=resource_allocation or {},
            concurrent_session_limit=concurrent_session_limit,
            active_session_count=0,
            is_available=True,
        )
        self.db.add(row)
        await self.db.flush()
        await self.db.commit()
        return self._row_dict(row)

    async def get(self, browser_id: str) -> Dict[str, Any]:
        row = await self._browser(browser_id)
        return self._row_dict(row)

    async def list(self, is_available: Optional[bool] = None) -> List[Dict[str, Any]]:
        result = await self.db.execute(select(BrowserInfrastructure))
        rows = result.scalars().all()
        if is_available is not None:
            rows = [r for r in rows if r.is_available == is_available]
        return [self._row_dict(r) for r in rows]

    async def update_health(
        self,
        browser_id: str,
        *,
        health_status: str,
        actor: str,
    ) -> Dict[str, Any]:
        """Update browser health status."""
        row = await self._browser(browser_id)
        valid_statuses = ("healthy", "degraded", "offline", "unknown")
        if health_status not in valid_statuses:
            raise BrowserInfrastructureError(f"Invalid health status: {health_status}")
        row.health_status = health_status  # type: ignore[assignment]
        from datetime import datetime, timezone
        row.last_health_check_at = None  # type: ignore[assignment]  # set by caller if desired
        await self.db.commit()
        return self._row_dict(row)

    async def update_allocation(
        self,
        browser_id: str,
        *,
        concurrent_session_limit: Optional[int] = None,
        resource_allocation: Optional[Dict[str, Any]] = None,
        actor: str,
    ) -> Dict[str, Any]:
        """Update browser resource allocation."""
        row = await self._browser(browser_id)
        if concurrent_session_limit is not None:
            if not 1 <= concurrent_session_limit <= 100:
                raise BrowserInfrastructureError("Concurrent session limit must be between 1 and 100")
            row.concurrent_session_limit = concurrent_session_limit  # type: ignore[assignment]
        if resource_allocation is not None:
            row.resource_allocation = resource_allocation  # type: ignore[assignment]
        await self.db.commit()
        return self._row_dict(row)

    async def delete(self, browser_id: str) -> Dict[str, Any]:
        row = await self._browser(browser_id)
        await self.db.delete(row)
        await self.db.commit()
        return {"id": str(row.id), "name": row.name, "status": "deleted"}

    @staticmethod
    def _row_dict(row: BrowserInfrastructure) -> Dict[str, Any]:
        return {
            "id": str(row.id),
            "name": row.name,
            "browser_type": row.browser_type,
            "mode": row.mode,
            "profile_name": row.profile_name,
            "remote_endpoint": row.remote_endpoint,
            "device_serial": row.device_serial,
            "health_status": row.health_status,
            "last_health_check_at": (
                row.last_health_check_at.isoformat() if row.last_health_check_at else None
            ),
            "resource_allocation": row.resource_allocation,
            "concurrent_session_limit": row.concurrent_session_limit,
            "active_session_count": row.active_session_count,
            "is_available": row.is_available,
        }