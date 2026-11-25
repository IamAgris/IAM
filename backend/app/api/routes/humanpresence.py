"""Human Public Presence Intelligence routes (OD-30 / PPIICE).

Public information only; no visitor memory, credentials or de-anonymisation.
"""

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.services.humanpresence_service import HumanPresenceService, PresenceError

router = APIRouter(prefix="/api/v1/human-presence", tags=["human-presence"])


class PersonRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    canonical_name: str
    notes: Optional[str] = None
    deanonymize_target: bool = False


class ProfileRequest(BaseModel):
    person_id: str
    source_name: str
    source_url: str
    profile_type: str = "personal_site"
    stated_name: Optional[str] = None
    role: Optional[str] = None
    organization: Optional[str] = None
    bio: Optional[str] = None
    interests: list[str] = []
    status: str = "self_reported"
    confidence: float = 0.4
    published_at: Optional[str] = None
    retrieved_at: Optional[str] = None


class ClaimRequest(BaseModel):
    person_id: str
    profile_id: Optional[str] = None
    claim_type: str
    value: Dict[str, Any]
    status: str = "uncertain"
    confidence: float = 0.5
    source_url: Optional[str] = None
    first_seen_at: Optional[str] = None
    last_seen_at: Optional[str] = None


class MatchRequest(BaseModel):
    other_id: str
    evidence: Dict[str, Any]
    confidence: float = 0.5


class RelationshipRequest(BaseModel):
    person_id: str
    related_person_id: Optional[str] = None
    organization_name: Optional[str] = None
    relationship_type: str
    evidence: Dict[str, Any]
    confidence: float = 0.5


class ResearchRequest(BaseModel):
    url: str


class CorrectionRequest(BaseModel):
    value: Dict[str, Any]
    reason: str


def _actor(request: Request) -> str:
    credential = getattr(request.state, "credential", None)
    return str(credential.get("name", "sdk")) if credential else "sdk"


def _handle(exc: PresenceError) -> HTTPException:
    return HTTPException(status_code=404 if "not found" in str(exc) else 400, detail=str(exc))


@router.get("/boundaries")
async def boundaries():
    return HumanPresenceService.boundaries()


@router.post("/people")
async def create_person(payload: PersonRequest, request: Request, db: AsyncSession = Depends(get_db_session)):
    try:
        return await HumanPresenceService(db).create_person(payload.model_dump(), _actor(request))
    except PresenceError as exc:
        raise _handle(exc)


@router.get("/people")
async def people(name: Optional[str] = None, db: AsyncSession = Depends(get_db_session)):
    return await HumanPresenceService(db).people(name)


@router.post("/profiles")
async def add_profile(payload: ProfileRequest, request: Request, db: AsyncSession = Depends(get_db_session)):
    try:
        return await HumanPresenceService(db).add_profile(payload.model_dump(exclude_none=True), _actor(request))
    except PresenceError as exc:
        raise _handle(exc)


@router.post("/profiles/{profile_id}/verify")
async def verify_profile(profile_id: str, request: Request, db: AsyncSession = Depends(get_db_session)):
    try:
        return await HumanPresenceService(db).verify_profile(profile_id, _actor(request))
    except PresenceError as exc:
        raise _handle(exc)


@router.post("/research")
async def research_page(person_id: str, payload: ResearchRequest, request: Request, db: AsyncSession = Depends(get_db_session)):
    try:
        return await HumanPresenceService(db).research_public_page(
            person_id, payload.url, _actor(request)
        )
    except PresenceError as exc:
        raise _handle(exc)


@router.post("/claims")
async def add_claim(payload: ClaimRequest, request: Request, db: AsyncSession = Depends(get_db_session)):
    try:
        return await HumanPresenceService(db).add_claim(payload.model_dump(exclude_none=True), _actor(request))
    except PresenceError as exc:
        raise _handle(exc)


@router.post("/claims/{claim_id}/corrections")
async def correct_claim(claim_id: str, payload: CorrectionRequest, request: Request, db: AsyncSession = Depends(get_db_session)):
    try:
        return await HumanPresenceService(db).correct_claim(
            claim_id, payload.value, payload.reason, _actor(request)
        )
    except PresenceError as exc:
        raise _handle(exc)


@router.post("/people/{person_id}/match")
async def match_people(person_id: str, payload: MatchRequest, request: Request, db: AsyncSession = Depends(get_db_session)):
    try:
        return await HumanPresenceService(db).match_people(
            person_id, payload.other_id, payload.evidence, payload.confidence, _actor(request)
        )
    except PresenceError as exc:
        raise _handle(exc)


@router.get("/people/{person_id}/matches")
async def matches(person_id: str, db: AsyncSession = Depends(get_db_session)):
    return await HumanPresenceService(db).matches(person_id)


@router.post("/relationships")
async def add_relationship(payload: RelationshipRequest, request: Request, db: AsyncSession = Depends(get_db_session)):
    try:
        return await HumanPresenceService(db).add_relationship(payload.model_dump(exclude_none=True), _actor(request))
    except PresenceError as exc:
        raise _handle(exc)


@router.get("/people/{person_id}/profiles")
async def profiles(person_id: str, db: AsyncSession = Depends(get_db_session)):
    return await HumanPresenceService(db).profiles(person_id)


@router.get("/people/{person_id}/claims")
async def claims(person_id: str, db: AsyncSession = Depends(get_db_session)):
    return await HumanPresenceService(db).claims(person_id)


@router.get("/people/{person_id}/timeline")
async def timeline(person_id: str, db: AsyncSession = Depends(get_db_session)):
    return await HumanPresenceService(db).timeline(person_id)
