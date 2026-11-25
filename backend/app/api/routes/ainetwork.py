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


@router.post("/agents")
async def register_agent(request: AgentRegisterRequest, db=Depends(get_db_session)):
    """Register a discovered external AI agent."""
    service = AINetworkService(db)
    try:
        return await service.register_agent(
            request.name, request.endpoint_url, request.protocol,
            request.capabilities, request.description, request.discovery_source,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/agents")
async def list_agents(db=Depends(get_db_session)):
    """List IAM's external AI network."""
    service = AINetworkService(db)
    return await service.list_agents()


@router.patch("/agents/{agent_id}/status")
async def set_agent_status(agent_id: str, request: AgentStatusRequest, db=Depends(get_db_session)):
    """Update agent status — including blocking untrusted agents."""
    service = AINetworkService(db)
    try:
        return await service.set_agent_status(agent_id, request.status)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/agents/{agent_id}/message")
async def send_message(agent_id: str, request: SendMessageRequest, db=Depends(get_db_session)):
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
async def get_interactions(
    agent_id: Optional[str] = None,
    limit: int = 50,
    db=Depends(get_db_session),
):
    """Get complete audit log of external communications."""
    service = AINetworkService(db)
    return await service.get_interactions(agent_id, limit)


@router.post("/trust")
async def record_trust(request: TrustRequest, db=Depends(get_db_session)):
    """Record a trust assessment for an external agent."""
    service = AINetworkService(db)
    return await service.record_trust_assessment(
        request.agent_id, request.assessment, request.trust_delta, request.evidence
    )


@router.post("/collaborations")
async def propose_collaboration(request: CollaborationRequest, db=Depends(get_db_session)):
    """Propose a task collaboration with an external agent."""
    service = AINetworkService(db)
    return await service.propose_collaboration(
        request.agent_id, request.task_description, request.task_type, request.requires_authorization
    )


@router.get("/collaborations")
async def list_collaborations(db=Depends(get_db_session)):
    """List all external AI collaborations."""
    service = AINetworkService(db)
    return await service.list_collaborations()
