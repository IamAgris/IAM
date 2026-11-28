"""Web3 alerting and health monitoring (proposed Doc 35 P7).

Read-only checks plus audit alerts. This module never modifies financial records,
never signs, and never contacts a provider. Alerts are written to the existing
``AuditEvent`` stream and, for high severity, ``SecurityIncident``.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.creatorapproval import CreatorAuthorization
from app.models.security import AuditEvent, SecurityIncident
from app.models.web3 import Web3ProviderHealth, Web3Transaction
from app.services.blockchain.audit import BlockchainAuditService
from app.services.blockchain.providers.base import ProviderDenied, require_flag
from app.services.blockchain.reconciliation import ReconciliationService


def _aware(value: Any) -> datetime:
    if not isinstance(value, datetime):
        return datetime.now(timezone.utc)
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


class Web3MonitoringService:
    def __init__(self, db: AsyncSession):
        self.db = db

    def policy(self) -> Dict[str, Any]:
        return {
            "enabled": settings.web3_monitoring_enabled,
            "network_calls_made": False,
            "alerts_only": True,
            "auto_correction": False,
            "stuck_minutes": settings.web3_monitoring_stuck_minutes,
        }

    async def run_checks(self, *, emit: bool = True) -> Dict[str, Any]:
        require_flag(settings.web3_monitoring_enabled, "Web3 monitoring is disabled")
        alerts: List[Dict[str, str]] = []

        if settings.web3_audit_enabled:
            audit = await BlockchainAuditService(self.db).verify()
            if not audit["verified"]:
                alerts.append(
                    {"severity": "high", "issue": "blockchain audit hash chain failed verification"}
                )
        else:
            audit = {"skipped": "audit disabled"}

        if settings.web3_registry_enabled:
            reconciliation = await ReconciliationService(self.db).reconcile()
            if not reconciliation["reconciled"]:
                for issue in reconciliation["issues"][:10]:
                    alerts.append({"severity": "high", "issue": f"ledger reconciliation: {issue}"})
        else:
            reconciliation = {"skipped": "registry disabled"}

        now = datetime.now(timezone.utc)
        transactions = (await self.db.execute(select(Web3Transaction))).scalars().all()
        stuck_threshold = now - timedelta(minutes=settings.web3_monitoring_stuck_minutes)
        for row in transactions:
            if row.status == "broadcast" and not row.tx_hash and _aware(row.created_at) < stuck_threshold:
                alerts.append(
                    {"severity": "high", "issue": f"transaction {row.id} has no tx hash after broadcast"}
                )

        authorizations = (await self.db.execute(select(CreatorAuthorization))).scalars().all()
        soon = now + timedelta(minutes=60)
        for auth in authorizations:
            if auth.is_active and not auth.revoked_at and auth.expires_at and _aware(auth.expires_at) <= soon:
                alerts.append(
                    {
                        "severity": "low",
                        "issue": f"signed authorization {auth.id} expires within an hour",
                    }
                )

        provider_health = (await self.db.execute(select(Web3ProviderHealth))).scalars().all()
        for entry in provider_health:
            if not entry.available:
                alerts.append(
                    {"severity": "low", "issue": f"provider {entry.provider}/{entry.network} is unavailable"}
                )

        if emit and alerts:
            for alert in alerts:
                self.db.add(
                    AuditEvent(
                        event_type="web3_alert",
                        actor="monitor",
                        target="web3_monitoring",
                        details=alert,
                    )
                )
                if alert["severity"] == "high":
                    self.db.add(
                        SecurityIncident(
                            title="Web3 monitoring alert",
                            description=alert["issue"][:1000],
                            severity="high",
                            status="open",
                        )
                    )
            await self.db.commit()

        return {
            "checked_at": now.isoformat(),
            "alert_count": len(alerts),
            "alerts": alerts,
            "audit": {"verified": audit.get("verified") if isinstance(audit, dict) else None},
            "reconciliation": {
                "reconciled": reconciliation.get("reconciled") if isinstance(reconciliation, dict) else None
            },
            "network_calls_made": False,
            "auto_correction": False,
        }
