"""Website Knowledge Base API routes."""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.services.web_knowledge_service import WebsiteKnowledgeError, WebsiteKnowledgeService

router = APIRouter(prefix="/api/v1/web/knowledge", tags=["web-knowledge"])


class KnowledgeCreate(BaseModel):
    domain: str
    display_name: Optional[str] = None
    homepage_url: Optional[str] = None
    login_procedure: List[Dict[str, Any]] = Field(default_factory=list)
    auth_methods: List[str] = Field(default_factory=list)
    registration_procedure: List[Dict[str, Any]] = Field(default_factory=list)
    supported_passkeys: bool = False
    mfa_methods: List[str] = Field(default_factory=list)
    known_restrictions: List[str] = Field(default_factory=list)
    browser_compatibility: List[str] = Field(default_factory=list)
    verification_requirements: List[str] = Field(default_factory=list)
    prior_failures: List[Dict[str, Any]] = Field(default_factory=list)
    success_patterns: List[Dict[str, Any]] = Field(default_factory=list)


class KnowledgeUpdate(BaseModel):
    display_name: Optional[str] = None
    homepage_url: Optional[str] = None
    login_procedure: Optional[List[Dict[str, Any]]] = None
    auth_methods: Optional[List[str]] = None
    registration_procedure: Optional[List[Dict[str, Any]]] = None
    supported_passkeys: Optional[bool] = None
    mfa_methods: Optional[List[str]] = None
    known_restrictions: Optional[List[str]] = None
    browser_compatibility: Optional[List[str]] = None
    verification_requirements: Optional[List[str]] = None
    prior_failures: Optional[List[Dict[str, Any]]] = None
    success_patterns: Optional[List[Dict[str, Any]]] = None


def _actor(request: Request) -> str:
    credential = getattr(request.state, "credential", None)
    return str(credential.get("name", "sdk")) if credential else "sdk"


def _fail(exc: WebsiteKnowledgeError) -> HTTPException:
    return HTTPException(400, str(exc))


@router.post("")
async def create_knowledge(
    payload: KnowledgeCreate,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    """Create website knowledge for a domain."""
    try:
        return await WebsiteKnowledgeService(db).create(
            domain=payload.domain,
            display_name=payload.display_name,
            homepage_url=payload.homepage_url,
            login_procedure=payload.login_procedure,
            auth_methods=payload.auth_methods,
            registration_procedure=payload.registration_procedure,
            supported_passkeys=payload.supported_passkeys,
            mfa_methods=payload.mfa_methods,
            known_restrictions=payload.known_restrictions,
            browser_compatibility=payload.browser_compatibility,
            verification_requirements=payload.verification_requirements,
            prior_failures=payload.prior_failures,
            success_patterns=payload.success_patterns,
            actor=_actor(request),
        )
    except WebsiteKnowledgeError as exc:
        raise _fail(exc) from exc


@router.get("")
async def list_knowledge(db: AsyncSession = Depends(get_db_session)):
    """List all website knowledge records."""
    return await WebsiteKnowledgeService(db).list()


@router.get("/{knowledge_id}")
async def get_knowledge(knowledge_id: str, db: AsyncSession = Depends(get_db_session)):
    """Get a single website knowledge record by ID."""
    try:
        return await WebsiteKnowledgeService(db).get(knowledge_id)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.patch("/{knowledge_id}")
async def update_knowledge(
    knowledge_id: str,
    payload: KnowledgeUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    """Update website knowledge."""
    try:
        return await WebsiteKnowledgeService(db).update(
            knowledge_id,
            display_name=payload.display_name,
            homepage_url=payload.homepage_url,
            login_procedure=payload.login_procedure,
            auth_methods=payload.auth_methods,
            registration_procedure=payload.registration_procedure,
            supported_passkeys=payload.supported_passkeys,
            mfa_methods=payload.mfa_methods,
            known_restrictions=payload.known_restrictions,
            browser_compatibility=payload.browser_compatibility,
            verification_requirements=payload.verification_requirements,
            prior_failures=payload.prior_failures,
            success_patterns=payload.success_patterns,
            actor=_actor(request),
        )
    except WebsiteKnowledgeError as exc:
        raise _fail(exc) from exc
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.delete("/{knowledge_id}")
async def delete_knowledge(
    knowledge_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    """Delete website knowledge."""
    try:
        return await WebsiteKnowledgeService(db).delete(knowledge_id, actor=_actor(request))
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc