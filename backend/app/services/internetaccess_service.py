"""IAM Internet Access and Digital Interaction System.

Public exploration is open. Consequential actions require owner authorization:
- Open: browse, search, read, retrieve public information, discover services.
- Gated: send messages, spend money, register accounts, publish, access private services.
"""

import re
import secrets
import uuid
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.internetaccess import (
    InternetSession, BrowserAction, OnlineAccount, PublishedContent,
    MonitoredTarget, RetrievedFile, InternetPermission, InternetEvent,
)
from app.services.browser_service import browser_service
from app.services.search_service import search_service
from app.services.creatorapproval_service import CreatorApprovalService
from app.services.iplci.service import IPLCIService

LEGAL_OPERATION_BY_ACTION: Dict[str, str] = {
    "browse_public": "analyse",
    "search_web": "analyse",
    "read_public_content": "read",
    "download_public_file": "read",
    "call_public_api": "analyse",
    "send_message": "disclose",
    "publish_content": "distribute",
    "spend_money": "commercialise",
    "register_account": "disclose",
    "access_private_service": "disclose",
}
LEGAL_BLOCKING = frozenset({"BLOCKED", "QUARANTINED", "REVOKED", "EXPIRED"})


ACCOUNT_ROTATE_ACTION = "internet.account_rotate"
ACCOUNT_CLOSE_ACTION = "internet.account_close"
_ENV_VAR_PATTERN = re.compile(r"[A-Z][A-Z0-9_]{1,63}")


