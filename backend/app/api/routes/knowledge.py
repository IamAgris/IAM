"""Knowledge routes - verified knowledge items with source provenance"""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid

from app.core.database import get_db_session
from app.models.memory import KnowledgeItem, KnowledgeSource
from app.models.security import AuditEvent

router = APIRouter(prefix="/api/v1/knowledge", tags=["knowledge"])


class KnowledgeItemCreate(BaseModel):
    title: str
    content: str
    source: Optional[str] = None
    confidence_level: float = 0.5
    topic: Optional[str] = None
    verification_status: str = "unverified"
    metadata: Dict[str, Any] = {}


class KnowledgeSourceCreate(BaseModel):
    url: Optional[str] = None
    title: Optional[str] = None
    credibility_score: float = 0.5


class KnowledgeItemResponse(BaseModel):
    id: str
    title: str
    content: str
    source: Optional[str]
    confidence_level: float
    verification_status: str
    topic: Optional[str]
    created_at: Optional[str]
    last_reviewed_at: Optional[str]

    class Config:
        from_attributes = True


class KnowledgeContributionCreate(BaseModel):
    """A knowledge item contributed by a node or user.

    Contributions can never set verification status: every contribution enters
    as unverified and is reviewed through the existing verification route.
    """

    title: str
    content: str
    source_url: Optional[str] = None
    topic: Optional[str] = None
    confidence_level: float = 0.5
    contributor: Optional[str] = None
    provenance: Dict[str, Any] = Field(default_factory=dict)


class KnowledgeContributionResponse(KnowledgeItemResponse):
    contribution_id: str
    status: str = "pending_review"


def validate_contribution(payload: KnowledgeContributionCreate) -> None:
    """Shared validation for contributed knowledge (no database dependency)."""
    if not payload.title.strip():
        raise HTTPException(status_code=400, detail="title must not be empty")
    if not payload.content.strip():
        raise HTTPException(status_code=400, detail="content must not be empty")
    if not 0 <= payload.confidence_level <= 1:
        raise HTTPException(status_code=400, detail="confidence_level must be between 0 and 1")


@router.get("/", response_model=List[KnowledgeItemResponse])
async def list_knowledge(
    limit: int = 50,
    topic: Optional[str] = None,
    verification_status: Optional[str] = None,
    db: AsyncSession = Depends(get_db_session),
):
    """List knowledge items with optional filters."""
    stmt = select(KnowledgeItem).order_by(KnowledgeItem.created_at.desc()).limit(limit)
    if topic:
        stmt = stmt.where(KnowledgeItem.topic == topic)
    if verification_status:
        stmt = stmt.where(KnowledgeItem.verification_status == verification_status)
    result = await db.execute(stmt)
    items = result.scalars().all()
    return [
        KnowledgeItemResponse(
            id=str(k.id),
            title=k.title,
            content=k.content,
            source=k.source,
            confidence_level=float(k.confidence_level) if k.confidence_level else 0.5,
            verification_status=k.verification_status,
            topic=k.topic,
            created_at=k.created_at.isoformat() if k.created_at else None,
            last_reviewed_at=k.last_reviewed_at.isoformat() if k.last_reviewed_at else None,
        )
        for k in items
    ]


