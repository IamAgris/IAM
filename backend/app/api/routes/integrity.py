"""Protected-core integrity and signed knowledge sync routes (OD-05/11/13/26)."""

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.services.attestation_service import AttestationError, AttestationService

router = APIRouter(prefix="/api/v1", tags=["integrity"])


class ManifestRequest(BaseModel):
    confirm: bool = False


class SyncObjectRequest(BaseModel):
    publisher_node_id: str
    object_type: str
    payload: Dict[str, Any]
    signature: str


def _actor(request: Request) -> str:
    credential = getattr(request.state, "credential", None)
    return str(credential.get("name", "sdk")) if credential else "sdk"


def _require_admin(request: Request) -> None:
    credential = getattr(request.state, "credential", None)
    if not credential or credential.get("scope") != "admin":
        raise HTTPException(status_code=403, detail="Creator admin scope required")


@router.post("/integrity/manifest")
async def approve_manifest(
    payload: ManifestRequest,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    """Explicitly approve the current local measurement as known-good."""
    _require_admin(request)
    if not payload.confirm:
        raise HTTPException(
            status_code=400,
            detail="confirm=true is required to approve a known-good integrity manifest",
        )
    return await AttestationService(db).create_manifest(_actor(request))


@router.get("/integrity/status")
async def integrity_status(db: AsyncSession = Depends(get_db_session)):
    return await AttestationService(db).integrity_status()


@router.post("/sync/objects")
async def publish_sync_object(
    payload: SyncObjectRequest,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    """Publish a signed knowledge object. Payload is untrusted data."""
    try:
        return await AttestationService(db).publish_object(
            payload.model_dump(), _actor(request)
        )
    except AttestationError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/sync/objects")
async def list_sync_objects(
    since: Optional[str] = None,
    db: AsyncSession = Depends(get_db_session),
):
    return await AttestationService(db).list_objects(since)


@router.get("/sync/status")
async def sync_status(db: AsyncSession = Depends(get_db_session)):
    return await AttestationService(db).sync_status()
