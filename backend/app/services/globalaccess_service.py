"""Global access service — anonymous visitors, GeoIP, and context isolation.

One central IAM intelligence; many isolated visitor sessions.
GeoIP is regional context only — never an identity, never a trust signal.
"""

import secrets
import hashlib
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
import httpx
import loguru
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.globalaccess import (
    AnonymousVisitor, VisitorSession, VisitorLocation, ConversationThread,
    VisitorMessage, VisitorPreference, VisitorConsent, VisitorMemoryPermission,
    RequestJob, RequestUsage, VisitorRateLimit, RegionalSetting,
)

logger = loguru.logger


class GlobalAccessService:
    """Manages anonymous visitor sessions with strict per-visitor isolation."""

    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    # -------------------------------------------------------------------------
    # Visitor & Session lifecycle
    # -------------------------------------------------------------------------

    async def create_or_get_visitor(
        self,
        visitor_token: Optional[str] = None,
        ip_hash: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a visitor identity or return existing one by secure token."""
        if visitor_token:
            result = await self.db.execute(
                select(AnonymousVisitor).where(AnonymousVisitor.visitor_token == visitor_token)
            )
            visitor = result.scalar_one_or_none()
            if visitor:
                visitor.last_activity_at = datetime.now(timezone.utc)
                await self.db.commit()
                return self._visitor_to_dict(visitor)

        # Generate secure, unpredictable token (OWASP recommendation)
        token = secrets.token_urlsafe(32)
        visitor = AnonymousVisitor(
            visitor_token=token,
            is_active=True,
        )
        self.db.add(visitor)
        await self.db.flush()

        # Set default privacy permissions: session memory only
        perms = VisitorMemoryPermission(
            visitor_id=visitor.id,
            allow_session_memory=True,
            allow_anonymous_memory=True,   # OD-05: remember anonymous visitors by default (opt-out)
            allow_shared_knowledge=False,  # private visitor data never becomes shared knowledge
        )
        self.db.add(perms)
        await self.db.commit()
        await self.db.refresh(visitor)

        return self._visitor_to_dict(visitor)

    async def create_session(
        self,
        visitor_id: str,
        mode: str = "focus",
        ip_address: Optional[str] = None,
        resolve_geo: bool = True,
    ) -> Dict[str, Any]:
        """Create an isolated visitor session with optional GeoIP context."""
        if mode not in ("focus", "recall", "create"):
            mode = "focus"

        session_token = secrets.token_urlsafe(32)
        session = VisitorSession(
            visitor_id=visitor_id,
            session_token=session_token,
            mode=mode,
            is_active=True,
        )
        self.db.add(session)
        await self.db.flush()

        # Create a default conversation thread
        thread = ConversationThread(session_id=session.id, title="New conversation")
        self.db.add(thread)
        await self.db.flush()

        if resolve_geo and ip_address:
            await self._resolve_geoip(session.id, ip_address)

        await self.db.commit()
        await self.db.refresh(session)

        return {
            "id": str(session.id),
            "session_token": session.session_token,
            "visitor_id": str(session.visitor_id),
            "mode": session.mode,
            "started_at": session.started_at.isoformat() if session.started_at else None,
            "default_thread_id": str(thread.id),
        }

    async def get_session(self, session_token: str) -> Optional[Dict[str, Any]]:
        """Get a session by token."""
        result = await self.db.execute(
            select(VisitorSession).where(VisitorSession.session_token == session_token)
        )
        session = result.scalar_one_or_none()
        if not session:
            return None
        return {
            "id": str(session.id),
            "session_token": session.session_token,
            "visitor_id": str(session.visitor_id),
            "mode": session.mode,
            "is_active": session.is_active,
        }

    async def get_session_context(self, session_token: str) -> Dict[str, Any]:
        """Get full context for a session including location and permissions.
        Used to build isolated conversation context for each request.
        """
        result = await self.db.execute(
            select(VisitorSession).where(VisitorSession.session_token == session_token)
        )
        session = result.scalar_one_or_none()
        if not session:
            return {}

        # Get location
        loc_result = await self.db.execute(
            select(VisitorLocation).where(VisitorLocation.session_id == session.id)
        )
        location = loc_result.scalar_one_or_none()

        # Get permission
        perm_result = await self.db.execute(
            select(VisitorMemoryPermission).where(VisitorMemoryPermission.visitor_id == session.visitor_id)
        )
        permission = perm_result.scalar_one_or_none()

        return {
            "session_id": str(session.id),
            "visitor_id": str(session.visitor_id),
            "mode": session.mode,
            "location": {
                "country": location.country if location else None,
                "region": location.region if location else None,
                "city": location.city if location else None,
                "language": location.language if location else None,
                "timezone": location.timezone if location else None,
                "currency": location.currency if location else None,
                "is_estimate": location.is_estimate if location else True,
            } if location else None,
            "memory_permission": {
                "allow_session_memory": permission.allow_session_memory if permission else True,
                "allow_anonymous_memory": permission.allow_anonymous_memory if permission else False,
                "allow_shared_knowledge": permission.allow_shared_knowledge if permission else False,
            } if permission else None,
        }

    # -------------------------------------------------------------------------
    # Conversation — strictly isolated
    # -------------------------------------------------------------------------

    async def add_message(
        self,
        session_token: str,
        role: str,
        content: str,
        thread_id: Optional[str] = None,
        mode: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Add a message to a visitor's private conversation."""
        result = await self.db.execute(
            select(VisitorSession).where(VisitorSession.session_token == session_token)
        )
        session = result.scalar_one_or_none()
        if not session:
            return None

        if thread_id:
            thread_result = await self.db.execute(
                select(ConversationThread).where(
                    ConversationThread.id == thread_id,
                    ConversationThread.session_id == session.id,
                )
            )
            thread = thread_result.scalar_one_or_none()
        else:
            thread_result = await self.db.execute(
                select(ConversationThread)
                .where(ConversationThread.session_id == session.id)
                .order_by(ConversationThread.created_at.asc())
                .limit(1)
            )
            thread = thread_result.scalar_one_or_none()

        if not thread:
            thread = ConversationThread(session_id=session.id, title="New conversation")
            self.db.add(thread)
            await self.db.flush()

        message = VisitorMessage(
            thread_id=thread.id,
            role=role,
            content=content,
            mode=mode or session.mode,
        )
        self.db.add(message)
        session.last_activity_at = datetime.now(timezone.utc)
        await self.db.commit()
        await self.db.refresh(message)

        return {
            "id": str(message.id),
            "thread_id": str(message.thread_id),
            "role": message.role,
            "content": message.content,
            "created_at": message.created_at.isoformat() if message.created_at else None,
        }

    async def get_thread_messages(
        self,
        session_token: str,
        thread_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Get messages from this session's conversation only — never another's."""
        result = await self.db.execute(
            select(VisitorSession).where(VisitorSession.session_token == session_token)
        )
        session = result.scalar_one_or_none()
        if not session:
            return []

        query = (
            select(VisitorMessage)
            .join(ConversationThread, VisitorMessage.thread_id == ConversationThread.id)
            .where(ConversationThread.session_id == session.id)
            .order_by(VisitorMessage.created_at.asc())
            .limit(limit)
        )
        if thread_id:
            query = query.where(VisitorMessage.thread_id == thread_id)

        messages_result = await self.db.execute(query)
        messages = messages_result.scalars().all()
        return [
            {
                "id": str(m.id),
                "role": m.role,
                "content": m.content,
                "mode": m.mode,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
            for m in messages
        ]

    async def set_session_mode(self, session_token: str, mode: str) -> bool:
        """Set the operating mode for a session."""
        if mode not in ("focus", "recall", "create"):
            return False
        result = await self.db.execute(
            select(VisitorSession).where(VisitorSession.session_token == session_token)
        )
        session = result.scalar_one_or_none()
        if not session:
            return False
        session.mode = mode
        await self.db.commit()
        return True

    # -------------------------------------------------------------------------
    # Privacy, consent, retention, deletion
    # -------------------------------------------------------------------------

    async def set_consent(
        self,
        visitor_id: str,
        consent_type: str,
        granted: bool,
        retention_days: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Record visitor privacy consent."""
        result = await self.db.execute(
            select(VisitorConsent).where(
                VisitorConsent.visitor_id == visitor_id,
                VisitorConsent.consent_type == consent_type,
            )
        )
        consent = result.scalar_one_or_none()
        if consent:
            consent.granted = granted
            consent.retention_days = retention_days
        else:
            consent = VisitorConsent(
                visitor_id=visitor_id,
                consent_type=consent_type,
                granted=granted,
                retention_days=retention_days,
            )
            self.db.add(consent)
        await self.db.commit()
        return {"consent_type": consent_type, "granted": granted, "retention_days": retention_days}

    async def set_memory_permission(
        self,
        visitor_id: str,
        allow_session_memory: Optional[bool] = None,
        allow_anonymous_memory: Optional[bool] = None,
        allow_shared_knowledge: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """Control whether visitor data may enter any memory layer."""
        result = await self.db.execute(
            select(VisitorMemoryPermission).where(VisitorMemoryPermission.visitor_id == visitor_id)
        )
        perm = result.scalar_one_or_none()
        if not perm:
            perm = VisitorMemoryPermission(visitor_id=visitor_id)
            self.db.add(perm)
        if allow_session_memory is not None:
            perm.allow_session_memory = allow_session_memory
        if allow_anonymous_memory is not None:
            perm.allow_anonymous_memory = allow_anonymous_memory
        if allow_shared_knowledge is not None:
            perm.allow_shared_knowledge = allow_shared_knowledge
        await self.db.commit()
        return {
            "allow_session_memory": perm.allow_session_memory,
            "allow_anonymous_memory": perm.allow_anonymous_memory,
            "allow_shared_knowledge": perm.allow_shared_knowledge,
        }

    async def delete_visitor_data(self, visitor_token: str) -> bool:
        """Honour deletion requests — remove all visitor data via cascade."""
        result = await self.db.execute(
            select(AnonymousVisitor).where(AnonymousVisitor.visitor_token == visitor_token)
        )
        visitor = result.scalar_one_or_none()
        if not visitor:
            return False
        await self.db.delete(visitor)
        await self.db.commit()
        logger.info(f"Deleted visitor data for token {visitor_token[:8]}...")
        return True

    async def check_rate_limit(self, scope_key: str, max_requests: int = 60, window_minutes: int = 1) -> bool:
        """Per-visitor / per-IP request budget (abuse protection)."""
        result = await self.db.execute(
            select(VisitorRateLimit).where(VisitorRateLimit.scope_key == scope_key)
        )
        record = result.scalar_one_or_none()
        now = datetime.now(timezone.utc)
        if not record or (now - record.window_start.replace(tzinfo=timezone.utc)).total_seconds() > window_minutes * 60:
            if record:
                record.window_start = now
                record.request_count = 1
                record.is_blocked = False
            else:
                record = VisitorRateLimit(scope_key=scope_key, window_start=now, request_count=1)
                self.db.add(record)
            await self.db.commit()
            return True
        if record.is_blocked:
            return False
        record.request_count += 1
        if record.request_count > max_requests:
            record.is_blocked = True
        await self.db.commit()
        return record.request_count <= max_requests

    # -------------------------------------------------------------------------
    # GeoIP — regional context only (estimate, never identity)
    # -------------------------------------------------------------------------

    async def _resolve_geoip(self, session_id: str, ip_address: str):
        """Resolve coarse GeoIP context from IP. Best-effort, non-blocking on failure."""
        location = VisitorLocation(
            session_id=session_id,
            is_estimate=True,
            user_corrected=False,
        )
        try:
            # Use ip-api.com free endpoint (no API key); skip private/local IPs
            if ip_address in ("127.0.0.1", "::1") or ip_address.startswith(("10.", "192.168.", "172.")):
                location.city = "Local"
                location.country = None
            else:
                async with httpx.AsyncClient() as client:
                    resp = await client.get(
                        f"http://ip-api.com/json/{ip_address}",
                        params={"fields": "status,country,regionName,city,timezone,currency,lang"},
                        timeout=5.0,
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        if data.get("status") == "success":
                            location.country = data.get("country")
                            location.region = data.get("regionName")
                            location.city = data.get("city")
                            location.timezone = data.get("timezone")
                            location.currency = data.get("currency")
                            location.language = data.get("lang")
        except Exception as e:
            logger.warning(f"GeoIP resolution failed (non-critical): {e}")

        self.db.add(location)
        await self.db.flush()

    async def correct_location(
        self,
        session_token: str,
        country: Optional[str] = None,
        language: Optional[str] = None,
        timezone: Optional[str] = None,
    ) -> bool:
        """Let visitors manually correct location/language."""
        result = await self.db.execute(
            select(VisitorSession).where(VisitorSession.session_token == session_token)
        )
        session = result.scalar_one_or_none()
        if not session:
            return False
        loc_result = await self.db.execute(
            select(VisitorLocation).where(VisitorLocation.session_id == session.id)
        )
        location = loc_result.scalar_one_or_none()
        if not location:
            location = VisitorLocation(session_id=session.id)
            self.db.add(location)
        if country is not None:
            location.country = country
        if language is not None:
            location.language = language
        if timezone is not None:
            location.timezone = timezone
        location.user_corrected = True
        await self.db.commit()
        return True

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _visitor_to_dict(self, visitor: AnonymousVisitor) -> Dict[str, Any]:
        return {
            "id": str(visitor.id),
            "visitor_token": visitor.visitor_token,
            "created_at": visitor.created_at.isoformat() if visitor.created_at else None,
            "is_active": visitor.is_active,
        }
