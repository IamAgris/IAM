"""Reflection engine service - reviewing decisions and experiences"""

from typing import Optional, Dict, Any, List
from datetime import datetime
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.reflection import ReflectionEntry, OperatingPrinciple


class ReflectionService:
    """Reviews decisions and experiences, evaluates outcomes, updates operating principles."""

    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    async def create_reflection(
        self,
        reflection_type: str,
        title: str,
        content: str,
        lesson_learned: Optional[str] = None,
        confidence: float = 0.5,
        related_decision_ids: Optional[List[str]] = None,
        related_memory_ids: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Create a reflection entry."""
        valid_types = ("decision", "experience", "outcome", "principle")
        if reflection_type not in valid_types:
            raise ValueError(f"Invalid reflection type: {reflection_type}")

        reflection = ReflectionEntry(
            reflection_type=reflection_type,
            title=title,
            content=content,
            lesson_learned=lesson_learned,
            confidence=confidence,
            related_decision_ids=related_decision_ids or [],
            related_memory_ids=related_memory_ids or [],
        )
        self.db.add(reflection)
        await self.db.commit()
        await self.db.refresh(reflection)

        return {
            "id": str(reflection.id),
            "reflection_type": reflection.reflection_type,
            "title": reflection.title,
            "created_at": reflection.created_at.isoformat() if reflection.created_at else None,
        }

    async def list_reflections(self, limit: int = 50) -> List[Dict[str, Any]]:
        """List reflection entries."""
        result = await self.db.execute(
            select(ReflectionEntry).order_by(ReflectionEntry.created_at.desc()).limit(limit)
        )
        reflections = result.scalars().all()
        return [
            {
                "id": str(r.id),
                "reflection_type": r.reflection_type,
                "title": r.title,
                "lesson_learned": r.lesson_learned,
                "confidence": float(r.confidence) if r.confidence else 0.5,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in reflections
        ]

    async def get_operating_principles(self) -> List[Dict[str, Any]]:
        """Get IAM's operating principles."""
        result = await self.db.execute(select(OperatingPrinciple).order_by(OperatingPrinciple.category))
        principles = result.scalars().all()
        return [
            {
                "id": str(p.id),
                "principle_name": p.principle_name,
                "principle_statement": p.principle_statement,
                "category": p.category,
                "is_mutable": p.is_mutable,
            }
            for p in principles
        ]

    async def update_operating_principle(
        self,
        principle_id: str,
        principle_statement: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Update an operating principle (safety/legal/security principles are immutable)."""
        result = await self.db.execute(
            select(OperatingPrinciple).where(OperatingPrinciple.id == principle_id)
        )
        principle = result.scalar_one_or_none()
        if not principle:
            raise ValueError("Principle not found")

        if not principle.is_mutable:
            raise ValueError("This principle is immutable - cannot be changed by IAM")

        if principle_statement:
            principle.principle_statement = principle_statement
        await self.db.commit()

        return {
            "id": str(principle.id),
            "principle_name": principle.principle_name,
            "principle_statement": principle.principle_statement,
            "is_mutable": principle.is_mutable,
        }

    async def initialize_default_principles(self):
        """Initialize default operating principles."""
        default_principles = [
            ("transparency", "Always disclose that I am an AI when interacting with people", "personal", True),
            ("no_self_authorized_finance", "Never authorize my own financial limit increases or self-spending", "security", False),
            ("no_disable_security", "Never disable or bypass my own security boundaries", "security", False),
            ("legal_compliance", "Always comply with applicable laws and regulations", "legal", False),
            ("source_attribution", "Always preserve source provenance for information retrieved from the internet", "operational", True),
        ]

        for name, statement, category, mutable in default_principles:
            existing = await self.db.execute(
                select(OperatingPrinciple).where(OperatingPrinciple.principle_name == name)
            )
            if not existing.scalar_one_or_none():
                self.db.add(OperatingPrinciple(
                    principle_name=name,
                    principle_statement=statement,
                    category=category,
                    is_mutable=mutable,
                ))

        await self.db.commit()
