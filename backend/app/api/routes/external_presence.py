"""External digital presence routes - website, email, authorized platform integrations"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid

from app.core.database import get_db_session
from app.models.security import IntegrationRegistry, IntegrationPermission, ApprovalRequest
from app.models.identity import AIIdentity

router = APIRouter(prefix="/api/v1/external-presence", tags=["external-presence"])


# --- Pydantic models ---

class WebsiteIdentityCreate(BaseModel):
    domain: str
    site_title: str
    site_description: Optional[str] = None
    is_published: bool = False


class WebsiteIdentityResponse(BaseModel):
    id: str
    domain: str
    site_title: str
    site_description: Optional[str]
    is_published: bool
    created_at: Optional[str]
    updated_at: Optional[str]

    class Config:
        from_attributes = True


class EmailIdentityCreate(BaseModel):
    email_address: str
    provider: str  # e.g. 'custom-domain', 'gmail', 'protonmail'
    is_verified: bool = False


class EmailIdentityResponse(BaseModel):
    id: str
    email_address: str
    provider: str
    is_verified: bool
    created_at: Optional[str]

    class Config:
        from_attributes = True


class IntegrationConnect(BaseModel):
    name: str
    provider: str  # e.g. 'vibecircle', 'twitter', 'github', 'linkedin'
    integration_type: str  # e.g. 'social', 'business', 'communication'
    config: Dict[str, Any] = {}
    requires_human_approval: bool = True


class IntegrationResponse(BaseModel):
    id: str
    name: str
    provider: str
    integration_type: str
    config: Dict[str, Any]
    is_active: bool
    created_at: Optional[str]
    updated_at: Optional[str]

    class Config:
        from_attributes = True


class ApprovalRequestCreate(BaseModel):
    action_type: str
    description: str
    requested_by: str = "autonomy-service"


class ApprovalResponse(BaseModel):
    id: str
    action_type: str
    description: str
    status: str
    requested_at: Optional[str]
    decided_at: Optional[str]


# --- In-memory store for website/email identity (Phase 9 MVP)
# In production these would be database tables
_website_identity: Optional[Dict[str, Any]] = None
_email_identity: Optional[Dict[str, Any]] = None


# --- Website Identity ---

@router.get("/website", response_model=Optional[WebsiteIdentityResponse])
async def get_website_identity():
    """Get the AI's external website identity."""
    return _website_identity


@router.post("/website", response_model=WebsiteIdentityResponse)
async def create_website_identity(website: WebsiteIdentityCreate):
    """Create or update the AI's external website identity."""
    global _website_identity
    _website_identity = {
        "id": str(uuid.uuid4()),
        "domain": website.domain,
        "site_title": website.site_title,
        "site_description": website.site_description,
        "is_published": website.is_published,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    }
    return _website_identity


@router.patch("/website", response_model=WebsiteIdentityResponse)
async def update_website_identity(website: WebsiteIdentityCreate):
    """Update the AI's external website identity."""
    global _website_identity
    if not _website_identity:
        raise HTTPException(status_code=404, detail="Website identity not found")
    _website_identity.update({
        "domain": website.domain,
        "site_title": website.site_title,
        "site_description": website.site_description,
        "is_published": website.is_published,
        "updated_at": datetime.utcnow().isoformat(),
    })
    return _website_identity


# --- Email Identity ---

@router.get("/email", response_model=Optional[EmailIdentityResponse])
async def get_email_identity():
    """Get the AI's external email identity."""
    return _email_identity


@router.post("/email", response_model=EmailIdentityResponse)
async def create_email_identity(email: EmailIdentityCreate):
    """Create or update the AI's external email identity."""
    global _email_identity
    _email_identity = {
        "id": str(uuid.uuid4()),
        "email_address": email.email_address,
        "provider": email.provider,
        "is_verified": email.is_verified,
        "created_at": datetime.utcnow().isoformat(),
    }
    return _email_identity


# --- External Integrations ---

@router.get("/integrations", response_model=List[IntegrationResponse])
async def list_integrations(db: AsyncSession = Depends(get_db_session)):
    """List all connected external integrations."""
    result = await db.execute(select(IntegrationRegistry).order_by(IntegrationRegistry.created_at.desc()))
    integrations = result.scalars().all()
    return [
        IntegrationResponse(
            id=str(i.id),
            name=i.name,
            provider=i.provider,
            integration_type=i.integration_type,
            config=i.config or {},
            is_active=i.is_active,
            created_at=i.created_at.isoformat() if i.created_at else None,
            updated_at=i.updated_at.isoformat() if i.updated_at else None,
        )
        for i in integrations
    ]


