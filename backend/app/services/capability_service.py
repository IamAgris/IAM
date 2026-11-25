"""Capability registry service - measurable skills and abilities catalogue"""

from typing import Optional, Dict, Any, List
from datetime import datetime
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.capability import CapabilityDefinition, CapabilityAssessment, LearningPath


class CapabilityService:
    """Maintains a catalogue of what IAM can do, cannot do, and wants to learn.
    
    Each capability requires measurable tests - not just reading about something.
    """

    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    async def create_capability(
        self,
        name: str,
        category: str,
        description: Optional[str] = None,
        target_proficiency: int = 100,
    ) -> Dict[str, Any]:
        """Define a new capability."""
        valid_categories = (
            "programming", "languages", "mathematics", "business", "science",
            "communication", "cybersecurity", "finance", "robotics",
        )
        if category not in valid_categories:
            raise ValueError(f"Invalid category: {category}")

        cap = CapabilityDefinition(
            name=name,
            category=category,
            description=description,
            target_proficiency=target_proficiency,
        )
        self.db.add(cap)
        await self.db.commit()
        await self.db.refresh(cap)

        return {
            "id": str(cap.id),
            "name": cap.name,
            "category": cap.category,
            "proficiency_level": 0,  # Starts at 0 until assessed
        }

    async def list_capabilities(self) -> List[Dict[str, Any]]:
        """List all capability definitions with their latest assessment."""
        result = await self.db.execute(select(CapabilityDefinition).order_by(CapabilityDefinition.name))
        capabilities = result.scalars().all()

        output = []
        for cap in capabilities:
            # Get latest assessment
            assess_result = await self.db.execute(
                select(CapabilityAssessment)
                .where(CapabilityAssessment.capability_id == cap.id)
                .order_by(CapabilityAssessment.assessed_at.desc())
                .limit(1)
            )
            latest = assess_result.scalar_one_or_none()

            output.append({
                "id": str(cap.id),
                "name": cap.name,
                "category": cap.category,
                "description": cap.description,
                "target_proficiency": cap.target_proficiency,
                "current_proficiency": latest.proficiency_level if latest else 0,
                "last_assessed": latest.assessed_at.isoformat() if latest and latest.assessed_at else None,
            })
        return output

    async def assess_capability(
        self,
        capability_id: str,
        proficiency_level: int,
        assessment_method: str,
        evidence: Optional[List[Dict[str, Any]]] = None,
        assessor: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Record a measurable capability assessment."""
        valid_methods = ("test", "project", "simulation", "review")
        if assessment_method not in valid_methods:
            raise ValueError(f"Invalid assessment method: {assessment_method}")
        if not 0 <= proficiency_level <= 100:
            raise ValueError("Proficiency must be between 0 and 100")

        assessment = CapabilityAssessment(
            capability_id=capability_id,
            proficiency_level=proficiency_level,
            assessment_method=assessment_method,
            evidence=evidence or [],
            assessor=assessor,
        )
        self.db.add(assessment)
        await self.db.commit()
        await self.db.refresh(assessment)

        return {
            "id": str(assessment.id),
            "capability_id": capability_id,
            "proficiency_level": assessment.proficiency_level,
            "assessed_at": assessment.assessed_at.isoformat() if assessment.assessed_at else None,
        }

    async def create_learning_path(
        self,
        capability_id: str,
        steps: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Create a planned learning journey for a capability."""
        path = LearningPath(
            capability_id=capability_id,
            total_steps=len(steps),
            steps=steps,
        )
        self.db.add(path)
        await self.db.commit()
        await self.db.refresh(path)

        return {
            "id": str(path.id),
            "capability_id": capability_id,
            "current_step": path.current_step,
            "total_steps": path.total_steps,
        }
