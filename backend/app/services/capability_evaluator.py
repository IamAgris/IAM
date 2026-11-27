"""Capability-based sub-agent model assignment (OD-52 Phase E).

Only free, availability-tested models with a registered alias are eligible.
IAM's local primary still reviews every delegated result.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.modelrouter import DiscoveredModel

ROLE_CAPABILITIES: Dict[str, List[str]] = {
    "research": ["reasoning", "long_context"],
    "coding": ["coding", "tool_calling"],
    "security": ["reasoning", "critical_evaluation"],
    "mathematics": ["reasoning"],
    "translation": ["translation", "multilingual"],
    "vision": ["vision", "image"],
    "reviewer": ["reasoning", "critical_evaluation"],
    "extraction": ["structured_output"],
}


class CapabilityEvaluator:
    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def _score(row: DiscoveredModel, capabilities: List[str]) -> int:
        caps = set(row.capabilities or [])
        tags = set(row.input_capabilities or []) | set(row.output_capabilities or [])
        matched = len(caps & set(capabilities))
        if row.tool_calling and "tool_calling" in capabilities:
            matched += 1
        if row.structured_output and "structured_output" in capabilities:
            matched += 1
        if row.reasoning and "reasoning" in capabilities:
            matched += 1
        if "vision" in capabilities and "image" in tags:
            matched += 1
        return matched

    async def select_for_role(self, role: str) -> Optional[str]:
        """Return the best eligible alias for a role, or None to fail closed."""
        capabilities = ROLE_CAPABILITIES.get(role, ["reasoning"])
        result = await self.db.execute(
            select(DiscoveredModel).where(
                DiscoveredModel.access_type == "free",
                DiscoveredModel.endpoint_status == "available",
                DiscoveredModel.alias.isnot(None),
            )
        )
        candidates = [
            row
            for row in result.scalars().all()
            if self._score(row, capabilities) > 0
        ]
        if not candidates:
            return None
        candidates.sort(
            key=lambda row: (
                self._score(row, capabilities),
                float(getattr(row, "quality_score", 0) or 0),
                int(row.context_length or 0),
            ),
            reverse=True,
        )
        return str(candidates[0].alias)
