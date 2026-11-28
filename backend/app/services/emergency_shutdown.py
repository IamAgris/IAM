"""Repository-wide emergency stop (OD-11 / OD-19).

One durable, creator-controlled switch halts every governed subsystem:
model inference, the autonomy worker, browser actions and trading. IAM can
never engage or lift it itself; both transitions require a signed Creator
authorization and are written to the audit stream. The in-process mirror is
loaded at startup so a restart cannot silently clear an emergency.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.models.emergency import EmergencyShutdownState
from app.models.security import AuditEvent

GLOBAL_SCOPE = "global"
SUBSYSTEMS = ("inference", "autonomy", "browser", "trading")
STOP_ACTION = "emergency.stop"
RESUME_ACTION = "emergency.resume"


class EmergencyHalted(PermissionError):
    """Raised when a governed subsystem is halted by an emergency stop."""

    def __init__(self, subsystem: str):
        super().__init__(f"emergency stop active: {subsystem} is halted")
        self.subsystem = subsystem


@dataclass
class _State:
    halted: bool = False
    reason: Optional[str] = None
    actor: Optional[str] = None
    authorization_id: Optional[str] = None
    engaged_at: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "halted": self.halted,
            "reason": self.reason,
            "actor": self.actor,
            "authorization_id": self.authorization_id,
            "engaged_at": self.engaged_at,
            "details": dict(self.details),
        }


class _EmergencyRegistry:
    """Process-local mirror of the durable state; safe to read in hot paths."""

    def __init__(self) -> None:
        self._state = _State()
        self._lock = asyncio.Lock()

    def snapshot(self) -> Dict[str, Any]:
        return {
            "scope": GLOBAL_SCOPE,
            **self._state.as_dict(),
            "subsystems": {name: self._state.halted for name in SUBSYSTEMS},
            "iam_can_lift": False,
        }

    def is_halted(self, subsystem: Optional[str] = None) -> bool:
        if subsystem is not None and subsystem not in SUBSYSTEMS:
            raise ValueError(f"unknown emergency subsystem: {subsystem}")
        return self._state.halted

    def assert_not_halted(self, subsystem: str) -> None:
        """Fail closed before any governed action is attempted."""
        if self.is_halted(subsystem):
            raise EmergencyHalted(subsystem)

    def apply(self, *, halted: bool, reason: str, actor: str, authorization_id: str) -> None:
        """Update the mirror after a committed state change."""
        self._state = _State(
            halted=halted,
            reason=reason,
            actor=actor,
            authorization_id=authorization_id,
            engaged_at=datetime.now(timezone.utc).isoformat() if halted else None,
            details={"subsystems": list(SUBSYSTEMS)},
        )

    async def load(self) -> None:
        """Load durable state at startup; a missing table means not halted."""
        try:
            async with AsyncSessionLocal() as db:
                row = (
                    await db.execute(
                        select(EmergencyShutdownState).where(
                            EmergencyShutdownState.scope == GLOBAL_SCOPE
                        )
                    )
                ).scalar_one_or_none()
                if row is None:
                    return
                self._state = _State(
                    halted=bool(row.halted),
                    reason=row.reason,
                    actor=row.actor,
                    authorization_id=row.authorization_id,
                    engaged_at=row.engaged_at.isoformat() if row.engaged_at else None,
                    details=dict(row.details or {}),
                )
        except Exception:  # pragma: no cover - startup DB may not be ready yet
            # Fail closed: an unknown state is treated as halted so an operator
            # must explicitly confirm and resume rather than resume by accident.
            self._state = _State(
                halted=True,
                reason="emergency state could not be loaded",
                details={"load_error": True},
            )


emergency = _EmergencyRegistry()


class EmergencyShutdownService:
    """Durable transitions plus audit evidence for the emergency control."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def status(self) -> Dict[str, Any]:
        return emergency.snapshot()

    async def _require_authorization(self, action: str, authorization: Optional[Dict[str, Any]]) -> str:
        from app.services.creatorapproval_service import CreatorApprovalService

        proof = authorization
        if not proof:
            proof = await CreatorApprovalService(self.db).check_authorization(
                action, requested_level="4", target_ref=GLOBAL_SCOPE
            )
        if not proof or not proof.get("authorized"):
            raise PermissionError(
                f"{action} requires a signed Creator authorization (level 4)"
            )
        return str(proof.get("authorization_id") or "verified")

    async def engage(
        self,
        *,
        reason: str,
        actor: str = "operator",
        authorization: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        if not reason or not reason.strip():
            raise ValueError("an emergency stop reason is required")
        authorization_id = await self._require_authorization(STOP_ACTION, authorization)
        async with emergency._lock:
            row = (
                await self.db.execute(
                    select(EmergencyShutdownState).where(
                        EmergencyShutdownState.scope == GLOBAL_SCOPE
                    )
                )
            ).scalar_one_or_none()
            if row is None:
                row = EmergencyShutdownState(scope=GLOBAL_SCOPE)
                self.db.add(row)
            now = datetime.now(timezone.utc)
            row.halted = True  # type: ignore[assignment]
            row.reason = reason.strip()  # type: ignore[assignment]
            row.actor = actor  # type: ignore[assignment]
            row.authorization_id = authorization_id  # type: ignore[assignment]
            row.engaged_at = now  # type: ignore[assignment]
            row.details = {"subsystems": list(SUBSYSTEMS)}  # type: ignore[assignment]
            self.db.add(
                AuditEvent(
                    event_type="emergency_stop_engaged",
                    actor=actor,
                    target=GLOBAL_SCOPE,
                    details={
                        "reason": reason.strip(),
                        "authorization_id": authorization_id,
                        "subsystems": list(SUBSYSTEMS),
                    },
                )
            )
            await self.db.commit()
            emergency.apply(
                halted=True, reason=reason.strip(), actor=actor,
                authorization_id=authorization_id,
            )
        return emergency.snapshot()

    async def resume(
        self,
        *,
        reason: str,
        actor: str = "operator",
        authorization: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        if not reason or not reason.strip():
            raise ValueError("a resume reason is required")
        authorization_id = await self._require_authorization(RESUME_ACTION, authorization)
        async with emergency._lock:
            row = (
                await self.db.execute(
                    select(EmergencyShutdownState).where(
                        EmergencyShutdownState.scope == GLOBAL_SCOPE
                    )
                )
            ).scalar_one_or_none()
            if row is None:
                row = EmergencyShutdownState(scope=GLOBAL_SCOPE)
                self.db.add(row)
            row.halted = False  # type: ignore[assignment]
            row.reason = reason.strip()  # type: ignore[assignment]
            row.actor = actor  # type: ignore[assignment]
            row.authorization_id = authorization_id  # type: ignore[assignment]
            row.engaged_at = None  # type: ignore[assignment]
            row.details = {"subsystems": list(SUBSYSTEMS)}  # type: ignore[assignment]
            self.db.add(
                AuditEvent(
                    event_type="emergency_stop_resumed",
                    actor=actor,
                    target=GLOBAL_SCOPE,
                    details={
                        "reason": reason.strip(),
                        "authorization_id": authorization_id,
                    },
                )
            )
            await self.db.commit()
            emergency.apply(
                halted=False, reason=reason.strip(), actor=actor,
                authorization_id=authorization_id,
            )
        return emergency.snapshot()
