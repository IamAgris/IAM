"""Post-deployment regression monitoring (OD-40 safeguard 9).

Compares a deployed version's measured score with a fresh trusted evaluation.
Automatic rollback is never self-authorized: it runs only when the operator has
enabled it *and* the signed release gate authorizes the rollback target.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.security import AuditEvent
from app.services import serving_model

from .base import ResearchError
from .release_gate import ModelReleaseError, ModelReleaseService, default_release_store


@dataclass
class RegressionCheck:
    model: str
    version: str
    baseline_score: float
    current_score: float
    delta: float
    regressed: bool
    action: str
    reason: str = ""

    def as_dict(self) -> Dict[str, Any]:
        return {
            "model": self.model,
            "version": self.version,
            "baseline_score": self.baseline_score,
            "current_score": self.current_score,
            "delta": self.delta,
            "regressed": self.regressed,
            "action": self.action,
            "reason": self.reason,
        }


async def check_regression(
    db: AsyncSession,
    model: str,
    version: str,
    *,
    evaluate: Callable[[str], float],
    store=None,
    actor: str = "iam",
) -> RegressionCheck:
    """Measure a deployed model and decide whether rollback is warranted."""
    store = store or default_release_store()
    service = ModelReleaseService(db, store)
    try:
        entry = service.registry.get(model, version)
    except ResearchError as exc:
        raise ModelReleaseError(str(exc)) from exc
    except KeyError as exc:
        raise ModelReleaseError(f"unknown model version: {model}@{version}") from exc

    baseline = float(entry.benchmark_score or 0.0)
    try:
        current = float(evaluate(model))
    except Exception as exc:  # pragma: no cover - defensive
        raise ModelReleaseError(f"post-deploy evaluation failed: {exc}") from exc

    delta = (baseline - current) / baseline if baseline else 0.0
    regressed = bool(settings.post_deploy_monitor_enabled) and delta > float(
        settings.post_deploy_regression_threshold
    )
    action = "observe"
    reason = "no measured regression"
    rollback_result: Optional[Dict[str, Any]] = None
    if regressed:
        action = "approval_required"
        reason = f"score fell {delta:.1%} below the registered baseline"
        if settings.post_deploy_auto_rollback_enabled:
            try:
                previous = serving_model.current().previous_version or version
                rollback_result = await service.rollback(
                    model, previous, reason=reason, actor=actor
                )
                action = "rolled_back"
                reason = "signed rollback completed"
            except (ModelReleaseError, LookupError, ValueError) as exc:
                reason = f"rollback not authorized: {exc}"

    db.add(
        AuditEvent(
            event_type="model_post_deploy_check",
            actor=actor,
            target=f"{model}@{version}",
            details={
                "baseline_score": baseline,
                "current_score": current,
                "delta": delta,
                "regressed": regressed,
                "action": action,
                "rollback": rollback_result,
            },
        )
    )
    await db.commit()
    return RegressionCheck(
        model=model,
        version=version,
        baseline_score=baseline,
        current_score=current,
        delta=delta,
        regressed=regressed,
        action=action,
        reason=reason,
    )
