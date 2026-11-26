"""Development routes — software projects, code changes, deployments, experiments.

Supports IAM's self-development lifecycle: identify → prototype → test →
evaluate → versioned release → authorized deployment → rollback.
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.core.database import get_db_session
from app.models.development import (
    SoftwareProject, CodeChange, DeploymentRecord, Experiment, UpgradeHistory,
)
from app.models.security import AuditEvent
from app.services.development_governance import (
    DeploymentGateDenied,
    is_protected_environment,
    verify_protected_deployment,
)
from app.services.ai_research.release_gate import (
    MODEL_RELEASE_ACTION,
    ModelReleaseError,
    ModelReleaseService,
)
from app.services.ai_research.continuous_improvement import ContinuousImprovement
from app.services.ai_research.artifacts import new_experiment_id
from app.services.ai_research.jobs import HardwareRequirement, ResearchJob, ResearchMethod
from app.services.free_sandboxes.base import ProviderUnavailable, SandboxError

router = APIRouter(prefix="/api/v1/development", tags=["development"])


class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None


class CodeChangeRequest(BaseModel):
    project_id: str
    description: Optional[str] = None
    file_path: Optional[str] = None
    change_type: Optional[str] = None  # add, modify, delete


class ExperimentCreate(BaseModel):
    name: str
    hypothesis: Optional[str] = None
    description: Optional[str] = None


class ExperimentResultRequest(BaseModel):
    status: str  # running, completed, failed
    results: Optional[Dict[str, Any]] = None


class DeploymentRequest(BaseModel):
    project_id: str
    version: str
    environment: str
    protected_core: bool = False
    change_ids: List[str] = []


class UpgradeRequest(BaseModel):
    component: str
    previous_version: Optional[str] = None
    new_version: Optional[str] = None
    reason: Optional[str] = None


class ModelReleaseRegister(BaseModel):
    model: str
    version: str
    checkpoint_ref: str
    capability_profile: Dict[str, Any] = Field(default_factory=dict)
    baseline_score: float
    min_improvement: float = 0.0
    dataset_ref: str
    dataset_sha256: str
    licence: str
    consent_recorded: bool = False
    poisoning_scan_ref: str
    benchmark_ref: str


class ModelPromoteRequest(BaseModel):
    benchmark_refs: List[str]


class ModelRollbackRequest(BaseModel):
    version: str
    reason: str = ""


class ResearchRunRequest(BaseModel):
    title: str
    task_type: str = "coding"
    complexity: int = 3
    method: str = "evaluation"
    model: str = settings.iam_primary_model
    dataset_ref: str = ""
    min_ram_mb: int = 4096
    min_vram_mb: int = 0
    max_runtime_minutes: int = 60


@router.get("/projects")
async def list_projects(db: AsyncSession = Depends(get_db_session)):
    r = await db.execute(select(SoftwareProject).order_by(SoftwareProject.created_at.desc()))
    items = r.scalars().all()
    return [{
        "id": str(p.id), "name": p.name, "description": p.description,
        "status": p.status, "created_at": p.created_at.isoformat() if p.created_at else None,
    } for p in items]


@router.post("/projects")
async def create_project(request: ProjectCreate, db: AsyncSession = Depends(get_db_session)):
    p = SoftwareProject(name=request.name, description=request.description)
    db.add(p)
    await db.commit()
    await db.refresh(p)
    return {"id": str(p.id), "name": p.name, "status": p.status}


@router.patch("/projects/{project_id}")
async def update_project(project_id: str, request: ProjectUpdate, db: AsyncSession = Depends(get_db_session)):
    r = await db.execute(select(SoftwareProject).where(SoftwareProject.id == project_id))
    p = r.scalar_one_or_none()
    if not p:
        raise HTTPException(404, "Project not found")
    for k, v in request.model_dump(exclude_unset=True).items():
        setattr(p, k, v)
    await db.commit()
    return {"id": str(p.id), "status": p.status, "name": p.name}


@router.post("/code-changes")
async def record_code_change(request: CodeChangeRequest, db: AsyncSession = Depends(get_db_session)):
    c = CodeChange(
        project_id=request.project_id, description=request.description,
        file_path=request.file_path, change_type=request.change_type,
    )
    db.add(c)
    await db.commit()
    await db.refresh(c)
    return {"id": str(c.id), "status": c.status, "change_type": c.change_type}


@router.get("/code-changes")
async def list_code_changes(project_id: Optional[str] = None, db: AsyncSession = Depends(get_db_session)):
    stmt = select(CodeChange)
    if project_id:
        stmt = stmt.where(CodeChange.project_id == project_id)
    r = await db.execute(stmt)
    return [{"id": str(c.id), "file_path": c.file_path, "change_type": c.change_type, "status": c.status} for c in r.scalars().all()]


@router.post("/code-changes/{change_id}/review")
async def review_code_change(change_id: str, db: AsyncSession = Depends(get_db_session)):
    """Record a peer/self review before testing (no authority is granted)."""
    result = await db.execute(select(CodeChange).where(CodeChange.id == change_id))
    change = result.scalar_one_or_none()
    if not change:
        raise HTTPException(404, "Code change not found")
    if change.status != "proposed":
        raise HTTPException(400, f"cannot review a change in status '{change.status}'")
    change.status = "reviewed"
    await db.commit()
    return {"id": str(change.id), "status": change.status}


@router.post("/code-changes/{change_id}/test")
async def test_code_change(change_id: str, db: AsyncSession = Depends(get_db_session)):
    """Record a passing test. Protected deployments require this gate."""
    result = await db.execute(select(CodeChange).where(CodeChange.id == change_id))
    change = result.scalar_one_or_none()
    if not change:
        raise HTTPException(404, "Code change not found")
    if change.status not in ("reviewed", "tested"):
        raise HTTPException(400, f"cannot test a change in status '{change.status}'")
    change.status = "tested"
    await db.commit()
    return {"id": str(change.id), "status": change.status}


@router.post("/experiments")
async def create_experiment(request: ExperimentCreate, db: AsyncSession = Depends(get_db_session)):
    e = Experiment(name=request.name, hypothesis=request.hypothesis, description=request.description)
    db.add(e)
    await db.commit()
    await db.refresh(e)
    return {"id": str(e.id), "name": e.name, "status": e.status}


@router.get("/experiments")
async def list_experiments(db: AsyncSession = Depends(get_db_session)):
    r = await db.execute(select(Experiment).order_by(Experiment.created_at.desc()))
    return [{"id": str(e.id), "name": e.name, "status": e.status, "hypothesis": e.hypothesis} for e in r.scalars().all()]


@router.patch("/experiments/{experiment_id}")
async def update_experiment(experiment_id: str, request: ExperimentResultRequest, db: AsyncSession = Depends(get_db_session)):
    r = await db.execute(select(Experiment).where(Experiment.id == experiment_id))
    e = r.scalar_one_or_none()
    if not e:
        raise HTTPException(404, "Experiment not found")
    e.status = request.status
    if request.results is not None:
        e.results = request.results
    if request.status in ("completed", "failed"):
        from datetime import datetime
        e.completed_at = datetime.utcnow()
    await db.commit()
    return {"id": str(e.id), "status": e.status}


@router.post("/deployments")
async def record_deployment(
    request: DeploymentRequest,
    http_request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    """Record a deployment; protected-core deploys need tests + signed authority."""
    protected = request.protected_core or is_protected_environment(request.environment)
    authority = None
    if protected:
        try:
            authority = await verify_protected_deployment(
                db, request.project_id, request.change_ids
            )
        except DeploymentGateDenied as exc:
            raise HTTPException(403, str(exc)) from exc

    d = DeploymentRecord(
        project_id=request.project_id,
        version=request.version,
        environment=request.environment,
    )
    db.add(d)
    await db.flush()
    credential = getattr(http_request.state, "credential", None)
    actor = credential.get("name", "iam") if credential else "iam"
    db.add(
        AuditEvent(
            event_type="protected_deployment_requested" if protected else "deployment_recorded",
            actor=actor,
            target=str(d.id),
            details={
                "project_id": request.project_id,
                "version": request.version,
                "environment": request.environment,
                "protected_core": protected,
                "authorization_id": authority["authorization_id"] if authority else None,
                "tested_changes": authority["tested_changes"] if authority else [],
            },
        )
    )
    await db.commit()
    await db.refresh(d)
    return {
        "id": str(d.id),
        "status": d.status,
        "version": d.version,
        "environment": d.environment,
        "protected_core": protected,
        "authorization_id": authority["authorization_id"] if authority else None,
    }


@router.get("/deployments")
async def list_deployments(db: AsyncSession = Depends(get_db_session)):
    r = await db.execute(select(DeploymentRecord).order_by(DeploymentRecord.deployed_at.desc()))
    return [{"id": str(d.id), "version": d.version, "environment": d.environment, "status": d.status} for d in r.scalars().all()]


@router.post("/upgrades")
async def record_upgrade(request: UpgradeRequest, db: AsyncSession = Depends(get_db_session)):
    u = UpgradeHistory(
        component=request.component, previous_version=request.previous_version,
        new_version=request.new_version, reason=request.reason,
    )
    db.add(u)
    await db.commit()
    await db.refresh(u)
    return {"id": str(u.id), "component": u.component, "status": u.status}


@router.get("/upgrades")
async def list_upgrades(db: AsyncSession = Depends(get_db_session)):
    r = await db.execute(select(UpgradeHistory).order_by(UpgradeHistory.created_at.desc()))
    return [{"id": str(u.id), "component": u.component, "new_version": u.new_version, "status": u.status} for u in r.scalars().all()]


def _release_actor(request: Request) -> str:
    credential = getattr(request.state, "credential", None)
    return credential.get("name", "iam") if credential else "iam"


@router.get("/models/release-policy")
async def model_release_policy():
    return {
        "action": MODEL_RELEASE_ACTION,
        "requires_signed_creator_authorization": True,
        "evidence": {
            "reproducible_benchmark_runs": 2,
            "matching_config_hash": True,
            "minimum_improvement": "declared per version",
            "provenance": [
                "dataset_sha256", "licence", "consent_recorded", "poisoning_scan_ref"
            ],
        },
        "supports_rollback": True,
    }


@router.post("/models/versions")
async def register_model_version(
    payload: ModelReleaseRegister,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    try:
        return await ModelReleaseService(db).register(
            model=payload.model,
            version=payload.version,
            checkpoint_ref=payload.checkpoint_ref,
            capability_profile=payload.capability_profile,
            baseline_score=payload.baseline_score,
            min_improvement=payload.min_improvement,
            dataset_ref=payload.dataset_ref,
            dataset_sha256=payload.dataset_sha256,
            licence=payload.licence,
            consent_recorded=payload.consent_recorded,
            poisoning_scan_ref=payload.poisoning_scan_ref,
            benchmark_ref=payload.benchmark_ref,
            actor=_release_actor(request),
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.get("/models/versions")
async def list_model_versions(
    model: Optional[str] = None,
    db: AsyncSession = Depends(get_db_session),
):
    return await ModelReleaseService(db).versions(model)


@router.post("/models/{model}/versions/{version}/promote")
async def promote_model_version(
    model: str,
    version: str,
    payload: ModelPromoteRequest,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    try:
        return await ModelReleaseService(db).promote(
            model, version, payload.benchmark_refs, _release_actor(request)
        )
    except ModelReleaseError as exc:
        raise HTTPException(403, str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/models/{model}/rollback")
async def rollback_model(
    model: str,
    payload: ModelRollbackRequest,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    try:
        return await ModelReleaseService(db).rollback(
            model, payload.version, payload.reason, _release_actor(request)
        )
    except ModelReleaseError as exc:
        raise HTTPException(403, str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.post("/research-runs")
async def run_research_cycle(
    payload: ResearchRunRequest,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    """Run one fail-closed research cycle with memory, scheduling and recovery."""
    try:
        method = ResearchMethod(payload.method)
    except ValueError as exc:
        raise HTTPException(400, f"unknown research method: {payload.method}") from exc
    if method in (
        ResearchMethod.SFT,
        ResearchMethod.LORA,
        ResearchMethod.QLORA,
        ResearchMethod.FULL_FINE_TUNE,
        ResearchMethod.DISTILLATION,
    ) and not payload.dataset_ref:
        raise HTTPException(400, "training research runs require dataset_ref")
    job = ResearchJob(
        experiment_id=new_experiment_id(),
        title=payload.title,
        task_type=payload.task_type,
        complexity=max(1, min(5, payload.complexity)),
        method=method,
        model=payload.model,
        dataset_ref=payload.dataset_ref,
        hardware=HardwareRequirement(
            min_ram_mb=payload.min_ram_mb,
            min_vram_mb=payload.min_vram_mb,
            max_runtime_minutes=payload.max_runtime_minutes,
        ),
    )
    try:
        result = await ContinuousImprovement(db).run(job, _release_actor(request))
    except (ProviderUnavailable, SandboxError) as exc:
        raise HTTPException(503, str(exc)) from exc
    return result.to_dict()


@router.get("/research-history")
async def research_history(db: AsyncSession = Depends(get_db_session)):
    return await ContinuousImprovement(db).history()
