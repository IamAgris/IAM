"""Memory routes - semantic memory retrieval with pgvector"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from app.core.database import get_db_session
from app.services.memory_service import MemoryService

router = APIRouter(prefix="/api/v1/memory", tags=["memory"])


# --- Pydantic models ---

class MemoryItemCreate(BaseModel):
    content: str
    memory_type: str = "fact"  # fact, opinion, hypothesis, preference, creative, experience
    source: Optional[str] = None
    confidence_level: float = 0.5
    topic: Optional[str] = None
    metadata: Dict[str, Any] = {}


class MemorySearch(BaseModel):
    query: str
    limit: int = 10
    memory_type: Optional[str] = None


class MemoryItemResponse(BaseModel):
    id: str
    content: str
    memory_type: str
    source: Optional[str]
    confidence_level: float
    topic: Optional[str]
    created_at: Optional[str]


# --- Routes ---

@router.get("/")
async def list_memories(
    limit: int = 50,
    memory_type: Optional[str] = None,
    db: AsyncSession = Depends(get_db_session),
):
    """List memories with optional type filter."""
    service = MemoryService(db)
    # Simple list without embedding for now; use /search for semantic
    from app.models.memory import MemoryItem
    from sqlalchemy import select
    stmt = select(MemoryItem).order_by(MemoryItem.created_at.desc()).limit(limit)
    if memory_type:
        stmt = stmt.where(MemoryItem.memory_type == memory_type)
    result = await db.execute(stmt)
    items = result.scalars().all()
    return [
        MemoryItemResponse(
            id=str(m.id),
            content=m.content,
            memory_type=m.memory_type,
            source=m.source,
            confidence_level=float(m.confidence_level) if m.confidence_level else 0.5,
            topic=m.topic,
            created_at=m.created_at.isoformat() if m.created_at else None,
        )
        for m in items
    ]


@router.post("/", response_model=MemoryItemResponse)
async def create_memory(
    item: MemoryItemCreate,
    db: AsyncSession = Depends(get_db_session),
):
    """Store a new memory item with embedding generation."""
    service = MemoryService(db)
    # Provenance is mandatory in MemoryService. Public callers may omit it, so
    # attribute those memories to the API boundary rather than failing with a
    # 500 after passing schema validation.
    source = item.source.strip() if item.source and item.source.strip() else "user-api"
    result = await service.store_memory(
        content=item.content,
        memory_type=item.memory_type,
        source=source,
        confidence=item.confidence_level,
        topic=item.topic,
        metadata_=item.metadata,
    )
    return MemoryItemResponse(
        id=result["id"],
        content=result["content"],
        memory_type=result["memory_type"],
        source=result["source"],
        confidence_level=result["confidence_level"],
        topic=result["topic"],
        created_at=result["created_at"],
    )


@router.post("/search")
async def search_memory(
    search: MemorySearch,
    db: AsyncSession = Depends(get_db_session),
):
    """Semantic search using pgvector cosine similarity."""
    service = MemoryService(db)
    results = await service.search_memory(
        query=search.query,
        limit=search.limit,
        memory_type=search.memory_type,
    )
    return {"query": search.query, "results": results, "count": len(results)}


@router.post("/verify/{memory_id}")
async def verify_memory(
    memory_id: str,
    status: str,  # verified, disputed, retracted
    db: AsyncSession = Depends(get_db_session),
):
    """Mark a memory as verified, disputed, or retracted."""
    if status not in ("verified", "disputed", "retracted"):
        raise HTTPException(status_code=400, detail="Invalid status")
    service = MemoryService(db)
    success = await service.verify_memory(memory_id, status)
    if not success:
        raise HTTPException(status_code=404, detail="Memory not found")
    return {"memory_id": memory_id, "verification_status": status}
