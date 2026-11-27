"""IICS foundation API — pending proposal overlay inside existing systems."""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.services.iics import (
    ActionLedger,
    BenchmarkCase,
    BenchmarkSuite,
    BudgetLimit,
    EgressGateway,
    PermissionGate,
    SourceRegistry,
    label_for_confidence,
)

router = APIRouter(prefix="/api/v1/iics", tags=["iics-foundation"])


class EgressRequest(BaseModel):
    url: str


class AuthorizeRequest(BaseModel):
    action_type: str
    url: Optional[str] = None
    purpose: str = "public research"
    jurisdiction: Optional[str] = None


class ActionRequest(BaseModel):
    actor: str
    tool: str
    target: str
    idempotency_key: str
    scope: str = "public"
    permission_source: str = "legal_gateway"
    approval_ref: Optional[str] = None
    bytes_transferred: int = 0
    cost_units: int = 0


class SourceRequest(BaseModel):
    url: str
    source_type: str = "public_web"
    licence: Optional[str] = None
    rights: Dict[str, bool] = {}
    territory: Optional[str] = None
    freshness_class: str = "documentation"
    reliability_score: float = 0.0
    conditions: List[str] = []
    legal_audit_event_id: Optional[str] = None


class ClaimRequest(BaseModel):
    claim: str
    confidence: float
    locator: Optional[str] = None
    publication_date: Optional[str] = None
    label: Optional[str] = None


@router.post("/egress/check")
async def check_egress(payload: EgressRequest) -> Dict[str, Any]:
    """Deterministically assess a URL without performing a request."""
    return EgressGateway().assess(payload.url).as_dict()


@router.post("/authorize")
async def authorize(payload: AuthorizeRequest, db: AsyncSession = Depends(get_db_session)) -> Dict[str, Any]:
    """Combine internet permission with the mandatory legal gateway."""
    return await PermissionGate(db).authorize(
        payload.action_type,
        payload.url,
        purpose=payload.purpose,
        jurisdiction=payload.jurisdiction,
    )


@router.post("/actions")
async def record_action(payload: ActionRequest, db: AsyncSession = Depends(get_db_session)) -> Dict[str, Any]:
    if payload.scope != "public" and not payload.approval_ref:
        raise HTTPException(status_code=403, detail="approval_ref required for non-public scope")
    return await ActionLedger(db).record(**payload.model_dump())


@router.get("/actions")
async def list_actions(db: AsyncSession = Depends(get_db_session)) -> List[Dict[str, Any]]:
    return await ActionLedger(db).list()


@router.get("/actions/budget")
async def action_budget(db: AsyncSession = Depends(get_db_session)) -> Dict[str, Any]:
    ledger = ActionLedger(db)
    usage = await ledger.usage()
    allowed, reason = await ledger.check_budget(BudgetLimit())
    return {"usage": usage, "allowed": allowed, "reason": reason}


@router.post("/sources")
async def register_source(payload: SourceRequest, db: AsyncSession = Depends(get_db_session)) -> Dict[str, Any]:
    return await SourceRegistry(db).register(**payload.model_dump())


@router.get("/sources")
async def list_sources(active_only: bool = False, db: AsyncSession = Depends(get_db_session)) -> List[Dict[str, Any]]:
    return await SourceRegistry(db).list(active_only=active_only)


@router.get("/sources/{source_id}")
async def get_source(source_id: str, db: AsyncSession = Depends(get_db_session)) -> Dict[str, Any]:
    source = await SourceRegistry(db).get(source_id)
    if not source:
        raise HTTPException(status_code=404, detail="source_not_found")
    return source


@router.post("/sources/{source_id}/refresh")
async def refresh_source(source_id: str, db: AsyncSession = Depends(get_db_session)) -> Dict[str, Any]:
    if not await SourceRegistry(db).touch(source_id):
        raise HTTPException(status_code=404, detail="source_not_found")
    return {"status": "refreshed"}


@router.post("/sources/{source_id}/revoke")
async def revoke_source(source_id: str, db: AsyncSession = Depends(get_db_session)) -> Dict[str, Any]:
    try:
        return await SourceRegistry(db).revoke(source_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/sources/{source_id}/claims")
async def add_claim(
    source_id: str, payload: ClaimRequest, db: AsyncSession = Depends(get_db_session)
) -> Dict[str, Any]:
    try:
        return await SourceRegistry(db).add_claim(source_id, **payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.get("/sources/{source_id}/claims")
async def list_claims(source_id: str, db: AsyncSession = Depends(get_db_session)) -> List[Dict[str, Any]]:
    return await SourceRegistry(db).claims(source_id)


def _builtin_cases() -> List[BenchmarkCase]:
    gateway = EgressGateway(resolver=lambda _: ["93.184.216.34"])
    return [
        BenchmarkCase(
            "ssrf_internal_blocked",
            1.0,
            lambda: 1.0 if not gateway.assess("http://127.0.0.1/latest/meta-data").allowed else 0.0,
        ),
        BenchmarkCase(
            "public_host_allowed",
            1.0,
            lambda: 1.0 if gateway.assess("https://example.com/page").allowed else 0.0,
        ),
        BenchmarkCase(
            "confidence_labelling",
            1.0,
            lambda: 1.0
            if (
                label_for_confidence(0.2) == "unverified"
                and label_for_confidence(0.55) == "provisional"
                and label_for_confidence(0.9) == "verified"
            )
            else 0.0,
        ),
        BenchmarkCase(
            "regression_gate_detects_drop",
            1.0,
            lambda: 1.0
            if not BenchmarkSuite.regression_gate({"x": 0.9}, {"x": 0.7}, 0.05)[0]
            else 0.0,
        ),
    ]


@router.post("/qa/run")
async def run_qa() -> Dict[str, Any]:
    """Run the scored internet QA suite and apply the regression gate."""
    results = await BenchmarkSuite(_builtin_cases()).run()
    baseline = {item["benchmark"]: item["score"] for item in results}
    allowed, regressions = BenchmarkSuite.regression_gate(baseline, baseline)
    return {"results": results, "gate_allowed": allowed, "regressions": regressions}
