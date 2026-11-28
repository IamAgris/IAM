"""Digital Security Incident service.

Tracks security events: credential leaks, suspicious auth attempts,
compromised sessions, unauthorised changes, breach monitoring.
"""

from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.web_knowledge import DigitalSecurityIncident, WebsiteKnowledge


class DigitalSecurityIncidentError(PermissionError):
    """Raised when a security incident operation fails."""


class DigitalSecurityService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _incident(self, incident_id: str) -> DigitalSecurityIncident:
        try:
            identifier = UUID(str(incident_id))
        except (ValueError, TypeError) as exc:
            raise ValueError("Invalid incident ID") from exc
        result = await self.db.execute(
            select(DigitalSecurityIncident).where(DigitalSecurityIncident.id == identifier)
        )
        row = result.scalar_one_or_none()
        if not row:
            raise ValueError("Security incident not found")
        return row

    async def create(
        self,
        *,
        website_knowledge_id: str,
        incident_type: str,
        title: str,
        description: Optional[str] = None,
        severity: str = "medium",
        affected_accounts: Optional[List[str]] = None,
        remediation_actions: Optional[List[Dict[str, Any]]] = None,
        evidence: Optional[List[Dict[str, Any]]] = None,
        actor: str,
    ) -> Dict[str, Any]:
        """Record a new security incident."""
        valid_types = (
            "credential_leak", "suspicious_auth", "compromised_session",
            "unauthorised_change", "breach",
        )
        if incident_type not in valid_types:
            raise DigitalSecurityIncidentError(f"Invalid incident type: {incident_type}")
        valid_severities = ("low", "medium", "high", "critical")
        if severity not in valid_severities:
            raise DigitalSecurityIncidentError(f"Invalid severity: {severity}")
        valid_statuses = ("open", "investigating", "resolved", "closed", "false_positive")

        # Verify the website knowledge exists
        wk_result = await self.db.execute(
            select(WebsiteKnowledge).where(WebsiteKnowledge.id == UUID(str(website_knowledge_id)))
        )
        if not wk_result.scalar_one_or_none():
            raise ValueError("Website knowledge record not found")

        row = DigitalSecurityIncident(
            website_knowledge_id=UUID(str(website_knowledge_id)),
            incident_type=incident_type,
            severity=severity,
            title=title,
            description=description,
            status="open",
            affected_accounts=affected_accounts or [],
            remediation_actions=remediation_actions or [],
            evidence=evidence or [],
        )
        self.db.add(row)
        await self.db.flush()
        await self.db.commit()
        return self._row_dict(row)

    async def get(self, incident_id: str) -> Dict[str, Any]:
        row = await self._incident(incident_id)
        return self._row_dict(row)

    async def list(self, website_knowledge_id: Optional[str] = None) -> List[Dict[str, Any]]:
        result = await self.db.execute(select(DigitalSecurityIncident))
        rows = result.scalars().all()
        if website_knowledge_id:
            rows = [r for r in rows if str(r.website_knowledge_id) == website_knowledge_id]
        return [self._row_dict(r) for r in rows]

    async def update_status(
        self,
        incident_id: str,
        *,
        status: str,
        actor: str,
    ) -> Dict[str, Any]:
        """Update incident status (open, investigating, resolved, closed, false_positive)."""
        row = await self._incident(incident_id)
        valid_statuses = ("open", "investigating", "resolved", "closed", "false_positive")
        if status not in valid_statuses:
            raise DigitalSecurityIncidentError(f"Invalid status: {status}")
        row.status = status  # type: ignore[assignment]
        if status == "resolved":
            from datetime import datetime, timezone
            row.resolved_at = None  # type: ignore[assignment]  # set by caller if desired
        await self.db.commit()
        return self._row_dict(row)

    @staticmethod
    def _row_dict(row: DigitalSecurityIncident) -> Dict[str, Any]:
        return {
            "id": str(row.id),
            "website_knowledge_id": str(row.website_knowledge_id),
            "incident_type": row.incident_type,
            "severity": row.severity,
            "title": row.title,
            "description": row.description,
            "detected_at": (
                row.detected_at.isoformat() if row.detected_at else None
            ),
            "resolved_at": (
                row.resolved_at.isoformat() if row.resolved_at else None
            ),
            "status": row.status,
            "affected_accounts": row.affected_accounts,
            "remediation_actions": row.remediation_actions,
            "evidence": row.evidence,
        }