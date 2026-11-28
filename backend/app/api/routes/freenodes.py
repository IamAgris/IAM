"""Doc 19 / OD-35: free infrastructure node candidate endpoints.

Assessment and lifecycle only. No cloud account creation, VM provisioning,
spending or provider-limit bypass is exposed here.
"""

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.database import get_db_session
from app.services.free_node_lifecycle import FreeNodeError, FreeNodeLifecycleService

router = APIRouter(prefix="/api/v1/free-nodes", tags=["free-node-lifecycle"])


class CandidateRequest(BaseModel):
    provider: str
    instance_class: Optional[str] = None
    architecture: str
    region: Optional[str] = None
    cpu_cores: float = 0
    ram_mb: int = 0
    disk_gb: float = 0
    cost_status: str = "free"
    terms_source: Optional[str] = None
    expires_at: Optional[str] = None
    notes: Optional[str] = None
    # Usefulness-gate evidence (must be supplied; absence fails closed):
    run_compatible: bool = False
    operational_overhead: str = "high"
    security_exposure: str = "unknown"
    net_benefit: bool = False


class StatusRequest(BaseModel):
    status: str


class VerificationRequest(BaseModel):
    source_url: str
    evidence: str


class MigrationRequest(BaseModel):
    days_before_expiry: int = 7


def _handle(exc: Exception):  # type: ignore[no-untyped-def]
    raise HTTPException(status_code=400, detail=str(exc))


@router.post("/", status_code=201)
async def record_candidate(request: CandidateRequest, db=Depends(get_db_session)):  # type: ignore[no-untyped-def]
    try:
        return await FreeNodeLifecycleService(db).record_candidate(request.model_dump())
    except FreeNodeError as exc:
        _handle(exc)


@router.get("")
async def list_candidates(limit: int = 50, db=Depends(get_db_session)):  # type: ignore[no-untyped-def]
    return await FreeNodeLifecycleService(db).list_candidates(limit)


@router.post("/{candidate_id}/verify-terms")
async def verify_terms(  # type: ignore[no-untyped-def]
    candidate_id: str, request: VerificationRequest, db=Depends(get_db_session)
):
    try:
        return await FreeNodeLifecycleService(db).verify_terms(
            candidate_id, request.source_url, request.evidence
        )
    except FreeNodeError as exc:
        _handle(exc)


@router.patch("/{candidate_id}/status")
async def set_status(  # type: ignore[no-untyped-def]
    candidate_id: str, request: StatusRequest, db=Depends(get_db_session)
):
    try:
        return await FreeNodeLifecycleService(db).set_status(candidate_id, request.status)
    except FreeNodeError as exc:
        _handle(exc)


@router.post("/{candidate_id}/migration-plan")
async def plan_migration(  # type: ignore[no-untyped-def]
    candidate_id: str, request: MigrationRequest, db=Depends(get_db_session)
):
    try:
        return await FreeNodeLifecycleService(db).plan_migration(
            candidate_id, request.days_before_expiry
        )
    except FreeNodeError as exc:
        _handle(exc)
