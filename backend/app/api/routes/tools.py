"""Tool registry and permissions routes"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid

from app.core.database import get_db_session
from app.models.autonomy import ToolRegistry, ToolPermission

router = APIRouter(prefix="/api/v1/autonomy/tools", tags=["autonomy"])


class ToolCreate(BaseModel):
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    parameters: Dict[str, Any] = {}


class ToolPermissionUpdate(BaseModel):
    permission_level: str  # autonomous, authorized, explicit, blocked
    requires_human_approval: bool = False


class ToolResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    category: Optional[str]
    parameters: Dict[str, Any]
    is_active: bool
    created_at: Optional[str]

    class Config:
        from_attributes = True


VALID_PERMISSION_LEVELS = ("autonomous", "authorized", "explicit", "blocked")


@router.get("/", response_model=List[ToolResponse])
async def list_tools(db: AsyncSession = Depends(get_db_session)):  # type: ignore[no-untyped-def]
    """List all registered tools."""
    result = await db.execute(select(ToolRegistry).order_by(ToolRegistry.created_at.desc()))
    tools = result.scalars().all()
    return [
        ToolResponse(
            id=str(t.id),
            name=t.name,  # type: ignore[arg-type]
            description=t.description,  # type: ignore[arg-type]
            category=t.category,  # type: ignore[arg-type]
            parameters=t.parameters or {},  # type: ignore[arg-type]
            is_active=t.is_active,  # type: ignore[arg-type]
            created_at=t.created_at.isoformat() if t.created_at else None,
        )
        for t in tools
    ]


@router.post("/", response_model=ToolResponse)
async def register_tool(tool: ToolCreate, db: AsyncSession = Depends(get_db_session)):  # type: ignore[no-untyped-def]
    """Register a new tool available for autonomous use."""
    # Check for duplicate name
    result = await db.execute(select(ToolRegistry).where(ToolRegistry.name == tool.name))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Tool with this name already exists")

    t = ToolRegistry(
        name=tool.name,
        description=tool.description,
        category=tool.category,
        parameters=tool.parameters,
    )
    db.add(t)
    await db.commit()
    await db.refresh(t)

    # Create default permission (blocked until explicitly allowed)
    perm = ToolPermission(
        tool_id=t.id,
        permission_level="blocked",
        requires_human_approval=True,
    )
    db.add(perm)
    await db.commit()

    return ToolResponse(
        id=str(t.id),
        name=t.name,  # type: ignore[arg-type]
        description=t.description,  # type: ignore[arg-type]
        category=t.category,  # type: ignore[arg-type]
        parameters=t.parameters or {},  # type: ignore[arg-type]
        is_active=t.is_active,  # type: ignore[arg-type]
        created_at=t.created_at.isoformat() if t.created_at else None,
    )


@router.get("/permissions")
async def list_tool_permissions(db: AsyncSession = Depends(get_db_session)):  # type: ignore[no-untyped-def]
    """List all tool permissions."""
    result = await db.execute(select(ToolPermission))
    perms = result.scalars().all()
    return [
        {
            "id": str(p.id),
            "tool_id": str(p.tool_id),
            "permission_level": p.permission_level,
            "requires_human_approval": p.requires_human_approval,
            "updated_at": p.updated_at.isoformat() if p.updated_at else None,
        }
        for p in perms
    ]


@router.patch("/permissions/{tool_id}")
async def update_tool_permission(  # type: ignore[no-untyped-def]
    tool_id: str,
    update: ToolPermissionUpdate,
    db: AsyncSession = Depends(get_db_session),
):
    """Update permission level for a tool."""
    if update.permission_level not in VALID_PERMISSION_LEVELS:
        raise HTTPException(status_code=400, detail="Invalid permission level")

    result = await db.execute(select(ToolPermission).where(ToolPermission.tool_id == tool_id))
    perm = result.scalar_one_or_none()
    if not perm:
        raise HTTPException(status_code=404, detail="Tool permission not found")

    perm.permission_level = update.permission_level  # type: ignore[assignment]
    perm.requires_human_approval = update.requires_human_approval  # type: ignore[assignment]
    await db.commit()

    return {
        "tool_id": tool_id,
        "permission_level": perm.permission_level,
        "requires_human_approval": perm.requires_human_approval,
    }
