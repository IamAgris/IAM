"""Life management service - daily self-management, long-term goals, life history"""

from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.lifemanagement import LifeCycle, DailyRoutine, LifeHistory, GoalLifecycle


class LifeManagementService:
    """Manages IAM's ongoing existence: daily cycles, routines, life history, goal lifecycles."""

    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    async def get_current_cycle(self) -> Optional[Dict[str, Any]]:
        """Get today's life cycle state."""
        result = await self.db.execute(
            select(LifeCycle).order_by(LifeCycle.cycle_date.desc()).limit(1)
        )
        cycle = result.scalar_one_or_none()
        if not cycle:
            return None
        return {
            "id": str(cycle.id),
            "state": cycle.state,
            "started_at": cycle.started_at.isoformat() if cycle.started_at else None,
            "ended_at": cycle.ended_at.isoformat() if cycle.ended_at else None,
            "activities_completed": cycle.activities_completed,
            "resources_consumed": cycle.resources_consumed,
        }

    async def set_cycle_state(self, state: str, activities: Optional[List[str]] = None) -> Dict[str, Any]:
        """Update the current life cycle state (idle, working, researching, learning, resting, conserving)."""
        valid_states = ("idle", "working", "researching", "learning", "resting", "conserving")
        if state not in valid_states:
            raise ValueError(f"Invalid state: {state}")

        # End current cycle if exists
        current = await self.get_current_cycle()
        if current and current["ended_at"] is None:
            result = await self.db.execute(
                select(LifeCycle).where(LifeCycle.id == current["id"])
            )
            cycle = result.scalar_one_or_none()
            if cycle:
                cycle.ended_at = datetime.now(timezone.utc)
                await self.db.commit()

        # Start new cycle
        new_cycle = LifeCycle(
            state=state,
            activities_completed=activities or [],
            resources_consumed={},
        )
        self.db.add(new_cycle)
        await self.db.commit()
        await self.db.refresh(new_cycle)

        return {
            "id": str(new_cycle.id),
            "state": new_cycle.state,
            "started_at": new_cycle.started_at.isoformat() if new_cycle.started_at else None,
        }

    async def record_life_history(
        self,
        event_type: str,
        title: str,
        description: Optional[str] = None,
        significance: int = 5,
        related_memory_ids: Optional[List[str]] = None,
        related_goal_ids: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Record an important life event."""
        valid_types = ("decision", "achievement", "milestone", "setback", "recovery")
        if event_type not in valid_types:
            raise ValueError(f"Invalid event type: {event_type}")
        if not 1 <= significance <= 10:
            raise ValueError("Significance must be between 1 and 10")

        history = LifeHistory(
            event_type=event_type,
            title=title,
            description=description,
            significance=significance,
            related_memory_ids=related_memory_ids or [],
            related_goal_ids=related_goal_ids or [],
        )
        self.db.add(history)
        await self.db.commit()
        await self.db.refresh(history)

        return {
            "id": str(history.id),
            "event_type": history.event_type,
            "title": history.title,
            "significance": history.significance,
            "occurred_at": history.occurred_at.isoformat() if history.occurred_at else None,
        }

    async def get_life_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get chronological life history."""
        result = await self.db.execute(
            select(LifeHistory).order_by(LifeHistory.occurred_at.desc()).limit(limit)
        )
        history = result.scalars().all()
        return [
            {
                "id": str(h.id),
                "event_type": h.event_type,
                "title": h.title,
                "description": h.description,
                "significance": h.significance,
                "occurred_at": h.occurred_at.isoformat() if h.occurred_at else None,
            }
            for h in history
        ]

    async def get_goal_lifecycles(self) -> List[Dict[str, Any]]:
        """Get all goal lifecycle tracking."""
        result = await self.db.execute(select(GoalLifecycle))
        lifecycles = result.scalars().all()
        return [
            {
                "id": str(g.id),
                "goal_id": str(g.goal_id),
                "phase": g.phase,
                "priority": g.priority,
                "progress_percentage": float(g.progress_percentage) if g.progress_percentage else 0,
                "last_reviewed_at": g.last_reviewed_at.isoformat() if g.last_reviewed_at else None,
                "next_review_at": g.next_review_at.isoformat() if g.next_review_at else None,
            }
            for g in lifecycles
        ]
