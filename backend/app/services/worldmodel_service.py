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

    async def get_entity(self, entity_id: str) -> Dict[str, Any]:
        """Get a single world entity by ID."""
        try:
            identifier = uuid.UUID(entity_id)
        except (ValueError, AttributeError) as exc:
            raise ValueError("Invalid entity ID") from exc
        result = await self.db.execute(select(WorldEntity).where(WorldEntity.id == identifier))
        entity = result.scalar_one_or_none()
        if not entity:
            raise ValueError("Entity not found")
        return {
            "id": str(entity.id),
            "name": entity.name,
            "entity_type": entity.entity_type,
            "description": entity.description,
            "properties": entity.properties,
            "confidence_level": float(entity.confidence_level),
        }

    async def list_relationships(
        self, entity_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List relationships, optionally filtered by a source or target entity."""
        stmt = select(EntityRelationship)
        if entity_id:
            try:
                identifier = uuid.UUID(entity_id)
            except (ValueError, AttributeError) as exc:
                raise ValueError("Invalid entity ID") from exc
            stmt = stmt.where(
                (EntityRelationship.source_entity_id == identifier)
                | (EntityRelationship.target_entity_id == identifier)
            )
        result = await self.db.execute(stmt.order_by(EntityRelationship.created_at))
        rels = result.scalars().all()
        return [
            {
                "id": str(r.id),
                "source_entity_id": str(r.source_entity_id),
                "target_entity_id": str(r.target_entity_id),
                "relationship_type": r.relationship_type,
                "strength": float(r.strength),
                "description": r.description,
            }
            for r in rels
        ]

    async def traverse(
        self, entity_id: str, depth: int = 2
    ) -> Dict[str, Any]:
        """Breadth-first traversal of entity relationships up to `depth` hops.

        Returns visited entities and the edges between them, with cycle
        protection via a visited set.
        """
        try:
            root = uuid.UUID(entity_id)
        except (ValueError, AttributeError) as exc:
            raise ValueError("Invalid entity ID") from exc
        if depth < 1 or depth > 5:
            raise ValueError("depth must be between 1 and 5")

        result = await self.db.execute(select(WorldEntity).where(WorldEntity.id == root))
        root_entity = result.scalar_one_or_none()
        if not root_entity:
            raise ValueError("Entity not found")

        rel_result = await self.db.execute(select(EntityRelationship))
        relationships = rel_result.scalars().all()

        adjacency: Dict[str, List[Dict[str, Any]]] = {}
        for rel in relationships:
            sid = str(rel.source_entity_id)
            tid = str(rel.target_entity_id)
            edge = {
                "relationship_id": str(rel.id),
                "source_entity_id": sid,
                "target_entity_id": tid,
                "relationship_type": rel.relationship_type,
                "strength": float(rel.strength),
                "description": rel.description,
            }
            adjacency.setdefault(sid, []).append(edge)
            adjacency.setdefault(tid, []).append({**edge, "direction": "incoming"})

        visited: Dict[str, Dict[str, Any]] = {str(root): self._entity_dict(root_entity)}
        queue: List[tuple[str, int]] = [(str(root), 0)]
        edges: List[Dict[str, Any]] = []
        while queue:
            current_id, current_depth = queue.pop(0)
            if current_depth >= depth:
                continue
            for edge in adjacency.get(current_id, []):
                if edge["relationship_id"] in {e["relationship_id"] for e in edges}:
                    continue
                target_id = edge["target_entity_id"]
                if target_id not in visited:
                    result = await self.db.execute(
                        select(WorldEntity).where(WorldEntity.id == target_id)
                    )
                    target = result.scalar_one_or_none()
                    if target:
                        visited[str(target.id)] = self._entity_dict(target)
                        queue.append((str(target.id), current_depth + 1))
                edges.append(edge)

        return {
            "root_entity_id": str(root),
            "depth": depth,
            "entities": list(visited.values()),
            "relationships": edges,
        }

    async def list_cause_effects(self) -> List[Dict[str, Any]]:
        """List all recorded cause-and-effect chains."""
        result = await self.db.execute(select(CauseEffectChain).order_by(CauseEffectChain.created_at))
        chains = result.scalars().all()
        return [
            {
                "id": str(c.id),
                "cause": c.cause_description,
                "effect": c.effect_description,
                "confidence": float(c.confidence),
                "evidence": c.evidence,
            }
            for c in chains
        ]

    async def list_world_events(self) -> List[Dict[str, Any]]:
        """List all recorded world events."""
        result = await self.db.execute(select(WorldEvent).order_by(WorldEvent.occurred_at.desc()))
        events = result.scalars().all()
        return [
            {
                "id": str(e.id),
                "event_type": e.event_type,
                "title": e.title,
                "description": e.description,
                "relevance_to_iam": float(e.relevance_to_iam),
                "related_entity_ids": e.related_entity_ids,
            }
            for e in events
        ]

    async def project_scenario(
        self,
        trigger_entity_id: str,
        trigger_description: str,
        depth: int = 3,
    ) -> Dict[str, Any]:
        """Deterministic scenario projection.

        Starting from a trigger entity/description, project downstream effects
        along recorded cause-effect chains up to `depth` hops. Each hop's
        confidence is multiplied by the preceding confidence, and projected
        outcomes are ranked by cumulative confidence so the most likely
        consequences surface first. Read-only: no state is mutated.
        """
        try:
            root = uuid.UUID(trigger_entity_id)
        except (ValueError, AttributeError) as exc:
            raise ValueError("Invalid trigger entity ID") from exc
        if depth < 1 or depth > 5:
            raise ValueError("depth must be between 1 and 5")

        result = await self.db.execute(select(WorldEntity).where(WorldEntity.id == root))
        root_entity = result.scalar_one_or_none()
        if not root_entity:
            raise ValueError("Trigger entity not found")

        result = await self.db.execute(select(CauseEffectChain).order_by(CauseEffectChain.created_at))
        chains = result.scalars().all()

        # Build adjacency by fuzzy cause/effect text match against entity names
        # and descriptions so projections can start from named entities.
        entity_by_name = {
            str(e.id): (e.name or "").lower() for e in (await self.db.execute(select(WorldEntity))).scalars().all()
        }

        projections: List[Dict[str, Any]] = []
        visited_chains: set = set()  # type: ignore[type-arg]
        queue: List[tuple[str, str, float, int]] = [
            (str(root), trigger_description, 1.0, 0)
        ]

        while queue:
            current_id, current_desc, current_conf, current_depth = queue.pop(0)
            if current_depth >= depth:
                continue
            for chain in chains:
                if chain.id in visited_chains:
                    continue
                cause = chain.cause_description.lower()
                effect = chain.effect_description.lower()
                match = (
                    current_desc.lower() in cause
                    or cause in current_desc.lower()
                    or any(name and name in cause for name in entity_by_name.values() if name)
                )
                if not match:
                    continue
                visited_chains.add(chain.id)
                projected_conf = round(current_conf * float(chain.confidence), 4)
                projections.append(
                    {
                        "cause_entity_id": current_id,
                        "cause": chain.cause_description,
                        "effect": chain.effect_description,
                        "confidence": float(chain.confidence),
                        "projected_confidence": projected_conf,
                        "depth": current_depth + 1,
                        "evidence": chain.evidence,
                    }
                )
                # Continue from effect text as the new cause descriptor
                queue.append((current_id, chain.effect_description, projected_conf, current_depth + 1))

        projections.sort(key=lambda p: p["projected_confidence"], reverse=True)
        return {
            "trigger_entity_id": str(root),
            "trigger_description": trigger_description,
            "depth": depth,
            "projection_count": len(projections),
            "projections": projections,
        }

    def _entity_dict(self, entity: WorldEntity) -> Dict[str, Any]:
        return {
            "id": str(entity.id),
            "name": entity.name,
            "entity_type": entity.entity_type,
            "description": entity.description,
            "properties": entity.properties,
            "confidence_level": float(entity.confidence_level),
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