@router.post("/", response_model=KnowledgeItemResponse)
async def create_knowledge(
    item: KnowledgeItemCreate,
    db: AsyncSession = Depends(get_db_session),
):
    """Create a new knowledge item with provenance tracking."""
    if item.verification_status not in ("unverified", "verified", "disputed", "retracted"):
        raise HTTPException(status_code=400, detail="Invalid verification status")

    knowledge = KnowledgeItem(
        title=item.title,
        content=item.content,
        source=item.source,
        confidence_level=item.confidence_level,
        verification_status=item.verification_status,
        topic=item.topic,
        metadata_=item.metadata,
    )
    db.add(knowledge)
    await db.flush()

    # If a URL/source is provided, create a knowledge source record
    if item.source:
        source = KnowledgeSource(
            knowledge_item_id=knowledge.id,
            url=item.source,
            title=item.title,
            credibility_score=item.confidence_level,
        )
        db.add(source)

    await db.commit()
    await db.refresh(knowledge)

    return KnowledgeItemResponse(
        id=str(knowledge.id),
        title=knowledge.title,
        content=knowledge.content,
        source=knowledge.source,
        confidence_level=float(knowledge.confidence_level),
        verification_status=knowledge.verification_status,
        topic=knowledge.topic,
        created_at=knowledge.created_at.isoformat() if knowledge.created_at else None,
        last_reviewed_at=knowledge.last_reviewed_at.isoformat() if knowledge.last_reviewed_at else None,
    )


@router.post("/contributions", response_model=KnowledgeContributionResponse)
async def contribute_knowledge(
    contribution: KnowledgeContributionCreate,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    """Accept a contribution and record it, unverified, in the audit trail.

    The endpoint is intentionally separate from ``POST /knowledge/``: direct
    creation is IAM's own knowledge path, while contributions carry an explicit
    contributor identity and provenance and always require review.
    """
    validate_contribution(contribution)

    credential = getattr(request.state, "credential", None)
    actor = contribution.contributor or (
        credential.get("name", "unknown") if credential else "unknown"
    )
    metadata = {
        "contribution": True,
        "contributor": actor,
        "provenance": contribution.provenance,
    }
    knowledge = KnowledgeItem(
        title=contribution.title.strip(),
        content=contribution.content.strip(),
        source=contribution.source_url,
        confidence_level=contribution.confidence_level,
        verification_status="unverified",
        topic=contribution.topic,
        metadata_=metadata,
    )
    db.add(knowledge)
    await db.flush()

    if contribution.source_url:
        db.add(
            KnowledgeSource(
                knowledge_item_id=knowledge.id,
                url=contribution.source_url,
                title=contribution.title,
                credibility_score=contribution.confidence_level,
            )
        )

    db.add(
        AuditEvent(
            event_type="knowledge_contribution",
            actor=actor,
            target=str(knowledge.id),
            details={
                "title": contribution.title[:200],
                "source_url": contribution.source_url,
                "topic": contribution.topic,
                "provenance": contribution.provenance,
                "verification_status": "unverified",
            },
        )
    )
    await db.commit()
    await db.refresh(knowledge)

    return KnowledgeContributionResponse(
        id=str(knowledge.id),
        title=knowledge.title,
        content=knowledge.content,
        source=knowledge.source,
        confidence_level=float(knowledge.confidence_level),
        verification_status=knowledge.verification_status,
        topic=knowledge.topic,
        created_at=knowledge.created_at.isoformat() if knowledge.created_at else None,
        last_reviewed_at=knowledge.last_reviewed_at.isoformat() if knowledge.last_reviewed_at else None,
        contribution_id=str(knowledge.id),
    )


@router.post("/verify/{knowledge_id}")
async def verify_knowledge(
    knowledge_id: str,
    status: str,
    db: AsyncSession = Depends(get_db_session),
):
    """Mark knowledge as verified, disputed, or retracted."""
    if status not in ("verified", "disputed", "retracted"):
        raise HTTPException(status_code=400, detail="Invalid status")

    result = await db.execute(select(KnowledgeItem).where(KnowledgeItem.id == knowledge_id))
    knowledge = result.scalar_one_or_none()
    if not knowledge:
        raise HTTPException(status_code=404, detail="Knowledge item not found")

    knowledge.verification_status = status
    knowledge.last_reviewed_at = datetime.utcnow()
    await db.commit()

    return {
        "knowledge_id": knowledge_id,
        "verification_status": status,
        "last_reviewed_at": knowledge.last_reviewed_at.isoformat() if knowledge.last_reviewed_at else None,
    }
