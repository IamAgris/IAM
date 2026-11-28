"""WS-04 enforcement: protected-core deployment requires signed Creator authority.

A workspace may propose and test code freely. Deploying to a protected
environment is different: the change must have passed a test gate and the
project must be covered by an active, unrevoked signed Creator authorization.
No UI flag or plain API call can create that authority.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.creatorapproval import CreatorAuthorization
from app.models.development import CodeChange
from app.services.creatorapproval_service import CreatorApprovalService

PROTECTED_DEPLOY_ACTION = "development.protected_deploy"
PROTECTED_ENVIRONMENTS = frozenset({"production", "prod", "core", "protected"})


class DeploymentGateDenied(PermissionError):
    """Raised when a protected deployment lacks tests or signed authority."""


def is_protected_environment(environment: str) -> bool:
    return bool(environment) and str(environment).strip().lower() in PROTECTED_ENVIRONMENTS


def _not_expired(expires_at: datetime) -> bool:
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    return expires_at > datetime.now(timezone.utc)


async def verify_protected_deployment(
    db: AsyncSession, project_id: str, change_ids: List[str]
) -> Dict[str, Any]:
    """Verify tested changes and a signed, project-scoped Creator authorization."""
    if not change_ids:
        raise DeploymentGateDenied(
            "protected deployment requires at least one tested code change"
        )
    try:
        ids = [UUID(str(value)) for value in change_ids]
        project_uuid = UUID(str(project_id))
    except (ValueError, TypeError) as exc:
        raise DeploymentGateDenied("invalid project or code change identifier") from exc

    result = await db.execute(
        select(CodeChange).where(
            CodeChange.id.in_(ids), CodeChange.project_id == project_uuid
        )
    )
    changes = list(result.scalars().all())
    if len(changes) != len(set(ids)):
        raise DeploymentGateDenied("one or more code changes do not belong to the project")
    if any(change.status not in ("tested", "deployed") for change in changes):
        raise DeploymentGateDenied("all code changes must be tested before deployment")

    authorizations = await db.execute(
        select(CreatorAuthorization).where(
            CreatorAuthorization.action_type == PROTECTED_DEPLOY_ACTION,
            CreatorAuthorization.is_active.is_(True),
            CreatorAuthorization.target_ref == str(project_uuid),
        )
    )
    approvals = CreatorApprovalService(db)
    for authorization in authorizations.scalars().all():
        if authorization.target_ref != str(project_uuid):
            continue
        if authorization.revoked_at or not _not_expired(authorization.expires_at):  # type: ignore[arg-type]
            continue
        authority = await approvals.check_authorization(
            PROTECTED_DEPLOY_ACTION, target_ref=str(project_uuid)
        )
        if not authority.get("authorized"):
            continue
        if authority.get("authorization_id") != str(authorization.id):
            continue
        return {
            "authorized": True,
            "authorization_id": str(authorization.id),
            "signer_id": authorization.signer_id,
            "target_ref": str(project_uuid),
            "tested_changes": [str(change.id) for change in changes],
            "expires_at": authority.get("expires_at"),
        }
    raise DeploymentGateDenied(
        "no active signed Creator authorization covers this protected deployment"
    )
