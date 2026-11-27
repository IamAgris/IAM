"""Model-independent identity, portability and fallback controls (OD-38/OD-29).

Identity, goals, skills and memory descriptors are portable across providers;
private message content and credentials are never exported. Adopting a primary
or fallback model is a protected-core change requiring signed Creator authority.
"""

import json
from datetime import datetime, timezone
from typing import Any, Dict, List
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.autonomy import Goal
from app.models.identity import AIIdentity
from app.models.lifemanagement import AIIdentityGenesis
from app.models.memory import Skill
from app.models.modelindependence import (
    FallbackConfig,
    ModelComparison,
    ModelPortabilityExport,
)
from app.models.security import AuditEvent
from app.services.ai_research.release_gate import default_release_store
from app.services.creatorapproval_service import CreatorApprovalService

ADOPT_ACTION = "model.adopt"
FALLBACK_ACTION = "model.fallback"
PORTABLE_SCOPES = frozenset({"identity", "goals", "skills", "memory"})
SCORE_WEIGHTS = {
    "coding_correctness": 25,
    "repository_engineering": 15,
    "autonomous_tool_use": 15,
    "reasoning": 20,
    "security": 10,
    "hardware_efficiency": 5,
    "reliability": 10,
}


class ModelIndependenceError(PermissionError):
    """Raised when a model change lacks authority or a portability rule is broken."""


def weighted_score(scores: Dict[str, Any]) -> float:
    """Owner-adjustable spec weights; missing criteria score zero, never assumed."""
    total = 0.0
    for name, weight in SCORE_WEIGHTS.items():
        value = scores.get(name, 0)
        try:
            total += float(value) * weight
        except (TypeError, ValueError):
            continue
    return round(min(1.0, max(0.0, total / 100.0)), 4)


