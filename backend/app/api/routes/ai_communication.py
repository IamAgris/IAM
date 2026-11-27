"""AI Communication & Collaboration API routes (Module C)."""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.services.ai_communication import AICommunicationError, AICommunicationService

router = APIRouter(prefix="/api/v1/ai-communication", tags=["ai-communication"])


class AIIdentityCreate(BaseModel):
    name: str
    provider: str
    model_id: Optional[str] = None
    communication_channel: str
    is_local: bool = False
    communication_permitted: bool = False
    trust_level: str = "untrusted"
    description: Optional[str] = None


class AIIdentityUpdate(BaseModel):
    communication_permitted: Optional[bool] = None
    trust_level: Optional[str] = None


class CapabilityCreate(BaseModel):
    ai_identity_id: str
    capability: str
    confidence_score: int
    evidence: List[Dict[str, Any]] = Field(default_factory=list)


class ConversationCreate(BaseModel):
    ai_identity_id: str
    title: str
    topic: Optional[str] = None
    is_human_mediated: bool = False


class MessageCreate(BaseModel):
    conversation_id: str
    sender: str
    content: str
    message_type: str = "text"
    confidence_score: Optional[int] = None


class ContextExchangeCreate(BaseModel):
    ai_identity_id: str
    context_type: str
    content: Dict[str, Any]
    conversation_id: Optional[str] = None


class VerificationCreate(BaseModel):
    message_id: str
    original_claim: str
    verified_claim: Optional[str] = None
    verification_method: str
    confidence: int
    evidence_references: List[Dict[str, Any]] = Field(default_factory=list)


class ReputationCreate(BaseModel):
    ai_identity_id: str
    accuracy_score: int
    honesty_score: int
    helpfulness_score: int
    correct_predictions: int = 0
    incorrect_predictions: int = 0


class PermissionCreate(BaseModel):
    ai_identity_id: str
    can_share_project_context: bool = False
    can_share_research_findings: bool = False
    can_share_code: bool = False
    can_receive_private_data: bool = False
    can_initiate_contact: bool = False
    can_receive_responses: bool = False


class HumanBridgeCreate(BaseModel):
    ai_identity_id: str
    iam_message: str


class HumanBridgeComplete(BaseModel):
    status: str
    human_response: Optional[str] = None
    ai_response: Optional[str] = None


def _actor(request: Request) -> str:
    credential = getattr(request.state, "credential", None)
    return str(credential.get("name", "sdk")) if credential else "sdk"


def _fail(exc: AICommunicationError) -> HTTPException:
    return HTTPException(400, str(exc))


# ------------------------------------------------------------------ identity registry

