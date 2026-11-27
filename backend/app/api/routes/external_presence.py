"""External digital presence routes - website, email, authorized platform integrations"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid

from app.core.database import get_db_session
from app.models.security import IntegrationRegistry, IntegrationPermission
from app.models.identity import AIIdentity
from app.services.creatorapproval_service import CreatorApprovalService

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
    requires_creator_approval: bool = True
    creator_request_id: Optional[str] = None
    created_at: Optional[str]
    updated_at: Optional[str]

    class Config:
        from_attributes = True


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
        is_active=False,  # Not active until signed Creator approval
        requires_creator_approval=bool(integration.requires_human_approval),
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

    creator_request_id = None
    if integration.requires_human_approval:
        # OD-19: the Creator email flow replaces the legacy in-app approval row.
        request = await CreatorApprovalService(db).create_request(
            action_type="external_presence.connect_integration",
            summary=f"Connect {integration.provider} integration {integration.name}",
            consequences=[
                "Integration will be able to act within its configured permission scope",
                "Activation still requires a verified signed challenge",
            ],
            risk_level="3",
            target_ref=str(integ.id),
            reason=integration.config.get("requested_by", "autonomy-service"),
        )
        creator_request_id = request["request_id"]

    await db.commit()
    await db.refresh(integ)

    return IntegrationResponse(
        id=str(integ.id),
        name=integ.name,
        provider=integ.provider,
        integration_type=integ.integration_type,
        config=integ.config or {},
        is_active=integ.is_active,
        requires_creator_approval=integ.requires_creator_approval,
        creator_request_id=creator_request_id,
        created_at=integ.created_at.isoformat() if integ.created_at else None,
        updated_at=integ.updated_at.isoformat() if integ.updated_at else None,
    )


@router.patch("/integrations/{integration_id}/activate")
async def activate_integration(
    integration_id: str,
    db: AsyncSession = Depends(get_db_session),
):
    """Activate an integration only after signed Creator email approval."""
    result = await db.execute(select(IntegrationRegistry).where(IntegrationRegistry.id == integration_id))
    integ = result.scalar_one_or_none()
    if not integ:
        raise HTTPException(status_code=404, detail="Integration not found")

    if integ.requires_creator_approval:
        authorization = await CreatorApprovalService(db).check_authorization(
            "external_presence.connect_integration", "3", target_ref=str(integ.id)
        )
        if not authorization["authorized"]:
            raise HTTPException(
                status_code=403,
                detail=(
                    authorization["reason"]
                    + " Request approval through the Creator email challenge."
                ),
            )

    integ.is_active = True
    await db.commit()

    return {"integration_id": integration_id, "is_active": True}


@router.post("/integrations/{integration_id}/request-approval")
async def request_integration_approval(
    integration_id: str,
    reason: Optional[str] = None,
    db: AsyncSession = Depends(get_db_session),
):
    """Send (or re-send) the Creator email request for a pending integration."""
    result = await db.execute(select(IntegrationRegistry).where(IntegrationRegistry.id == integration_id))
    integ = result.scalar_one_or_none()
    if not integ:
        raise HTTPException(status_code=404, detail="Integration not found")
    if not integ.requires_creator_approval:
        raise HTTPException(status_code=400, detail="Integration does not require approval")
    request = await CreatorApprovalService(db).create_request(
        action_type="external_presence.connect_integration",
        summary=f"Connect {integ.provider} integration {integ.name}",
        consequences=["Integration can act within its configured permission scope"],
        risk_level="3",
        target_ref=str(integ.id),
        reason=reason,
    )
    return request


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


# Legacy in-app approval endpoints were removed (OD-19).
# Creator approvals now travel by email and are proven by signed challenges:
#   POST /api/v1/creator/requests  -> send approval email
#   POST /api/v1/creator/gateway/decision -> verified signature
