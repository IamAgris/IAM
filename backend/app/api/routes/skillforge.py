"""IAM Skill Forge API — native skill creation, verification and lifecycle.

These endpoints manage the Skill Forge subsystem. They are distinct from the
legacy ``/api/v1/skills`` proficiency registry.

Creator authority follows OD-19: there is no Creator UI. ``approve`` sends an
email request and publishes nothing until a signed challenge is verified via
``/api/v1/creator/requests/{id}/decide``. ``grants`` must be reached only through
that same signed-email gateway, not a dashboard.
"""

from typing import Any, Callable, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.services.skillforge import SkillForgeService
from app.services.skillforge.engine import SkillBuildRequest
from app.services.skillforge.layout import LayoutError
from app.services.skillforge.manifest import (
    ALLOWED_PERMISSIONS,
    CLASSIFICATION_LEVELS,
    ManifestError,
)
from app.services.skillforge.permissions import (
    ALLOWED_TRANSITIONS,
    PermissionDenied,
)

router = APIRouter(prefix="/api/v1/skill-forge", tags=["iam-skill-forge"])


class ApprovalRequest(BaseModel):
    reason: Optional[str] = None


class QuarantineRequest(BaseModel):
    reason: str = "manual"


class RollbackRequest(BaseModel):
    version: str = Field(pattern=r"^\d+\.\d+\.\d+$")


class GrantRequest(BaseModel):
    permission: str
    reason: Optional[str] = None


async def _run(operation: Callable, *args: Any, **kwargs: Any) -> Any:  # type: ignore[type-arg]
    """Translate domain errors into consistent HTTP responses."""
    try:
        return await operation(*args, **kwargs)
    except PermissionDenied as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (ManifestError, LayoutError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/policy")
async def policy():  # type: ignore[no-untyped-def]
    """Declare the authority model that the runtime enforces independently."""
    return {
        "classification_levels": CLASSIFICATION_LEVELS,
        "allowed_permissions": {
            key: sorted(value) for key, value in ALLOWED_PERMISSIONS.items()
        },
        "state_transitions": {
            key: sorted(value) for key, value in ALLOWED_TRANSITIONS.items()
        },
        "manifest_is_authoritative": False,
    }


@router.get("/gaps")
async def discover_gaps(db: AsyncSession = Depends(get_db_session)):  # type: ignore[no-untyped-def]
    """Capability Discovery: areas where a native skill could help."""
    return await _run(SkillForgeService(db).discover_gaps)


@router.get("/skills")
async def list_skills(  # type: ignore[no-untyped-def]
    status: Optional[str] = None,
    origin: Optional[str] = None,
    db: AsyncSession = Depends(get_db_session),
):
    return await _run(SkillForgeService(db).list_skills, status, origin)


@router.post("/skills", status_code=201)
async def create_skill(  # type: ignore[no-untyped-def]
    request: SkillBuildRequest,
    db: AsyncSession = Depends(get_db_session),
):
    """Build a new skill, or register a new version of an existing skill."""
    return await _run(SkillForgeService(db).create, request)


@router.get("/skills/{skill_id}")
async def get_skill(skill_id: str, db: AsyncSession = Depends(get_db_session)):  # type: ignore[no-untyped-def]
    return await _run(SkillForgeService(db).get, skill_id)


@router.post("/skills/{skill_id}/validate")
async def validate_skill(skill_id: str, db: AsyncSession = Depends(get_db_session)):  # type: ignore[no-untyped-def]
    return await _run(SkillForgeService(db).validate, skill_id)


@router.post("/skills/{skill_id}/test")
async def test_skill(skill_id: str, db: AsyncSession = Depends(get_db_session)):  # type: ignore[no-untyped-def]
    return await _run(SkillForgeService(db).test, skill_id)


@router.post("/skills/{skill_id}/approve", status_code=202)
async def request_skill_approval(  # type: ignore[no-untyped-def]
    skill_id: str,
    request: ApprovalRequest,
    db: AsyncSession = Depends(get_db_session),
):
    """Send the Creator an approval email. No UI, no approval is granted here."""
    return await _run(SkillForgeService(db).request_approval, skill_id, request.reason)


@router.post("/skills/{skill_id}/publish")
async def publish_skill(skill_id: str, db: AsyncSession = Depends(get_db_session)):  # type: ignore[no-untyped-def]
    return await _run(SkillForgeService(db).publish, skill_id)


@router.post("/skills/{skill_id}/activate")
async def activate_skill(skill_id: str, db: AsyncSession = Depends(get_db_session)):  # type: ignore[no-untyped-def]
    return await _run(SkillForgeService(db).activate, skill_id)


@router.post("/skills/{skill_id}/quarantine")
async def quarantine_skill(  # type: ignore[no-untyped-def]
    skill_id: str,
    request: QuarantineRequest,
    db: AsyncSession = Depends(get_db_session),
):
    return await _run(SkillForgeService(db).quarantine, skill_id, request.reason)


@router.post("/skills/{skill_id}/rollback")
async def rollback_skill(  # type: ignore[no-untyped-def]
    skill_id: str,
    request: RollbackRequest,
    db: AsyncSession = Depends(get_db_session),
):
    return await _run(SkillForgeService(db).rollback, skill_id, request.version)


@router.get("/skills/{skill_id}/versions")
async def skill_versions(skill_id: str, db: AsyncSession = Depends(get_db_session)):  # type: ignore[no-untyped-def]
    return await _run(SkillForgeService(db).versions, skill_id)


@router.get("/skills/{skill_id}/audit")
async def skill_audit(skill_id: str, db: AsyncSession = Depends(get_db_session)):  # type: ignore[no-untyped-def]
    return await _run(SkillForgeService(db).audit, skill_id)


@router.get("/skills/{skill_id}/tests")
async def skill_tests(skill_id: str, db: AsyncSession = Depends(get_db_session)):  # type: ignore[no-untyped-def]
    return await _run(SkillForgeService(db).test_history, skill_id)


@router.get("/skills/{skill_id}/grants")
async def skill_grants(skill_id: str, db: AsyncSession = Depends(get_db_session)):  # type: ignore[no-untyped-def]
    return await _run(SkillForgeService(db).grants, skill_id)


@router.post("/skills/{skill_id}/grants", status_code=201)
async def grant_permission(  # type: ignore[no-untyped-def]
    skill_id: str,
    request: GrantRequest,
    db: AsyncSession = Depends(get_db_session),
):
    """Creator-only: issue a scoped permission grant stored outside the skill."""
    return await _run(
        SkillForgeService(db).grant,
        skill_id,
        request.permission,
        request.reason,
    )


@router.delete("/skills/{skill_id}/grants/{permission}")
async def revoke_permission(  # type: ignore[no-untyped-def]
    skill_id: str, permission: str, db: AsyncSession = Depends(get_db_session)
):
    return await _run(SkillForgeService(db).revoke, skill_id, permission)


@router.get("/skills/{skill_id}/effective-permissions")
async def effective_permissions(  # type: ignore[no-untyped-def]
    skill_id: str, db: AsyncSession = Depends(get_db_session)
):
    """Runtime authority check — the definitive answer before executing a skill."""
    return await _run(SkillForgeService(db).effective_permissions, skill_id)
