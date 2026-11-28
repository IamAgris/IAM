"""Decision records route"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid

from app.core.database import get_db_session
from app.models.autonomy import DecisionRecord

router = APIRouter(prefix="/api/v1/autonomy/decisions", tags=["autonomy"])


class DecisionCreate(BaseModel):
    decision: str
    reasoning: Optional[str] = None
    confidence: float = 0.5


class DecisionResponse(BaseModel):
    id: str
    decision: str
    reasoning: Optional[str]
    confidence: float
    outcome: Optional[str]
    made_at: Optional[str]
    reviewed_at: Optional[str]

    class Config:
        from_attributes = True


@router.get("/", response_model=List[DecisionResponse])
async def list_decisions(db: AsyncSession = Depends(get_db_session)):  # type: ignore[no-untyped-def]
    """List all decision records."""
    result = await db.execute(select(DecisionRecord).order_by(DecisionRecord.made_at.desc()))
    decisions = result.scalars().all()
    return [
        DecisionResponse(
            id=str(d.id),
            decision=d.decision,  # type: ignore[arg-type]
            reasoning=d.reasoning,  # type: ignore[arg-type]
            confidence=float(d.confidence) if d.confidence else 0.5,
            outcome=d.outcome,  # type: ignore[arg-type]
            made_at=d.made_at.isoformat() if d.made_at else None,
            reviewed_at=d.reviewed_at.isoformat() if d.reviewed_at else None,
        )
        for d in decisions
    ]


@router.post("/", response_model=DecisionResponse)
async def create_decision(decision: DecisionCreate, db: AsyncSession = Depends(get_db_session)):  # type: ignore[no-untyped-def]
    """Record a new decision with reasoning and confidence."""
    d = DecisionRecord(
        decision=decision.decision,
        reasoning=decision.reasoning,
        confidence=decision.confidence,
    )
    db.add(d)
    await db.commit()
    await db.refresh(d)

    return DecisionResponse(
        id=str(d.id),
        decision=d.decision,  # type: ignore[arg-type]
        reasoning=d.reasoning,  # type: ignore[arg-type]
        confidence=float(d.confidence),
        outcome=d.outcome,  # type: ignore[arg-type]
        made_at=d.made_at.isoformat() if d.made_at else None,
        reviewed_at=d.reviewed_at.isoformat() if d.reviewed_at else None,
    )


@router.patch("/{decision_id}", response_model=DecisionResponse)
async def update_decision_outcome(  # type: ignore[no-untyped-def]
    decision_id: str,
    outcome: str,
    db: AsyncSession = Depends(get_db_session),
):
    """Record the outcome of a past decision."""
    result = await db.execute(select(DecisionRecord).where(DecisionRecord.id == decision_id))
    d = result.scalar_one_or_none()
    if not d:
        raise HTTPException(status_code=404, detail="Decision not found")

    d.outcome = outcome  # type: ignore[assignment]
    d.reviewed_at = datetime.utcnow()  # type: ignore[assignment]
    await db.commit()

    return DecisionResponse(
        id=str(d.id),
        decision=d.decision,  # type: ignore[arg-type]
        reasoning=d.reasoning,  # type: ignore[arg-type]
        confidence=float(d.confidence),
        outcome=d.outcome,  # type: ignore[arg-type]
        made_at=d.made_at.isoformat() if d.made_at else None,
        reviewed_at=d.reviewed_at.isoformat() if d.reviewed_at else None,
    )
