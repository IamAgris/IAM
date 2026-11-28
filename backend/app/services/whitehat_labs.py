"""WH-04/WH-05: disposable security labs and remediation validation.

Every session is bound to a signed, active Creator authorization and runs in
the isolated workspace manager. A fix is marked verified only when a bounded
validation command actually completes; no claim is made when execution is
disabled or unavailable.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.security import AuditEvent
from app.models.security_labs import SecurityWorkSession
from app.services.security_policy import AuthorisedTargetPolicy, normalize_target
from app.services.whitehat_policy import (
    build_security_audit,
    ensure_learning_only,
)
from app.services.workspaces.service import WorkspaceService


class WhiteHatLabError(PermissionError):
    """Raised when a lab or validation cannot be safely created."""


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


class WhiteHatLabService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.workspaces = WorkspaceService(db)

    async def _session(self, session_id: str) -> SecurityWorkSession:
        try:
            identifier = UUID(str(session_id))
        except (ValueError, TypeError) as exc:
            raise LookupError("session not found") from exc
        result = await self.db.execute(
            select(SecurityWorkSession).where(SecurityWorkSession.id == identifier)
        )
        session = result.scalar_one_or_none()
        if not session:
            raise LookupError("session not found")
        return session

    async def _audit(
        self, session: SecurityWorkSession, action: str, actor: str, **details: Any
    ) -> None:
        self.db.add(
            AuditEvent(
                event_type="security_work_session",
                actor=actor,
                target=str(session.id),
                details=build_security_audit(
                    action=action,
                    actor=actor,
                    target=session.target,  # type: ignore[arg-type]
                    scope=details.get("scope", {}),
                    authority=details.get("authority", {}),
                    tool_calls=details.get("tool_calls", []),
                    approval=details.get("approval", {}),
                    changes=details.get("changes", {}),
                ),
            )
        )

    async def create_lab(
        self, target: str, actor: str, ttl_seconds: int = 3600
    ) -> Dict[str, Any]:
        authority = await AuthorisedTargetPolicy(self.db).verify(target, "read")
        ttl = max(60, min(int(ttl_seconds), 86400))
        workspace = await self.workspaces.create(
            name=f"lab-{UUID(authority['authorization_id']).hex[:8]}",
            project_id=None,
            provider="local",
            credential_env_var=None,
            actor=actor,
        )
        session = SecurityWorkSession(
            kind="simulation_lab",
            status="created",
            target=normalize_target(target),
            workspace_id=UUID(workspace["id"]),
            authorization_id=UUID(authority["authorization_id"]),
            expires_at=datetime.now(timezone.utc) + timedelta(seconds=ttl),
            details={
                "authority": authority,
                "isolation": {"core_access": False, "network": "none"},
            },
        )
        self.db.add(session)
        await self._audit(
            session,
            "simulation_lab_created",
            actor,
            authority=authority,
            approval={"authorization_id": authority["authorization_id"]},
            changes={"workspace_id": workspace["id"]},
        )
        await self.db.commit()
        return self._serialize(session)

    async def start_lab(self, session_id: str, actor: str) -> Dict[str, Any]:
        session = await self._session(session_id)
        if session.kind != "simulation_lab" or session.status != "created":
            raise WhiteHatLabError("lab session cannot be started")
        workspace_id = str(session.workspace_id)
        await self.workspaces.start(workspace_id, actor)
        session.status = "running"  # type: ignore[assignment]
        await self._audit(session, "simulation_lab_started", actor)
        await self.db.commit()
        return self._serialize(session)

    async def validate_remediation(
        self,
        target: str,
        finding_id: str,
        proposed_fix: str,
        validation_command: str,
        actor: str,
        ttl_seconds: int = 1800,
    ) -> Dict[str, Any]:
        authority = await AuthorisedTargetPolicy(self.db).verify(target, "read")
        ensure_learning_only({"proposed_fix": proposed_fix})
        ttl = max(60, min(int(ttl_seconds), 86400))
        workspace = await self.workspaces.create(
            name=f"fix-{finding_id[:8]}" if finding_id else "remediation",
            project_id=None,
            provider="local",
            credential_env_var=None,
            actor=actor,
        )
        session = SecurityWorkSession(
            kind="remediation_validation",
            status="running",
            target=normalize_target(target),
            workspace_id=UUID(workspace["id"]),
            authorization_id=UUID(authority["authorization_id"]),
            expires_at=datetime.now(timezone.utc) + timedelta(seconds=ttl),
            details={
                "finding_id": finding_id,
                "proposed_fix": proposed_fix[:4000],
                "validation_command": validation_command[:2000],
                "authority": authority,
            },
        )
        self.db.add(session)
        await self.db.flush()

        outcome: Dict[str, Any]
        if settings.workspace_enabled:
            await self.workspaces.start(workspace["id"], actor)
            outcome = await self.workspaces.execute(
                workspace["id"], validation_command, actor
            )
            session.status = "verified" if outcome.get("status") == "completed" else "failed"  # type: ignore[assignment]
        else:
            outcome = {
                "status": "failed",
                "reason": "workspace execution disabled; remediation not verified",
            }
            session.status = "failed"  # type: ignore[assignment]
        session.completed_at = datetime.now(timezone.utc)  # type: ignore[assignment]
        session.details["validation"] = {
            "status": outcome.get("status"),
            "stdout": str(outcome.get("stdout") or "")[:2000],
            "stderr": str(outcome.get("stderr") or "")[:2000],
            "reason": outcome.get("reason"),
        }
        await self._audit(
            session,
            "remediation_validated",
            actor,
            authority=authority,
            tool_calls=["workspace.execute"],
            approval={"authorization_id": authority["authorization_id"]},
            changes={"finding_id": finding_id, "status": session.status},
        )
        await self.db.commit()
        return {**self._serialize(session), "validation": session.details["validation"]}

    async def destroy_session(self, session_id: str, actor: str) -> Dict[str, Any]:
        session = await self._session(session_id)
        if session.status in ("destroyed", "expired"):
            return self._serialize(session)
        if session.workspace_id:
            try:
                await self.workspaces.destroy(str(session.workspace_id), actor)
            except (LookupError, PermissionError):
                pass
        session.status = "destroyed"  # type: ignore[assignment]
        session.completed_at = datetime.now(timezone.utc)  # type: ignore[assignment]
        await self._audit(session, "security_session_destroyed", actor)
        await self.db.commit()
        return self._serialize(session)

    async def cleanup_expired(self, actor: str = "system") -> int:
        result = await self.db.execute(select(SecurityWorkSession))
        now = datetime.now(timezone.utc)
        expired = [
            session
            for session in result.scalars().all()
            if session.status not in ("destroyed", "expired", "verified", "failed")
            and _aware(session.expires_at) <= now  # type: ignore[arg-type]
        ]
        for session in expired:
            if session.workspace_id:
                try:
                    await self.workspaces.destroy(str(session.workspace_id), actor)
                except (LookupError, PermissionError):
                    pass
            session.status = "expired"  # type: ignore[assignment]
            session.completed_at = now  # type: ignore[assignment]
            await self._audit(session, "security_session_expired", actor)
        if expired:
            await self.db.commit()
        return len(expired)

    async def list_sessions(self) -> List[Dict[str, Any]]:
        await self.cleanup_expired()
        result = await self.db.execute(
            select(SecurityWorkSession).order_by(SecurityWorkSession.created_at.desc())
        )
        return [self._serialize(session) for session in result.scalars().all()]

    @staticmethod
    def _serialize(session: SecurityWorkSession) -> Dict[str, Any]:
        return {
            "id": str(session.id),
            "kind": session.kind,
            "status": session.status,
            "target": session.target,
            "workspace_id": str(session.workspace_id) if session.workspace_id else None,
            "authorization_id": str(session.authorization_id) if session.authorization_id else None,
            "details": session.details or {},
            "created_at": session.created_at.isoformat() if session.created_at else None,
            "expires_at": session.expires_at.isoformat() if session.expires_at else None,
            "completed_at": session.completed_at.isoformat() if session.completed_at else None,
        }
