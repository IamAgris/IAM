"""Doc 19 / OD-35: free infrastructure node discovery and lifecycle.

Extends OEDIE (OD-15), Doc 22 provider adapters and the OD-26 node protocol.
This service only records assessments and lifecycle state. It never creates cloud
accounts, provisions VMs, spends money or bypasses provider limits. Deployment
requires creator authorisation (OD-03/OD-25), and any registered node remains a
candidate until attested (OD-12/OD-13).
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.freenode import FreeNodeCandidate

STATUSES = {
    "discovered", "assessed", "authorised", "deployed", "registered",
    "expiring", "migrated", "stopped", "rejected",
}
ARCHITECTURES = {"amd64", "arm64"}
COST_STATUSES = {"free", "free_credit", "unknown"}


class FreeNodeError(ValueError):
    """Invalid candidate data or lifecycle transition."""


class FreeNodeLifecycleService:
    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def _parse_dt(value: Any) -> Optional[datetime]:
        if value is None or isinstance(value, datetime):
            return value
        try:
            return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError as exc:
            raise FreeNodeError("expires_at must be an ISO-8601 timestamp") from exc

    @staticmethod
    def assess(payload: Dict[str, Any]) -> Dict[str, Any]:
        """Usefulness gate: a free resource is not automatically a useful node.

        All five checks in Doc 19 §3 must pass. Missing evidence fails closed.
        """
        reasons: List[str] = []
        cpu = float(payload.get("cpu_cores") or 0)
        ram_mb = int(payload.get("ram_mb") or 0)
        architecture = str(payload.get("architecture") or "").lower()

        if cpu > 0 and ram_mb >= 1024:
            useful = True
        else:
            useful = False
            reasons.append("insufficient CPU/RAM to add useful capacity")

        run_compatible = bool(payload.get("run_compatible")) and architecture in ARCHITECTURES
        if not run_compatible:
            reasons.append("node software compatibility not evidenced for this architecture")

        overhead = str(payload.get("operational_overhead") or "high").lower()
        if overhead not in {"low", "medium"}:
            reasons.append("networking/maintenance overhead not shown to be acceptable")

        security = str(payload.get("security_exposure") or "unknown").lower()
        if security not in {"low", "medium"}:
            reasons.append("security exposure not assessed as acceptable")

        net_benefit = bool(payload.get("net_benefit"))
        if not net_benefit:
            reasons.append("net benefit over maintenance cost not demonstrated")

        decision = "deploy" if not reasons else "decline"
        return {
            "useful": useful,
            "run_compatible": run_compatible,
            "operational_overhead": overhead,
            "security_exposure": security,
            "net_benefit": net_benefit,
            "decision": decision,
            "reasons": reasons,
            "creator_authorisation_required": True,
            "note": "Free availability alone never justifies a node.",
        }

    async def record_candidate(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        provider = str(payload.get("provider") or "").strip()
        architecture = str(payload.get("architecture") or "").lower()
        cost = str(payload.get("cost_status") or "free").lower()
        if not provider:
            raise FreeNodeError("provider is required")
        if architecture not in ARCHITECTURES:
            raise FreeNodeError("architecture must be amd64 or arm64")
        if cost not in COST_STATUSES:
            raise FreeNodeError("invalid cost_status")

        assessment = self.assess(payload)
        record = FreeNodeCandidate(
            provider=provider,
            instance_class=payload.get("instance_class"),
            architecture=architecture,
            region=payload.get("region"),
            cpu_cores=payload.get("cpu_cores") or 0,
            ram_mb=payload.get("ram_mb") or 0,
            disk_gb=payload.get("disk_gb") or 0,
            cost_status=cost,
            terms_source=payload.get("terms_source"),
            expires_at=self._parse_dt(payload.get("expires_at")),
            notes=payload.get("notes"),
            useful=assessment["useful"],
            run_compatible=assessment["run_compatible"],
            usefulness_reason="; ".join(assessment["reasons"]) or "all usefulness checks passed",
            status="assessed" if assessment["decision"] == "deploy" else "rejected",
            authorisation_required=True,
        )
        self.db.add(record)
        await self.db.commit()
        await self.db.refresh(record)
        return {**self._to_dict(record), "assessment": assessment}

    async def verify_terms(self, candidate_id: str, source_url: str, evidence: str) -> Dict[str, Any]:
        """Record live-verified free-tier terms. Claims from snippets never qualify."""
        if not source_url.strip() or not evidence.strip():
            raise FreeNodeError("source_url and evidence are required")
        record = await self._get(candidate_id)
        record.terms_source = source_url  # type: ignore[assignment]
        record.eligibility_verified = True  # type: ignore[assignment]
        record.last_reviewed_at = datetime.utcnow()  # type: ignore[assignment]
        await self.db.commit()
        return {"id": str(record.id), "eligibility_verified": True}

    async def set_status(self, candidate_id: str, status: str) -> Dict[str, Any]:
        if status not in STATUSES:
            raise FreeNodeError("invalid status")
        record = await self._get(candidate_id)
        if status in {"deployed", "registered"} and not record.eligibility_verified:
            raise FreeNodeError("free-tier terms must be verified before deployment")
        record.status = status  # type: ignore[assignment]
        record.last_reviewed_at = datetime.utcnow()  # type: ignore[assignment]
        await self.db.commit()
        return {"id": str(record.id), "status": record.status}

    async def plan_migration(self, candidate_id: str, days_before_expiry: int = 7) -> Dict[str, Any]:
        """Set an expiry alarm and migration plan before a free allowance lapses."""
        if days_before_expiry < 0:
            raise FreeNodeError("days_before_expiry must be non-negative")
        record = await self._get(candidate_id)
        if not record.expires_at:
            raise FreeNodeError("candidate has no expiry date")
        record.quota_alarm_at = record.expires_at - timedelta(days=days_before_expiry)  # type: ignore[assignment]
        record.migration_plan = (
            f"Stop non-essential workloads by {record.quota_alarm_at.isoformat()}; "  # type: ignore[assignment]
            "move state to the core or another verified free node; never fall back to paid capacity."
        )
        record.status = "expiring"  # type: ignore[assignment]
        await self.db.commit()
        return {
            "id": str(record.id),
            "quota_alarm_at": record.quota_alarm_at.isoformat(),
            "status": record.status,
        }

    async def list_candidates(self, limit: int = 50) -> List[Dict[str, Any]]:
        result = await self.db.execute(
            select(FreeNodeCandidate)
            .order_by(FreeNodeCandidate.discovered_at.desc())
            .limit(limit)
        )
        return [self._to_dict(r) for r in result.scalars().all()]

    async def _get(self, candidate_id: str) -> FreeNodeCandidate:
        result = await self.db.execute(
            select(FreeNodeCandidate).where(FreeNodeCandidate.id == candidate_id)
        )
        record = result.scalar_one_or_none()
        if not record:
            raise FreeNodeError("candidate not found")
        return record

    @staticmethod
    def _to_dict(record: FreeNodeCandidate) -> Dict[str, Any]:
        return {
            "id": str(record.id),
            "provider": record.provider,
            "instance_class": record.instance_class,
            "architecture": record.architecture,
            "region": record.region,
            "cpu_cores": float(record.cpu_cores),
            "ram_mb": record.ram_mb,
            "disk_gb": float(record.disk_gb),
            "cost_status": record.cost_status,
            "terms_source": record.terms_source,
            "eligibility_verified": record.eligibility_verified,
            "useful": record.useful,
            "usefulness_reason": record.usefulness_reason,
            "run_compatible": record.run_compatible,
            "status": record.status,
            "authorisation_required": record.authorisation_required,
            "registered_node_id": record.registered_node_id,
            "expires_at": record.expires_at.isoformat() if record.expires_at else None,
            "quota_alarm_at": record.quota_alarm_at.isoformat() if record.quota_alarm_at else None,
            "migration_plan": record.migration_plan,
            "discovered_at": record.discovered_at.isoformat() if record.discovered_at else None,
        }
