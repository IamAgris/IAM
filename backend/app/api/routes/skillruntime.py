"""Skill Runtime API — gated execution of approved Skill Forge packages."""

from typing import Any, Callable, Dict, Optional

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db_session
from app.services.skillruntime.service import (
    SkillRuntimeError,
    SkillRuntimeRateLimited,
    SkillRuntimeService,
)

router = APIRouter(prefix="/api/v1/skill-runtime", tags=["skill-runtime"])


class InvokeRequest(BaseModel):
    skill_id: str
    permission: str
    script: Optional[str] = None
    arguments: Dict[str, Any] = Field(default_factory=dict)


async def _run(request: Request, operation: Callable, *args: Any, **kwargs: Any) -> Any:
    try:
        return await operation(*args, **kwargs)
    except SkillRuntimeRateLimited as exc:
        return JSONResponse(status_code=429, content={"detail": str(exc)})
    except SkillRuntimeError as exc:
        return JSONResponse(status_code=403, content={"detail": str(exc)})
    except LookupError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})


@router.get("/policy")
async def policy():
    return {
        "enabled": settings.skill_runtime_enabled,
        "adapter": settings.skill_runtime_adapter,
        "default_adapter": "stub",
        "network_execution": bool(
            settings.skill_runtime_network_enabled and settings.skill_runtime_network_name
        ),
        "network_name": (
            settings.skill_runtime_network_name
            if settings.skill_runtime_network_enabled
            else None
        ),
        "container_limits": {
            "memory": settings.skill_runtime_memory,
            "cpus": settings.skill_runtime_cpus,
            "timeout_seconds": settings.skill_runtime_timeout_seconds,
        },
        "requires_active_skill": True,
        "requires_checksum_match": True,
        "requires_effective_permission": True,
    }


@router.get("/capabilities/{skill_id}")
async def capabilities(
    skill_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    return await _run(request, SkillRuntimeService(db).capabilities, skill_id)


@router.post("/invoke")
async def invoke(
    payload: InvokeRequest,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    credential = getattr(request.state, "credential", None)
    caller = credential.get("name", "iam") if credential else "iam"
    return await _run(
        request,
        SkillRuntimeService(db).invoke,
        payload.skill_id,
        permission=payload.permission,
        script=payload.script,
        arguments=payload.arguments,
        caller=caller,
    )


@router.get("/executions/{execution_id}/logs")
async def execution_logs(
    execution_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    return await _run(request, SkillRuntimeService(db).logs, execution_id)


@router.get("/executions")
async def executions(
    request: Request,
    skill_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db_session),
):
    return await _run(request, SkillRuntimeService(db).executions, skill_id)
