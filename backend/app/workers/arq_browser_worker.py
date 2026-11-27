"""ARQ worker for UWAIE browser tasks (Doc 29 Phase 1).

The job payload carries only caller-supplied steps and verification — page
content never becomes a step. Every run writes evidence and an envelope through
the existing BrowserEvidenceService/UWAIEService.

Idempotency: the API enqueues with ``job_id=task_id``. A duplicate delivery sees
a terminal state and returns the stored envelope without re-executing external
actions. Deadlines and cancellation are checked before launch. Retries are
explicit (increment_retry is bounded); failed external actions are never
silently replayed.
"""

from typing import Any, Dict, List

from arq.connections import RedisSettings

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.services.browser_evidence_service import (
    BrowserEvidenceError,
    BrowserEvidenceService,
)
from app.services.uwaie_service import UWAIEError, UWAIEService

TERMINAL_STATES = {"completed", "failed", "cancelled", "timed_out"}


async def run_browser_task(
    ctx: Dict[str, Any],
    *,
    task_id: str,
    steps: List[Dict[str, Any]],
    verification: Dict[str, Any],
    session_token: str,
    actor: str = "sdk",
    actor_type: str = "agent",
    permission_scope: str | None = None,
) -> Dict[str, Any]:
    async with AsyncSessionLocal() as db:
        evidence = BrowserEvidenceService(db)
        current = await evidence.envelope(task_id)
        if current["status"] in TERMINAL_STATES:
            return current

        if await evidence.is_expired(task_id):
            try:
                await evidence.set_state(task_id, "timed_out")
            except BrowserEvidenceError:
                pass
            await evidence.append_audit(
                task_id, actor=actor, actor_type=actor_type,
                action="browser.task.timeout", target=task_id,
                outcome={"status": "timed_out"},
            )
            return await evidence.envelope(task_id, status="timed_out")

        try:
            await evidence.set_state(task_id, "running")
        except BrowserEvidenceError:
            # Another worker already started this idempotent job.
            return await evidence.envelope(task_id)

        try:
            result = await UWAIEService(db).execute(
                steps=steps,
                verification=verification,
                session_token=session_token,
                actor=actor,
                task_id=task_id,
                actor_type=actor_type,
                permission_scope=permission_scope,
            )
        except (BrowserEvidenceError, UWAIEError, RuntimeError) as exc:
            try:
                await evidence.set_state(task_id, "failed")
                await evidence.increment_retry(task_id)
                await evidence.append_audit(
                    task_id, actor=actor, actor_type=actor_type,
                    action="browser.task.failed", target=task_id,
                    outcome={"error": str(exc)[:500]},
                )
            except BrowserEvidenceError:
                pass
            raise
        return result.get("envelope") or await evidence.envelope(task_id)


class WorkerSettings:
    functions = [run_browser_task]
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    job_timeout = int(settings.browser_session_ttl_seconds)
    max_jobs = max(1, settings.browser_max_concurrent_sessions)
