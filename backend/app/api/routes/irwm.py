"""Runtime resource and workload manager endpoints (OD-39)."""

from typing import Optional

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
async def status():
    return irwm.status()


@router.post("/admit")
async def admit(payload: AdmitRequest):
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
async def release(payload: ReleaseRequest):
    return await irwm.release(payload.model)


@router.post("/sweep")
async def sweep():
    return {"unloaded": irwm.sweep_idle()}
