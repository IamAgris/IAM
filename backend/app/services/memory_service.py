"""Memory service - long-term memory and knowledge management with pgvector"""

from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timezone
import uuid
import httpx
import loguru
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text, or_, update, delete, func
from app.core.config import settings
from app.models.memory import MemoryItem, MemoryEmbedding, MemoryRelationship
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
        confidence: Optional[float] = None,
        topic: Optional[str] = None,
        metadata_: Optional[Dict[str, Any]] = None,
        governance_context: Optional[Dict[str, Any]] = None,
        expires_at: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Store a new memory item with provenance tracking and embedding.

        A source is required so every memory carries provenance. Confidence is
        stored as supplied but callers should derive it from evidence, not
        assert it outright; unverified memories default to ``unverified`` status.
        """
        if not content or not content.strip():
            raise ValueError("memory content must not be empty")
        if not source:
            raise ValueError("memory source is required for provenance")

        from app.services.iplci.context import resolve_governance_context
        from app.services.iplci.gateway import get_gateway

        resolved = resolve_governance_context(governance_context)
        if resolved:
            await get_gateway().enforce_collection(
                source_id=resolved["source_id"],
                agent_id=str(resolved.get("agent_id") or "main"),
            )
        confidence_level = (
            float(confidence) if confidence is not None else 0.5
        )
        confidence_level = max(0.0, min(1.0, confidence_level))
        memory = MemoryItem(
            content=content.strip(),
            memory_type=memory_type,
            source=source,
            confidence_level=confidence_level,
            topic=topic,
            metadata_=metadata_ or {},
            expires_at=expires_at,
            verification_status="unverified",
        )
        self.db.add(memory)
        await self.db.flush()

        # Generate embedding via LiteLLM
        embedding_vector = await self._generate_embedding(content.strip())
        if embedding_vector:
            embedding = MemoryEmbedding(
                memory_item_id=memory.id,
                embedding=embedding_vector,
                model=settings.memory_embedding_model,
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
            "verification_status": memory.verification_status,
            "expires_at": memory.expires_at.isoformat() if memory.expires_at else None,
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
        """Mark a memory as verified, disputed, retracted, or expired.

        Only statuses from the check constraint are accepted. Returns False if
        the memory does not exist.
        """
        allowed = {"unverified", "verified", "disputed", "retracted", "expired"}
        if status not in allowed:
            raise ValueError(f"invalid verification status: {status}")
        result = await self.db.execute(
            select(MemoryItem).where(MemoryItem.id == memory_id)
        )
        memory = result.scalar_one_or_none()
        if not memory:
            return False
        memory.verification_status = status  # type: ignore[assignment]
        memory.last_reviewed_at = datetime.now(timezone.utc)
        await self.db.commit()
        return True

    async def expire_memories(self) -> int:
        """Mark memories whose ``expires_at`` has passed as ``expired``.

        Returns the number of memories expired in this sweep.
        """
        now = datetime.now(timezone.utc)
        result = await self.db.execute(
            update(MemoryItem)
            .where(
                MemoryItem.expires_at.is_not(None),
                MemoryItem.expires_at < now,
                MemoryItem.verification_status != "expired",
            )
            .values(verification_status="expired", last_reviewed_at=now)
            .execution_options(synchronize_session="fetch")
        )
        await self.db.commit()
        return result.rowcount or 0

    async def create_memory_relationship(
        self,
        source_memory_id: str,
        target_memory_id: str,
        relationship_type: str,
        strength: float = 1.0,
    ) -> Dict[str, Any]:
        """Record a relationship between two memories (associative substrate).

        ``relationship_type`` is caller-defined (e.g. ``supports``,
        ``contradicts``, ``derives_from``, ``related_to``). ``strength`` is
        clamped to [0, 1]. Self-relationships are rejected.
        """
        if source_memory_id == target_memory_id:
            raise ValueError("memory cannot relate to itself")
        strength = max(0.0, min(1.0, float(strength)))
        rel = MemoryRelationship(
            source_memory_id=uuid.UUID(source_memory_id),
            target_memory_id=uuid.UUID(target_memory_id),
            relationship_type=relationship_type,
            strength=strength,
        )
        self.db.add(rel)
        await self.db.commit()
        await self.db.refresh(rel)
        return {
            "id": str(rel.id),
            "source_memory_id": str(rel.source_memory_id),
            "target_memory_id": str(rel.target_memory_id),
            "relationship_type": rel.relationship_type,
            "strength": float(rel.strength),
            "created_at": rel.created_at.isoformat() if rel.created_at else None,
        }

    async def get_memory_relationships(
        self, memory_id: str, direction: str = "both"
    ) -> List[Dict[str, Any]]:
        """Traverse relationships for a memory.

        ``direction``: ``outgoing`` (this memory is source), ``incoming``
        (this memory is target), or ``both``.
        """
        uuid_id = uuid.UUID(memory_id)
        if direction == "outgoing":
            stmt = select(MemoryRelationship).where(
                MemoryRelationship.source_memory_id == uuid_id
            )
        elif direction == "incoming":
            stmt = select(MemoryRelationship).where(
                MemoryRelationship.target_memory_id == uuid_id
            )
        else:
            stmt = select(MemoryRelationship).where(
                or_(
                    MemoryRelationship.source_memory_id == uuid_id,
                    MemoryRelationship.target_memory_id == uuid_id,
                )
            )
        result = await self.db.execute(stmt)
        rows = result.scalars().all()
        out: List[Dict[str, Any]] = []
        for rel in rows:
            out.append(
                {
                    "id": str(rel.id),
                    "source_memory_id": str(rel.source_memory_id),
                    "target_memory_id": str(rel.target_memory_id),
                    "relationship_type": rel.relationship_type,
                    "strength": float(rel.strength),
                    "direction": (
                        "outgoing"
                        if rel.source_memory_id == uuid_id
                        else "incoming"
                    ),
                    "created_at": rel.created_at.isoformat() if rel.created_at else None,
                }
            )
        return out

    async def find_duplicate_memories(
        self, limit: int = 20, similarity_threshold: float = 0.92
    ) -> List[Tuple[Dict[str, Any], Dict[str, Any], float]]:
        """Find candidate duplicate memory pairs by cosine similarity.

        Returns a list of ``(memory_a, memory_b, similarity)`` tuples. Only
        non-expired memories are considered. This is a detection aid; callers
        decide whether to merge.
        """
        query_embedding = None
        # Use all embeddings pairwise via self-join on cosine distance.
        sql = text("""
            SELECT
                a.id AS a_id, a.content AS a_content, a.memory_type AS a_type,
                a.source AS a_source, a.topic AS a_topic, a.verification_status AS a_status,
                b.id AS b_id, b.content AS b_content, b.memory_type AS b_type,
                b.source AS b_source, b.topic AS b_topic, b.verification_status AS b_status,
                1 - (ae.embedding <=> be.embedding) AS similarity
            FROM memory_items a
            JOIN memory_embeddings ae ON ae.memory_item_id = a.id
            JOIN memory_items b ON b.id > a.id
            JOIN memory_embeddings be ON be.memory_item_id = b.id
            WHERE (a.expires_at IS NULL OR a.expires_at > NOW())
              AND (b.expires_at IS NULL OR b.expires_at > NOW())
              AND 1 - (ae.embedding <=> be.embedding) >= :threshold
            ORDER BY similarity DESC
            LIMIT :limit
        """)
        result = await self.db.execute(
            sql, {"threshold": similarity_threshold, "limit": limit}
        )
        rows = result.fetchall()
        out: List[Tuple[Dict[str, Any], Dict[str, Any], float]] = []
        for row in rows:
            a = {
                "id": str(row.a_id),
                "content": row.a_content,
                "memory_type": row.a_type,
                "source": row.a_source,
                "topic": row.a_topic,
                "verification_status": row.a_status,
            }
            b = {
                "id": str(row.b_id),
                "content": row.b_content,
                "memory_type": row.b_type,
                "source": row.b_source,
                "topic": row.b_topic,
                "verification_status": row.b_status,
            }
            out.append((a, b, float(row.similarity)))
        return out

    async def consolidate_memories(
        self, dry_run: bool = True
    ) -> Dict[str, Any]:
        """Consolidate memory: expire stale items and flag near-duplicates.

        When ``dry_run`` is False, expired memories are marked ``expired`` and
        duplicate pairs are recorded as ``contradicts`` relationships only when
        one is verified and the other disputed/retracted (no silent merging).
        Returns a summary of actions taken or proposed.
        """
        expired_count = await self.expire_memories() if not dry_run else 0
        duplicates = await self.find_duplicate_memories()
        linked = 0
        if not dry_run:
            for a, b, _sim in duplicates:
                a_status = a.get("verification_status")
                b_status = b.get("verification_status")
                # Link conflicting verified/disputed pairs as contradictions.
                if {a_status, b_status} & {"verified", "disputed", "retracted"}:
                    await self.create_memory_relationship(
                        a["id"], b["id"], "contradicts", strength=0.8
                    )
                    linked += 1
        return {
            "dry_run": dry_run,
            "expired_count": expired_count,
            "duplicate_pairs_found": len(duplicates),
            "contradiction_links_created": linked,
        }

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
