"""Human Assistance & Intervention System (HAIS).

IAM pauses at the exact step that needs a human, records the required level,
and resumes only after an authorised person resolves it. It never attempts to
solve CAPTCHAs, identity checks or other human-only verifications itself.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.digital_access import AssistanceRequest
from app.models.security import AuditEvent

LEVELS = {
    "1": "inform",
    "2": "assist",
    "3": "approve",
    "4": "perform",
    "5": "escalate",
}
STATUSES = ("pending", "resolved", "escalated", "expired")


class AssistanceError(PermissionError):
    """Raised when an assistance request is invalid."""


class HumanAssistanceService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _request(self, request_id: str) -> AssistanceRequest:
        try:
            identifier = UUID(str(request_id))
        except (ValueError, TypeError) as exc:
            raise LookupError("assistance request not found") from exc
        result = await self.db.execute(
            select(AssistanceRequest).where(AssistanceRequest.id == identifier)
        )
        row = result.scalar_one_or_none()
        if not row:
            raise LookupError("assistance request not found")
        return row

    async def request(
        self,
        *,
        level: str,
        reason: str,
        context: Optional[Dict[str, Any]] = None,
        task_ref: Optional[str] = None,
        actor: str,
    ) -> Dict[str, Any]:
        if level not in LEVELS or not reason:
            raise AssistanceError(f"level must be one of {tuple(LEVELS)} and reason is required")
        row = AssistanceRequest(
            level=level,
            reason=reason[:2000],
            context=context or {},
            task_ref=task_ref,
            status="pending",
        )
        self.db.add(row)
        await self.db.flush()
        await self._audit(
            row.id, actor, "assistance_requested",
            {"level": level, "human_action": LEVELS[level]},
        )
        await self.db.commit()
        return self._row(row)

    async def resolve(
        self, request_id: str, resolved_by: str, actor: str, note: str = ""
    ) -> Dict[str, Any]:
        row = await self._request(request_id)
        if row.status != "pending":
            raise AssistanceError("assistance request is no longer pending")
        row.status = "resolved"  # type: ignore[assignment]
        row.resolved_by = resolved_by  # type: ignore[assignment]
        row.resolved_at = datetime.now(timezone.utc)  # type: ignore[assignment]
        await self._audit(
            row.id, actor, "assistance_resolved",
            {"resolved_by": resolved_by, "note": note[:500]},
        )
        await self.db.commit()
        return self._row(row)

    async def escalate(self, request_id: str, actor: str, reason: str = "") -> Dict[str, Any]:
        row = await self._request(request_id)
        row.status = "escalated"  # type: ignore[assignment]
        await self._audit(
            row.id, actor, "assistance_escalated", {"reason": reason[:500]}
        )
        await self.db.commit()
        return self._row(row)

    async def list(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        query = select(AssistanceRequest)
        if status:
            if status not in STATUSES:
                raise AssistanceError(f"unknown status: {status}")
            query = query.where(AssistanceRequest.status == status)
        result = await self.db.execute(query.order_by(AssistanceRequest.created_at.desc()))
        return [self._row(row) for row in result.scalars().all()]

    async def _audit(self, target: Any, actor: str, event: str, details: Dict[str, Any]) -> None:
        self.db.add(
            AuditEvent(event_type=event, actor=actor, target=str(target), details=details)
        )

    @staticmethod
    def _row(row: AssistanceRequest) -> Dict[str, Any]:
        return {
            "id": str(row.id),
            "level": row.level,
            "human_action": LEVELS.get(str(row.level)),
            "reason": row.reason,
            "context": row.context or {},
            "task_ref": row.task_ref,
            "status": row.status,
            "resolved_by": row.resolved_by,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "resolved_at": row.resolved_at.isoformat() if row.resolved_at else None,
        }
