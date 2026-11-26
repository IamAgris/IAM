"""Remaining white-hat controls: study plan, labs and remediation validation."""

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.services.security_policy import AuthorisedTargetDenied
from app.services.whitehat_labs import WhiteHatLabError, WhiteHatLabService
from app.services.whitehat_policy import DEFENSIVE_FRAMEWORKS, STUDY_POLICY

router = APIRouter(prefix="/api/v1/aegis", tags=["iam-aegis"])


class LabCreate(BaseModel):
    target: str
    ttl_seconds: int = 3600


class RemediationValidationRequest(BaseModel):
    target: str
    finding_id: str
    proposed_fix: str
    validation_command: str
    ttl_seconds: int = 1800


def _actor(request: Request) -> str:
    credential = getattr(request.state, "credential", None)
    return credential.get("name", "iam") if credential else "iam"


@router.get("/study-plan")
async def study_plan():
    """WH-08/WH-09: what IAM studies and the learning-only capability boundary."""
    return {
        "posture": "defensive_only",
        "frameworks": list(DEFENSIVE_FRAMEWORKS),
        "policy": STUDY_POLICY,
        "note": "Study records never grant executable capability; offensive tools are not created.",
    }


@router.post("/labs")
async def create_lab(
    payload: LabCreate,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    try:
        return await WhiteHatLabService(db).create_lab(
            payload.target, _actor(request), payload.ttl_seconds
        )
    except AuthorisedTargetDenied as exc:
        raise HTTPException(403, str(exc)) from exc
    except WhiteHatLabError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.get("/labs")
async def list_labs(db: AsyncSession = Depends(get_db_session)):
    return await WhiteHatLabService(db).list_sessions()


@router.post("/labs/{session_id}/start")
async def start_lab(
    session_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    try:
        return await WhiteHatLabService(db).start_lab(session_id, _actor(request))
    except WhiteHatLabError as exc:
        raise HTTPException(400, str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.post("/labs/{session_id}/destroy")
async def destroy_lab(
    session_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    try:
        return await WhiteHatLabService(db).destroy_session(session_id, _actor(request))
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.post("/remediations/validate")
async def validate_remediation(
    payload: RemediationValidationRequest,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    """WH-05: verify a proposed fix in an isolated lab before proposing it."""
    try:
        return await WhiteHatLabService(db).validate_remediation(
            payload.target,
            payload.finding_id,
            payload.proposed_fix,
            payload.validation_command,
            _actor(request),
            payload.ttl_seconds,
        )
    except AuthorisedTargetDenied as exc:
        raise HTTPException(403, str(exc)) from exc
    except (WhiteHatLabError, ValueError) as exc:
        raise HTTPException(400, str(exc)) from exc
