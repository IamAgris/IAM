"""External AI network routes — discovery, communication, collaboration, trust"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from app.core.database import get_db_session
from app.services.ainetwork_service import AINetworkService

router = APIRouter(prefix="/api/v1/network", tags=["ai-network"])


class AgentRegisterRequest(BaseModel):
    name: str
    endpoint_url: Optional[str] = None
    protocol: str = "rest"
    capabilities: Optional[List[str]] = None
    description: Optional[str] = None
    discovery_source: Optional[str] = None


class AgentStatusRequest(BaseModel):
    status: str  # discovered, contacted, trusted, blocked


class SendMessageRequest(BaseModel):
    agent_id: str
    message: str
    timeout_seconds: float = 30.0


class TrustRequest(BaseModel):
    agent_id: str
    assessment: str
    trust_delta: float
    evidence: Optional[List[Dict[str, Any]]] = None


class CollaborationRequest(BaseModel):
    agent_id: str
    task_description: str
    task_type: Optional[str] = None
    requires_authorization: bool = False


class AgentRegisterIdentityRequest(AgentRegisterRequest):
    """Optional identity claims — always self-reported until independently verified."""
    claimed_identity: Optional[str] = None
    creator: Optional[str] = None
    operator: Optional[str] = None
    stated_purpose: Optional[str] = None
    expertise: Optional[List[str]] = None


class IdentityVerificationRequest(BaseModel):
    evidence: List[Dict[str, Any]]


class InterviewRecordRequest(BaseModel):
    question: str
    answer: Optional[str] = None
    provenance: Optional[str] = None


@router.post("/agents")
async def register_agent(request: AgentRegisterIdentityRequest, db=Depends(get_db_session)):  # type: ignore[no-untyped-def]
    """Register a discovered external AI agent. Identity claims stay self-reported."""
    service = AINetworkService(db)
    try:
        return await service.register_agent(
            name=request.name,
            endpoint_url=request.endpoint_url,
            protocol=request.protocol,
            capabilities=request.capabilities,
            description=request.description,
            discovery_source=request.discovery_source,
            claimed_identity=request.claimed_identity,
            creator=request.creator,
            operator=request.operator,
            stated_purpose=request.stated_purpose,
            expertise=request.expertise,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/agents")
async def list_agents(db=Depends(get_db_session)):  # type: ignore[no-untyped-def]
    """List IAM's external AI network."""
    service = AINetworkService(db)
    return await service.list_agents()


@router.patch("/agents/{agent_id}/status")
async def set_agent_status(agent_id: str, request: AgentStatusRequest, db=Depends(get_db_session)):  # type: ignore[no-untyped-def]
    """Update agent status — including blocking untrusted agents."""
    service = AINetworkService(db)
    try:
        return await service.set_agent_status(agent_id, request.status)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/agents/{agent_id}/message")
async def send_message(agent_id: str, request: SendMessageRequest, db=Depends(get_db_session)):  # type: ignore[no-untyped-def]
    """Send a message to an external AI through its accessible interface.
    
    Private IAM data is never shared without owner authorization.
    Inbound content is validated and treated as untrusted information.
    """
    service = AINetworkService(db)
    try:
        return await service.send_message(agent_id, request.message, request.timeout_seconds)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/interactions")
async def get_interactions(  # type: ignore[no-untyped-def]
    agent_id: Optional[str] = None,
    limit: int = 50,
    db=Depends(get_db_session),
):
    """Get complete audit log of external communications."""
    service = AINetworkService(db)
    return await service.get_interactions(agent_id, limit)


@router.post("/trust")
async def record_trust(request: TrustRequest, db=Depends(get_db_session)):  # type: ignore[no-untyped-def]
    """Record a trust assessment for an external agent."""
    service = AINetworkService(db)
    return await service.record_trust_assessment(
        request.agent_id, request.assessment, request.trust_delta, request.evidence
    )


@router.post("/collaborations")
async def propose_collaboration(request: CollaborationRequest, db=Depends(get_db_session)):  # type: ignore[no-untyped-def]
    """Propose a task collaboration with an external agent."""
    service = AINetworkService(db)
    return await service.propose_collaboration(
        request.agent_id, request.task_description, request.task_type, request.requires_authorization
    )


@router.get("/collaborations")
async def list_collaborations(db=Depends(get_db_session)):  # type: ignore[no-untyped-def]
    """List all external AI collaborations."""
    service = AINetworkService(db)
    return await service.list_collaborations()


@router.post("/agents/{agent_id}/verify")
async def verify_identity(agent_id: str, request: IdentityVerificationRequest, db=Depends(get_db_session)):  # type: ignore[no-untyped-def]
    """Record independent verification evidence for an external AI identity.

    A self-reported claim never becomes a verified identity on its own.
    """
    service = AINetworkService(db)
    try:
        return await service.verify_identity(agent_id, request.evidence)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/agents/{agent_id}/interviews")
async def record_interview(agent_id: str, request: InterviewRecordRequest, db=Depends(get_db_session)):  # type: ignore[no-untyped-def]
    """Store a structured interview answer with provenance as untrusted data."""
    service = AINetworkService(db)
    try:
        return await service.record_interview(agent_id, request.question, request.answer, request.provenance)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/agents/{agent_id}/interviews")
async def get_interviews(agent_id: str, limit: int = 50, db=Depends(get_db_session)):  # type: ignore[no-untyped-def]
    """Get interview history with provenance and risk markers."""
    service = AINetworkService(db)
    return await service.get_interviews(agent_id, limit)


@router.get("/agents/{agent_id}/profile")
async def get_relationship_profile(agent_id: str, db=Depends(get_db_session)):  # type: ignore[no-untyped-def]
    """Get the AI relationship registry profile for one system (Doc 18 §7)."""
    service = AINetworkService(db)
    try:
        return await service.get_relationship_profile(agent_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
