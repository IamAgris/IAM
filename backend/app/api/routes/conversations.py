"""Conversation routes with database persistence.

The original four endpoints keep their paths and response shapes so the
existing frontend needs no changes. Conversations are scoped to a server-issued
owner token (HttpOnly cookie), so one browser cannot read or delete another
browser's history. Additional management endpoints are layered on top.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid

from app.api.middleware.conversation_owner import conversation_owner, cookie_owner
from app.core.database import get_db_session
from app.models.memory import Conversation, ConversationMessage
from app.services.conversation_service import ConversationService
from app.services.crypto_service import crypto

router = APIRouter(prefix="/api/v1/conversations", tags=["conversations"])


class ConversationCreate(BaseModel):
    title: Optional[str] = None
    metadata: Dict[str, Any] = {}
    ended_at: Optional[str] = None


class ConversationResponse(BaseModel):
    id: str
    title: Optional[str]
    started_at: Optional[str]
    ended_at: Optional[str]
    metadata: Dict[str, Any]


class MessageCreate(BaseModel):
    conversation_id: Optional[str] = None
    role: str  # user, assistant, system, tool
    content: str
    metadata: Dict[str, Any] = {}


class MessageResponse(BaseModel):
    id: str
    conversation_id: str
    role: str
    content: str
    created_at: Optional[str]
    metadata: Dict[str, Any]


class ConversationDetailResponse(BaseModel):
    id: str
    title: Optional[str]
    started_at: Optional[str]
    ended_at: Optional[str]
    metadata: Dict[str, Any]
    messages: List[MessageResponse]


def _conversation_uuid(value: str) -> str:
    """Validate an id before comparing it to a UUID column."""
    try:
        return str(uuid.UUID(value))
    except (ValueError, AttributeError, TypeError):
        raise HTTPException(status_code=404, detail="Conversation not found")


def _ended_at(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        raise HTTPException(status_code=400, detail="ended_at must be an ISO datetime")


# --- Original routes (contract shapes unchanged) ---


@router.get("/", response_model=List[ConversationResponse])
async def list_conversations(
    http_request: Request,
    db: AsyncSession = Depends(get_db_session),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    q: Optional[str] = None,
) -> List[ConversationResponse]:
    """List the caller's conversations, newest first."""
    service = ConversationService(db)
    conversations = await service.list_conversations(
        limit=limit,
        offset=offset,
        owner=conversation_owner(http_request),
        query=q,
    )
    return [
        ConversationResponse(
            id=item["id"],
            title=item.get("title"),
            started_at=item.get("created_at"),
            ended_at=item.get("ended_at"),
            metadata=item.get("metadata") or {},
        )
        for item in conversations
    ]


@router.post("/", response_model=ConversationResponse)
async def create_conversation(
    conversation: ConversationCreate,
    http_request: Request,
    db: AsyncSession = Depends(get_db_session),
) -> ConversationResponse:
    """Create a conversation owned by the caller."""
    conv = Conversation(
        title=conversation.title,
        metadata_={
            **conversation.metadata,
            "owner_token": conversation_owner(http_request) or "",
        },
        ended_at=_ended_at(conversation.ended_at),
    )
    db.add(conv)
    await db.commit()
    await db.refresh(conv)
    return ConversationResponse(
        id=str(conv.id),
        title=str(conv.title) if conv.title else None,
        started_at=conv.started_at.isoformat() if conv.started_at else None,
        ended_at=conv.ended_at.isoformat() if conv.ended_at else None,
        metadata=dict(conv.metadata_ or {}),
    )


# Registered before ``/{conversation_id}`` so the literal path wins.
@router.post("/messages", response_model=MessageResponse)
async def create_message(
    message: MessageCreate,
    http_request: Request,
    db: AsyncSession = Depends(get_db_session),
) -> MessageResponse:
    """Create a message in one of the caller's conversations."""
    owner = conversation_owner(http_request)
    conv_id = message.conversation_id
    if not conv_id:
        conv = Conversation(
            title="New Conversation", metadata_={"owner_token": owner or ""}
        )
        db.add(conv)
        await db.flush()
        conv_id = str(conv.id)
    else:
        conv_id = _conversation_uuid(conv_id)
        result = await db.execute(select(Conversation).where(Conversation.id == conv_id))
        existing = result.scalar_one_or_none()
        if existing is None or not ConversationService._is_owner(existing, owner):
            raise HTTPException(status_code=404, detail="Conversation not found")

    msg = ConversationMessage(
        conversation_id=conv_id,
        role=message.role,
        content=crypto.encrypt(message.content),
        metadata_=message.metadata,
    )
    db.add(msg)
    await db.commit()
    await db.refresh(msg)
    return MessageResponse(
        id=str(msg.id),
        conversation_id=str(msg.conversation_id),
        role=str(msg.role),
        content=crypto.decrypt(str(msg.content)),
        created_at=msg.created_at.isoformat() if msg.created_at else None,
        metadata=dict(msg.metadata_ or {}),
    )


