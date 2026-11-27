"""Bounded parallel subagent orchestration (OD-51 §4.4).

IAM remains the primary intelligence. Specialist models are optional resources:
they are fanned out with hard concurrency, timeout, memory and call-count limits,
each result is independently reviewed by IAM's local primary inside
``delegation.run``, and only accepted findings are exposed as labelled,
unverified context. Rejected, timed-out or malformed results never contribute.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, cast

import loguru
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_session_factory
from app.services import delegation
from app.services.delegation import DelegationResult
from app.services.model_inference import InferenceService, inference_service, _estimate_ram_mb

logger = loguru.logger


class OrchestrationDenied(PermissionError):
    """Raised when a fan-out request exceeds the confirmed OD-51 bounds."""


@dataclass
class DelegationTask:
    task: str
    model: Optional[str] = None
    role: str = "specialist"


@dataclass
class OrchestrationResult:
    results: List[DelegationResult] = field(default_factory=list)
    denied_reason: Optional[str] = None

    @property
    def accepted(self) -> List[DelegationResult]:
        return [item for item in self.results if item.status == "accepted"]

    def as_dict(self) -> Dict[str, Any]:
        return {
            "denied_reason": self.denied_reason,
            "count": len(self.results),
            "accepted": len(self.accepted),
            "tasks": [item.as_dict() for item in self.results],
            "claim": "accepted findings are unverified external input reviewed by IAM's primary",
        }

    def context_message(self) -> Optional[str]:
        """Only IAM-accepted findings are passed to the primary, clearly labelled."""
        lines = [
            str(item.context_message())
            for item in self.accepted
            if item.context_message()
        ]
        return "\n\n".join(lines) if lines else None


class _MemoryBudget:
    """Bound aggregate delegated memory without relying on a hosted provider."""

    def __init__(self, limit_mb: int):
        self.limit_mb = limit_mb
        self.used_mb = 0
        self._lock = asyncio.Lock()

    async def acquire(self, estimate_mb: int) -> bool:
        async with self._lock:
            if self.used_mb + estimate_mb > self.limit_mb:
                return False
            self.used_mb += estimate_mb
            return True

    async def release(self, estimate_mb: int) -> None:
        async with self._lock:
            self.used_mb = max(0, self.used_mb - estimate_mb)


async def run_parallel(
    db: AsyncSession,
    tasks: List[DelegationTask],
    *,
    actor: str = "iam",
    service: InferenceService = inference_service,
) -> OrchestrationResult:
    """Run bounded specialist tasks, each with independent primary verification."""
    if not settings.iam_delegation_enabled:
        return OrchestrationResult(denied_reason="delegation disabled")
    if not tasks:
        return OrchestrationResult()
    if len(tasks) > settings.iam_delegation_max_calls_per_request:
        return OrchestrationResult(
            denied_reason=(
                f"requested {len(tasks)} delegated calls exceeds the limit of "
                f"{settings.iam_delegation_max_calls_per_request}"
            )
        )

    budget = _MemoryBudget(settings.iam_delegation_max_parallel * settings.iam_delegation_memory_limit_mb)
    semaphore = asyncio.Semaphore(settings.iam_delegation_max_parallel)

    async def one(task: DelegationTask) -> DelegationResult:
        assigned = None
        if not task.model and db is not None:
            from app.services.capability_evaluator import CapabilityEvaluator

            try:
                assigned = await CapabilityEvaluator(db).select_for_role(task.role)
            except Exception:  # pragma: no cover - registry may be unavailable
                assigned = None
        target = (task.model or assigned or settings.adaptive_delegate_model).strip()
        estimate = _estimate_ram_mb(target, "hosted")
        async with semaphore:
            if not await budget.acquire(estimate):
                return DelegationResult(
                    "rejected", target, reason="delegation memory budget exhausted"
                )
            try:
                # Each task gets its own session: AsyncSession is not safe for
                # concurrent use, and stored findings stay per-task isolated.
                session_factory = cast(Any, get_session_factory)
                async with session_factory()() as session:
                    return await asyncio.wait_for(
                        delegation.run(
                            session,
                            task.task,
                            model=target,
                            actor=actor,
                            service=service,
                        ),
                        timeout=settings.iam_delegation_timeout_seconds,
                    )
            except asyncio.TimeoutError:
                return DelegationResult("error", target, reason="delegation timed out")
            except Exception as exc:  # pragma: no cover - defensive
                logger.warning(f"Parallel delegation task failed: {exc}")
                return DelegationResult("error", target, reason="delegation task failed")
            finally:
                await budget.release(estimate)

    results = await asyncio.gather(*(one(task) for task in tasks))
    return OrchestrationResult(results=list(results))
