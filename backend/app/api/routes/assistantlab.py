"""AI Assistant Interoperability and Technology Learning routes (OD-28).

Internal research capability. No route exposes a user-facing assistant feature.
"""

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.services.assistantlab_service import AssistantLabService, LabError

router = APIRouter(prefix="/api/v1/assistant-lab", tags=["assistant-lab"])


class SystemRequest(BaseModel):
    name: str
    vendor: str
    official_docs_url: str
    integration_method: str = "official_interface_only"
    public_capabilities: list[str] = []
    terms_url: Optional[str] = None


class NoteRequest(BaseModel):
    assistant_id: str
    topic: str
    observation: str
    source_url: str
    source_date: Optional[str] = None
    confidence: float = 0.5
    status: str = "observation"


class AdapterRequest(BaseModel):
    assistant_id: str
    name: str
    interface_type: str
    endpoint_template: Optional[str] = None
    auth_method: str = "operator_provided_credential"
    requires_credential: bool = True
    notes: Optional[str] = None


class ExperimentRequest(BaseModel):
    capability: str
    hypothesis: str
    method: str


class ResultRequest(BaseModel):
    result: str
    evidence: Dict[str, Any] = {}


class AdoptRequest(BaseModel):
    creator_approval_reference: str


class ComparisonRequest(BaseModel):
    assistant_id: str
    capability: str
    rating: int
    evidence_note: str


def _actor(request: Request) -> str:
    credential = getattr(request.state, "credential", None)
    return str(credential.get("name", "sdk")) if credential else "sdk"


def _handle(exc: LabError) -> HTTPException:
    return HTTPException(status_code=404 if "not found" in str(exc) else 400, detail=str(exc))


@router.get("/boundaries")
async def boundaries():
    return AssistantLabService.boundaries()


@router.post("/systems")
async def register_system(payload: SystemRequest, request: Request, db: AsyncSession = Depends(get_db_session)):
    try:
        return await AssistantLabService(db).register_system(payload.model_dump(), _actor(request))
    except LabError as exc:
        raise _handle(exc)


@router.get("/systems")
async def systems(db: AsyncSession = Depends(get_db_session)):
    return await AssistantLabService(db).systems()


@router.post("/notes")
async def add_note(payload: NoteRequest, request: Request, db: AsyncSession = Depends(get_db_session)):
    try:
        return await AssistantLabService(db).add_note(payload.model_dump(exclude_none=True), _actor(request))
    except LabError as exc:
        raise _handle(exc)


@router.get("/notes")
async def notes(assistant_id: str, topic: Optional[str] = None, db: AsyncSession = Depends(get_db_session)):
    return await AssistantLabService(db).notes(assistant_id, topic)


@router.post("/adapters")
async def register_adapter(payload: AdapterRequest, request: Request, db: AsyncSession = Depends(get_db_session)):
    try:
        return await AssistantLabService(db).register_adapter(payload.model_dump(exclude_none=True), _actor(request))
    except LabError as exc:
        raise _handle(exc)


@router.get("/adapters")
async def adapters(assistant_id: str, db: AsyncSession = Depends(get_db_session)):
    return await AssistantLabService(db).adapters(assistant_id)


@router.post("/experiments")
async def start_experiment(payload: ExperimentRequest, request: Request, db: AsyncSession = Depends(get_db_session)):
    try:
        return await AssistantLabService(db).start_experiment(payload.model_dump(), _actor(request))
    except LabError as exc:
        raise _handle(exc)


@router.get("/experiments")
async def experiments(db: AsyncSession = Depends(get_db_session)):
    return await AssistantLabService(db).experiments()


@router.post("/experiments/{experiment_id}/result")
async def record_result(experiment_id: str, payload: ResultRequest, request: Request, db: AsyncSession = Depends(get_db_session)):
    try:
        return await AssistantLabService(db).record_result(experiment_id, payload.model_dump(), _actor(request))
    except LabError as exc:
        raise _handle(exc)


@router.post("/experiments/{experiment_id}/adopt")
async def adopt_experiment(experiment_id: str, payload: AdoptRequest, request: Request, db: AsyncSession = Depends(get_db_session)):
    try:
        return await AssistantLabService(db).adopt_experiment(
            experiment_id, payload.creator_approval_reference, _actor(request)
        )
    except LabError as exc:
        raise _handle(exc)


@router.post("/comparisons")
async def compare(payload: ComparisonRequest, request: Request, db: AsyncSession = Depends(get_db_session)):
    try:
        return await AssistantLabService(db).compare(payload.model_dump(), _actor(request))
    except LabError as exc:
        raise _handle(exc)


@router.get("/comparisons")
async def comparisons(capability: Optional[str] = None, db: AsyncSession = Depends(get_db_session)):
    return await AssistantLabService(db).comparisons(capability)


@router.get("/status")
async def status(db: AsyncSession = Depends(get_db_session)):
    return await AssistantLabService(db).status()
