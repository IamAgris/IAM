"""World model routes - internal representation of how the world works"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from app.core.database import get_db_session
from app.services.worldmodel_service import WorldModelService

router = APIRouter(prefix="/api/v1/world", tags=["world-model"])


class EntityRequest(BaseModel):
    name: str
    entity_type: str
    description: Optional[str] = None
    properties: Optional[Dict[str, Any]] = None
    confidence: float = 0.5


class RelationshipRequest(BaseModel):
    source_entity_id: str
    target_entity_id: str
    relationship_type: str
    strength: float = 1.0
    description: Optional[str] = None


class CauseEffectRequest(BaseModel):
    cause_description: str
    effect_description: str
    confidence: float = 0.5
    evidence: Optional[List[Dict[str, Any]]] = None


class WorldEventRequest(BaseModel):
    event_type: str
    title: str
    description: Optional[str] = None
    relevance_to_iam: float = 0.5
    related_entity_ids: Optional[List[str]] = None


class CapabilityLimitationRequest(BaseModel):
    capability_name: str
    proficiency_level: int
    limitation_description: Optional[str] = None
    assessment_method: Optional[str] = None


class TraverseRequest(BaseModel):
    entity_id: str
    depth: int = 2


class ScenarioRequest(BaseModel):
    trigger_entity_id: str
    trigger_description: str
    depth: int = 3


@router.get("/entities/{entity_id}")
async def get_entity(entity_id: str, db: AsyncSession = Depends(get_db_session)):
    """Get a single world entity by ID."""
    service = WorldModelService(db)
    try:
        return await service.get_entity(entity_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/relationships")
async def list_relationships(
    entity_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db_session),
):
    """List entity relationships, optionally filtered by a source or target entity."""
    service = WorldModelService(db)
    return await service.list_relationships(entity_id)


@router.post("/traverse")
async def traverse(request: TraverseRequest, db: AsyncSession = Depends(get_db_session)):
    """Breadth-first traversal of entity relationships up to `depth` hops.

    Returns visited entities and the edges between them, with cycle
    protection. Read-only: no state is mutated.
    """
    service = WorldModelService(db)
    try:
        return await service.traverse(request.entity_id, request.depth)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/cause-effect")
async def list_cause_effects(db: AsyncSession = Depends(get_db_session)):
    """List all recorded cause-and-effect chains."""
    service = WorldModelService(db)
    return await service.list_cause_effects()


@router.get("/events")
async def list_world_events(db: AsyncSession = Depends(get_db_session)):
    """List all recorded world events."""
    service = WorldModelService(db)
    return await service.list_world_events()


@router.post("/project")
async def project_scenario(request: ScenarioRequest, db: AsyncSession = Depends(get_db_session)):
    """Deterministic scenario projection.

    Starting from a trigger entity/description, project downstream effects
    along recorded cause-effect chains up to `depth` hops. Each hop's
    confidence is multiplied by the preceding confidence, and projected
    outcomes are ranked by cumulative confidence. Read-only: no state is
    mutated.
    """
    service = WorldModelService(db)
    try:
        return await service.project_scenario(
            request.trigger_entity_id, request.trigger_description, request.depth
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/entities")
async def create_entity(request: EntityRequest, db: AsyncSession = Depends(get_db_session)):
    """Create a world entity."""
    service = WorldModelService(db)
    try:
        return await service.create_entity(
            request.name, request.entity_type, request.description,
            request.properties, request.confidence,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/entities")
async def list_entities(
    entity_type: Optional[str] = None,
    db: AsyncSession = Depends(get_db_session),
):
    """List world entities."""
    service = WorldModelService(db)
    return await service.list_entities(entity_type)


@router.post("/relationships")
async def create_relationship(request: RelationshipRequest, db: AsyncSession = Depends(get_db_session)):
    """Create a relationship between world entities."""
    service = WorldModelService(db)
    return await service.create_relationship(
        request.source_entity_id, request.target_entity_id,
        request.relationship_type, request.strength, request.description,
    )


@router.post("/cause-effect")
async def record_cause_effect(request: CauseEffectRequest, db: AsyncSession = Depends(get_db_session)):
    """Record a cause-and-effect relationship."""
    service = WorldModelService(db)
    return await service.record_cause_effect(
        request.cause_description, request.effect_description,
        request.confidence, request.evidence,
    )


@router.post("/events")
async def record_world_event(request: WorldEventRequest, db: AsyncSession = Depends(get_db_session)):
    """Record a world event."""
    service = WorldModelService(db)
    return await service.record_world_event(
        request.event_type, request.title, request.description,
        request.relevance_to_iam, request.related_entity_ids,
    )


@router.post("/capabilities")
async def update_capability_limitation(
    request: CapabilityLimitationRequest,
    db: AsyncSession = Depends(get_db_session),
):
    """Track IAM's own capabilities and limitations."""
    service = WorldModelService(db)
    return await service.update_capability_limitation(
        request.capability_name, request.proficiency_level,
        request.limitation_description, request.assessment_method,
    )
