"""Ledger reconciliation, P&L and incoming receipts (Phase 8).

Reconciliation is a real cross-check: every transaction with ledger entries
must balance, and every ledger entry must point to a transaction. Income is
recorded separately from outgoing spend authority (OD-25).
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.business import FinancialLedger, FinancialTransaction, IncomingReceipt
from app.models.security import AuditEvent
from app.services.creatorapproval_service import CreatorApprovalService

RECEIVE_ACTION = "receive_payment"


class LedgerError(PermissionError):
    """Raised when an incoming receipt lacks separate signed authority."""


def _aware(value: Any) -> datetime:
    if not isinstance(value, datetime):
        return datetime.now(timezone.utc)
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


class LedgerService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def reconcile(self) -> Dict[str, Any]:
        transactions = await self.db.execute(select(FinancialTransaction))
        entries = await self.db.execute(select(FinancialLedger))
        tx_map = {str(row.id): row for row in transactions.scalars().all()}
        balances: Dict[str, Dict[str, Any]] = {
            key: {"debit": 0.0, "credit": 0.0, "entries": 0}
            for key in tx_map
        }
        issues: List[str] = []
        for entry in entries.scalars().all():
            key = str(entry.transaction_id)
            if key not in balances:
                issues.append(f"orphan ledger entry {entry.id}: transaction {key} not found")
                continue
            balances[key]["debit"] += float(entry.debit_amount or 0)
            balances[key]["credit"] += float(entry.credit_amount or 0)
            balances[key]["entries"] += 1
        details = []
        for key, totals in balances.items():
            difference = round(totals["debit"] - totals["credit"], 4)
            if totals["entries"] and abs(difference) > 0.0001:
                issues.append(f"unbalanced transaction {key}: difference {difference}")
            details.append(
                {
                    "transaction_id": key,
                    "type": tx_map[key].type,
                    "debit": round(totals["debit"], 4),
                    "credit": round(totals["credit"], 4),
                    "balanced": totals["entries"] == 0 or abs(difference) <= 0.0001,
                }
            )
        total_debit = round(sum(item["debit"] for item in details), 4)
        total_credit = round(sum(item["credit"] for item in details), 4)
        return {
            "reconciled": not issues,
            "issues": issues,
            "transactions": details,
            "summary": {
                "transaction_count": len(details),
                "total_debit": total_debit,
                "total_credit": total_credit,
                "difference": round(total_debit - total_credit, 4),
            },
        }

    async def profit_and_loss(
        self,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        result = await self.db.execute(select(FinancialTransaction))
        period_start = _aware(start) if start else datetime.min.replace(tzinfo=timezone.utc)
        period_end = _aware(end) if end else datetime.max.replace(tzinfo=timezone.utc)
        income = 0.0
        expenses = 0.0
        for item in result.scalars().all():
            when = _aware(item.created_at)
            if not period_start <= when <= period_end:
                continue
            value = float(item.amount or 0)
            if item.type == "income":
                income += value
            elif item.type == "expense":
                expenses += value
        reconciliation = await self.reconcile()
        return {
            "period_start": period_start.isoformat(),
            "period_end": period_end.isoformat(),
            "income": round(income, 4),
            "expenses": round(expenses, 4),
            "net": round(income - expenses, 4),
            "ledger_reconciled": reconciliation["reconciled"],
            "ledger_issues": reconciliation["issues"],
        }

    async def record_receipt(
        self,
        *,
        amount: float,
        source: str,
        reference: str,
        approval_id: Optional[str],
        actor: str,
    ) -> Dict[str, Any]:
        try:
            value = float(amount)
        except (TypeError, ValueError) as exc:
            raise LedgerError("amount must be numeric") from exc
        if value <= 0 or not source or not reference:
            raise LedgerError("amount, source and reference are required")
        if not approval_id:
            raise LedgerError("incoming payments require separate signed authority (OD-25)")
        authority = await CreatorApprovalService(self.db).check_authorization(
            RECEIVE_ACTION, requested_level="2", target_ref=str(approval_id)
        )
        if not authority.get("authorized"):
            raise LedgerError("no active signed Creator authorization for this receipt")

        transaction = FinancialTransaction(
            amount=value,
            type="income",
            description=f"receipt from {source}",
            reference_id=str(authority["authorization_id"]),
        )
        self.db.add(transaction)
        await self.db.flush()
        receipt = IncomingReceipt(
            transaction_id=transaction.id,
            source=source,
            reference=reference,
            amount=value,
            authorization_id=str(authority["authorization_id"]),
        )
        self.db.add(receipt)
        self.db.add(
            AuditEvent(
                event_type="incoming_receipt_recorded",
                actor=actor,
                target=str(transaction.id),
                details={
                    "source": source,
                    "reference": reference,
                    "amount": value,
                    "authorization_id": str(authority["authorization_id"]),
                    "spending_authority_granted": False,
                },
            )
        )
        await self.db.commit()
        return {
            "id": str(receipt.id),
            "transaction_id": str(transaction.id),
            "source": source,
            "reference": reference,
            "amount": value,
            "authorization_id": str(authority["authorization_id"]),
            "spending_authority_granted": False,
        }

    async def receipts(self) -> List[Dict[str, Any]]:
        result = await self.db.execute(select(IncomingReceipt))
        return [
            {
                "id": str(row.id),
                "transaction_id": str(row.transaction_id),
                "source": row.source,
                "reference": row.reference,
                "amount": float(row.amount),
                "authorization_id": row.authorization_id,
                "received_at": row.received_at.isoformat() if row.received_at else None,
            }
            for row in result.scalars().all()
        ]
