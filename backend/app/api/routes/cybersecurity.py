"""IAM Cybersecurity API — external security engines under IAM control.

ARTEX is an optional engine in this layer, never part of IAM's protected core.
Every task is created without external contact, approved by the creator, and
re-checked by the IAM Security Guard before dispatch.

Creator authority follows OD-19: there is no Creator UI. Privileged endpoints
(``register``, ``scopes``, ``approve``, ``reject``, ``dispatch``) require a
signed Creator authorization created via ``/api/v1/creator/requests/{id}/decide``.
A plain email reply is never accepted as authority.
"""

from typing import Any, Callable, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.services.cybersecurity.security_guard import (
    EXECUTION_TOOLS,
    KNOWN_TOOLS,
    READ_TOOLS,
    SecurityGuardDenied,
)
from app.services.cybersecurity.service import SecurityEngineService

router = APIRouter(prefix="/api/v1/cybersecurity", tags=["iam-cybersecurity"])


class EngineRegisterRequest(BaseModel):
    name: str
    provider: str = "artex"
    base_url: str = "http://127.0.0.1:8787"
    token_env_var: str = "ARTEX_MCP_TOKEN"
    enabled: bool = False
    dry_run: bool = True
    allow_private_network: bool = False
    allow_execution: bool = False
    allowed_scopes: List[str] = Field(default_factory=lambda: ["read"])


class ScopeRequest(BaseModel):
    target: str
    target_type: str = "host"
    description: Optional[str] = None
    authorization_id: Optional[str] = None
    allow_write: bool = False


class TaskCreateRequest(BaseModel):
    target: str
    description: str
    operation: str = "list_task_findings"
    risk_level: str = "sensitive"


class ApprovalRequest(BaseModel):
    reason: Optional[str] = None


class RemediationRequest(BaseModel):
    guidance: str


async def _run(operation: Callable, *args: Any, **kwargs: Any) -> Any:
    try:
        return await operation(*args, **kwargs)
    except SecurityGuardDenied as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/policy")
async def policy():
    """IAM-side policy — enforced independently of the external engine."""
    return {
        "posture": "defensive_only",
        "default_state": {"enabled": False, "dry_run": True, "scopes": ["read"]},
        "read_tools": sorted(READ_TOOLS),
        "execution_tools": sorted(EXECUTION_TOOLS),
        "all_tools": sorted(KNOWN_TOOLS),
        "prohibited": [
            "internet-wide or wildcard targets",
            "exploitation, persistence, evasion and privilege escalation",
            "destructive testing outside an isolated lab",
            "unapproved or unauthorised operations",
            "public or non-loopback engine endpoints",
        ],
        "engine_output_is_untrusted_data": True,
    }


@router.get("/engines")
async def list_engines(db: AsyncSession = Depends(get_db_session)):
    return await _run(SecurityEngineService(db).list_engines)


@router.post("/engines", status_code=201)
async def register_engine(
    request: EngineRegisterRequest, db: AsyncSession = Depends(get_db_session)
):
    return await _run(
        SecurityEngineService(db).register_engine,
        name=request.name,
        provider=request.provider,
        base_url=request.base_url,
        token_env_var=request.token_env_var,
        enabled=request.enabled,
        dry_run=request.dry_run,
        allow_private_network=request.allow_private_network,
        allow_execution=request.allow_execution,
        allowed_scopes=request.allowed_scopes,
    )


@router.get("/engines/{engine_id}")
async def get_engine(engine_id: str, db: AsyncSession = Depends(get_db_session)):
    return await _run(SecurityEngineService(db).get_engine, engine_id)


@router.post("/engines/{engine_id}/health")
async def engine_health(engine_id: str, db: AsyncSession = Depends(get_db_session)):
    return await _run(SecurityEngineService(db).health_check, engine_id)


@router.get("/engines/{engine_id}/scopes")
async def list_scopes(engine_id: str, db: AsyncSession = Depends(get_db_session)):
    return await _run(SecurityEngineService(db).list_scopes, engine_id)


@router.post("/engines/{engine_id}/scopes", status_code=201)
async def add_scope(
    engine_id: str,
    request: ScopeRequest,
    db: AsyncSession = Depends(get_db_session),
):
    return await _run(
        SecurityEngineService(db).add_scope,
        engine_id,
        target=request.target,
        target_type=request.target_type,
        description=request.description,
        authorization_id=request.authorization_id,
        allow_write=request.allow_write,
    )


@router.get("/tasks")
async def list_tasks(db: AsyncSession = Depends(get_db_session)):
    return await _run(SecurityEngineService(db).list_tasks)


@router.post("/engines/{engine_id}/tasks", status_code=201)
async def create_task(
    engine_id: str,
    request: TaskCreateRequest,
    db: AsyncSession = Depends(get_db_session),
):
    return await _run(
        SecurityEngineService(db).create_task,
        engine_id,
        target=request.target,
        description=request.description,
        operation=request.operation,
        risk_level=request.risk_level,
    )


@router.get("/tasks/{task_id}")
async def get_task(task_id: str, db: AsyncSession = Depends(get_db_session)):
    return await _run(SecurityEngineService(db).get_task, task_id)


@router.post("/tasks/{task_id}/approve")
async def approve_task(
    task_id: str,
    request: ApprovalRequest,
    db: AsyncSession = Depends(get_db_session),
):
    return await _run(
        SecurityEngineService(db).approve_task, task_id, reason=request.reason
    )


@router.post("/tasks/{task_id}/reject")
async def reject_task(task_id: str, db: AsyncSession = Depends(get_db_session)):
    return await _run(SecurityEngineService(db).reject_task, task_id)


@router.post("/tasks/{task_id}/dispatch")
async def dispatch_task(task_id: str, db: AsyncSession = Depends(get_db_session)):
    return await _run(SecurityEngineService(db).dispatch_task, task_id)


@router.post("/tasks/{task_id}/sync")
async def sync_task(task_id: str, db: AsyncSession = Depends(get_db_session)):
    return await _run(SecurityEngineService(db).sync_task, task_id)


@router.post("/tasks/{task_id}/retest", status_code=201)
async def retest_task(task_id: str, db: AsyncSession = Depends(get_db_session)):
    return await _run(SecurityEngineService(db).retest, task_id)


@router.post("/tasks/{task_id}/create-skill", status_code=201)
async def create_defensive_skill(
    task_id: str, db: AsyncSession = Depends(get_db_session)
):
    """Skill Forge handoff — creates a gated defensive skill, not a publish."""
    return await _run(SecurityEngineService(db).create_defensive_skill, task_id)


@router.get("/tasks/{task_id}/findings")
async def task_findings(task_id: str, db: AsyncSession = Depends(get_db_session)):
    return await _run(SecurityEngineService(db).findings_for_task, task_id)


@router.post("/findings/{finding_id}/remediate")
async def remediate_finding(
    finding_id: str,
    request: RemediationRequest,
    db: AsyncSession = Depends(get_db_session),
):
    return await _run(
        SecurityEngineService(db).remediate, finding_id, request.guidance
    )


@router.get("/audit")
async def audit(db: AsyncSession = Depends(get_db_session)):
    return await _run(SecurityEngineService(db).audit_for)
