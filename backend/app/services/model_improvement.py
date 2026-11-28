"""Evidence-only capability proposals (OD-52 Phase H).

Never promotes a model, changes the serving primary or starts training.
It only reports where a discovered free model may fill a capability gap, for
owner review under OD-11/OD-40 and subject to licence/data-use checks.
"""

from __future__ import annotations

from typing import Any, Dict, List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.modelrouter import DiscoveredModel
from app.services.capability_evaluator import ROLE_CAPABILITIES


class ModelImprovementService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def proposals(self) -> List[Dict[str, Any]]:
        result = await self.db.execute(
            select(DiscoveredModel).where(
                DiscoveredModel.access_type == "free",
                DiscoveredModel.endpoint_status == "available",
            )
        )
        rows = result.scalars().all()
        proposals: List[Dict[str, Any]] = []
        for row in rows:
            capabilities = set(row.capabilities or [])
            for role, required in ROLE_CAPABILITIES.items():
                matched = capabilities & set(required)
                if not matched:
                    continue
                proposals.append(
                    {
                        "model_id": row.model_id,
                        "role": role,
                        "matched_capabilities": sorted(matched),
                        "quality_score": str(row.quality_score) if row.quality_score is not None else None,
                        "evidence": {
                            "endpoint_status": row.endpoint_status,
                            "last_tested": row.last_tested.isoformat() if row.last_tested else None,
                            "test_result": row.test_result,
                        },
                        "claim": "proposal only",
                        "licensing_check_required": True,
                        "promotion_performed": False,
                        "training_performed": False,
                    }
                )
        return proposals
