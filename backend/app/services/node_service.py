"""Node registration and bounded resource accounting (OD-26).

A node joining the creator network is a *candidate*, never a trusted peer.
It offers up to 1% of resources the operator explicitly permitted. The core
decides how to use that capacity; the ceiling is checked on every report.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.sdk import NodeResourceReport, RegisteredNode
from app.models.security import AuditEvent

CONTRIBUTION_CEILING_PERCENT = 1.0


class NodeError(ValueError):
    """Invalid registration or resource report."""


def _validated_percent(value: Any) -> float:
    percent = float(value)
    if percent < 0 or percent > CONTRIBUTION_CEILING_PERCENT:
        raise NodeError(
            "contribution percent must be between 0 and 1 "
            "(OD-26 ceiling: 1% of permitted available resources)"
        )
    return percent


class NodeService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def register(
        self,
        payload: Dict[str, Any],
        actor: str = "sdk",
    ) -> Dict[str, Any]:
        name = str(payload.get("name") or "").strip()
        architecture = str(payload.get("architecture") or "").strip()
        if not name or not architecture:
            raise NodeError("name and architecture are required")

        resources = payload.get("resources") or {}
        if not isinstance(resources, dict):
            raise NodeError("resources must be an object")

        percent = _validated_percent(
            resources.get("permitted_contribution_percent", CONTRIBUTION_CEILING_PERCENT)
        )

        existing = await self.db.execute(
            select(RegisteredNode).where(RegisteredNode.name == name)
        )
        if existing.scalar_one_or_none():
            raise NodeError("node with this name is already registered")

        node = RegisteredNode(
            name=name,
            architecture=architecture,
            resources=resources,
            capabilities=payload.get("capabilities") or [],
            trust_level="candidate",
            is_active=False,
            contribution_percent=percent,
            status="registered",
        )
        self.db.add(node)
        self.db.add(
            AuditEvent(
                event_type="node_registered",
                actor=actor,
                target=name,
                details={
                    "architecture": architecture,
                    "contribution_percent": percent,
                    "trust_level": "candidate",
                },
            )
        )
        await self.db.commit()
        await self.db.refresh(node)
        return self.to_dict(node)

    async def report_resources(
        self,
        node_id: str,
        payload: Dict[str, Any],
        actor: str = "sdk",
    ) -> Dict[str, Any]:
        node = await self._get(node_id)
        percent = _validated_percent(
            payload.get("contribution_percent", node.contribution_percent)
        )
        if percent > node.contribution_percent:
            raise NodeError(
                "reported contribution exceeds the node's disclosed ceiling"
            )
        for field in ("cpu_cores", "ram_bytes", "storage_bytes"):
            if field not in payload:
                raise NodeError(f"{field} is required")

        ram = float(payload["ram_bytes"])
        storage = float(payload["storage_bytes"])
        if ram < 0 or storage < 0 or float(payload["cpu_cores"]) < 0:
            raise NodeError("resource values cannot be negative")

        report = NodeResourceReport(
            node_id=node.id,
            cpu_cores=int(payload["cpu_cores"]),
            ram_bytes=ram,
            storage_bytes=storage,
            used_percent=payload.get("used_percent"),
            contribution_percent=percent,
            permitted_ram_bytes=ram * percent / 100,
            permitted_storage_bytes=storage * percent / 100,
        )
        node.last_seen_at = datetime.now(timezone.utc)  # type: ignore[assignment]
        node.resources = {  # type: ignore[assignment]
            **node.resources,
            "cpu_cores": payload["cpu_cores"],
            "ram_bytes": ram,
            "storage_bytes": storage,
        }
        self.db.add(report)
        self.db.add(
            AuditEvent(
                event_type="node_resource_report",
                actor=actor,
                target=node.name,
                details={
                    "contribution_percent": percent,
                    "permitted_ram_bytes": report.permitted_ram_bytes,
                    "permitted_storage_bytes": report.permitted_storage_bytes,
                },
            )
        )
        await self.db.commit()
        return {
            "report_id": str(report.id),
            "node_id": str(node.id),
            "contribution_percent": percent,
            "ceiling_percent": node.contribution_percent,
            "permitted_ram_bytes": report.permitted_ram_bytes,
            "permitted_storage_bytes": report.permitted_storage_bytes,
            "disclosed": True,
        }

    async def status(self, node_id: str) -> Dict[str, Any]:
        node = await self._get(node_id)
        data = self.to_dict(node)
        reports = await self.db.execute(
            select(NodeResourceReport)
            .where(NodeResourceReport.node_id == node.id)
            .order_by(NodeResourceReport.reported_at.desc())
            .limit(1)
        )
        latest = reports.scalar_one_or_none()
        data["latest_report"] = (
            {
                "reported_at": latest.reported_at.isoformat() if latest.reported_at else None,
                "contribution_percent": latest.contribution_percent,
                "permitted_ram_bytes": latest.permitted_ram_bytes,
                "permitted_storage_bytes": latest.permitted_storage_bytes,
            }
            if latest
            else None
        )
        return data

    async def list_nodes(self) -> List[Dict[str, Any]]:
        result = await self.db.execute(select(RegisteredNode).order_by(RegisteredNode.created_at.desc()))
        return [self.to_dict(node) for node in result.scalars().all()]

    async def _get(self, node_id: str) -> RegisteredNode:
        result = await self.db.execute(
            select(RegisteredNode).where(RegisteredNode.id == node_id)
        )
        node = result.scalar_one_or_none()
        if not node:
            raise NodeError("node not found")
        return node

    @staticmethod
    def to_dict(node: RegisteredNode) -> Dict[str, Any]:
        return {
            "id": str(node.id),
            "name": node.name,
            "architecture": node.architecture,
            "resources": node.resources,
            "capabilities": node.capabilities,
            "trust_level": node.trust_level,
            "is_active": node.is_active,
            "contribution_percent": node.contribution_percent,
            "ceiling_percent": CONTRIBUTION_CEILING_PERCENT,
            "status": node.status,
            "protocol_version": settings.iam_protocol_version,
            "created_at": node.created_at.isoformat() if node.created_at else None,
            "last_seen_at": node.last_seen_at.isoformat() if node.last_seen_at else None,
        }
