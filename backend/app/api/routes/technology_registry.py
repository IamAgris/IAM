"""Doc 20 / OD-36: Technology Capability Registry endpoints."""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.database import get_db_session
from app.services.technology_registry_service import (
    TechnologyRegistryError,
    TechnologyRegistryService,
)

router = APIRouter(prefix="/api/v1/technology-registry", tags=["technology-registry"])


class RegisterRequest(BaseModel):
    name: str
    version: Optional[str] = None
    official_source: Optional[str] = None
    source_url: Optional[str] = None
    language: Optional[str] = None
    architectures: List[str] = []
    licence: Optional[str] = None
    commercial_use_ok: bool = False
    cost_status: str = "free"
    hardware_requirements: Dict[str, Any] = {}
    capabilities: List[str] = []
    limitations: List[str] = []
    security_status: Optional[str] = None
    maintenance_status: Optional[str] = None
    compatibility: Dict[str, Any] = {}
    notes: Optional[str] = None


class StateRequest(BaseModel):
    state: str


class BenchmarkRequest(BaseModel):
    benchmark: Dict[str, Any]


def _handle(exc: Exception):
    raise HTTPException(status_code=400, detail=str(exc))


@router.post("/", status_code=201)
async def register(request: RegisterRequest, db=Depends(get_db_session)):
    """Record a researched third-party technology. No install or execution occurs."""
    try:
        return await TechnologyRegistryService(db).register(request.model_dump())
    except TechnologyRegistryError as exc:
        _handle(exc)


@router.get("")
async def list_technologies(
    state: Optional[str] = None, limit: int = 50, db=Depends(get_db_session)
):
    try:
        return await TechnologyRegistryService(db).list_technologies(state, limit)
    except TechnologyRegistryError as exc:
        _handle(exc)


@router.get("/{tech_id}")
async def get_technology(tech_id: str, db=Depends(get_db_session)):
    try:
        return await TechnologyRegistryService(db).get(tech_id)
    except TechnologyRegistryError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.patch("/{tech_id}/state")
async def set_state(tech_id: str, request: StateRequest, db=Depends(get_db_session)):
    """Advance lifecycle state. 'integrated' requires prior approval (OD-11)."""
    try:
        return await TechnologyRegistryService(db).set_state(tech_id, request.state)
    except TechnologyRegistryError as exc:
        _handle(exc)


@router.post("/{tech_id}/benchmarks", status_code=201)
async def record_benchmark(
    tech_id: str, request: BenchmarkRequest, db=Depends(get_db_session)
):
    try:
        return await TechnologyRegistryService(db).record_benchmark(
            tech_id, request.benchmark
        )
    except TechnologyRegistryError as exc:
        _handle(exc)
