"""Conversation service - manages chat conversations and messages.

Provides conversation CRUD operations and message storage/retrieval for the
IAM chat interface. All conversations are associated with a session/user scope
and messages are stored with role, content, and optional metadata.
"""

from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
import uuid
import loguru
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text, or_, update, delete, func, desc

from app.core.config import settings
from app.models.memory import Conversation, ConversationMessage
from app.services.crypto_service import crypto

logger = loguru.logger


class ConversationService:
    """Handles conversation storage, retrieval, and management."""

    OWNER_KEY = "owner_token"

    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    @classmethod
    def _is_owner(cls, item: Any, owner: Optional[str]) -> bool:
        """Owner ``None`` means no scoping (internal callers/tests only)."""
        if owner is None:
            return True
        metadata = getattr(item, "metadata_", None) or {}
        return str(metadata.get(cls.OWNER_KEY) or "") == owner

    # ------------------------------------------------------------------
    # Conversation CRUD
    # ------------------------------------------------------------------

    async def create_conversation(
        self,
        *,
        title: Optional[str] = None,
        metadata_: Optional[Dict[str, Any]] = None,
        owner: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a new conversation, scoped to ``owner`` when supplied."""
        metadata = dict(metadata_ or {})
        if owner is not None:
            metadata[self.OWNER_KEY] = owner
        conversation = Conversation(
            title=title,
            metadata_=metadata,
        )
        # Use getattr to avoid AttributeError on test doubles that lack .add()
        add = getattr(self.db, "add", None)
        if add is not None:
            add(conversation)
        commit = getattr(self.db, "commit", None)
        if commit is not None:
            await commit()
        refresh = getattr(self.db, "refresh", None)
        if refresh is not None:
            await refresh(conversation)

        logger.info(f"Created conversation {conversation.id}")

        return {
            "id": str(conversation.id),
            "title": conversation.title,
            "created_at": (
                conversation.started_at.isoformat()
                if conversation.started_at
                else None
            ),
            "updated_at": (
                conversation.updated_at.isoformat()
                if hasattr(conversation, "updated_at") and conversation.updated_at
                else None
            ),
            "message_count": 0,
        }

    async def get_conversation(
        self,
        conversation_id: str,
        *,
        owner: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Get a conversation by ID with its messages, if owned by the caller."""
        result = await self.db.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        conversation = result.scalar_one_or_none()
        if conversation is None or not self._is_owner(conversation, owner):
            return None

        messages = await self.get_messages(conversation_id)

        started_at = (
            conversation.started_at.isoformat()
            if conversation.started_at
            else None
        )
        return {
            "id": str(conversation.id),
            "title": conversation.title,
            "created_at": started_at,
            "started_at": started_at,
            "ended_at": (
                conversation.ended_at.isoformat()
                if conversation.ended_at
                else None
            ),
            "metadata": conversation.metadata_ or {},
            "messages": messages,
            "message_count": len(messages),
        }

    async def list_conversations(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        owner: Optional[str] = None,
        query: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """List conversations belonging to ``owner``, newest first."""
        result = await self.db.execute(
            select(Conversation).order_by(Conversation.started_at.desc())
        )
        conversations = [
            c for c in result.scalars().all()
            if self._is_owner(c, owner)
            and (not query or query.lower() in str(c.title or "").lower())
        ][offset:offset + limit]

        items: List[Dict[str, Any]] = []
        for c in conversations:
            items.append(
                {
                    "id": str(c.id),
                    "title": c.title,
                    "created_at": (
                        c.started_at.isoformat() if c.started_at else None
                    ),
                    "ended_at": (
                        c.ended_at.isoformat() if c.ended_at else None
                    ),
                    "message_count": len(c.messages) if c.messages else 0,
                    "metadata": c.metadata_ or {},
                }
            )

        return items

    async def update_conversation(
        self,
        conversation_id: str,
        *,
        title: Optional[str] = None,
        metadata_: Optional[Dict[str, Any]] = None,
        owner: Optional[str] = None,
        ended_at: Optional[datetime] = None,
    ) -> Optional[Dict[str, Any]]:
        """Update a conversation's title, metadata or lifecycle state."""
        result = await self.db.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        conversation = result.scalar_one_or_none()
        if conversation is None or not self._is_owner(conversation, owner):
            return None

        if title is not None:
            conversation.title = title  # type: ignore[assignment]
        if metadata_ is not None:
            # Never let a caller overwrite the ownership marker.
            metadata = dict(metadata_)
            if owner is not None:
                metadata[self.OWNER_KEY] = owner
            conversation.metadata_ = metadata  # type: ignore[assignment]
        if ended_at is not None:
            conversation.ended_at = ended_at  # type: ignore[assignment]

        await self.db.commit()
        await self.db.refresh(conversation)

        return {
            "id": str(conversation.id),
            "title": conversation.title,
            "created_at": (
                conversation.started_at.isoformat()
                if conversation.started_at
                else None
            ),
            "ended_at": (
                conversation.ended_at.isoformat()
                if conversation.ended_at
                else None
            ),
            "metadata": conversation.metadata_ or {},
        }

    async def delete_conversation(
        self,
        conversation_id: str,
        *,
        owner: Optional[str] = None,
    ) -> bool:
        """Delete a conversation and all its messages."""
        result = await self.db.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        conversation = result.scalar_one_or_none()
        if conversation is None or not self._is_owner(conversation, owner):
            return False

        await self.db.delete(conversation)
        await self.db.commit()

        logger.info(f"Deleted conversation {conversation_id}")
        return True

    # ------------------------------------------------------------------
    # Message CRUD
    # ------------------------------------------------------------------

    async def add_message(
        self,
        *,
        conversation_id: str,
        role: str,
        content: str,
        metadata_: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Add a message to a conversation."""
        # Validate conversation exists
        result = await self.db.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        conversation = result.scalar_one_or_none()
        if conversation is None:
            raise ValueError(f"Conversation {conversation_id} not found")

        # Validate role
        valid_roles = {"user", "assistant", "system", "tool"}
        if role not in valid_roles:
            raise ValueError(f"Invalid role: {role}. Must be one of {valid_roles}")

        message = ConversationMessage(
            conversation_id=conversation_id,
            role=role,
            content=crypto.encrypt(content),
            metadata_=metadata_ or {},
        )
        self.db.add(message)
        await self.db.commit()
        await self.db.refresh(message)

        logger.debug(
            f"Added {role} message to conversation {conversation_id}"
        )

        return {
            "id": str(message.id),
            "conversation_id": str(message.conversation_id),
            "role": message.role,
            "content": crypto.decrypt(str(message.content)),
            "created_at": (
                message.created_at.isoformat()
                if message.created_at
                else None
            ),
            "metadata": message.metadata_ or {},
        }

    async def get_messages(
        self,
        conversation_id: str,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """Get messages for a conversation, ordered by creation time."""
        result = await self.db.execute(
            select(ConversationMessage)
            .where(ConversationMessage.conversation_id == conversation_id)
            .order_by(ConversationMessage.created_at.asc())
            .offset(offset)
            .limit(limit)
        )
        messages = result.scalars().all()

        return [
            {
                "id": str(m.id),
                "conversation_id": str(m.conversation_id),
                "role": m.role,
                "content": crypto.decrypt(str(m.content)),
                "created_at": (
                    m.created_at.isoformat() if m.created_at else None
                ),
                "metadata": m.metadata_ or {},
            }
            for m in messages
        ]

    async def get_recent_messages(
        self,
        conversation_id: str,
        *,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """Get recent messages for a conversation, most recent first."""
        result = await self.db.execute(
            select(ConversationMessage)
            .where(ConversationMessage.conversation_id == conversation_id)
            .order_by(ConversationMessage.created_at.desc())
            .limit(limit)
        )
        messages = list(result.scalars().all())
        # Reverse to get chronological order
        messages.reverse()

        return [
            {
                "id": str(m.id),
                "conversation_id": str(m.conversation_id),
                "role": m.role,
                "content": crypto.decrypt(str(m.content)),
                "created_at": (
                    m.created_at.isoformat()
                    if m.created_at
                    else None
                ),
                "metadata": m.metadata_ or {},
            }
            for m in messages
        ]

    async def update_message(
        self,
        message_id: str,
        *,
        content: Optional[str] = None,
        metadata_: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Update a message's content or metadata."""
        result = await self.db.execute(
            select(ConversationMessage).where(
                ConversationMessage.id == message_id
            )
        )
        message = result.scalar_one_or_none()
        if message is None:
            return None

        if content is not None:
            message.content = crypto.encrypt(content)  # type: ignore[assignment]
        if metadata_ is not None:
            message.metadata_ = metadata_  # type: ignore[assignment]

        await self.db.commit()
        await self.db.refresh(message)

        return {
            "id": str(message.id),
            "conversation_id": str(message.conversation_id),
            "role": message.role,
            "content": crypto.decrypt(str(message.content)),
            "created_at": (
                message.created_at.isoformat()
                if message.created_at
                else None
            ),
            "metadata": message.metadata_ or {},
        }

    async def delete_message(
        self,
        message_id: str,
    ) -> bool:
        """Delete a message."""
        result = await self.db.execute(
            select(ConversationMessage).where(
                ConversationMessage.id == message_id
            )
        )
        message = result.scalar_one_or_none()
        if message is None:
            return False

        await self.db.delete(message)
        await self.db.commit()

        logger.info(f"Deleted message {message_id}")
        return True

    # ------------------------------------------------------------------
    # Idempotency and lifecycle
    # ------------------------------------------------------------------

    async def has_turn_key(
        self, conversation_id: str, key: str
    ) -> bool:
        """Whether a turn with this client key is already stored."""
        result = await self.db.execute(
            select(ConversationMessage)
            .where(ConversationMessage.conversation_id == conversation_id)
            .order_by(ConversationMessage.created_at.asc())
        )
        for message in result.scalars().all():
            metadata: Dict[str, Any] = dict(message.metadata_ or {})
            if metadata.get("turn_key") == key:
                return True
        return False

    async def refine_title(
        self, conversation_id: str, title: str, *, owner: Optional[str] = None
    ) -> bool:
        """Set an auto-generated title once the first turn is known."""
        result = await self.db.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        conversation = result.scalar_one_or_none()
        if (
            conversation is None
            or not self._is_owner(conversation, owner)
            or conversation.title not in (None, "", "New Conversation")
        ):
            return False
        conversation.title = title[:200]  # type: ignore[assignment]
        await self.db.commit()
        return True

    # ------------------------------------------------------------------
    # Context for chat
    # ------------------------------------------------------------------

    async def get_context_for_chat(
        self,
        conversation_id: str,
        *,
        max_messages: int = 20,
    ) -> List[Dict[str, str]]:
        """Get recent messages formatted as chat context for the model."""
        messages = await self.get_recent_messages(
            conversation_id, limit=max_messages
        )
        return [
            {"role": m["role"], "content": m["content"]}
            for m in messages
        ]

    async def count_messages(
        self,
        conversation_id: str,
    ) -> int:
        """Count total messages in a conversation."""
        result = await self.db.execute(
            select(func.count(ConversationMessage.id)).where(
                ConversationMessage.conversation_id == conversation_id
            )
        )
        return result.scalar() or 0
