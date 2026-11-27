"""Multi-agent browser sessions, handover and recovery (Doc 29 P7).

One isolated session per agent. Sessions are never shared without signed Creator
authorization; capacity is bounded by OD-39 and the browser session cap. Human
takeover goes through HAIS and never attempts CAPTCHAs or identity checks.
"""

from __future__ import annotations

import secrets
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.uwaie import WebsiteWorkflow
from app.models.web_knowledge import BrowserAgentSession
from app.services.browser_evidence_service import BrowserEvidenceService
from app.services.browser_service import browser_service
from app.services.creatorapproval_service import CreatorApprovalService
from app.services.human_assistance import HumanAssistanceService
from app.services.irwm import IRWM

TRANSFER_ACTION = "browser.session.transfer"


class BrowserMultiAgentError(PermissionError):
    """Raised when a multi-agent browser operation is not permitted."""


class BrowserMultiAgentService:
    """Agent session registry with isolation, handover and recovery."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.evidence = BrowserEvidenceService(db)

    async def _session(self, token: str) -> Any:
        result = await self.db.execute(
            select(BrowserAgentSession).where(
                BrowserAgentSession.session_token == str(token)
            )
        )
        row = result.scalar_one_or_none()
        if not row:
            raise BrowserMultiAgentError("browser agent session not found")
        return cast(Any, row)

    async def capacity(self) -> Dict[str, Any]:
        result = await self.db.execute(select(BrowserAgentSession))
        rows = result.scalars().all() if hasattr(result, "scalars") else result.all()
        open_count = sum(1 for row in rows if row.state in ("open", "recovering"))
        limit = max(1, settings.browser_max_concurrent_sessions)
        try:
            resources = IRWM().status()
        except Exception:
            resources = {"available": False}
        return {
            "open_sessions": open_count,
            "limit": limit,
            "can_admit": open_count < limit,
            "model_resources": resources,
            "note": "model RAM and browser sessions are separate budgets",
        }

    async def open_for_agent(
        self,
        agent_id: str,
        *,
        mode: str = "isolated",
        permission_scope: Optional[List[str]] = None,
        task_id: Optional[str] = None,
        actor: str = "iam",
    ) -> Dict[str, Any]:
        if not agent_id:
            raise BrowserMultiAgentError("agent_id is required")
        result = await self.db.execute(
            select(BrowserAgentSession).where(
                BrowserAgentSession.agent_id == str(agent_id)
            )
        )
        rows = result.scalars().all() if hasattr(result, "scalars") else result.all()
        existing = [row for row in rows if row.state in ("open", "recovering")]
        if existing:
            raise BrowserMultiAgentError("agent already has an active browser session")
        capacity = await self.capacity()
        if not capacity["can_admit"]:
            raise BrowserMultiAgentError("browser session capacity reached")
        token = f"agent-{secrets.token_urlsafe(18)}"
        meta = await browser_service.open_session(
            token,
            mode=mode,
            owner=str(agent_id),
            permission_scope=list(permission_scope or []),
        )
        row = BrowserAgentSession(
            agent_id=str(agent_id),
            session_token=token,
            task_id=task_id,
            owner=str(agent_id),
            permission_scope=list(permission_scope or []),
            isolation_level=mode,
            state="open",
            payload={"engine": meta.get("engine")},
        )
        self.db.add(row)
        await self.db.commit()
        if task_id:
            await self.evidence.append_audit(
                task_id, actor=actor, action="browser.agent.session_open",
                target=token, outcome={"agent_id": agent_id, "mode": mode},
            )
        return self._row(row)

    async def close_for_agent(
        self,
        session_token: str,
        agent_id: str,
        *,
        actor: str = "iam",
    ) -> Dict[str, Any]:
        row = await self._session(session_token)
        if row.agent_id != str(agent_id) and row.owner != str(agent_id):
            raise BrowserMultiAgentError("session belongs to a different agent")
        await browser_service.close_session(row.session_token)  # type: ignore[arg-type]
        row.state = "closed"  # type: ignore[assignment]
        row.closed_at = datetime.now(timezone.utc)  # type: ignore[assignment]
        await self.db.commit()
        if row.task_id:
            await self.evidence.append_audit(
                row.task_id, actor=actor, action="browser.agent.session_close",  # type: ignore[arg-type]
                target=row.session_token, outcome={"agent_id": agent_id},  # type: ignore[arg-type]
            )
        return self._row(row)

    async def transfer(
        self,
        session_token: str,
        *,
        from_agent: str,
        to_agent: str,
        authorization_id: str,
        actor: str = "creator",
    ) -> Dict[str, Any]:
        auth = await CreatorApprovalService(self.db).check_authorization(
            TRANSFER_ACTION, "3"
        )
        if not auth.get("authorized"):
            raise BrowserMultiAgentError(
                "sharing a browser session requires signed Creator authorization"
            )
        row = await self._session(session_token)
        if row.agent_id != str(from_agent):
            raise BrowserMultiAgentError("source agent does not own this session")
        row.agent_id = str(to_agent)  # type: ignore[assignment]
        row.owner = str(to_agent)  # type: ignore[assignment]
        row.payload = {  # type: ignore[assignment]
            **(row.payload or {}),
            "transferred_with": authorization_id,
            "transferred_at": datetime.now(timezone.utc).isoformat(),
        }
        await self.db.commit()
        await self.evidence.append_audit(
            row.task_id or session_token, actor=actor,  # type: ignore[arg-type]
            actor_type="creator", action="browser.agent.session_transfer",
            target=session_token,
            outcome={"from": from_agent, "to": to_agent,
                     "authorization_id": authorization_id},
        )
        return self._row(row)

    async def request_takeover(
        self,
        session_token: str,
        *,
        reason: str,
        actor: str = "iam",
    ) -> Dict[str, Any]:
        row = await self._session(session_token)
        request = await HumanAssistanceService(self.db).request(
            level="4",  # human performs the step
            reason=reason,
            context={"session_token": session_token, "agent_id": row.agent_id},
            task_ref=row.task_id,  # type: ignore[arg-type]
            actor=actor,
        )
        await self.evidence.append_audit(
            row.task_id or session_token, actor=actor,  # type: ignore[arg-type]
            action="browser.agent.handover", target=session_token,
            outcome={"request_id": request.get("id"), "level": "4"},
        )
        return request

    async def recover(
        self,
        session_token: str,
        *,
        actor: str = "iam",
    ) -> Dict[str, Any]:
        row = await self._session(session_token)
        if row.state != "recovering":
            row.state = "recovering"  # type: ignore[assignment]
            await self.db.commit()
        page = await browser_service.get_persistent_page(session_token)
        if page and not getattr(page, "is_closed", lambda: False)():
            row.state = "open"  # type: ignore[assignment]
            await self.db.commit()
            return {"recovered": True, "session_id": session_token}
        # Re-open the isolated context; never fall back to a shared session.
        await browser_service.close_session(session_token)
        meta = await browser_service.open_session(
            session_token, mode=row.isolation_level, owner=row.owner,  # type: ignore[arg-type]
            permission_scope=list(row.permission_scope or []),
        )
        row.state = "open"  # type: ignore[assignment]
        row.payload = {**(row.payload or {}), "recovered_at": datetime.now(timezone.utc).isoformat()}  # type: ignore[assignment]
        await self.db.commit()
        await self.evidence.append_audit(
            row.task_id or session_token, actor=actor,  # type: ignore[arg-type]
            action="browser.agent.recovery", target=session_token,
            outcome={"recovered": True, "engine": meta.get("engine")},
        )
        return {"recovered": True, "session_id": session_token, "reopened": True}

    async def share_approved_workflow(
        self,
        workflow_id: str,
        *,
        from_agent: str,
        to_agent: str,
        actor: str = "iam",
    ) -> Dict[str, Any]:
        """Only approved, credential-free workflows can be shared between agents."""
        result = await self.db.execute(
            select(WebsiteWorkflow).where(WebsiteWorkflow.id == uuid.UUID(str(workflow_id)))
        )
        workflow = result.scalar_one_or_none()
        if not workflow or not getattr(workflow, "is_approved", False):
            raise BrowserMultiAgentError("workflow is unknown or not Creator-approved")
        await self.evidence.append_audit(
            str(workflow_id), actor=actor, action="browser.agent.workflow_share",
            target=str(workflow_id),
            outcome={"from": from_agent, "to": to_agent, "credential_free": True},
        )
        return {
            "workflow_id": str(workflow.id),
            "name": getattr(workflow, "name", None),
            "steps": getattr(workflow, "steps", []),
            "credential_free": True,
            "shared_with": to_agent,
        }

    @staticmethod
    def _row(row: BrowserAgentSession) -> Dict[str, Any]:
        return {
            "id": str(row.id),
            "agent_id": row.agent_id,
            "session_id": row.session_token,
            "task_id": row.task_id,
            "owner": row.owner,
            "permission_scope": row.permission_scope,
            "isolation_level": row.isolation_level,
            "state": row.state,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "closed_at": row.closed_at.isoformat() if row.closed_at else None,
        }
