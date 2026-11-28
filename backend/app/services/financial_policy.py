"""OD-04 zero standing budget enforcement at the actual spend path.

Income is autonomous. Any outgoing expense or transfer requires an active,
unrevoked, unexpired signed Creator authorization whose ``target_ref`` equals
the approval identifier supplied with the transaction. Hard caps apply on top
of that authority: $10 per transaction and $100 month-to-date by default.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.business import FinancialTransaction
from app.services.creatorapproval_service import CreatorApprovalService

SPEND_ACTION = "spend_approved_budget"
TRANSFER_ACTION = "transfer_money"
TRANSACTION_TYPES = ("income", "expense", "transfer")
MIN_TRANSACTION_LIMIT_USD = 1.0
MAX_TRANSACTION_LIMIT_USD = 10.0


def transaction_limit_usd() -> float:
    """Deployment-configured per-transaction cap, bounded to OD-04's $1–$10 band."""
    try:
        configured = float(settings.finance_transaction_limit_usd)
    except (TypeError, ValueError):
        configured = MAX_TRANSACTION_LIMIT_USD
    return min(MAX_TRANSACTION_LIMIT_USD, max(MIN_TRANSACTION_LIMIT_USD, configured))


class SpendDenied(PermissionError):
    """Raised when a financial action has no signed authority or breaks a cap."""


def _aware(value: Any) -> datetime:
    if not isinstance(value, datetime):
        return datetime.now(timezone.utc)
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


async def authorize_transaction(
    db: AsyncSession,
    *,
    amount: float,
    transaction_type: str,
    approval_id: Optional[str],
) -> Optional[Dict[str, Any]]:
    """Return the signed authority for outgoing funds, or ``None`` for income."""
    if transaction_type not in TRANSACTION_TYPES:
        raise SpendDenied(f"unknown transaction type: {transaction_type}")
    try:
        value = float(amount)
    except (TypeError, ValueError) as exc:
        raise SpendDenied("amount must be numeric") from exc
    if value <= 0:
        raise SpendDenied("amount must be positive")
    if transaction_type == "income":
        return None

    if not approval_id:
        raise SpendDenied(
            "outgoing funds require a signed Creator approval_id (OD-04 zero standing budget)"
        )
    action = TRANSFER_ACTION if transaction_type == "transfer" else SPEND_ACTION
    level = "4" if action == TRANSFER_ACTION else "3"
    authority = await CreatorApprovalService(db).check_authorization(
        action, requested_level=level, target_ref=str(approval_id)
    )
    if not authority.get("authorized"):
        raise SpendDenied("no active signed Creator authorization covers this approval_id")
    limit = transaction_limit_usd()
    if value > limit:
        raise SpendDenied(f"transaction exceeds the configured ${limit} per-transaction cap")

    if transaction_type == "expense":
        now = datetime.now(timezone.utc)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        result = await db.execute(
            select(FinancialTransaction).where(
                FinancialTransaction.type == "expense"
            )
        )
        spent = sum(
            float(item.amount)
            for item in result.scalars().all()
            if _aware(item.created_at) >= month_start
            and _aware(item.created_at) <= now
        )
        if spent + value > settings.finance_monthly_limit_usd:
            raise SpendDenied(
                f"month-to-date spend plus this transaction exceeds the "
                f"${settings.finance_monthly_limit_usd} monthly cap"
            )
    return authority
