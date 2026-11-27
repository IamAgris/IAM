"""Memory service - long-term memory and knowledge management with pgvector"""

from typing import Optional, Dict, Any, List
from datetime import datetime
import uuid
import httpx
import loguru
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text, or_
from app.core.config import settings
from app.models.memory import MemoryItem, MemoryEmbedding
from app.models.security import AuditEvent
from app.services.source_identity import node_id_for_url
from urllib.parse import urlparse

logger = loguru.logger


async def _emit_recall(db, **details: Any) -> None:
    """Emit a privacy-filtered recall signal to the durable activity stream."""
    db.add(
        AuditEvent(
            event_type="memory.retrieved",
            actor="memory-service",
            target="memory",
            details=details,
        )
    )
    await db.commit()


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
        governance_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Store a new memory item with provenance tracking and embedding."""
        from app.services.iplci.context import resolve_governance_context
        from app.services.iplci.gateway import get_gateway

        resolved = resolve_governance_context(governance_context)
        if resolved:
            await get_gateway().enforce_collection(
                source_id=resolved["source_id"],
                agent_id=str(resolved.get("agent_id") or "main"),
            )
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
            # Fallback keyword recall when no embedding model is configured.
            # Still produces a real recall event with provenance fingerprints.
            result = await self.db.execute(
                select(MemoryItem)
                .where(
                    or_(
                        MemoryItem.content.ilike(f"%{query}%"),
                        MemoryItem.topic.ilike(f"%{query}%"),
                    )
                )
                .limit(limit)
            )
            rows = [
                (
                    item.id, item.content, item.memory_type, item.source,
                    item.confidence_level, item.topic, item.created_at, 0.0,
                )
                for item in result.scalars().all()
            ]
            await self._emit_recall_from_rows(rows)
            return [
                {
                    "id": str(row[0]),
                    "content": row[1],
                    "memory_type": row[2],
                    "source": row[3],
                    "confidence_level": float(row[4]) if row[4] else 0.5,
                    "topic": row[5],
                    "created_at": row[6].isoformat() if row[6] else None,
                    "similarity": 0.0,
                }
                for row in rows
            ]

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
        await self._emit_recall_from_rows(rows)

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

    async def _emit_recall_from_rows(self, rows) -> None:
        """Emit only counts and source fingerprints — never memory content."""
        if not rows:
            return
        public_nodes = []
        for row in rows:
            source = row[3]
            if isinstance(source, str) and source.startswith(("http://", "https://")):
                public_nodes.append(
                    {
                        "node_id": node_id_for_url(source),
                        "domain": urlparse(source).netloc,
                    }
                )
        await _emit_recall(
            self.db,
            label="Retrieving memory",
            result_count=len(rows),
            memory_class="public_research" if public_nodes else "private",
            nodes=public_nodes[:6],
        )

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
        """Generate an embedding locally; never call a paid embedding provider.

        OD-04/free-models-only: semantic recall is optional. When Ollama or the
        local embedding tag is unavailable, callers fall back to deterministic
        keyword recall and record that similarity was not measured.
        """
        if settings.memory_embedding_provider != "local" or not settings.ollama_enabled:
            return None
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{settings.ollama_base_url.rstrip('/')}/api/embed",
                    json={"model": settings.memory_embedding_model, "input": text},
                )
            if response.status_code != 200:
                logger.warning(f"Local embedding provider returned {response.status_code}")
                return None
            data = response.json()
            vectors = data.get("embeddings") or (
                [data["embedding"]] if data.get("embedding") else []
            )
            return [float(value) for value in vectors[0]] if vectors else None
        except Exception as exc:
            logger.debug(f"Local embedding unavailable: {exc}")
            return None
