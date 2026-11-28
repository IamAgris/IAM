"""Node registry routes (OD-26, OD-29).

Registration creates a candidate node. Resource reports are bounded at 1% of
the resources the operator permitted. Authentication is enforced globally by
AuthMiddleware; these routes require an operator-scope credential or higher.
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db_session
from app.services.attestation_service import AttestationError, AttestationService
from app.services.node_service import NodeService

router = APIRouter(prefix="/api/v1/nodes", tags=["nodes"])


class NodeRegistrationRequest(BaseModel):
    name: str
    architecture: str
    resources: Dict[str, Any]
    capabilities: Optional[List[str]] = None


class ResourceReportRequest(BaseModel):
    cpu_cores: int
    ram_bytes: float
    storage_bytes: float
    used_percent: Optional[float] = None
    contribution_percent: Optional[float] = None


def _actor(request: Request) -> str:
    credential = getattr(request.state, "credential", None)
    return str(credential.get("name", "sdk")) if credential else "sdk"


def _require_admin(request: Request) -> None:
    credential = getattr(request.state, "credential", None)
    if not credential or credential.get("scope") != "admin":
        raise HTTPException(status_code=403, detail="Creator admin scope required")


@router.post("/register")
async def register_node(  # type: ignore[no-untyped-def]
    request: NodeRegistrationRequest,
    http_request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    """Register a deployment as a candidate node, not a trusted peer."""
    try:
        return await NodeService(db).register(request.model_dump(), _actor(http_request))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("")
async def list_nodes(db: AsyncSession = Depends(get_db_session)):  # type: ignore[no-untyped-def]
    return await NodeService(db).list_nodes()


@router.get("/{node_id}")
async def node_status(node_id: str, db: AsyncSession = Depends(get_db_session)):  # type: ignore[no-untyped-def]
    try:
        return await NodeService(db).status(node_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/{node_id}/resources")
async def report_resources(  # type: ignore[no-untyped-def]
    node_id: str,
    request: ResourceReportRequest,
    http_request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    """Record a bounded resource report and expose the 1% allocation."""
    try:
        return await NodeService(db).report_resources(
            node_id, request.model_dump(exclude_none=True), _actor(http_request)
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


class AttestationRequest(BaseModel):
    payload: Dict[str, Any]
    signature: str


class RestrictedReportRequest(BaseModel):
    reason: str


@router.post("/{node_id}/attestation")
async def attest_node(  # type: ignore[no-untyped-def]
    node_id: str,
    request: AttestationRequest,
    http_request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    """Verify a signed node attestation and assign trust accordingly."""
    try:
        return await AttestationService(db).attest_node(
            node_id,
            {"payload": request.payload, "signature": request.signature},
            _actor(http_request),
        )
    except AttestationError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/{node_id}/restricted-report")
async def restricted_report(  # type: ignore[no-untyped-def]
    node_id: str,
    request: RestrictedReportRequest,
    http_request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    """A modified deployment self-downgrades to reporting-only status."""
    try:
        return await AttestationService(db).restricted_report(
            node_id, request.reason, _actor(http_request)
        )
    except AttestationError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/{node_id}/revoke")
async def revoke_node(  # type: ignore[no-untyped-def]
    node_id: str,
    http_request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    """Creator revocation of a node's trusted credentials."""
    _require_admin(http_request)
    try:
        return await AttestationService(db).revoke(node_id, _actor(http_request))
    except AttestationError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/protocol/diagnostics")
async def sdk_diagnostics():  # type: ignore[no-untyped-def]
    """Non-sensitive protocol diagnostics for SDK clients."""
    return {
        "protocol_version": settings.iam_protocol_version,
        "node_registration": "available",
        "contribution_ceiling_percent": 1.0,
        "protected_core_modification": "not permitted via SDK",
    }
