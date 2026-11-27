"""Resilience engine service - health monitoring, recovery, backup verification, disaster recovery"""

from typing import Optional, Dict, Any, List
from datetime import datetime
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.resilience import HealthCheck, RecoveryLog, BackupVerification, IncidentRecord, CredentialRotation


class ResilienceService:
    """Operational survival system - monitoring, recovery, backups, disaster recovery."""

    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    async def record_health_check(
        self,
        service_name: str,
        status: str,
        response_time_ms: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Record a service health check."""
        valid_statuses = ("healthy", "degraded", "down")
        if status not in valid_statuses:
            raise ValueError(f"Invalid status: {status}")

        check = HealthCheck(
            service_name=service_name,
            status=status,
            response_time_ms=response_time_ms,
            details=details or {},
        )
        self.db.add(check)
        await self.db.commit()
        await self.db.refresh(check)

        return {
            "id": str(check.id),
            "service_name": check.service_name,
            "status": check.status,
            "checked_at": check.checked_at.isoformat() if check.checked_at else None,
        }

    async def get_latest_health(self, service_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get latest health checks, optionally filtered by service."""
        stmt = select(HealthCheck).order_by(HealthCheck.service_name, HealthCheck.checked_at.desc())
        result = await self.db.execute(stmt)
        checks = result.scalars().all()

        # Deduplicate - keep latest per service
        latest = {}
        for c in checks:
            if c.service_name not in latest:
                latest[c.service_name] = c

        return [
            {
                "id": str(c.id),
                "service_name": c.service_name,
                "status": c.status,
                "checked_at": c.checked_at.isoformat() if c.checked_at else None,
            }
            for c in latest.values()
        ]

    async def record_recovery(
        self,
        service_name: str,
        action: str,
        success: bool,
        details: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Record an automatic recovery action."""
        log = RecoveryLog(
            service_name=service_name,
            action=action,
            success=success,
            details=details or {},
        )
        self.db.add(log)
        await self.db.commit()
        await self.db.refresh(log)

        return {
            "id": str(log.id),
            "service_name": log.service_name,
            "action": log.action,
            "success": log.success,
        }

    async def record_backup_verification(
        self,
        backup_id: str,
        verification_type: str,
        success: bool,
        restored_items: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Verify a backup can be restored."""
        v = BackupVerification(
            backup_id=backup_id,
            verification_type=verification_type,
            success=success,
            restored_items=restored_items,
        )
        self.db.add(v)
        await self.db.commit()
        await self.db.refresh(v)

        return {
            "id": str(v.id),
            "backup_id": v.backup_id,
            "success": v.success,
        }

    async def record_incident(
        self,
        incident_type: str,
        severity: str,
        title: str,
        description: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Record a security or failure incident."""
        valid_types = ("security", "failure", "outage", "suspicious_activity")
        valid_severities = ("low", "medium", "high", "critical")
        if incident_type not in valid_types:
            raise ValueError(f"Invalid incident type: {incident_type}")
        if severity not in valid_severities:
            raise ValueError(f"Invalid severity: {severity}")

        incident = IncidentRecord(
            incident_type=incident_type,
            severity=severity,
            title=title,
            description=description,
        )
        self.db.add(incident)
        await self.db.commit()
        await self.db.refresh(incident)

        return {
            "id": str(incident.id),
            "incident_type": incident.incident_type,
            "severity": incident.severity,
            "title": incident.title,
        }

    async def record_credential_rotation(
        self,
        secret_name: str,
        integration_id: Optional[str] = None,
        next_rotation_due: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Record credential rotation."""
        rot = CredentialRotation(
            secret_name=secret_name,
            integration_id=integration_id,
            next_rotation_due=next_rotation_due,
        )
        self.db.add(rot)
        await self.db.commit()
        await self.db.refresh(rot)

        return {
            "id": str(rot.id),
            "secret_name": rot.secret_name,
            "rotated_at": rot.rotated_at.isoformat() if rot.rotated_at else None,
        }
