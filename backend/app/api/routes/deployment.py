"""Deployment readiness endpoint (redacted, admin scope)."""

from typing import Any

from fastapi import APIRouter

from app.services.deployment_preflight import check_deployment

router = APIRouter(prefix="/api/v1/deployment", tags=["deployment"])


@router.get("/preflight")
async def preflight() -> dict[str, Any]:
    return check_deployment()
