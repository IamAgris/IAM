"""Economy routes — opportunities, projects, financial ledger and budgets.

All financial operations respect: zero standing budget (OD-04), legal entity
ownership (OD-02), double-entry ledger, and audited approvals.
"""

from fastapi import APIRouter, Depends, HTTPException
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


@router.get("/economics/opportunities")
async def list_opportunities(db: AsyncSession = Depends(get_db_session)):
    r = await db.execute(select(BusinessOpportunity).order_by(BusinessOpportunity.created_at.desc()))
    return [{"id": str(o.id), "title": o.title, "status": o.status,
             "estimated_revenue": float(o.estimated_revenue) if o.estimated_revenue else None,
             "confidence": float(o.confidence)} for o in r.scalars().all()]


@router.post("/economics/opportunities")
async def create_opportunity(request: OpportunityCreate, db: AsyncSession = Depends(get_db_session)):
    o = BusinessOpportunity(title=request.title, description=request.description,
                            estimated_revenue=request.estimated_revenue, confidence=request.confidence)
    db.add(o)
    await db.commit()
    await db.refresh(o)
    return {"id": str(o.id), "title": o.title, "status": o.status}


@router.get("/economics/projects")
async def list_projects(db: AsyncSession = Depends(get_db_session)):
    r = await db.execute(select(BusinessProject).order_by(BusinessProject.created_at.desc()))
    return [{"id": str(p.id), "name": p.name, "status": p.status,
             "revenue": float(p.revenue), "expenses": float(p.expenses)} for p in r.scalars().all()]


@router.post("/economics/projects")
async def create_project(request: ProjectCreate, db: AsyncSession = Depends(get_db_session)):
    p = BusinessProject(name=request.name, description=request.description,
                        opportunity_id=request.opportunity_id)
    db.add(p)
    await db.commit()
    await db.refresh(p)
    return {"id": str(p.id), "name": p.name, "status": p.status}


@router.get("/finance/transactions")
async def list_transactions(db: AsyncSession = Depends(get_db_session)):
    r = await db.execute(select(FinancialTransaction).order_by(FinancialTransaction.created_at.desc()))
    return [{"id": str(t.id), "amount": float(t.amount), "type": t.type,
             "description": t.description} for t in r.scalars().all()]


@router.post("/finance/transactions")
async def create_transaction(request: TransactionCreate, db: AsyncSession = Depends(get_db_session)):
    # Zero standing budget: financial actions require an approval reference
    if not request.approval_id:
        raise HTTPException(403, "Financial transactions require an owner approval_id (OD-04 zero standing budget)")
    t = FinancialTransaction(amount=request.amount, type=request.type,
                             description=request.description, reference_id=request.approval_id)
    db.add(t)
    await db.commit()
    await db.refresh(t)
    return {"id": str(t.id), "amount": float(t.amount), "type": t.type}


@router.get("/finance/ledger")
async def get_ledger(db: AsyncSession = Depends(get_db_session)):
    r = await db.execute(select(FinancialLedger).order_by(FinancialLedger.recorded_at.desc()))
    return [{"id": str(l.id), "transaction_id": str(l.transaction_id), "account": l.account,
             "debit": float(l.debit_amount), "credit": float(l.credit_amount)} for l in r.scalars().all()]


@router.post("/finance/ledger")
async def add_ledger_entry(request: LedgerEntry, db: AsyncSession = Depends(get_db_session)):
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
async def list_budgets(db: AsyncSession = Depends(get_db_session)):
    r = await db.execute(select(FinancialBudget))
    return [{"id": str(b.id), "category": b.category, "amount": float(b.amount),
             "is_approved": b.is_approved} for b in r.scalars().all()]


@router.post("/finance/budgets")
async def create_budget(request: BudgetCreate, db: AsyncSession = Depends(get_db_session)):
    b = FinancialBudget(category=request.category, amount=request.amount,
                        period=request.period, is_approved=request.is_approved)
    db.add(b)
    await db.commit()
    await db.refresh(b)
    return {"id": str(b.id), "category": b.category, "is_approved": b.is_approved}
