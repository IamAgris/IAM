"""OEDIE free sandbox API — admin-gated management of free infrastructure (Doc 22)."""

from typing import Any, Callable, Dict, List, Optional

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session
from app.services.free_sandboxes import (
    SandboxCapability,
    SandboxError,
    WorkloadRequest,
)
from app.services.free_sandboxes.service import FreeSandboxService

router = APIRouter(prefix="/api/v1/free-sandboxes", tags=["free-sandboxes"])


class ProvisionPayload(BaseModel):
    task_id: str
    capability: SandboxCapability
    description: str = ""
    artifact_refs: List[str] = Field(default_factory=list)
    max_runtime_seconds: int = 1800
    metadata: Dict[str, Any] = Field(default_factory=dict)


class RecoverPayload(ProvisionPayload):
    failed_provider: str


async def _run(request: Request, operation: Callable, *args: Any, **kwargs: Any) -> Any:
    try:
        return await operation(*args, **kwargs)
    except SandboxError as exc:
        return JSONResponse(status_code=403, content={"detail": str(exc)})
    except LookupError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})


def _actor(request: Request) -> str:
    credential = getattr(request.state, "credential", None)
    return credential.get("name", "iam") if credential else "iam"


def _service(request: Request, db: AsyncSession) -> FreeSandboxService:
    return FreeSandboxService(db, actor=_actor(request))


def _workload(payload: ProvisionPayload) -> WorkloadRequest:
    return WorkloadRequest(
        task_id=payload.task_id,
        capability=payload.capability,
        description=payload.description,
        artifact_refs=payload.artifact_refs,
        max_runtime_seconds=payload.max_runtime_seconds,
        metadata=payload.metadata,
    )


@router.get("/policy")
async def policy(
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    return _service(request, db).policy()


@router.get("/providers")
async def providers(
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    return await _run(request, _service(request, db).ensure_providers)


@router.post("/discover")
async def discover(
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    return await _run(request, _service(request, db).discover)


@router.post("/providers/{name}/request-registration")
async def request_registration(
    name: str,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    return await _run(request, _service(request, db).request_registration, name)


@router.post("/providers/{name}/verify-credentials")
async def verify_credentials(
    name: str,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    return await _run(request, _service(request, db).validate_credentials, name)


@router.post("/providers/{name}/verify-quota")
async def verify_quota(
    name: str,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    return await _run(request, _service(request, db).verify_quota, name)


@router.get("/status")
async def status(
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    service = _service(request, db)
    return {"policy": service.policy(), "scheduler": service.health()}


@router.post("/monitor")
async def monitor(
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    return await _run(request, _service(request, db).monitor_once)


@router.get("/expiry-calendar")
async def expiry_calendar(
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    return await _run(request, _service(request, db).expiry_calendar)


@router.post("/provision")
async def provision(
    payload: ProvisionPayload,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    return await _run(request, _service(request, db).provision, _workload(payload))


@router.post("/recover")
async def recover(
    payload: RecoverPayload,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    return await _run(
        request,
        _service(request, db).recover,
        _workload(payload),
        payload.failed_provider,
    )


@router.get("/environments")
async def environments(
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    return await _run(request, _service(request, db).list_environments)


@router.get("/environments/{external_id}")
async def environment_status(
    external_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    return await _run(request, _service(request, db).status, external_id)


@router.post("/environments/{external_id}/start")
async def start_environment(
    external_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    return await _run(request, _service(request, db).start, external_id)


@router.post("/environments/{external_id}/stop")
async def stop_environment(
    external_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    return await _run(request, _service(request, db).stop, external_id)


@router.delete("/environments/{external_id}")
async def delete_environment(
    external_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    return await _run(request, _service(request, db).delete, external_id)


@router.post("/environments/{external_id}/results")
async def collect_results(
    external_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    return await _run(request, _service(request, db).collect_results, external_id)
