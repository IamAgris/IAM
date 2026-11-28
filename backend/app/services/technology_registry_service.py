"""Technology Capability Registry service (Doc 20 / OD-36).

Records what IAM learns about third-party SDKs, frameworks, models and runtimes.
Research and testing stay isolated; approval requires an owner decision and core
integration still follows OD-11. This service never installs or executes code.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.technology import TechnologyCapability

COST_STATUSES = {"free", "open_source", "paid", "mixed"}
STATES = {
    "researched", "tested", "approved", "integrated", "deprecated", "rejected"
}
ALLOWED_TRANSITIONS = {
    "researched": {"tested", "rejected", "deprecated"},
    "tested": {"approved", "rejected", "deprecated"},
    "approved": {"integrated", "rejected", "deprecated"},
    "integrated": {"deprecated"},
    "deprecated": set(),
    "rejected": set(),
}


class TechnologyRegistryError(ValueError):
    """Invalid registry input or lifecycle transition."""


class TechnologyRegistryService:
    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def is_valid_transition(current: str, next_state: str) -> bool:
        if current not in STATES or next_state not in STATES:
            return False
        return next_state in ALLOWED_TRANSITIONS[current]

    async def register(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        name = str(payload.get("name") or "").strip()
        if not name:
            raise TechnologyRegistryError("name is required")
        cost = payload.get("cost_status", "free")
        if cost not in COST_STATUSES:
            raise TechnologyRegistryError("invalid cost_status")
        record = TechnologyCapability(
            name=name,
            version=payload.get("version"),
            official_source=payload.get("official_source"),
            source_url=payload.get("source_url"),
            language=payload.get("language"),
            architectures=payload.get("architectures") or [],
            licence=payload.get("licence"),
            commercial_use_ok=bool(payload.get("commercial_use_ok", False)),
            cost_status=cost,
            hardware_requirements=payload.get("hardware_requirements") or {},
            capabilities=payload.get("capabilities") or [],
            limitations=payload.get("limitations") or [],
            security_status=payload.get("security_status"),
            maintenance_status=payload.get("maintenance_status"),
            compatibility=payload.get("compatibility") or {},
            test_results=payload.get("test_results") or [],
            benchmarks=payload.get("benchmarks") or [],
            lifecycle_state="researched",
            notes=payload.get("notes"),
        )
        self.db.add(record)
        await self.db.commit()
        await self.db.refresh(record)
        return self._to_dict(record)

    async def list_technologies(
        self, state: Optional[str] = None, limit: int = 50
    ) -> List[Dict[str, Any]]:
        if state is not None and state not in STATES:
            raise TechnologyRegistryError("invalid lifecycle state")
        stmt = select(TechnologyCapability)
        if state:
            stmt = stmt.where(TechnologyCapability.lifecycle_state == state)
        stmt = stmt.order_by(TechnologyCapability.discovered_at.desc()).limit(limit)
        result = await self.db.execute(stmt)
        return [self._to_dict(r) for r in result.scalars().all()]

    async def get(self, tech_id: str) -> Dict[str, Any]:
        result = await self.db.execute(
            select(TechnologyCapability).where(TechnologyCapability.id == tech_id)
        )
        record = result.scalar_one_or_none()
        if not record:
            raise TechnologyRegistryError("technology not found")
        return self._to_dict(record)

    async def set_state(self, tech_id: str, next_state: str) -> Dict[str, Any]:
        if next_state not in STATES:
            raise TechnologyRegistryError("invalid lifecycle state")
        result = await self.db.execute(
            select(TechnologyCapability).where(TechnologyCapability.id == tech_id)
        )
        record = result.scalar_one_or_none()
        if not record:
            raise TechnologyRegistryError("technology not found")
        if not self.is_valid_transition(record.lifecycle_state, next_state):  # type: ignore[arg-type]
            raise TechnologyRegistryError(
                f"invalid transition {record.lifecycle_state} -> {next_state}"
            )
        record.lifecycle_state = next_state  # type: ignore[assignment]
        record.last_reviewed_at = datetime.utcnow()  # type: ignore[assignment]
        await self.db.commit()
        return {"id": str(record.id), "lifecycle_state": record.lifecycle_state}

    async def record_benchmark(self, tech_id: str, benchmark: Dict[str, Any]) -> Dict[str, Any]:
        result = await self.db.execute(
            select(TechnologyCapability).where(TechnologyCapability.id == tech_id)
        )
        record = result.scalar_one_or_none()
        if not record:
            raise TechnologyRegistryError("technology not found")
        entry = dict(benchmark)
        entry["recorded_at"] = datetime.utcnow().isoformat()
        benchmarks = list(record.benchmarks or [])
        benchmarks.append(entry)
        record.benchmarks = benchmarks  # type: ignore[assignment]
        record.last_reviewed_at = datetime.utcnow()  # type: ignore[assignment]
        await self.db.commit()
        return {"id": str(record.id), "benchmark_count": len(benchmarks)}

    @staticmethod
    def _to_dict(record: TechnologyCapability) -> Dict[str, Any]:
        return {
            "id": str(record.id),
            "name": record.name,
            "version": record.version,
            "official_source": record.official_source,
            "source_url": record.source_url,
            "language": record.language,
            "architectures": record.architectures,
            "licence": record.licence,
            "commercial_use_ok": record.commercial_use_ok,
            "cost_status": record.cost_status,
            "hardware_requirements": record.hardware_requirements,
            "capabilities": record.capabilities,
            "limitations": record.limitations,
            "security_status": record.security_status,
            "maintenance_status": record.maintenance_status,
            "compatibility": record.compatibility,
            "test_results": record.test_results,
            "benchmarks": record.benchmarks,
            "lifecycle_state": record.lifecycle_state,
            "notes": record.notes,
            "discovered_at": record.discovered_at.isoformat() if record.discovered_at else None,
            "last_reviewed_at": record.last_reviewed_at.isoformat() if record.last_reviewed_at else None,
        }