@router.post("/integrations", response_model=IntegrationResponse)
async def connect_integration(
    integration: IntegrationConnect,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Connect an external integration (e.g. VibeCircle, Twitter, GitHub).
    
    Per the AURA blueprint: VibeCircle is an optional connector, not a dependency.
    Integrations requiring external account creation need human approval.
    """
    # Check for duplicate provider+name
    result = await db.execute(
        select(IntegrationRegistry).where(
            IntegrationRegistry.provider == integration.provider,
            IntegrationRegistry.name == integration.name,
        )
    )
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Integration already exists")

    integ = IntegrationRegistry(
        name=integration.name,
        provider=integration.provider,
        integration_type=integration.integration_type,
        config=integration.config,
        is_active=False,  # Not active until approved
    )
    db.add(integ)
    await db.flush()

    # Create permission record
    perm = IntegrationPermission(
        integration_id=integ.id,
        permission_scope="read",
        expires_at=None,
    )
    db.add(perm)

    # If human approval required, create approval request
    if integration.requires_human_approval:
        approval = ApprovalRequest(
            action_type=f"connect_integration:{integration.provider}",
            description=f"Connect external integration: {integration.name} ({integration.provider})",
            requested_by=integration.config.get("requested_by", "autonomy-service"),
            status="pending",
        )
        db.add(approval)

    await db.commit()
    await db.refresh(integ)

    return IntegrationResponse(
        id=str(integ.id),
        name=integ.name,
        provider=integ.provider,
        integration_type=integ.integration_type,
        config=integ.config or {},
        is_active=integ.is_active,
        created_at=integ.created_at.isoformat() if integ.created_at else None,
        updated_at=integ.updated_at.isoformat() if integ.updated_at else None,
    )


@router.patch("/integrations/{integration_id}/activate")
async def activate_integration(
    integration_id: str,
    db: AsyncSession = Depends(get_db_session),
):
    """Activate an integration after approval."""
    result = await db.execute(select(IntegrationRegistry).where(IntegrationRegistry.id == integration_id))
    integ = result.scalar_one_or_none()
    if not integ:
        raise HTTPException(status_code=404, detail="Integration not found")

    integ.is_active = True
    await db.commit()

    return {"integration_id": integration_id, "is_active": True}


@router.delete("/integrations/{integration_id}")
async def disconnect_integration(
    integration_id: str,
    db: AsyncSession = Depends(get_db_session),
):
    """Disconnect an external integration."""
    result = await db.execute(select(IntegrationRegistry).where(IntegrationRegistry.id == integration_id))
    integ = result.scalar_one_or_none()
    if not integ:
        raise HTTPException(status_code=404, detail="Integration not found")

    await db.delete(integ)
    await db.commit()

    return {"integration_id": integration_id, "disconnected": True}


# --- Approval Requests ---

@router.get("/approvals", response_model=List[ApprovalResponse])
async def list_approval_requests(db: AsyncSession = Depends(get_db_session)):
    """List all pending approval requests."""
    result = await db.execute(
        select(ApprovalRequest).order_by(ApprovalRequest.requested_at.desc())
    )
    requests = result.scalars().all()
    return [
        ApprovalResponse(
            id=str(r.id),
            action_type=r.action_type,
            description=r.description,
            status=r.status,
            requested_at=r.requested_at.isoformat() if r.requested_at else None,
            decided_at=r.decided_at.isoformat() if r.decided_at else None,
        )
        for r in requests
    ]


@router.post("/approvals", response_model=ApprovalResponse)
async def create_approval_request(
    request: ApprovalRequestCreate,
    db: AsyncSession = Depends(get_db_session),
):
    """Create a new approval request for a sensitive action."""
    approval = ApprovalRequest(
        action_type=request.action_type,
        description=request.description,
        requested_by=request.requested_by,
        status="pending",
    )
    db.add(approval)
    await db.commit()
    await db.refresh(approval)

    return ApprovalResponse(
        id=str(approval.id),
        action_type=approval.action_type,
        description=approval.description,
        status=approval.status,
        requested_at=approval.requested_at.isoformat() if approval.requested_at else None,
        decided_at=approval.decided_at.isoformat() if approval.decided_at else None,
    )


@router.patch("/approvals/{approval_id}/decide")
async def decide_approval_request(
    approval_id: str,
    decision: str,  # 'approved' or 'rejected'
    decided_by: str = "human",
    reason: Optional[str] = None,
    db: AsyncSession = Depends(get_db_session),
):
    """Approve or reject a pending approval request."""
    if decision not in ("approved", "rejected"):
        raise HTTPException(status_code=400, detail="Decision must be 'approved' or 'rejected'")

    result = await db.execute(select(ApprovalRequest).where(ApprovalRequest.id == approval_id))
    approval = result.scalar_one_or_none()
    if not approval:
        raise HTTPException(status_code=404, detail="Approval request not found")

    approval.status = decision
    approval.decided_at = datetime.utcnow()
    approval.decided_by = decided_by
    if reason:
        approval.reason = reason

    await db.commit()

    return ApprovalResponse(
        id=str(approval.id),
        action_type=approval.action_type,
        description=approval.description,
        status=approval.status,
        requested_at=approval.requested_at.isoformat() if approval.requested_at else None,
        decided_at=approval.decided_at.isoformat() if approval.decided_at else None,
    )
