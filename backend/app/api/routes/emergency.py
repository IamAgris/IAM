"""Repository-wide emergency stop endpoints (OD-11 / OD-19).

These are operator endpoints, but an admin API credential is only the
transport gate. The authority to engage or lift a halt comes solely from a
signed Creator authorization, verified by EmergencyShutdownService.
"""

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.services.emergency_shutdown import EmergencyShutdownService

router = APIRouter(prefix="/api/v1/ops", tags=["ops"])


class EmergencyAction(BaseModel):
    reason: str
    signed_authorization: Optional[Dict[str, Any]] = None


def _actor(request: Request) -> str:
    credential = getattr(request.state, "credential", None)
    if isinstance(credential, dict):
        return str(credential.get("name") or "operator")
    return "operator"


@router.get("/emergency-status")
async def emergency_status(
    db: AsyncSession = Depends(get_db_session),
) -> Dict[str, Any]:
    """Read the current halt state. No mutation; admin scope required."""
    return await EmergencyShutdownService(db).status()


@router.post("/emergency-stop")
async def emergency_stop(
    payload: EmergencyAction,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
) -> Dict[str, Any]:
    """Halt inference, autonomy, browser and trading. Requires signed Creator authority."""
    try:
        return await EmergencyShutdownService(db).engage(
            reason=payload.reason,
            actor=_actor(request),
            authorization=payload.signed_authorization,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/emergency-resume")
async def emergency_resume(
    payload: EmergencyAction,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
) -> Dict[str, Any]:
    """Lift a halt. IAM cannot resume itself; signed Creator authority is required."""
    try:
        return await EmergencyShutdownService(db).resume(
            reason=payload.reason,
            actor=_actor(request),
            authorization=payload.signed_authorization,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
