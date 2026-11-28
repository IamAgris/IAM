"""Autonomous Web Task Engine.

Multi-step web task management: task decomposition, checkpoints, retry logic,
dependency management, scheduled execution, progress reporting, cancellation.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, cast
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.web_knowledge import AutonomousWebTask, WebsiteKnowledge
from app.services.browser_evidence_service import BrowserEvidenceService, build_envelope


class AutonomousWebTaskError(PermissionError):
    """Raised when an autonomous web task operation fails."""


class AutonomousWebTaskService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _task(self, task_id: str) -> AutonomousWebTask:
        try:
            identifier = UUID(str(task_id))
        except (ValueError, TypeError) as exc:
            raise ValueError("Invalid task ID") from exc
        result = await self.db.execute(
            select(AutonomousWebTask).where(AutonomousWebTask.id == identifier)
        )
        row = result.scalar_one_or_none()
        if not row:
            raise ValueError("Autonomous web task not found")
        return row

    @staticmethod
    def _parse_schedule_at(value: Optional[str]) -> Optional[datetime]:
        """Parse an ISO 8601 schedule. Naive timestamps are rejected."""
        if value is None:
            return None
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except (AttributeError, TypeError, ValueError) as exc:
            raise AutonomousWebTaskError(
                "schedule_at must be an ISO 8601 timestamp with a timezone"
            ) from exc
        if parsed.tzinfo is None:
            raise AutonomousWebTaskError(
                "schedule_at must include a timezone (e.g. 2026-11-29T10:00:00Z)"
            )
        return parsed

    async def create(
        self,
        *,
        title: str,
        description: Optional[str] = None,
        website_knowledge_id: Optional[str] = None,
        task_type: str,
        priority: int = 5,
        decomposition: Optional[List[Dict[str, Any]]] = None,
        checkpoints: Optional[List[Dict[str, Any]]] = None,
        dependencies: Optional[List[str]] = None,
        schedule_at: Optional[str] = None,
        max_retries: int = 3,
        is_background: bool = False,
        actor: str,
        actor_type: str = "agent",
        permission_scope: Optional[str] = None,
        session_id: Optional[str] = None,
        mode: str = "headless",
        engine: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a new autonomous web task."""
        valid_types = (
            "registration", "login", "data_entry", "publication", "research",
            "checkout", "monitoring", "migration", "other",
        )
        if task_type not in valid_types:
            raise AutonomousWebTaskError(f"Invalid task type: {task_type}")
        if not 1 <= priority <= 10:
            raise AutonomousWebTaskError("Priority must be between 1 and 10")
        if actor_type not in ("agent", "creator"):
            raise AutonomousWebTaskError("Invalid actor type")
        if mode not in ("headless", "visible", "isolated"):
            raise AutonomousWebTaskError("Invalid browser mode")

        # Verify the website knowledge exists if provided
        if website_knowledge_id:
            wk_result = await self.db.execute(
                select(WebsiteKnowledge).where(
                    WebsiteKnowledge.id == UUID(str(website_knowledge_id))
                )
            )
            if not wk_result.scalar_one_or_none():
                raise ValueError("Website knowledge record not found")

        row = AutonomousWebTask(
            title=title,
            description=description,
            website_knowledge_id=UUID(str(website_knowledge_id)) if website_knowledge_id else None,
            task_type=task_type,
            status="pending",
            priority=priority,
            decomposition=decomposition or [],
            checkpoints=checkpoints or [],
            dependencies=dependencies or [],
            schedule_at=self._parse_schedule_at(schedule_at),
            started_at=None,
            completed_at=None,
            cancelled_at=None,
            progress_percentage=0,
            error_message=None,
            retry_count=0,
            max_retries=max_retries,
            is_background=is_background,
        )
        self.db.add(row)
        await self.db.flush()
        await self.db.commit()
        # Doc 29 WP-03: every task has an attributed browser run and envelope.
        run = await BrowserEvidenceService(self.db).start_run(
            task_id=str(row.id),
            actor=actor,
            actor_type=actor_type,
            permission_scope=permission_scope,
            session_id=session_id,
            mode=mode,
            engine=engine,
            priority=priority,
        )
        result = self._row_dict(row)
        result.update({
            "task_id": run["task_id"],
            "session_id": run["session_id"],
            # Legacy task status stays authoritative for existing callers;
            # the browser run state is exposed separately under WP-03.
            "run_state": run["state"],
            "evidence_refs": [],
            "actor": run["actor"],
            "actor_type": run["actor_type"],
            "permission_scope": run["permission_scope"],
            "envelope": build_envelope(
                task_id=run["task_id"],
                session_id=run["session_id"],
                status=run["state"],
                actor=run["actor"],
                actor_type=run["actor_type"],
                permission_scope=run["permission_scope"],
            ),
        })
        return result

    async def get(self, task_id: str) -> Dict[str, Any]:
        row = await self._task(task_id)
        return self._row_dict(row)

    async def list(
        self,
        website_knowledge_id: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        result = await self.db.execute(select(AutonomousWebTask))
        rows = result.scalars().all()
        if website_knowledge_id:
            rows = [r for r in rows if str(r.website_knowledge_id) == website_knowledge_id]
        if status:
            rows = [r for r in rows if r.status == status]
        return [self._row_dict(r) for r in rows]

    async def update_progress(
        self,
        task_id: str,
        *,
        progress_percentage: int,
        status: Optional[str] = None,
        error_message: Optional[str] = None,
        checkpoint: Optional[Dict[str, Any]] = None,
        actor: str,
    ) -> Dict[str, Any]:
        """Update task progress."""
        row = await self._task(task_id)
        if not 0 <= progress_percentage <= 100:
            raise AutonomousWebTaskError("Progress must be between 0 and 100")
        row.progress_percentage = progress_percentage  # type: ignore[assignment]
        if status is not None:
            valid_statuses = (
                "pending", "planning", "executing", "paused",
                "completed", "failed", "cancelled",
            )
            if status not in valid_statuses:
                raise AutonomousWebTaskError(f"Invalid status: {status}")
            row.status = status  # type: ignore[assignment]
        if error_message is not None:
            row.error_message = error_message  # type: ignore[assignment]
        if checkpoint is not None:
            checkpoints = list(row.checkpoints or [])
            checkpoints.append(checkpoint)
            row.checkpoints = checkpoints  # type: ignore[assignment]
        await self.db.commit()
        return self._row_dict(row)

    async def retry(
        self,
        task_id: str,
        actor: str,
    ) -> Dict[str, Any]:
        """Retry a failed task (increments retry count)."""
        row = await self._task(task_id)
        if row.status != "failed":
            raise AutonomousWebTaskError("Only failed tasks can be retried")
        if row.retry_count >= row.max_retries:
            raise AutonomousWebTaskError("Maximum retries exceeded")
        row.retry_count += 1  # type: ignore[assignment]
        row.status = "pending"  # type: ignore[assignment]
        row.error_message = None  # type: ignore[assignment]
        await self.db.commit()
        return self._row_dict(row)

    async def cancel(self, task_id: str, actor: str) -> Dict[str, Any]:
        """Cancel a pending or executing task."""
        row = cast(Any, await self._task(task_id))
        if row.status in ("completed", "cancelled"):
            raise AutonomousWebTaskError(
                f"Cannot cancel task with status: {row.status}"
            )
        row.status = "cancelled"
        from datetime import datetime, timezone
        row.cancelled_at = datetime.now(timezone.utc)
        await self.db.commit()
        evidence = BrowserEvidenceService(self.db)
        try:
            await evidence.set_state(str(row.id), "cancelled")
            await evidence.append_audit(
                str(row.id), actor=actor, action="task.cancel",
                target=str(row.id), outcome={"status": "cancelled"},
            )
        except PermissionError:
            # A task created before WP-03 has no attributed run; the task
            # cancellation itself still succeeds.
            pass
        return self._row_dict(row)

    @staticmethod
    def _row_dict(row: AutonomousWebTask) -> Dict[str, Any]:
        return {
            "id": str(row.id),
            "task_id": str(row.id),
            "title": row.title,
            "description": row.description,
            "website_knowledge_id": (
                str(row.website_knowledge_id) if row.website_knowledge_id else None
            ),
            "task_type": row.task_type,
            "status": row.status,
            "priority": row.priority,
            "decomposition": row.decomposition,
            "checkpoints": row.checkpoints,
            "dependencies": row.dependencies,
            "schedule_at": (
                row.schedule_at.isoformat() if row.schedule_at else None
            ),
            "started_at": (
                row.started_at.isoformat() if row.started_at else None
            ),
            "completed_at": (
                row.completed_at.isoformat() if row.completed_at else None
            ),
            "cancelled_at": (
                row.cancelled_at.isoformat() if row.cancelled_at else None
            ),
            "progress_percentage": row.progress_percentage,
            "error_message": row.error_message,
            "retry_count": row.retry_count,
            "max_retries": row.max_retries,
            "is_background": row.is_background,
        }