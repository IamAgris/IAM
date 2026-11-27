"""Browser task, evidence and attribution service (Doc 29 WP-03).

Every browser operation is traceable from request to session to action to
evidence and verified result. Page content remains untrusted data, and secret
values are redacted before anything is persisted.
"""

from __future__ import annotations

import base64
import hashlib
import re
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.web_knowledge import BrowserAudit, BrowserEvidence, BrowserTaskRun

SECRET_KEY = re.compile(
    r"password|passwd|secret|token|authorization|cookie|api[_-]?key|credential",
    re.IGNORECASE,
)
BEARER = re.compile(r"Bearer\s+[A-Za-z0-9._\-+/=]+", re.IGNORECASE)
MAX_EXCERPT = 2000
DEFAULT_RETENTION_DAYS = 30

STATES = (
    "queued", "running", "awaiting_approval", "verifying",
    "completed", "failed", "cancelled", "timed_out",
)
TRANSITIONS = {
    "queued": ("running", "cancelled", "timed_out"),
    "running": ("awaiting_approval", "verifying", "failed", "cancelled", "timed_out"),
    "awaiting_approval": ("running", "verifying", "failed", "cancelled"),
    "verifying": ("completed", "failed"),
    "completed": (),
    "failed": ("running",),
    "cancelled": (),
    "timed_out": (),
}


class BrowserEvidenceError(PermissionError):
    """Raised when a browser task/evidence contract rule is violated."""