class ModelIndependenceService:
    def __init__(self, db: AsyncSession, store=None):
        self.db = db
        self.store = store or default_release_store()

    async def _authority(self, action: str, target: str) -> Dict[str, Any]:
        authority = await CreatorApprovalService(self.db).check_authorization(
            action, target_ref=target
        )
        if not authority.get("authorized"):
            raise ModelIndependenceError(
                f"no active signed Creator authorization for {action} on {target}"
            )
        return authority

    async def record_comparison(
        self,
        *,
        model_name: str,
        provider: str,
        model_id: str,
        capabilities_tested: List[str],
        scores: Dict[str, Any],
        actor: str,
    ) -> Dict[str, Any]:
        row = ModelComparison(
            model_name=model_name,
            provider=provider,
            model_id=model_id,
            capabilities_tested=list(capabilities_tested),
            scores=dict(scores),
            overall_score=weighted_score(scores),
        )
        self.db.add(row)
        await self.db.flush()
        self.db.add(
            AuditEvent(
                event_type="model_comparison_recorded",
                actor=actor,
                target=f"{provider}:{model_id}",
                details={"model": model_name, "overall_score": row.overall_score},
            )
        )
        await self.db.commit()
        return self._comparison(row)

    async def comparisons(self) -> List[Dict[str, Any]]:
        result = await self.db.execute(
            select(ModelComparison).order_by(ModelComparison.tested_at.desc())
        )
        return [self._comparison(row) for row in result.scalars().all()]

    async def adopt(self, comparison_id: str, actor: str) -> Dict[str, Any]:
        result = await self.db.execute(
            select(ModelComparison).where(ModelComparison.id == UUID(str(comparison_id)))
        )
        row = result.scalar_one_or_none()
        if not row:
            raise LookupError("model comparison not found")
        authority = await self._authority(ADOPT_ACTION, row.model_name)
        adopted = await self.db.execute(select(ModelComparison))
        for item in adopted.scalars().all():
            item.is_adopted = item.id == row.id
        self.db.add(
            AuditEvent(
                event_type="primary_model_adopted",
                actor=actor,
                target=row.model_name,
                details={
                    "model_id": row.model_id,
                    "provider": row.provider,
                    "overall_score": row.overall_score,
                    "authorization_id": authority["authorization_id"],
                },
            )
        )
        await self.db.commit()
        return {**self._comparison(row), "is_adopted": True}

    async def export(self, scope: List[str], actor: str) -> Dict[str, Any]:
        selected = [item for item in (scope or sorted(PORTABLE_SCOPES)) if item in PORTABLE_SCOPES]
        if not selected:
            raise ModelIndependenceError("export scope must include a portable domain")
        manifest: Dict[str, Any] = {
            "format": "iam-portability-v1",
            "model_independent": True,
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "scope": selected,
            "identity": {},
            "goals": [],
            "skills": [],
            "memory": {"excluded_private_content": True},
        }
        if "identity" in selected:
            genesis = await self.db.execute(select(AIIdentityGenesis).limit(1))
            record = genesis.scalar_one_or_none()
            identity = await self.db.execute(select(AIIdentity).limit(1))
            current = identity.scalar_one_or_none()
            manifest["identity"] = {
                "permanent_id": record.permanent_id if record else None,
                "public_name": record.public_name if record else (current.name if current else None),
            }
        if "goals" in selected:
            result = await self.db.execute(select(Goal).order_by(Goal.priority.asc()).limit(200))
            manifest["goals"] = [
                {"title": item.title, "status": item.status, "priority": item.priority}
                for item in result.scalars().all()
            ]
        if "skills" in selected:
            result = await self.db.execute(select(Skill).order_by(Skill.name.asc()).limit(500))
            manifest["skills"] = [
                {
                    "name": item.name,
                    "category": item.category,
                    "proficiency_level": item.proficiency_level,
                }
                for item in result.scalars().all()
            ]
        record = ModelPortabilityExport(
            export_format="json",
            export_scope=selected,
            export_location="",
        )
        self.db.add(record)
        await self.db.flush()
        key = f"model-portability/export-{record.id}.json"
        self.store.put(
            key,
            json.dumps(manifest, sort_keys=True, indent=2).encode("utf-8"),
            {"content_type": "application/json", "private_content": False},
        )
        record.export_location = key
        self.db.add(
            AuditEvent(
                event_type="model_portability_exported",
                actor=actor,
                target=str(record.id),
                details={"scope": selected, "location": key},
            )
        )
        await self.db.commit()
        return {
            "id": str(record.id),
            "format": record.export_format,
            "scope": selected,
            "location": key,
            "private_content": False,
        }

    async def exports(self) -> List[Dict[str, Any]]:
        result = await self.db.execute(select(ModelPortabilityExport))
        return [
            {
                "id": str(row.id),
                "format": row.export_format,
                "scope": row.export_scope or [],
                "location": row.export_location,
                "exported_at": row.exported_at.isoformat() if row.exported_at else None,
            }
            for row in result.scalars().all()
        ]

    async def set_fallback(
        self, primary: str, fallback: str, provider: str, actor: str
    ) -> Dict[str, Any]:
        if not primary or not fallback or not provider:
            raise ModelIndependenceError("primary, fallback and provider are required")
        authority = await self._authority(FALLBACK_ACTION, primary)
        result = await self.db.execute(select(FallbackConfig))
        for item in result.scalars().all():
            item.is_active = False
        row = FallbackConfig(
            primary_model=primary,
            fallback_model=fallback,
            fallback_provider=provider,
            is_active=True,
        )
        self.db.add(row)
        await self.db.flush()
        self.db.add(
            AuditEvent(
                event_type="model_fallback_configured",
                actor=actor,
                target=primary,
                details={
                    "fallback_model": fallback,
                    "fallback_provider": provider,
                    "authorization_id": authority["authorization_id"],
                },
            )
        )
        await self.db.commit()
        return {
            "id": str(row.id),
            "primary_model": primary,
            "fallback_model": fallback,
            "fallback_provider": provider,
            "is_active": True,
        }

    async def active_fallback(self) -> Dict[str, Any]:
        result = await self.db.execute(
            select(FallbackConfig).where(FallbackConfig.is_active.is_(True))
        )
        row = result.scalar_one_or_none()
        if not row:
            return {"configured": False}
        return {
            "configured": True,
            "primary_model": row.primary_model,
            "fallback_model": row.fallback_model,
            "fallback_provider": row.fallback_provider,
        }

    @staticmethod
    def _comparison(row: ModelComparison) -> Dict[str, Any]:
        return {
            "id": str(row.id),
            "model_name": row.model_name,
            "provider": row.provider,
            "model_id": row.model_id,
            "capabilities_tested": row.capabilities_tested or [],
            "scores": row.scores or {},
            "overall_score": float(row.overall_score) if row.overall_score is not None else None,
            "is_adopted": bool(row.is_adopted),
            "tested_at": row.tested_at.isoformat() if row.tested_at else None,
        }
