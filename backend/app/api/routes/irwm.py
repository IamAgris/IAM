"""Runtime resource and workload manager endpoints (OD-39)."""

from typing import Optional, Any

from fastapi import APIRouter
from pydantic import BaseModel

from app.core.config import settings
from app.services.irwm import irwm

router = APIRouter(prefix="/api/v1/irwm", tags=["irwm"])


class AdmitRequest(BaseModel):
    model: str
    estimated_ram_mb: int
    context_tokens: Optional[int] = None
    task_complexity: int = 3


class ReleaseRequest(BaseModel):
    model: str


@router.get("/status")
async def status() -> Any:
    return irwm.status()


@router.post("/admit")
async def admit(payload: AdmitRequest) -> Any:
    if not settings.irwm_enabled:
        return {
            "decision": "admit",
            "reason": "IRWM disabled; caller is responsible for resource limits",
            "model": payload.model,
        }
    return await irwm.admit(
        payload.model,
        payload.estimated_ram_mb,
        payload.context_tokens,
        payload.task_complexity,
    )


@router.post("/release")
async def release(payload: ReleaseRequest) -> Any:
    return await irwm.release(payload.model)


@router.post("/sweep")
async def sweep() -> Any:
    # sweep_idle now also expires stuck in-flight leases
    result = irwm.sweep_idle()
    return {"unloaded": result, "status": irwm.status()}


@router.post("/force-release")
async def force_release(payload: ReleaseRequest) -> Any:
    """Admin recovery: clear a leaked in-flight slot for a resident model."""
    async with irwm._lock:
        if irwm.resident and irwm.resident.model == payload.model:
            irwm.resident.in_flight = 0
            irwm.resident.in_flight_since = None
            irwm.resident.last_used = __import__("time").monotonic()
            irwm.history.append({"decision": "force_released", "model": payload.model})
            return {"released": True, "model": payload.model}
    return {"released": False, "reason": "model is not resident"}
