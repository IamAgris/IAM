"""Core-authorised object storage routes (OD-29)."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.services.storage_service import StorageError, StorageService

router = APIRouter(prefix="/api/v1/storage", tags=["storage"])


class UploadRequest(BaseModel):
    name: str
    content: str
    content_type: str = "text/plain"
    approved_for_sharing: bool = False


def _actor(request: Request) -> str:
    credential = getattr(request.state, "credential", None)
    return str(credential.get("name", "sdk")) if credential else "sdk"


@router.post("/objects")
async def upload_object(  # type: ignore[no-untyped-def]
    payload: UploadRequest,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    try:
        return await StorageService(db).upload(
            payload.name,
            payload.content,
            payload.content_type,
            _actor(request),
            payload.approved_for_sharing,
        )
    except StorageError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/objects")
async def list_objects(  # type: ignore[no-untyped-def]
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    return await StorageService(db).list(_actor(request))


@router.get("/objects/{object_id}")
async def get_object(  # type: ignore[no-untyped-def]
    object_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    try:
        return await StorageService(db).get(object_id, _actor(request))
    except StorageError as exc:
        status = 404 if "not found" in str(exc) else 400
        raise HTTPException(status_code=status, detail=str(exc))
