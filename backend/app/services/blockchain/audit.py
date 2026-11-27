"""Append-only, hash-chained blockchain audit records (proposed Doc 33 §8).

Existing ``AuditEvent`` remains the general audit stream; blockchain entries are
written to both, with the chain hash stored in ``AuditEvent.details``. The database
trigger in migration 054 rejects UPDATE/DELETE. Secret-shaped fields are removed
before any payload is persisted.
"""

import hashlib
import json
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.security import AuditEvent
from app.models.web3 import BlockchainAuditLog
from app.services.blockchain.providers.base import ProviderDenied, require_flag

GENESIS_HASH = "0" * 64
REDACTED = "[redacted]"
SECRET_MARKERS = (
    "secret", "private", "password", "macaroon", "rune", "cookie", "seed",
    "token", "mnemonic", "credential",
)


def redact(value: Any) -> Any:
    """Remove secret-shaped keys from a nested payload before persistence."""
    if isinstance(value, dict):
        return {
            key: (REDACTED if any(m in str(key).lower() for m in SECRET_MARKERS) else redact(item))
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [redact(item) for item in value]
    return value


def canonical_bytes(payload: Dict[str, Any]) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def entry_hash(
    *, seq: int, prev_hash: str, event_type: str, actor: str,
    target: Optional[str], approval_id: Optional[str], details: Dict[str, Any],
) -> str:
    payload = {
        "seq": seq,
        "prev_hash": prev_hash,
        "event_type": event_type,
        "actor": actor,
        "target": target or "",
        "approval_id": approval_id or "",
        "details": redact(details),
    }
    return hashlib.sha256(canonical_bytes(payload)).hexdigest()


class BlockchainAuditService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def append(
        self,
        *,
        event_type: str,
        actor: str,
        target: Optional[str] = None,
        approval_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        require_flag(settings.web3_audit_enabled, "blockchain audit logging is disabled")
        if not event_type or not actor:
            raise ProviderDenied("event_type and actor are required")

        result = await self.db.execute(select(BlockchainAuditLog))
        rows = result.scalars().all()
        last = max(rows, key=lambda row: row.seq) if rows else None
        seq = int(last.seq) + 1 if last else 1
        prev_hash = last.entry_hash if last else GENESIS_HASH
        safe_details = redact(details or {})
        digest = entry_hash(
            seq=seq, prev_hash=prev_hash, event_type=event_type, actor=actor,
            target=target, approval_id=approval_id, details=safe_details,
        )
        entry = BlockchainAuditLog(
            seq=seq,
            prev_hash=prev_hash,
            entry_hash=digest,
            event_type=event_type,
            actor=actor,
            target=target,
            approval_id=approval_id,
            details=safe_details,
        )
        self.db.add(entry)
        await self.db.flush()
        self.db.add(
            AuditEvent(
                event_type=event_type,
                actor=actor,
                target=target,
                details={
                    **safe_details,
                    "approval_id": approval_id,
                    "audit_seq": seq,
                    "entry_hash": digest,
                    "chain": "blockchain_audit_log",
                },
            )
        )
        await self.db.commit()
        return {"seq": seq, "entry_hash": digest, "prev_hash": prev_hash}

    async def verify(self) -> Dict[str, Any]:
        result = await self.db.execute(select(BlockchainAuditLog))
        rows = sorted(result.scalars().all(), key=lambda row: row.seq)
        issues: List[str] = []
        expected_prev = GENESIS_HASH
        for index, row in enumerate(rows, start=1):
            if int(row.seq) != index:
                issues.append(f"sequence gap or duplicate at {row.seq} (expected {index})")
            if row.prev_hash != expected_prev:
                issues.append(f"broken chain link at seq {row.seq}")
            digest = entry_hash(
                seq=int(row.seq), prev_hash=str(row.prev_hash),
                event_type=row.event_type, actor=row.actor, target=row.target,
                approval_id=row.approval_id, details=row.details or {},
            )
            if digest != row.entry_hash:
                issues.append(f"hash mismatch at seq {row.seq}")
            expected_prev = row.entry_hash
        return {
            "verified": not issues,
            "entries": len(rows),
            "issues": issues,
        }