@router.get("/{conversation_id}/messages", response_model=List[MessageResponse])
async def get_messages(
    conversation_id: str,
    http_request: Request,
    db: AsyncSession = Depends(get_db_session),
) -> List[MessageResponse]:
    """Get messages from one of the caller's conversations."""
    conversation_id = _conversation_uuid(conversation_id)
    service = ConversationService(db)
    if await service.get_conversation(conversation_id, owner=conversation_owner(http_request)) is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    result = await db.execute(
        select(ConversationMessage)
        .where(ConversationMessage.conversation_id == conversation_id)
        .order_by(ConversationMessage.created_at.asc())
    )
    messages = result.scalars().all()
    return [
        MessageResponse(
            id=str(m.id),
            conversation_id=str(m.conversation_id),
            role=str(m.role),
            content=crypto.decrypt(str(m.content)),
            created_at=m.created_at.isoformat() if m.created_at else None,
            metadata=dict(m.metadata_ or {}),
        )
        for m in messages
    ]


# --- Additional management routes ---


@router.get("/{conversation_id}", response_model=ConversationDetailResponse)
async def get_conversation(
    conversation_id: str,
    http_request: Request,
    db: AsyncSession = Depends(get_db_session),
) -> ConversationDetailResponse:
    """Get a conversation together with all its messages."""
    conversation_id = _conversation_uuid(conversation_id)
    service = ConversationService(db)
    result = await service.get_conversation(
        conversation_id, owner=conversation_owner(http_request)
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return ConversationDetailResponse(**result)


@router.post("/{conversation_id}/claim", response_model=ConversationResponse)
async def claim_conversation(
    conversation_id: str,
    http_request: Request,
    db: AsyncSession = Depends(get_db_session),
) -> ConversationResponse:
    """Bind an anonymous browser's conversation to the signed-in identity.

    Requires an authenticated credential and ownership of the cookie token.
    This gives per-person continuity after login without any client change.
    """
    conversation_id = _conversation_uuid(conversation_id)
    owner = conversation_owner(http_request)
    if not owner or not owner.startswith("credential:"):
        raise HTTPException(status_code=403, detail="Authentication required to claim")
    service = ConversationService(db)
    result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    conversation = result.scalar_one_or_none()
    if conversation is None or not ConversationService._is_owner(
        conversation, cookie_owner(http_request)
    ):
        raise HTTPException(status_code=404, detail="Conversation not found")
    metadata = dict(conversation.metadata_ or {})
    metadata[ConversationService.OWNER_KEY] = owner
    conversation.metadata_ = metadata  # type: ignore[assignment]
    await db.commit()
    await db.refresh(conversation)
    return ConversationResponse(
        id=str(conversation.id),
        title=str(conversation.title) if conversation.title else None,
        started_at=conversation.started_at.isoformat() if conversation.started_at else None,
        ended_at=conversation.ended_at.isoformat() if conversation.ended_at else None,
        metadata=dict(conversation.metadata_ or {}),
    )


@router.put("/{conversation_id}", response_model=ConversationResponse)
async def update_conversation(
    conversation_id: str,
    conversation: ConversationCreate,
    http_request: Request,
    db: AsyncSession = Depends(get_db_session),
) -> ConversationResponse:
    """Update a conversation's title, metadata or ended_at."""
    conversation_id = _conversation_uuid(conversation_id)
    service = ConversationService(db)
    result = await service.update_conversation(
        conversation_id,
        title=conversation.title,
        metadata_=conversation.metadata,
        owner=conversation_owner(http_request),
        ended_at=_ended_at(conversation.ended_at),
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return ConversationResponse(
        id=result["id"],
        title=result["title"],
        started_at=result["created_at"],
        ended_at=result.get("ended_at"),
        metadata=result["metadata"],
    )


@router.delete("/{conversation_id}", status_code=204)
async def delete_conversation(
    conversation_id: str,
    http_request: Request,
    db: AsyncSession = Depends(get_db_session),
) -> None:
    """Delete one of the caller's conversations and its messages."""
    conversation_id = _conversation_uuid(conversation_id)
    deleted = await ConversationService(db).delete_conversation(
        conversation_id, owner=conversation_owner(http_request)
    )
    if not deleted:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return None


@router.put("/{conversation_id}/messages/{message_id}", response_model=MessageResponse)
async def update_message(
    conversation_id: str,
    message_id: str,
    message: MessageCreate,
    http_request: Request,
    db: AsyncSession = Depends(get_db_session),
) -> MessageResponse:
    """Update a message in one of the caller's conversations."""
    conversation_id = _conversation_uuid(conversation_id)
    service = ConversationService(db)
    if await service.get_conversation(
        conversation_id, owner=conversation_owner(http_request)
    ) is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    result = await service.update_message(
        message_id, content=message.content, metadata_=message.metadata
    )
    if result is None or result["conversation_id"] != conversation_id:
        raise HTTPException(status_code=404, detail="Message not found")
    return MessageResponse(**result)


@router.delete("/{conversation_id}/messages/{message_id}", status_code=204)
async def delete_message(
    conversation_id: str,
    message_id: str,
    http_request: Request,
    db: AsyncSession = Depends(get_db_session),
) -> None:
    """Delete a message from one of the caller's conversations."""
    conversation_id = _conversation_uuid(conversation_id)
    service = ConversationService(db)
    if await service.get_conversation(
        conversation_id, owner=conversation_owner(http_request)
    ) is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    deleted = await service.delete_message(message_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Message not found")
    return None