@router.post("/identity-registry")
async def register_ai_identity(
    payload: AIIdentityCreate,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    """Register an AI system IAM can communicate with."""
    try:
        return await AICommunicationService(db).register_ai_identity(
            name=payload.name,
            provider=payload.provider,
            model_id=payload.model_id,
            communication_channel=payload.communication_channel,
            is_local=payload.is_local,
            communication_permitted=payload.communication_permitted,
            trust_level=payload.trust_level,
            description=payload.description,
            actor=_actor(request),
        )
    except AICommunicationError as exc:
        raise _fail(exc) from exc


@router.get("/identity-registry")
async def list_ai_identities(db: AsyncSession = Depends(get_db_session)):
    """List AI systems IAM can communicate with."""
    return await AICommunicationService(db).list_identities()


@router.patch("/identity-registry/{identity_id}")
async def update_ai_identity(
    identity_id: str,
    payload: AIIdentityUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    """Update AI identity communication permissions and trust level."""
    try:
        return await AICommunicationService(db).update_identity(
            identity_id,
            communication_permitted=payload.communication_permitted,
            trust_level=payload.trust_level,
            actor=_actor(request),
        )
    except AICommunicationError as exc:
        raise _fail(exc) from exc
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc


# ------------------------------------------------------------------ capabilities

@router.post("/capabilities")
async def register_capability(
    payload: CapabilityCreate,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    """Register an AI capability."""
    try:
        return await AICommunicationService(db).register_capability(
            ai_identity_id=payload.ai_identity_id,
            capability=payload.capability,
            confidence_score=payload.confidence_score,
            evidence=payload.evidence,
            actor=_actor(request),
        )
    except AICommunicationError as exc:
        raise _fail(exc) from exc


@router.get("/capabilities")
async def list_capabilities(
    ai_identity_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db_session),
):
    """List AI capability records."""
    return await AICommunicationService(db).list_capabilities(ai_identity_id)


# ------------------------------------------------------------------ conversations

@router.post("/conversations")
async def create_conversation(
    payload: ConversationCreate,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    """Create a conversation thread with an AI system."""
    try:
        return await AICommunicationService(db).create_conversation(
            ai_identity_id=payload.ai_identity_id,
            title=payload.title,
            topic=payload.topic,
            is_human_mediated=payload.is_human_mediated,
            actor=_actor(request),
        )
    except AICommunicationError as exc:
        raise _fail(exc) from exc


@router.get("/conversations")
async def list_conversations(
    ai_identity_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db_session),
):
    """List conversation threads."""
    return await AICommunicationService(db).list_conversations(ai_identity_id)


@router.post("/conversations/{conversation_id}/messages")
async def add_message(
    conversation_id: str,
    payload: MessageCreate,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    """Add a message to a conversation thread."""
    try:
        return await AICommunicationService(db).add_message(
            conversation_id=conversation_id,
            sender=payload.sender,
            content=payload.content,
            message_type=payload.message_type,
            confidence_score=payload.confidence_score,
            actor=_actor(request),
        )
    except AICommunicationError as exc:
        raise _fail(exc) from exc


@router.get("/conversations/{conversation_id}/messages")
async def list_messages(
    conversation_id: str,
    db: AsyncSession = Depends(get_db_session),
):
    """List messages in a conversation thread."""
    return await AICommunicationService(db).list_messages(conversation_id)


# ------------------------------------------------------------------ context exchange

@router.post("/context")
async def exchange_context(
    payload: ContextExchangeCreate,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    """Record context shared with an AI system."""
    try:
        return await AICommunicationService(db).exchange_context(
            ai_identity_id=payload.ai_identity_id,
            context_type=payload.context_type,
            content=payload.content,
            conversation_id=payload.conversation_id,
            actor=_actor(request),
        )
    except AICommunicationError as exc:
        raise _fail(exc) from exc


@router.get("/context")
async def list_context_exchanges(
    ai_identity_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db_session),
):
    """List context exchange records."""
    return await AICommunicationService(db).list_context_exchanges(ai_identity_id)


# ------------------------------------------------------------------ response verification

@router.post("/conversations/{message_id}/verify")
async def verify_response(
    message_id: str,
    payload: VerificationCreate,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    """Verify an AI response against independent evidence."""
    try:
        return await AICommunicationService(db).verify_response(
            message_id=payload.message_id,
            original_claim=payload.original_claim,
            verified_claim=payload.verified_claim,
            verification_method=payload.verification_method,
            confidence=payload.confidence,
            evidence_references=payload.evidence_references,
            actor=_actor(request),
        )
    except AICommunicationError as exc:
        raise _fail(exc) from exc


# ------------------------------------------------------------------ reputation

@router.post("/reputation")
async def record_reputation(
    payload: ReputationCreate,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    """Record AI reputation scores."""
    try:
        return await AICommunicationService(db).record_reputation(
            ai_identity_id=payload.ai_identity_id,
            accuracy_score=payload.accuracy_score,
            honesty_score=payload.honesty_score,
            helpfulness_score=payload.helpfulness_score,
            correct_predictions=payload.correct_predictions,
            incorrect_predictions=payload.incorrect_predictions,
            actor=_actor(request),
        )
    except AICommunicationError as exc:
        raise _fail(exc) from exc


@router.get("/reputation")
async def list_reputations(
    ai_identity_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db_session),
):
    """List AI reputation records."""
    return await AICommunicationService(db).list_reputations(ai_identity_id)


# ------------------------------------------------------------------ permissions

@router.post("/permissions")
async def set_permissions(
    payload: PermissionCreate,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    """Set communication permissions for an AI system."""
    try:
        return await AICommunicationService(db).set_permissions(
            ai_identity_id=payload.ai_identity_id,
            can_share_project_context=payload.can_share_project_context,
            can_share_research_findings=payload.can_share_research_findings,
            can_share_code=payload.can_share_code,
            can_receive_private_data=payload.can_receive_private_data,
            can_initiate_contact=payload.can_initiate_contact,
            can_receive_responses=payload.can_receive_responses,
            actor=_actor(request),
        )
    except AICommunicationError as exc:
        raise _fail(exc) from exc


@router.get("/permissions")
async def list_permissions(db: AsyncSession = Depends(get_db_session)):
    """List communication permissions."""
    return await AICommunicationService(db).list_permissions()


# ------------------------------------------------------------------ human communication bridge

@router.post("/human-bridge")
async def create_human_bridge(
    payload: HumanBridgeCreate,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    """Create a human-mediated communication request."""
    try:
        return await AICommunicationService(db).create_human_bridge(
            ai_identity_id=payload.ai_identity_id,
            iam_message=payload.iam_message,
            actor=_actor(request),
        )
    except AICommunicationError as exc:
        raise _fail(exc) from exc


@router.get("/human-bridge")
async def list_human_bridges(db: AsyncSession = Depends(get_db_session)):
    """List human-mediated communication bridge records."""
    return await AICommunicationService(db).list_bridges()


@router.post("/human-bridge/{bridge_id}/complete")
async def complete_human_bridge(
    bridge_id: str,
    payload: HumanBridgeComplete,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    """Complete a human-mediated communication."""
    try:
        return await AICommunicationService(db).complete_bridge(
            bridge_id,
            status=payload.status,
            human_response=payload.human_response,
            ai_response=payload.ai_response,
            actor=_actor(request),
        )
    except AICommunicationError as exc:
        raise _fail(exc) from exc
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc


# ------------------------------------------------------------------ audit

@router.get("/audit")
async def list_audit(
    ai_identity_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db_session),
):
    """List AI communication audit events."""
    return await AICommunicationService(db).list_audit(ai_identity_id)