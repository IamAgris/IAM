"""Bootstrap route — initialize IAM identity and default policies. Idempotent."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db_session
from app.services.bootstrap_service import BootstrapService

router = APIRouter(prefix="/api/v1/setup", tags=["setup"])


@router.post("/initialize")
async def initialize(db: AsyncSession = Depends(get_db_session)):  # type: ignore[no-untyped-def]
    """Initialize IAM genesis identity, constitution, governance and policies."""
    service = BootstrapService(db)
    result = await service.initialize_all()
    return {"status": "initialized", "components": result}


@router.get("/genesis")
async def get_genesis(db: AsyncSession = Depends(get_db_session)):  # type: ignore[no-untyped-def]
    """Get the permanent IAM identity (never changes)."""
    from app.models.lifemanagement import AIIdentityGenesis
    from sqlalchemy import select
    result = await db.execute(select(AIIdentityGenesis))
    genesis = result.scalar_one_or_none()
    if not genesis:
        return {"error": "Not initialized"}
    return {
        "permanent_id": genesis.permanent_id,
        "public_name": genesis.public_name,
        "full_name": genesis.full_name,
        "created_at": genesis.created_at.isoformat() if genesis.created_at else None,
        "origin_config": genesis.origin_config,
    }
