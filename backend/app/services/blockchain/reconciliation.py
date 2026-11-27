"""Read-only reconciliation of Web3 records against IAM's ledger (proposed Doc 35 P7).

This module never modifies financial records. A difference is reported as an issue
and recorded as an ``AuditEvent``; correction requires a signed decision and the
existing ``LedgerService``, not an automatic write here.
"""

from typing import Any, Dict, List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.business import FinancialTransaction
from app.models.security import AuditEvent
from app.models.web3 import Web3Transaction
from app.services.blockchain.providers.base import ProviderDenied, require_flag


class ReconciliationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def reconcile(self, *, emit_audit: bool = False, actor: str = "iam") -> Dict[str, Any]:
        require_flag(
            settings.web3_registry_enabled, "Web3 registry is disabled"
        )
        transactions = (await self.db.execute(select(Web3Transaction))).scalars().all()
        ledger = (await self.db.execute(select(FinancialTransaction))).scalars().all()
        references = {str(row.reference_id) for row in ledger if row.reference_id}
        amounts = {
            str(row.reference_id): float(row.amount or 0)
            for row in ledger
            if row.reference_id
        }

        issues: List[str] = []
        checked = 0
        for row in transactions:
            if row.status not in ("confirmed", "reconciled"):
                continue
            checked += 1
            key = row.idempotency_key
            if key not in references:
                issues.append(f"web3 transaction {row.id} has no ledger reference {key}")
                continue
            if row.amount is not None and abs(float(row.amount) - amounts.get(key, 0)) > 0.0001:
                issues.append(f"web3 transaction {row.id} amount differs from ledger entry {key}")

        result = {
            "reconciled": not issues,
            "checked": checked,
            "issues": issues,
            "ledger_entries": len(ledger),
            "corrections_made": False,
        }
        if emit_audit:
            self.db.add(
                AuditEvent(
                    event_type="web3_reconciliation_run",
                    actor=actor,
                    target="web3_ledger",
                    details={"checked": checked, "issues": issues[:20], "reconciled": not issues},
                )
            )
            await self.db.commit()
        return result
