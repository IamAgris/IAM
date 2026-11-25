"""Memory service - long-term memory and knowledge management with pgvector"""

from typing import Optional, Dict, Any, List
from datetime import datetime
import uuid
import httpx
import loguru
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from app.core.config import settings
from app.models.memory import MemoryItem, MemoryEmbedding

logger = loguru.logger


class MemoryService:
    """Handles memory storage, retrieval, and semantic search with pgvector."""

    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    async def store_memory(
        self,
        content: str,
        memory_type: str = "fact",
        source: Optional[str] = None,
        confidence: float = 0.5,
        topic: Optional[str] = None,
        metadata_: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Store a new memory item with provenance tracking and embedding."""
        memory = MemoryItem(
            content=content,
            memory_type=memory_type,
            source=source,
            confidence_level=confidence,
            topic=topic,
            metadata_=metadata_ or {},
        )
        self.db.add(memory)
        await self.db.flush()

        # Generate embedding via LiteLLM
        embedding_vector = await self._generate_embedding(content)
        if embedding_vector:
            embedding = MemoryEmbedding(
                memory_item_id=memory.id,
                embedding=embedding_vector,
                model="text-embedding-3-small",
            )
            self.db.add(embedding)

        await self.db.commit()
        await self.db.refresh(memory)

        return {
            "id": str(memory.id),
            "content": memory.content,
            "memory_type": memory.memory_type,
            "source": memory.source,
            "confidence_level": float(memory.confidence_level) if memory.confidence_level else 0.5,
            "topic": memory.topic,
            "created_at": memory.created_at.isoformat() if memory.created_at else None,
        }

    async def search_memory(
        self, query: str, limit: int = 10, memory_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Semantic search using pgvector cosine similarity."""
        # Generate query embedding
        query_embedding = await self._generate_embedding(query)
        if not query_embedding:
            return []

        # Build SQL query with pgvector cosine distance
        embedding_str = "[" + ",".join(str(x) for x in query_embedding) + "]"

        if memory_type:
            sql = text("""
                SELECT mi.id, mi.content, mi.memory_type, mi.source,
                       mi.confidence_level, mi.topic, mi.created_at,
                       1 - (me.embedding <=> CAST(:embedding AS vector)) AS similarity
                FROM memory_items mi
                JOIN memory_embeddings me ON me.memory_item_id = mi.id
                WHERE mi.memory_type = :memory_type
                ORDER BY me.embedding <=> CAST(:embedding AS vector)
                LIMIT :limit
            """)
            result = await self.db.execute(
                sql,
                {"embedding": embedding_str, "memory_type": memory_type, "limit": limit},
            )
        else:
            sql = text("""
                SELECT mi.id, mi.content, mi.memory_type, mi.source,
                       mi.confidence_level, mi.topic, mi.created_at,
                       1 - (me.embedding <=> CAST(:embedding AS vector)) AS similarity
                FROM memory_items mi
                JOIN memory_embeddings me ON me.memory_item_id = mi.id
                ORDER BY me.embedding <=> CAST(:embedding AS vector)
                LIMIT :limit
            """)
            result = await self.db.execute(
                sql,
                {"embedding": embedding_str, "limit": limit},
            )

        rows = result.fetchall()
        return [
            {
                "id": str(row[0]),
                "content": row[1],
                "memory_type": row[2],
                "source": row[3],
                "confidence_level": float(row[4]) if row[4] else 0.5,
                "topic": row[5],
                "created_at": row[6].isoformat() if row[6] else None,
                "similarity": float(row[7]) if row[7] is not None else 0.0,
            }
            for row in rows
        ]

    async def verify_memory(self, memory_id: str, status: str) -> bool:
        """Mark a memory as verified, disputed, or retracted."""
        result = await self.db.execute(
            select(MemoryItem).where(MemoryItem.id == memory_id)
        )
        memory = result.scalar_one_or_none()
        if not memory:
            return False
        memory.verification_status = status
        memory.last_reviewed_at = datetime.utcnow()
        await self.db.commit()
        return True

    async def _generate_embedding(self, text: str) -> Optional[List[float]]:
        """Generate embedding via LiteLLM gateway."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{settings.litellm_base_url}/embeddings",
                    headers={
                        "Authorization": f"Bearer {settings.litellm_master_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": "text-embedding-3-small",
                        "input": text,
                    },
                    timeout=30.0,
                )
                if response.status_code == 200:
                    data = response.json()
                    return data["data"][0]["embedding"]
                else:
                    logger.warning(f"Embedding API returned {response.status_code}")
                    return None
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            return None