class InternetAccessService:
    """Unified internet access with permission-gated actions."""

    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    async def initialize_permissions(self):  # type: ignore[no-untyped-def]
        """Initialize default permission gates."""
        defaults = [
            ("browse_public", "exploration", True, False, "Visit public websites"),
            ("search_web", "exploration", True, False, "Search public search engines"),
            ("read_public_content", "exploration", True, False, "Read articles, papers, documentation"),
            ("download_public_file", "exploration", True, False, "Download permitted public files"),
            ("uwai_upload_file", "account", False, True, "Upload a file through browser automation"),
            ("uwai_computer_use", "account", False, True, "Visual click/type control of a browser session"),
            ("call_public_api", "exploration", True, False, "Call public APIs"),
            ("send_message", "communication", False, True, "Send emails/messages via authorised services"),
            ("register_account", "account", False, True, "Register accounts on external platforms"),
            ("publish_content", "publishing", False, True, "Publish content, products, websites"),
            ("spend_money", "financial", False, True, "Spend money or make transactions"),
            ("access_private_service", "account", False, True, "Access private/credentialed services"),
            ("join_community", "account", False, True, "Join online communities"),
        ]
        for action, category, autonomous, requires_auth, desc in defaults:
            existing = await self.db.execute(
                select(InternetPermission).where(InternetPermission.action_type == action)
            )
            if not existing.scalar_one_or_none():
                self.db.add(InternetPermission(
                    action_type=action,
                    category=category,
                    is_autonomous=autonomous,
                    requires_creator_authorization=requires_auth,
                    description=desc,
                ))
        await self.db.commit()

    async def check_internet_permission_only(self, action_type: str) -> Dict[str, Any]:
        """Internet permission layer only — no legal-gateway recursion."""
        result = await self.db.execute(
            select(InternetPermission).where(InternetPermission.action_type == action_type)
        )
        perm = result.scalar_one_or_none()
        if not perm:
            return {"permitted": True, "note": "No explicit gate — treat as public exploration"}

        if perm.is_autonomous:
            return {"permitted": True, "category": perm.category, "source": "public_exploration"}

        auth = await CreatorApprovalService(self.db).check_authorization(
            action_type, "3"
        )
        if auth.get("authorized"):
            return {
                "permitted": True,
                "category": perm.category,
                "source": "signed_creator_authorization",
                "authorization_id": auth.get("authorization_id"),
                "signer_id": auth.get("signer_id"),
            }
        return {
            "permitted": False,
            "category": perm.category,
            "reason": f"Action '{action_type}' requires signed Creator authorization",
        }

    async def check_permission(self, action_type: str) -> Dict[str, Any]:
        """Mandatory combined gate used by every caller."""
        decision = await self.check_internet_permission_only(action_type)
        if not decision.get("permitted"):
            return decision
        # Test doubles and non-session stores cannot back the IPLCI audit trail;
        # real sessions always run the mandatory gate.
        if not isinstance(self.db, AsyncSession):
            decision["legal"] = {"decision": "SKIPPED", "reason": "non_session_db"}
            return decision
        legal = IPLCIService(db=self.db)
        source_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"iics:public:{action_type}"))
        try:
            if not await legal.store.get_source(source_id):
                await legal.register_source(
                    {
                        "id": source_id,
                        "uri": f"iics://public/{action_type}",
                        "rights_status": "COMMERCIAL_LICENCE",
                        "source_class": "OPEN_RESEARCH",
                        "acquisition_method": "public_internet",
                        "attribution_required": True,
                        "permission_evidence": "public internet action; rights subject to law",
                    },
                    actor="iics",
                )
            outcome = await legal.gate_check(
                {
                    "agent_id": "iics",
                    "operation": LEGAL_OPERATION_BY_ACTION.get(action_type, "analyse"),
                    "source_id": source_id,
                    "purpose": action_type,
                    "context": {"action_type": action_type},
                },
                actor="iics",
            )
        except Exception as exc:  # fail closed
            return {
                "permitted": False,
                "reason": f"legal gateway unavailable: {type(exc).__name__}",
            }
        if outcome.get("error_code") or outcome.get("decision") in LEGAL_BLOCKING:
            return {
                "permitted": False,
                "reason": str(outcome.get("reason") or "legal gateway denied"),
                "legal_decision": outcome,
            }
        decision["legal"] = {
            "decision": outcome.get("decision"),
            "decision_class": outcome.get("decision_class"),
            "conditions": list(outcome.get("conditions") or []),
            "audit_event_id": outcome.get("audit_event_id"),
        }
        return decision

    async def create_session(self, purpose: Optional[str] = None) -> Dict[str, Any]:
        """Create an internet browsing session."""
        token = secrets.token_urlsafe(24)
        session = InternetSession(session_token=token, purpose=purpose, is_active=True)
        self.db.add(session)
        await self.db.commit()
        await self.db.refresh(session)
        await self._log_event("session_created", purpose, "low", {"session_token": token})
        return {
            "session_token": token,
            "id": str(session.id),
            "started_at": session.started_at.isoformat() if session.started_at else None,
        }

    async def close_session(self, token: str) -> bool:
        """Close a browsing session and its persistent page."""
        result = await self.db.execute(
            select(InternetSession).where(InternetSession.session_token == token)
        )
        session = result.scalar_one_or_none()
        if not session:
            return False
        session.is_active = False  # type: ignore[assignment]
        session.ended_at = datetime.utcnow()  # type: ignore[assignment]
        await browser_service.close_persistent_page(token)
        await self.db.commit()
        return True

    async def browse(
        self,
        url: str,
        session_token: Optional[str] = None,
        action: str = "navigate",
        target: Optional[str] = None,
        value: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Browse or interact with the internet. Public exploration is autonomous."""
        permission = await self.check_permission("browse_public")
        if not permission["permitted"]:
            return {"success": False, "error": permission["reason"]}

        # Record action
        session_id = None
        if session_token:
            result = await self.db.execute(
                select(InternetSession).where(InternetSession.session_token == session_token)
            )
            session = result.scalar_one_or_none()
            session_id = session.id if session else None

        action_result = await browser_service.interact(
            action=action,
            target=target or url,
            value=value,
            session_token=session_token,
        )

        if session_id:
            self.db.add(BrowserAction(
                session_id=session_id,
                action_type=action,
                target=target or url,
                value=value,
                result=str(action_result.get("result"))[:1000],
                authorized=True,
            ))
            await self.db.commit()

        await self._log_event("browser_action", target or url, "low", {"action": action})
        return action_result

    async def search(self, query: str, max_results: int = 10) -> Dict[str, Any]:
        """Search engines and the web — public exploration, autonomous."""
        permission = await self.check_permission("search_web")
        if not permission["permitted"]:
            return {"error": permission["reason"]}
        results = await search_service.search(query, max_results)
        await self._log_event("search", query, "low", {"max_results": max_results})
        return results

    async def register_account(
        self,
        platform: str,
        account_identifier: Optional[str] = None,
        credential_reference: Optional[str] = None,
        account_type: str = "service",
        authorised_by: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Register an online account — requires owner authorization."""
        permission = await self.check_permission("register_account")
        if not permission["permitted"]:
            return {"error": permission["reason"], "authorization_required": True}
        account = OnlineAccount(
            platform=platform,
            account_identifier=account_identifier,
            account_type=account_type,
            is_authorised=True,
            authorised_by=authorised_by or permission.get("authorization_id", "owner"),
            credential_reference=credential_reference,  # secret store reference, never raw secret
        )
        self.db.add(account)
        await self.db.commit()
        await self.db.refresh(account)
        await self._log_event("account_registered", platform, "medium", {})
        return {
            "id": str(account.id),
            "platform": platform,
            "is_authorised": True,
        }

    async def list_accounts(self) -> List[Dict[str, Any]]:
        """List account metadata only — credential values are never stored or returned."""
        result = await self.db.execute(select(OnlineAccount))
        return [
            {
                "id": str(row.id),
                "platform": row.platform,
                "account_identifier": row.account_identifier,
                "account_type": row.account_type,
                "is_authorised": bool(row.is_authorised),
                "credential_reference": row.credential_reference,
                "credential_rotated_at": (
                    row.credential_rotated_at.isoformat() if row.credential_rotated_at else None
                ),
                "revoked_at": row.revoked_at.isoformat() if row.revoked_at else None,
            }
            for row in result.scalars().all()
        ]

    async def _account(self, account_id: str) -> OnlineAccount:
        try:
            identifier = UUID(str(account_id))
        except (ValueError, TypeError) as exc:
            raise LookupError("online account not found") from exc
        result = await self.db.execute(
            select(OnlineAccount).where(OnlineAccount.id == identifier)
        )
        account = result.scalar_one_or_none()
        if not account:
            raise LookupError("online account not found")
        return account

    async def rotate_account_credential(
        self, account_id: str, credential_reference: str, actor: str
    ) -> Dict[str, Any]:
        account = await self._account(account_id)
        if not _ENV_VAR_PATTERN.fullmatch(credential_reference or ""):
            raise PermissionError("credential_reference must be an environment-variable name")
        authority = await CreatorApprovalService(self.db).check_authorization(
            ACCOUNT_ROTATE_ACTION, requested_level="3", target_ref=str(account.id)
        )
        if not authority.get("authorized"):
            raise PermissionError("signed Creator authorization required to rotate credentials")
        account.credential_reference = credential_reference  # type: ignore[assignment]
        account.credential_rotated_at = datetime.now(timezone.utc)  # type: ignore[assignment]
        await self._log_event(
            "account_credential_rotated",
            account.platform,  # type: ignore[arg-type]
            "medium",
            {"account_id": str(account.id), "authorization_id": authority["authorization_id"]},
        )
        await self.db.commit()
        return {
            "id": str(account.id),
            "credential_reference": account.credential_reference,
            "credential_rotated_at": account.credential_rotated_at.isoformat(),
        }

    async def close_account(self, account_id: str, actor: str) -> Dict[str, Any]:
        account = await self._account(account_id)
        authority = await CreatorApprovalService(self.db).check_authorization(
            ACCOUNT_CLOSE_ACTION, requested_level="3", target_ref=str(account.id)
        )
        if not authority.get("authorized"):
            raise PermissionError("signed Creator authorization required to close an account")
        account.is_authorised = False  # type: ignore[assignment]
        account.revoked_at = datetime.now(timezone.utc)  # type: ignore[assignment]
        await self._log_event(
            "account_closed",
            account.platform,  # type: ignore[arg-type]
            "medium",
            {"account_id": str(account.id), "authorization_id": authority["authorization_id"]},
        )
        await self.db.commit()
        return {"id": str(account.id), "is_authorised": False, "revoked_at": account.revoked_at.isoformat()}

    async def publish_content(
        self,
        title: str,
        content_type: str,
        target_platform: Optional[str] = None,
        url: Optional[str] = None,
        authorised_by: Optional[str] = None,
        governance_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Publish content — requires owner authorization."""
        from app.services.iplci.context import resolve_governance_context
        from app.services.iplci.gateway import get_gateway

        resolved = resolve_governance_context(governance_context)
        if resolved:
            await get_gateway().enforce_publication(
                source_id=resolved["source_id"],
                agent_id=str(resolved.get("agent_id") or "main"),
            )
        permission = await self.check_permission("publish_content")
        if not permission["permitted"]:
            return {"error": permission["reason"], "authorization_required": True}
        content = PublishedContent(
            title=title,
            content_type=content_type,
            target_platform=target_platform,
            url=url,
            is_authorised=True,
            authorised_by=authorised_by or permission.get("authorization_id", "owner"),
            published_at=datetime.utcnow(),
        )
        self.db.add(content)
        await self.db.commit()
        await self.db.refresh(content)
        await self._log_event("content_published", title, "medium", {"platform": target_platform})
        return {"id": str(content.id), "title": title, "published": True}

    async def add_monitored_target(
        self,
        target_url: str,
        target_type: str = "website",
        check_interval_minutes: int = 60,
    ) -> Dict[str, Any]:
        """Add a website/service to monitor."""
        target = MonitoredTarget(
            target_url=target_url,
            target_type=target_type,
            check_interval_minutes=check_interval_minutes,
        )
        self.db.add(target)
        await self.db.commit()
        await self.db.refresh(target)
        return {"id": str(target.id), "target_url": target_url}

    async def record_retrieved_file(
        self,
        source_url: str,
        filename: Optional[str] = None,
        content_type: Optional[str] = None,
        storage_path: Optional[str] = None,
        size_bytes: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Record a downloaded file; scan before use."""
        f = RetrievedFile(
            source_url=source_url,
            filename=filename,
            content_type=content_type,
            storage_path=storage_path,
            size_bytes=size_bytes,
            scan_status="pending",
        )
        self.db.add(f)
        await self.db.commit()
        await self.db.refresh(f)
        await self._log_event("file_retrieved", source_url, "low", {})
        return {"id": str(f.id), "source_url": source_url, "scan_status": "pending"}

    async def get_events(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get internet activity audit trail."""
        result = await self.db.execute(
            select(InternetEvent).order_by(InternetEvent.created_at.desc()).limit(limit)
        )
        return [
            {
                "id": str(e.id),
                "event_type": e.event_type,
                "target": e.target,
                "risk_level": e.risk_level,
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in result.scalars().all()
        ]

    async def _log_event(self, event_type: str, target: Optional[str], risk: str, details: Dict[str, Any]):  # type: ignore[no-untyped-def]
        self.db.add(InternetEvent(
            event_type=event_type,
            target=target,
            risk_level=risk,
            details=details,
        ))
        await self.db.commit()
