"""World model service - internal representation of how the world works"""

from typing import Optional, Dict, Any, List
from datetime import datetime
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.worldmodel import (
    WorldEntity, EntityRelationship, CauseEffectChain, WorldEvent, CapabilityLimitation,
)


class WorldModelService:
    """Maintains IAM's internal model of the world for reasoning about situations."""

    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    async def create_entity(
        self,
        name: str,
        entity_type: str,
        description: Optional[str] = None,
        properties: Optional[Dict[str, Any]] = None,
        confidence: float = 0.5,
    ) -> Dict[str, Any]:
        """Create a world entity (person, organisation, country, technology, concept, event)."""
        valid_types = ("person", "organisation", "country", "technology", "concept", "event")
        if entity_type not in valid_types:
            raise ValueError(f"Invalid entity type: {entity_type}")

        entity = WorldEntity(
            name=name,
            entity_type=entity_type,
            description=description,
            properties=properties or {},
            confidence_level=confidence,
        )
        self.db.add(entity)
        await self.db.commit()
        await self.db.refresh(entity)

        return {
            "id": str(entity.id),
            "name": entity.name,
            "entity_type": entity.entity_type,
            "description": entity.description,
            "confidence_level": float(entity.confidence_level),
        }

    async def list_entities(self, entity_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """List world entities, optionally filtered by type."""
        stmt = select(WorldEntity).order_by(WorldEntity.name)
        if entity_type:
            stmt = stmt.where(WorldEntity.entity_type == entity_type)
        result = await self.db.execute(stmt)
        entities = result.scalars().all()
        return [
            {
                "id": str(e.id),
                "name": e.name,
                "entity_type": e.entity_type,
                "description": e.description,
                "confidence_level": float(e.confidence_level),
            }
            for e in entities
        ]

    async def create_relationship(
        self,
        source_entity_id: str,
        target_entity_id: str,
        relationship_type: str,
        strength: float = 1.0,
        description: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a relationship between two world entities."""
        rel = EntityRelationship(
            source_entity_id=source_entity_id,
            target_entity_id=target_entity_id,
            relationship_type=relationship_type,
            strength=strength,
            description=description,
        )
        self.db.add(rel)
        await self.db.commit()
        await self.db.refresh(rel)

        return {
            "id": str(rel.id),
            "relationship_type": rel.relationship_type,
            "strength": float(rel.strength),
        }

    async def record_cause_effect(
        self,
        cause_description: str,
        effect_description: str,
        confidence: float = 0.5,
        evidence: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Record a cause-and-effect relationship for decision reasoning."""
        chain = CauseEffectChain(
            cause_description=cause_description,
            effect_description=effect_description,
            confidence=confidence,
            evidence=evidence or [],
        )
        self.db.add(chain)
        await self.db.commit()
        await self.db.refresh(chain)

        return {
            "id": str(chain.id),
            "cause": chain.cause_description,
            "effect": chain.effect_description,
            "confidence": float(chain.confidence),
        }

    async def record_world_event(
        self,
        event_type: str,
        title: str,
        description: Optional[str] = None,
        relevance_to_iam: float = 0.5,
        related_entity_ids: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Record a world event that may affect IAM's decisions."""
        event = WorldEvent(
            event_type=event_type,
            title=title,
            description=description,
            relevance_to_iam=relevance_to_iam,
            related_entity_ids=related_entity_ids or [],
        )
        self.db.add(event)
        await self.db.commit()
        await self.db.refresh(event)

        return {
            "id": str(event.id),
            "event_type": event.event_type,
            "title": event.title,
            "relevance_to_iam": float(event.relevance_to_iam),
        }

    async def update_capability_limitation(
        self,
        capability_name: str,
        proficiency_level: int,
        limitation_description: Optional[str] = None,
        assessment_method: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Track IAM's own capabilities and limitations."""
        cap = CapabilityLimitation(
            capability_name=capability_name,
            proficiency_level=proficiency_level,
            limitation_description=limitation_description,
            assessment_method=assessment_method,
        )
        self.db.add(cap)
        await self.db.commit()
        await self.db.refresh(cap)

        return {
            "id": str(cap.id),
            "capability_name": cap.capability_name,
            "proficiency_level": cap.proficiency_level,
        }
