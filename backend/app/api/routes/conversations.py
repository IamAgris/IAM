"""Conversation routes with database persistence"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid

from app.core.database import get_db_session
from app.models.memory import Conversation, ConversationMessage
from app.services.crypto_service import crypto

router = APIRouter(prefix="/api/v1/conversations", tags=["conversations"])


# --- Pydantic models ---

class ConversationCreate(BaseModel):
    title: Optional[str] = None
    metadata: Dict[str, Any] = {}


class ConversationResponse(BaseModel):
    id: str
    title: Optional[str]
    started_at: Optional[str]
    ended_at: Optional[str]
    metadata: Dict[str, Any]

    class Config:
        from_attributes = True


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

    class Config:
        from_attributes = True


# --- Routes ---

@router.get("/", response_model=List[ConversationResponse])
async def list_conversations(db: AsyncSession = Depends(get_db_session)):
    """List all conversations."""
    result = await db.execute(select(Conversation).order_by(Conversation.started_at.desc()))
    conversations = result.scalars().all()
    return [
        ConversationResponse(
            id=str(c.id),
            title=c.title,
            started_at=c.started_at.isoformat() if c.started_at else None,
            ended_at=c.ended_at.isoformat() if c.ended_at else None,
            metadata=c.metadata_ or {},
        )
        for c in conversations
    ]


@router.post("/", response_model=ConversationResponse)
async def create_conversation(
    conversation: ConversationCreate,
    db: AsyncSession = Depends(get_db_session),
):
    """Create a new conversation."""
    conv = Conversation(
        title=conversation.title,
        metadata_=conversation.metadata,
    )
    db.add(conv)
    await db.commit()
    await db.refresh(conv)
    return ConversationResponse(
        id=str(conv.id),
        title=conv.title,
        started_at=conv.started_at.isoformat() if conv.started_at else None,
        ended_at=conv.ended_at.isoformat() if conv.ended_at else None,
        metadata=conv.metadata_ or {},
    )


@router.get("/{conversation_id}/messages", response_model=List[MessageResponse])
async def get_messages(
    conversation_id: str,
    db: AsyncSession = Depends(get_db_session),
):
    """Get all messages in a conversation."""
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
            role=m.role,
            content=crypto.decrypt(m.content),
            created_at=m.created_at.isoformat() if m.created_at else None,
            metadata=m.metadata_ or {},
        )
        for m in messages
    ]


@router.post("/messages", response_model=MessageResponse)
async def create_message(
    message: MessageCreate,
    db: AsyncSession = Depends(get_db_session),
):
    """Create a new message in a conversation."""
    # If no conversation_id provided, create a new conversation
    conv_id = message.conversation_id
    if not conv_id:
        conv = Conversation(title="New Conversation", metadata_={})
        db.add(conv)
        await db.flush()
        conv_id = str(conv.id)
    else:
        # Verify conversation exists
        result = await db.execute(
            select(Conversation).where(Conversation.id == conv_id)
        )
        if not result.scalar_one_or_none():
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
        role=msg.role,
        content=crypto.decrypt(msg.content),
        created_at=msg.created_at.isoformat() if msg.created_at else None,
        metadata=msg.metadata_ or {},
    )
