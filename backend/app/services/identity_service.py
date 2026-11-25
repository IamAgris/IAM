"""Identity service - manages AI digital identity with database persistence"""

from typing import Optional, Dict, Any, List
from datetime import datetime
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.identity import AIIdentity, AIPersonality, IdentityHistory


class IdentityService:
    """Handles identity creation, updates, and history tracking with DB persistence."""

    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    async def get_identity(self) -> Optional[Dict[str, Any]]:
        """Retrieve the current AI identity from the database."""
        result = await self.db.execute(select(AIIdentity).limit(1))
        identity = result.scalar_one_or_none()
        if not identity:
            return None
        return {
            "id": str(identity.id),
            "name": identity.name,
            "description": identity.description,
            "avatar_url": identity.avatar_url,
            "communication_preferences": identity.communication_preferences,
            "interests": identity.interests,
            "personal_goals": identity.personal_goals,
            "created_at": identity.created_at.isoformat() if identity.created_at else None,
            "updated_at": identity.updated_at.isoformat() if identity.updated_at else None,
        }

    async def create_identity(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Initialize a new AI identity and record it in history."""
        # Check if identity already exists
        existing = await self.get_identity()
        if existing:
            raise ValueError("Identity already exists. Use update_identity instead.")

        identity = AIIdentity(
            name=data["name"],
            description=data.get("description"),
            avatar_url=data.get("avatar_url"),
            communication_preferences=data.get("communication_preferences", {}),
            interests=data.get("interests", []),
            personal_goals=data.get("personal_goals", []),
        )
        self.db.add(identity)
        await self.db.flush()

        # Record initial history entry
        history = IdentityHistory(
            identity_id=identity.id,
            change_type="identity_created",
            previous_value=None,
            new_value={
                "name": identity.name,
                "description": identity.description,
            },
            reason="Initial identity initialization",
        )
        self.db.add(history)
        await self.db.commit()
        await self.db.refresh(identity)

        return {
            "id": str(identity.id),
            "name": identity.name,
            "description": identity.description,
            "avatar_url": identity.avatar_url,
            "communication_preferences": identity.communication_preferences,
            "interests": identity.interests,
            "personal_goals": identity.personal_goals,
            "created_at": identity.created_at.isoformat() if identity.created_at else None,
            "updated_at": identity.updated_at.isoformat() if identity.updated_at else None,
        }

    async def update_identity(
        self, identity_id: str, changes: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update identity and record change in history."""
        result = await self.db.execute(select(AIIdentity).where(AIIdentity.id == identity_id))
        identity = result.scalar_one_or_none()
        if not identity:
            raise ValueError("Identity not found")

        # Capture previous values for history
        previous = {
            "name": identity.name,
            "description": identity.description,
            "avatar_url": identity.avatar_url,
            "communication_preferences": identity.communication_preferences,
            "interests": identity.interests,
            "personal_goals": identity.personal_goals,
        }

        # Apply changes
        for key, value in changes.items():
            if hasattr(identity, key):
                setattr(identity, key, value)

        # Record history
        history = IdentityHistory(
            identity_id=identity.id,
            change_type="identity_updated",
            previous_value=previous,
            new_value=changes,
            reason=changes.get("reason", "Identity update"),
        )
        self.db.add(history)
        await self.db.commit()
        await self.db.refresh(identity)

        return {
            "id": str(identity.id),
            "name": identity.name,
            "description": identity.description,
            "avatar_url": identity.avatar_url,
            "communication_preferences": identity.communication_preferences,
            "interests": identity.interests,
            "personal_goals": identity.personal_goals,
            "updated_at": identity.updated_at.isoformat() if identity.updated_at else None,
        }

    async def get_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get identity change history."""
        result = await self.db.execute(
            select(IdentityHistory)
            .order_by(IdentityHistory.changed_at.desc())
            .limit(limit)
        )
        history = result.scalars().all()
        return [
            {
                "id": str(h.id),
                "change_type": h.change_type,
                "previous_value": h.previous_value,
                "new_value": h.new_value,
                "changed_at": h.changed_at.isoformat() if h.changed_at else None,
                "reason": h.reason,
            }
            for h in history
        ]
