"""Development routes — software projects, code changes, deployments, experiments.

Supports IAM's self-development lifecycle: identify → prototype → test →
evaluate → versioned release → authorized deployment → rollback.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db_session
from app.models.development import (
    SoftwareProject, CodeChange, DeploymentRecord, Experiment, UpgradeHistory,
)

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


class UpgradeRequest(BaseModel):
    component: str
    previous_version: Optional[str] = None
    new_version: Optional[str] = None
    reason: Optional[str] = None


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
async def record_deployment(request: DeploymentRequest, db: AsyncSession = Depends(get_db_session)):
    d = DeploymentRecord(project_id=request.project_id, version=request.version, environment=request.environment)
    db.add(d)
    await db.commit()
    await db.refresh(d)
    return {"id": str(d.id), "status": d.status, "version": d.version, "environment": d.environment}


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