def redact(value: Any, depth: int = 0) -> Any:
    """Remove secret-looking keys and bearer tokens from structured data."""
    if depth > 8:
        return "[TRUNCATED]"
    if isinstance(value, dict):
        return {
            str(key): ("[REDACTED]" if SECRET_KEY.search(str(key)) else redact(item, depth + 1))
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [redact(item, depth + 1) for item in value]
    if isinstance(value, str):
        cleaned = BEARER.sub("[REDACTED]", value)
        return cleaned[:MAX_EXCERPT]
    return value


def build_envelope(
    task_id: str,
    *,
    session_id: Optional[str] = None,
    status: str = "queued",
    evidence_refs: Optional[List[str]] = None,
    actor: str = "iam",
    actor_type: str = "agent",
    permission_scope: Optional[str] = None,
) -> Dict[str, Any]:
    """Doc 29 §7.1 standard response envelope for browser operations."""
    if status not in STATES and status != "verified":
        raise BrowserEvidenceError(f"invalid browser task status: {status}")
    if actor_type not in ("agent", "creator"):
        raise BrowserEvidenceError(f"invalid actor type: {actor_type}")
    return {
        "task_id": str(task_id),
        "session_id": session_id,
        "status": status,
        "evidence_refs": list(evidence_refs or []),
        "actor": str(actor),
        "actor_type": actor_type,
        "permission_scope": permission_scope,
    }


class BrowserEvidenceService:
    """Persist runs, evidence packages and append-only attribution records."""

    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def _now_ms() -> int:
        return int(time.time() * 1000)

    @staticmethod
    def _evidence_root() -> Path:
        root = Path(
            settings.browser_evidence_dir
            or str(Path(__import__("tempfile").gettempdir()) / "iam-browser-evidence")
        ).resolve()
        root.mkdir(parents=True, exist_ok=True)
        return root

    async def _run(self, task_id: str) -> BrowserTaskRun:
        result = await self.db.execute(
            select(BrowserTaskRun).where(BrowserTaskRun.task_id == str(task_id))
        )
        row = result.scalar_one_or_none()
        if not row:
            raise BrowserEvidenceError("browser task run not found")
        return row

    @staticmethod
    def _run_dict(row: BrowserTaskRun) -> Dict[str, Any]:
        return {
            "id": str(row.id),
            "task_id": row.task_id,
            "session_id": row.session_id,
            "actor": row.actor,
            "actor_type": row.actor_type,
            "permission_scope": row.permission_scope,
            "mode": row.mode,
            "engine": row.engine,
            "state": row.state,
            "priority": row.priority,
            "deadline": row.deadline.isoformat() if row.deadline else None,
            "retries": row.retries,
            "started_at": row.started_at.isoformat() if row.started_at else None,
            "finished_at": row.finished_at.isoformat() if row.finished_at else None,
            "result_ref": row.result_ref,
        }

    async def start_run(
        self,
        *,
        task_id: str,
        actor: str,
        actor_type: str = "agent",
        permission_scope: Optional[str] = None,
        session_id: Optional[str] = None,
        mode: str = "headless",
        engine: Optional[str] = None,
        priority: int = 5,
        deadline: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Create the attributed run record for a browser task."""
        if actor_type not in ("agent", "creator"):
            raise BrowserEvidenceError(f"invalid actor type: {actor_type}")
        if mode not in ("headless", "visible", "isolated"):
            raise BrowserEvidenceError(f"invalid browser mode: {mode}")
        if not 1 <= priority <= 10:
            raise BrowserEvidenceError("priority must be between 1 and 10")
        row = BrowserTaskRun(
            task_id=str(task_id),
            session_id=session_id,
            actor=str(actor),
            actor_type=actor_type,
            permission_scope=permission_scope,
            mode=mode,
            engine=engine,
            state="queued",
            priority=priority,
            deadline=deadline,
            retries=0,
        )
        self.db.add(row)
        await self.db.flush()
        await self.db.commit()
        return self._run_dict(row)

    async def set_state(
        self,
        task_id: str,
        state: str,
        *,
        result_ref: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Advance a run through verified state transitions only."""
        if state not in STATES:
            raise BrowserEvidenceError(f"invalid browser task state: {state}")
        row = cast(Any, await self._run(task_id))
        allowed = TRANSITIONS.get(str(row.state), ())
        if state != row.state and state not in allowed:
            raise BrowserEvidenceError(
                f"invalid transition {row.state} -> {state}"
            )
        row.state = state
        now = datetime.now(timezone.utc)
        if state == "running" and row.started_at is None:
            row.started_at = now
        if state in ("completed", "failed", "cancelled", "timed_out"):
            row.finished_at = now
        if result_ref is not None:
            row.result_ref = result_ref
        await self.db.commit()
        return self._run_dict(row)

    async def record_evidence(
        self,
        task_id: str,
        *,
        url: Optional[str] = None,
        screenshot_b64: Optional[str] = None,
        excerpt: Optional[str] = None,
        source_metadata: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None,
    ) -> str:
        """Store one evidence package and return its evidence_id."""
        await self._run(task_id)
        screenshot_ref = None
        digest_input = b""
        if screenshot_b64:
            try:
                raw = base64.b64decode(screenshot_b64, validate=True)
            except (ValueError, TypeError) as exc:
                raise BrowserEvidenceError("invalid screenshot payload") from exc
            digest_input = raw
            evidence_id = hashlib.sha256(
                f"{task_id}:{self._now_ms()}".encode("utf-8")
            ).hexdigest()[:24]
            screenshot_ref = str(self._evidence_root() / f"{evidence_id}.png")
            Path(screenshot_ref).write_bytes(raw)
        else:
            digest_input = str(excerpt or url or task_id).encode("utf-8")
        row = BrowserEvidence(
            task_id=str(task_id),
            session_id=session_id,
            url=str(url)[:2000] if url else None,
            screenshot_ref=screenshot_ref,
            excerpt=redact(excerpt)[:MAX_EXCERPT] if excerpt else None,
            source_metadata=redact(source_metadata or {}),
            sha256=hashlib.sha256(digest_input).hexdigest(),
            timestamp_ms=self._now_ms(),
            retention_until=datetime.now(timezone.utc)
            + timedelta(days=DEFAULT_RETENTION_DAYS),
        )
        self.db.add(row)
        await self.db.flush()
        await self.db.commit()
        return str(row.id)

    async def evidence_for(self, task_id: str) -> List[Dict[str, Any]]:
        """Return evidence refs for a task, newest first."""
        result = await self.db.execute(
            select(BrowserEvidence).where(BrowserEvidence.task_id == str(task_id))
        )
        rows = cast(
            List[Any],
            result.scalars().all() if hasattr(result, "scalars") else result.all(),
        )
        return [
            {
                "evidence_id": str(row.id),
                "url": row.url,
                "screenshot_ref": row.screenshot_ref,
                "excerpt": row.excerpt,
                "source_metadata": row.source_metadata,
                "sha256": row.sha256,
                "timestamp_ms": row.timestamp_ms,
            }
            for row in sorted(rows, key=lambda item: item.timestamp_ms, reverse=True)
        ]

    async def append_audit(
        self,
        task_id: str,
        *,
        actor: str,
        action: str,
        target: Optional[str] = None,
        outcome: Optional[Dict[str, Any]] = None,
        actor_type: str = "agent",
    ) -> str:
        """Append an attribution event. No update or delete path is exposed."""
        if actor_type not in ("agent", "creator"):
            raise BrowserEvidenceError(f"invalid actor type: {actor_type}")
        row = BrowserAudit(
            task_id=str(task_id),
            actor=str(actor),
            actor_type=actor_type,
            action=str(action)[:200],
            target=str(target)[:2000] if target else None,
            outcome=redact(outcome or {}),
            timestamp_ms=self._now_ms(),
        )
        self.db.add(row)
        await self.db.flush()
        await self.db.commit()
        return str(row.id)

    async def envelope(
        self,
        task_id: str,
        *,
        status: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Build the standard envelope from persisted run + evidence state."""
        run = cast(Any, await self._run(task_id))
        evidence = await self.evidence_for(task_id)
        return build_envelope(
            task_id,
            session_id=session_id or run.session_id,
            status=status or run.state,
            evidence_refs=[item["evidence_id"] for item in evidence],
            actor=run.actor,
            actor_type=run.actor_type,
            permission_scope=run.permission_scope,
        )

    async def is_expired(self, task_id: str) -> bool:
        """True when the run deadline has passed and no terminal state is set."""
        run = cast(Any, await self._run(task_id))
        if not run.deadline:
            return False
        return bool(datetime.now(timezone.utc) >= run.deadline)

    async def increment_retry(self, task_id: str, max_retries: int = 3) -> int:
        """Record a bounded retry attempt on the run."""
        run = cast(Any, await self._run(task_id))
        retries = int(run.retries or 0)
        if retries >= max_retries:
            raise BrowserEvidenceError("maximum browser task retries exceeded")
        run.retries = retries + 1
        await self.db.commit()
        return int(run.retries)

    async def purge_expired(self) -> int:
        """Delete evidence whose retention window has ended (files and rows)."""
        result = await self.db.execute(select(BrowserEvidence))
        rows = cast(
            List[Any],
            result.scalars().all() if hasattr(result, "scalars") else result.all(),
        )
        now = datetime.now(timezone.utc)
        expired = [row for row in rows if row.retention_until and row.retention_until < now]
        for row in expired:
            if row.screenshot_ref:
                try:
                    Path(row.screenshot_ref).unlink(missing_ok=True)
                except OSError:
                    pass
            await self.db.delete(row)
        if expired:
            await self.db.commit()
        return len(expired)
