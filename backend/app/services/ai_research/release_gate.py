"""Self-improvement release gate (OD-40).

A model is promoted only when stored benchmark evidence is reproducible, the
post-training score clears the declared improvement threshold, dataset
provenance is complete, and an active signed Creator authorization covers the
exact model@version. Rollback requires the same signed authority.
"""

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.development import (
    ModelEvaluation as ModelEvaluationRow,
    ModelRegistry as ModelRegistryRow,
    ModelVersion as ModelVersionRow,
    UpgradeHistory,
)
from app.models.security import AuditEvent
from app.services.ai_research.base import ResearchError
from app.services.ai_research.benchmarks import BenchmarkResult, BenchmarkRunner
from app.services.ai_research.governance import SignedApproval
from app.services.ai_research.registry import ModelRegistry, ModelVersion
from app.services.ai_research.training import TrainingService
from app.services import serving_model
from app.services.creatorapproval_service import CreatorApprovalService

MODEL_RELEASE_ACTION = "development.model_release"


class ModelReleaseError(PermissionError):
    """Raised when a model version fails an evidence or authority gate."""


def default_release_store():  # type: ignore[no-untyped-def]
    """Return the configured research artifact store (local or durable S3)."""
    from .artifacts import default_store

    return default_store()


class ModelReleaseService:
    def __init__(self, db: AsyncSession, store=None):  # type: ignore[no-untyped-def]
        self.db = db
        self.store = store or default_release_store()  # type: ignore[no-untyped-call]
        self.registry = ModelRegistry(self.store)

    async def _model_row(self, model: str) -> ModelRegistryRow:
        result = await self.db.execute(
            select(ModelRegistryRow).where(ModelRegistryRow.name == model)
        )
        row = result.scalar_one_or_none()
        if not row:
            row = ModelRegistryRow(
                name=model, provider="iam", model_id=model, capabilities=[]
            )
            self.db.add(row)
            await self.db.flush()
        return row

    def _benchmarks(self, refs: List[str]) -> List[BenchmarkResult]:
        if len(refs) < 2:
            raise ModelReleaseError(
                "promotion requires two reproducible benchmark evidence artifacts"
            )
        results: List[BenchmarkResult] = []
        for ref in refs:
            try:
                payload = json.loads(self.store.get(ref).decode("utf-8"))
            except (ValueError, UnicodeDecodeError, OSError) as exc:
                raise ModelReleaseError(f"unreadable benchmark evidence: {ref}") from exc
            try:
                results.append(BenchmarkResult(**payload))
            except TypeError as exc:
                raise ModelReleaseError(f"invalid benchmark evidence: {ref}") from exc
        try:
            BenchmarkRunner.assert_reproducible(results[0], results[1])
        except Exception as exc:  # BenchmarkUnstable and related research errors
            raise ModelReleaseError(str(exc)) from exc
        return results

    async def _authority(self, model: str, version: str) -> Dict[str, Any]:
        authority = await CreatorApprovalService(self.db).check_authorization(
            MODEL_RELEASE_ACTION, target_ref=f"{model}@{version}"
        )
        if not authority.get("authorized"):
            raise ModelReleaseError(
                "no active signed Creator authorization covers this model release"
            )
        return authority

    async def register(
        self,
        *,
        model: str,
        version: str,
        checkpoint_ref: str,
        capability_profile: Dict[str, Any],
        baseline_score: float,
        min_improvement: float,
        dataset_ref: str,
        dataset_sha256: str,
        licence: str,
        consent_recorded: bool,
        poisoning_scan_ref: str,
        benchmark_ref: str,
        actor: str,
    ) -> Dict[str, Any]:
        entry = ModelVersion(
            model=model,
            version=version,
            checkpoint_ref=checkpoint_ref,
            benchmark_score=baseline_score,
            capability_profile=capability_profile,
            benchmark_ref=benchmark_ref,
            baseline_score=baseline_score,
            min_improvement=min_improvement,
            dataset_ref=dataset_ref,
            dataset_sha256=dataset_sha256,
            licence=licence,
            consent_recorded=consent_recorded,
            poisoning_scan_ref=poisoning_scan_ref,
        )
        self.registry.register(entry)
        row = await self._model_row(model)
        row.capabilities = list(capability_profile.keys())  # type: ignore[assignment]
        self.db.add(
            AuditEvent(
                event_type="model_version_registered",
                actor=actor,
                target=f"{model}@{version}",
                details={
                    "checkpoint_ref": checkpoint_ref,
                    "dataset_sha256": dataset_sha256,
                    "licence": licence,
                    "consent_recorded": consent_recorded,
                    "poisoning_scan_ref": poisoning_scan_ref,
                },
            )
        )
        await self.db.commit()
        return entry.to_dict()

    async def promote(
        self,
        model: str,
        version: str,
        benchmark_refs: List[str],
        actor: str,
    ) -> Dict[str, Any]:
        entry = self.registry.get(model, version)
        results = self._benchmarks(benchmark_refs)
        for result in results:
            if result.model != model:
                raise ModelReleaseError(
                    f"benchmark evidence belongs to {result.model}, not {model}"
                )
        post_score = results[-1].mean
        try:
            TrainingService.validate_improvement(
                entry.baseline_score, post_score, entry.min_improvement
            )
        except Exception as exc:
            raise ModelReleaseError(str(exc)) from exc
        missing = [
            name
            for name, value in (
                ("dataset_sha256", entry.dataset_sha256),
                ("licence", entry.licence),
                ("poisoning_scan_ref", entry.poisoning_scan_ref),
                ("consent_recorded", entry.consent_recorded),
            )
            if not value
        ]
        if missing:
            raise ModelReleaseError(
                "model version lacks required provenance: " + ", ".join(missing)
            )
        authority = await self._authority(model, version)

        previous = self.registry.active(model)
        approval = SignedApproval(
            request_id=str(authority["authorization_id"]),
            signed_by=str(authority["signer_id"]),
            signature=str(authority["authorization_id"]),
        )
        self.registry.approve(model, version, approval=approval, protected=True)
        self.registry.deploy(model, version)
        # The self-improvement cycle only reaches live inference after all gates.
        serving_model.activate(model, version=version, actor=actor)

        row = await self._model_row(model)
        version_rows = await self.db.execute(
            select(ModelVersionRow).where(
                ModelVersionRow.model_id == row.id, ModelVersionRow.version == version
            )
        )
        version_row = version_rows.scalar_one_or_none()
        if not version_row:
            version_row = ModelVersionRow(model_id=row.id, version=version)
            self.db.add(version_row)
        version_row.is_primary = True  # type: ignore[assignment]
        version_row.deployed_at = datetime.now(timezone.utc)  # type: ignore[assignment]
        self.db.add(
            ModelEvaluationRow(
                model_id=row.id,
                task_type=results[-1].task_type,
                score=post_score,
                details={
                    "baseline_score": entry.baseline_score,
                    "min_improvement": entry.min_improvement,
                    "config_hash": results[-1].config_hash,
                    "benchmark_refs": benchmark_refs,
                },
            )
        )
        self.db.add(
            UpgradeHistory(
                component=model,
                previous_version=previous,
                new_version=version,
                reason="signed model release",
                status="completed",
            )
        )
        self.db.add(
            AuditEvent(
                event_type="model_released",
                actor=actor,
                target=f"{model}@{version}",
                details={
                    "authorization_id": authority["authorization_id"],
                    "previous_version": previous,
                    "post_training_score": post_score,
                    "config_hash": results[-1].config_hash,
                },
            )
        )
        await self.db.commit()
        return {
            "model": model,
            "version": version,
            "status": "deployed",
            "score": post_score,
            "authorization_id": authority["authorization_id"],
        }

    async def rollback(
        self, model: str, version: str, reason: str, actor: str
    ) -> Dict[str, Any]:
        authority = await self._authority(model, version)
        previous = self.registry.active(model)
        try:
            self.registry.rollback(model, version)
        except ResearchError as exc:
            raise LookupError(str(exc)) from exc
        # Put inference back on the exact version named by the signed rollback.
        serving_model.rollback(target_version=version)
        row = await self._model_row(model)
        versions = await self.db.execute(
            select(ModelVersionRow).where(ModelVersionRow.model_id == row.id)
        )
        for item in versions.scalars().all():
            item.is_primary = item.version == version  # type: ignore[assignment]
        self.db.add(
            UpgradeHistory(
                component=model,
                previous_version=previous,
                new_version=version,
                reason=reason[:500] or "signed rollback",
                status="rolled_back",
            )
        )
        self.db.add(
            AuditEvent(
                event_type="model_rolled_back",
                actor=actor,
                target=f"{model}@{version}",
                details={
                    "authorization_id": authority["authorization_id"],
                    "previous_version": previous,
                    "reason": reason[:500],
                },
            )
        )
        await self.db.commit()
        return {
            "model": model,
            "version": version,
            "status": "deployed",
            "authorization_id": authority["authorization_id"],
        }

    async def versions(self, model: Optional[str] = None) -> List[Dict[str, Any]]:
        self.registry.hydrate()
        if model:
            return [item.to_dict() for item in self.registry.list_versions(model)]
        return [item.to_dict() for item in self.registry._versions.values()]
