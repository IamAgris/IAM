"""Autonomy routes - worker status and system-level autonomy info"""

from fastapi import APIRouter
from app.workers.autonomy_worker import autonomy_worker

router = APIRouter(prefix="/api/v1/autonomy", tags=["autonomy"])


@router.get("/status")
async def get_autonomy_status():
    """Get the current state of the autonomy worker."""
    return {
        "running": autonomy_worker.running,
        "state": autonomy_worker.state,
        "tick_interval": autonomy_worker.tick_interval,
        "last_cycle": autonomy_worker.last_cycle,
        "orchestration": "langgraph_durable" if autonomy_worker.last_cycle is not None else "initializing",
    }
