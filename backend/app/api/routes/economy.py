"""Economy routes — opportunities, projects, financial ledger and budgets.

All financial operations respect: zero standing budget (OD-04), legal entity
ownership (OD-02), double-entry ledger, and audited approvals.
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db_session
from app.models.business import (
    BusinessOpportunity, BusinessProject, BusinessPerformance,
    FinancialTransaction, FinancialLedger, FinancialBudget, OperatingExpense,
)
from app.models.security import AuditEvent
from app.core.config import settings
from app.services.financial_policy import (
    MAX_TRANSACTION_LIMIT_USD,
    MIN_TRANSACTION_LIMIT_USD,
    SpendDenied,
    authorize_transaction,
    transaction_limit_usd,
)
from app.services.ledger_service import LedgerError, LedgerService


def _actor(request: Request) -> str:
    credential = getattr(request.state, "credential", None)
    return credential.get("name", "iam") if credential else "iam"

router = APIRouter(prefix="/api/v1", tags=["economy"])


class OpportunityCreate(BaseModel):
    title: str
    description: Optional[str] = None
    estimated_revenue: Optional[float] = None
    confidence: float = 0.5


class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None
    opportunity_id: Optional[str] = None
    legal_entity: Optional[str] = None


class TransactionCreate(BaseModel):
    amount: float
    type: str  # income, expense, transfer
    description: Optional[str] = None
    reference_id: Optional[str] = None
    approval_id: Optional[str] = None


class LedgerEntry(BaseModel):
    transaction_id: str
    account: str
    debit_amount: float = 0
    credit_amount: float = 0


class BudgetCreate(BaseModel):
    category: str
    amount: float
    period: str
    is_approved: bool = False


class ReceiptCreate(BaseModel):
    amount: float
    source: str
    reference: str
    approval_id: Optional[str] = None


@router.get("/economics/opportunities")
async def list_opportunities(db: AsyncSession = Depends(get_db_session)):  # type: ignore[no-untyped-def]
    r = await db.execute(select(BusinessOpportunity).order_by(BusinessOpportunity.created_at.desc()))
    return [{"id": str(o.id), "title": o.title, "status": o.status,
             "estimated_revenue": float(o.estimated_revenue) if o.estimated_revenue else None,
             "confidence": float(o.confidence)} for o in r.scalars().all()]


@router.post("/economics/opportunities")
async def create_opportunity(request: OpportunityCreate, db: AsyncSession = Depends(get_db_session)):  # type: ignore[no-untyped-def]
    o = BusinessOpportunity(title=request.title, description=request.description,
                            estimated_revenue=request.estimated_revenue, confidence=request.confidence)
    db.add(o)
    await db.commit()
    await db.refresh(o)
    return {"id": str(o.id), "title": o.title, "status": o.status}


@router.get("/economics/projects")
async def list_projects(db: AsyncSession = Depends(get_db_session)):  # type: ignore[no-untyped-def]
    r = await db.execute(select(BusinessProject).order_by(BusinessProject.created_at.desc()))
    return [{"id": str(p.id), "name": p.name, "status": p.status,
             "legal_entity": p.legal_entity,
             "revenue": float(p.revenue), "expenses": float(p.expenses)} for p in r.scalars().all()]


@router.post("/economics/projects")
async def create_project(request: ProjectCreate, db: AsyncSession = Depends(get_db_session)):  # type: ignore[no-untyped-def]
    p = BusinessProject(name=request.name, description=request.description,
                        opportunity_id=request.opportunity_id,
                        legal_entity=request.legal_entity)
    db.add(p)
    await db.commit()
    await db.refresh(p)
    return {"id": str(p.id), "name": p.name, "status": p.status}


@router.get("/finance/policy")
async def finance_policy():  # type: ignore[no-untyped-def]
    """Current OD-04 caps — configured, not compiled into the spend check."""
    return {
        "per_transaction_limit_usd": transaction_limit_usd(),
        "per_transaction_allowed_range_usd": [
            MIN_TRANSACTION_LIMIT_USD,
            MAX_TRANSACTION_LIMIT_USD,
        ],
        "monthly_limit_usd": float(settings.finance_monthly_limit_usd),
        "zero_standing_budget": True,
    }


@router.get("/finance/transactions")
async def list_transactions(db: AsyncSession = Depends(get_db_session)):  # type: ignore[no-untyped-def]
    r = await db.execute(select(FinancialTransaction).order_by(FinancialTransaction.created_at.desc()))
    return [{"id": str(t.id), "amount": float(t.amount), "type": t.type,
             "description": t.description} for t in r.scalars().all()]


@router.post("/finance/transactions")
async def create_transaction(  # type: ignore[no-untyped-def]
    request: TransactionCreate,
    http_request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    """Outgoing funds need a signed per-action authority and must fit the caps."""
    try:
        authority = await authorize_transaction(
            db,
            amount=request.amount,
            transaction_type=request.type,
            approval_id=request.approval_id,
        )
    except SpendDenied as exc:
        raise HTTPException(403, str(exc)) from exc

    t = FinancialTransaction(
        amount=request.amount,
        type=request.type,
        description=request.description,
        reference_id=(
            authority["authorization_id"] if authority else request.reference_id
        ),
    )
    db.add(t)
    await db.flush()
    db.add(
        AuditEvent(
            event_type="financial_transaction_recorded",
            actor=_actor(http_request),
            target=str(t.id),
            details={
                "type": request.type,
                "amount": float(request.amount),
                "authorization_id": authority["authorization_id"] if authority else None,
                "signed_authority": bool(authority),
            },
        )
    )
    await db.commit()
    await db.refresh(t)
    return {
        "id": str(t.id),
        "amount": float(t.amount),
        "type": t.type,
        "signed_authority": bool(authority),
    }


@router.get("/finance/ledger")
async def get_ledger(db: AsyncSession = Depends(get_db_session)):  # type: ignore[no-untyped-def]
    r = await db.execute(select(FinancialLedger).order_by(FinancialLedger.recorded_at.desc()))
    return [{"id": str(l.id), "transaction_id": str(l.transaction_id), "account": l.account,
             "debit": float(l.debit_amount), "credit": float(l.credit_amount)} for l in r.scalars().all()]


@router.post("/finance/ledger")
async def add_ledger_entry(request: LedgerEntry, db: AsyncSession = Depends(get_db_session)):  # type: ignore[no-untyped-def]
    # Double-entry check: debit must equal credit
    if abs(request.debit_amount - request.credit_amount) > 0.0001:
        raise HTTPException(400, "Double-entry violation: debit must equal credit")
    l = FinancialLedger(transaction_id=request.transaction_id, account=request.account,
                        debit_amount=request.debit_amount, credit_amount=request.credit_amount)
    db.add(l)
    await db.commit()
    await db.refresh(l)
    return {"id": str(l.id), "account": l.account}


@router.get("/finance/budgets")
async def list_budgets(db: AsyncSession = Depends(get_db_session)):  # type: ignore[no-untyped-def]
    r = await db.execute(select(FinancialBudget))
    return [{"id": str(b.id), "category": b.category, "amount": float(b.amount),
             "is_approved": b.is_approved} for b in r.scalars().all()]


@router.post("/finance/budgets")
async def create_budget(  # type: ignore[no-untyped-def]
    request: BudgetCreate,
    http_request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    """Budgets are always proposed; only a signed Creator action may approve."""
    b = FinancialBudget(category=request.category, amount=request.amount,
                        period=request.period, is_approved=False)
    db.add(b)
    await db.flush()
    db.add(
        AuditEvent(
            event_type="finance_budget_proposed",
            actor=_actor(http_request),
            target=str(b.id),
            details={"category": request.category, "amount": float(request.amount)},
        )
    )
    await db.commit()
    await db.refresh(b)
    return {"id": str(b.id), "category": b.category, "is_approved": False}


@router.get("/finance/reconciliation")
async def reconciliation(db: AsyncSession = Depends(get_db_session)):  # type: ignore[no-untyped-def]
    """Cross-check ledger entries against transactions (not just a list)."""
    return await LedgerService(db).reconcile()


@router.get("/finance/profit-and-loss")
async def profit_and_loss(  # type: ignore[no-untyped-def]
    start: Optional[str] = None,
    end: Optional[str] = None,
    db: AsyncSession = Depends(get_db_session),
):
    try:
        period_start = datetime.fromisoformat(start.replace("Z", "+00:00")) if start else None
        period_end = datetime.fromisoformat(end.replace("Z", "+00:00")) if end else None
    except ValueError as exc:
        raise HTTPException(400, "start/end must be ISO-8601 dates") from exc
    return await LedgerService(db).profit_and_loss(period_start, period_end)


@router.post("/finance/receipts")
async def record_receipt(  # type: ignore[no-untyped-def]
    request: ReceiptCreate,
    http_request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    """Incoming payments need their own signed authority, never spending budget."""
    try:
        return await LedgerService(db).record_receipt(
            amount=request.amount,
            source=request.source,
            reference=request.reference,
            approval_id=request.approval_id,
            actor=_actor(http_request),
        )
    except LedgerError as exc:
        raise HTTPException(403, str(exc)) from exc


@router.get("/finance/receipts")
async def list_receipts(db: AsyncSession = Depends(get_db_session)):  # type: ignore[no-untyped-def]
    return await LedgerService(db).receipts()
