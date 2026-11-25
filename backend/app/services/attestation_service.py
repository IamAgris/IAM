"""Protected-core integrity, node attestation and signed sync (OD-05/11/13/26).

A signed attestation is evidence, never proof: an operator with host control
can hide modifications. Every response states confidence and evidence rather
than claiming certainty.
"""

import base64
import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.integrity import IntegrityManifest, NodeAttestation, SyncObject
from app.models.sdk import RegisteredNode
from app.models.security import AuditEvent

BACKEND_ROOT = Path(__file__).resolve().parents[2]

PROTECTED_PATHS = (
    "app/main.py",
    "app/core/config.py",
    "app/core/database.py",
    "app/api/deps.py",
    "app/api/middleware/auth_middleware.py",
    "app/services/creatorapproval_service.py",
    "app/services/attestation_service.py",
    "app/workers/autonomy_worker.py",
    "app/models/governance.py",
)

ATTESTATION_MAX_AGE_SECONDS = 300


class AttestationError(ValueError):
    pass


def canonical_payload(payload: Dict[str, Any]) -> bytes:
    return json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def content_hash(payload: Any) -> str:
    return hashlib.sha256(canonical_payload(payload)).hexdigest()


def _parse_time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


class AttestationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ---------------------------------------------------------------- integrity

    def measure_core(self) -> Dict[str, Any]:
        files: Dict[str, str] = {}
        for relative in PROTECTED_PATHS:
            path = BACKEND_ROOT / relative
            if not path.exists():
                files[relative] = "missing"
                continue
            files[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
        return {"files": files, "root_hash": content_hash(files)}

    async def create_manifest(self, actor: str = "creator") -> Dict[str, Any]:
        """Explicitly approve the current measurement as the known-good baseline."""
        measured = self.measure_core()
        previous = await self.db.execute(
            select(IntegrityManifest).where(IntegrityManifest.is_active.is_(True))
        )
        for manifest in previous.scalars().all():
            manifest.is_active = False
        record = IntegrityManifest(
            version=f"manifest-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
            root_hash=measured["root_hash"],
            manifest=measured["files"],
            signed_by=actor,
            is_active=True,
        )
        self.db.add(record)
        self.db.add(
            AuditEvent(
                event_type="integrity_manifest_approved",
                actor=actor,
                target=record.version,
                details={"root_hash": record.root_hash, "files": len(measured["files"])},
            )
        )
        await self.db.commit()
        await self.db.refresh(record)
        return {
            "id": str(record.id),
            "version": record.version,
            "root_hash": record.root_hash,
            "signed_by": record.signed_by,
        }

    async def integrity_status(self) -> Dict[str, Any]:
        result = await self.db.execute(
            select(IntegrityManifest)
            .where(IntegrityManifest.is_active.is_(True))
            .order_by(IntegrityManifest.created_at.desc())
        )
        manifest = result.scalar_one_or_none()
        current = self.measure_core()
        if not manifest:
            return {
                "known_good_manifest": None,
                "current_root_hash": current["root_hash"],
                "matches": None,
                "confidence": "unmeasured",
                "evidence": ["No known-good manifest has been approved yet."],
                "claim": "best_effort_not_certainty",
            }
        expected = manifest.manifest or {}
        differences = [
            path
            for path in sorted(set(expected) | set(current["files"]))
            if expected.get(path) != current["files"].get(path)
        ]
        return {
            "known_good_manifest": manifest.version,
            "expected_root_hash": manifest.root_hash,
            "current_root_hash": current["root_hash"],
            "matches": not differences,
            "differences": differences,
            "confidence": "measured_directly_on_this_host",
            "evidence": [
                "Local protected files were hashed at request time.",
                "A signed attestation from another host is evidence, not proof.",
            ],
            "claim": "best_effort_not_certainty",
        }

    # -------------------------------------------------------------- attestation

    async def attest_node(
        self, node_id: str, submission: Dict[str, Any], actor: str = "sdk"
    ) -> Dict[str, Any]:
        node_result = await self.db.execute(
            select(RegisteredNode).where(RegisteredNode.id == node_id)
        )
        node = node_result.scalar_one_or_none()
        if not node:
            raise AttestationError("node not found")

        payload = dict(submission.get("payload") or submission)
        signature_b64 = str(submission.get("signature") or payload.pop("signature", ""))
        if not signature_b64:
            raise AttestationError("signature is required")

        for field in ("node_id", "public_key", "core_hash", "timestamp", "nonce"):
            if not payload.get(field):
                raise AttestationError(f"{field} is required")
        if payload["node_id"] != node_id:
            raise AttestationError("attestation node_id does not match the route")

        age = datetime.now(timezone.utc) - _parse_time(str(payload["timestamp"]))
        if abs(age.total_seconds()) > ATTESTATION_MAX_AGE_SECONDS:
            raise AttestationError("attestation timestamp is outside the accepted window")

        previous = await self.db.execute(
            select(NodeAttestation)
            .where(NodeAttestation.node_id == node.id)
            .order_by(NodeAttestation.created_at.desc())
        )
        known = previous.scalars().all()
        if any(str(p.payload.get("nonce")) == str(payload["nonce"]) for p in known):
            raise AttestationError("attestation nonce was already used")
        if known and known[0].public_key != payload["public_key"]:
            raise AttestationError("node public key changed; re-registration required")

        try:
            key = Ed25519PublicKey.from_public_bytes(
                base64.b64decode(str(payload["public_key"]), validate=True)
            )
            key.verify(
                base64.b64decode(signature_b64, validate=True),
                canonical_payload(payload),
            )
        except (ValueError, InvalidSignature, TypeError) as exc:
            raise AttestationError("invalid Ed25519 attestation signature") from exc

        manifest_result = await self.db.execute(
            select(IntegrityManifest).where(IntegrityManifest.is_active.is_(True))
        )
        manifest = manifest_result.scalar_one_or_none()
        if not manifest:
            raise AttestationError("no approved known-good manifest exists")

        matches = payload["core_hash"] == manifest.root_hash
        outcome = "trusted" if matches else "restricted"

        record = NodeAttestation(
            node_id=node.id,
            public_key=str(payload["public_key"]),
            core_hash=str(payload["core_hash"]),
            platform_hash=payload.get("platform_hash"),
            signature=signature_b64,
            payload=payload,
            verified=True,
            result=outcome,
        )
        node.trust_level = outcome
        node.is_active = matches
        if not matches:
            node.status = "modified"
        self.db.add(record)
        self.db.add(
            AuditEvent(
                event_type="node_attested",
                actor=actor,
                target=node.name,
                details={
                    "result": outcome,
                    "core_hash_matches": matches,
                    "confidence": "signature_verified_core_hash_compared",
                },
            )
        )
        await self.db.commit()
        return {
            "node_id": node_id,
            "trust_level": outcome,
            "is_active": node.is_active,
            "signature_verified": True,
            "core_hash_matches": matches,
            "confidence": "signature_verified_core_hash_compared",
            "claim": "best_effort_not_certainty",
            "attestation_id": str(record.id),
        }

    async def restricted_report(
        self, node_id: str, reason: str, actor: str = "sdk"
    ) -> Dict[str, Any]:
        """A modified deployment downgrades itself and reports status (OD-13)."""
        node = await self._node(node_id)
        node.trust_level = "restricted"
        node.is_active = False
        node.status = "modified"
        self.db.add(
            AuditEvent(
                event_type="node_restricted_report",
                actor=actor,
                target=node.name,
                details={"reason": reason[:1000]},
            )
        )
        await self.db.commit()
        return {
            "node_id": node_id,
            "trust_level": "restricted",
            "is_active": False,
            "privileges": "reporting_only",
        }

    async def revoke(self, node_id: str, actor: str = "creator") -> Dict[str, Any]:
        node = await self._node(node_id)
        node.trust_level = "revoked"
        node.is_active = False
        self.db.add(
            AuditEvent(
                event_type="node_revoked",
                actor=actor,
                target=node.name,
                details={},
            )
        )
        await self.db.commit()
        return {"node_id": node_id, "trust_level": "revoked", "is_active": False}

    # -------------------------------------------------------------------- sync

    async def publish_object(
        self, submission: Dict[str, Any], actor: str = "sdk"
    ) -> Dict[str, Any]:
        """Accept a signed knowledge object from a currently trusted node."""
        publisher = str(submission.get("publisher_node_id") or "")
        object_type = str(submission.get("object_type") or "")
        payload_data = submission.get("payload")
        signature_b64 = str(submission.get("signature") or "")
        if not publisher or not object_type or payload_data is None or not signature_b64:
            raise AttestationError(
                "publisher_node_id, object_type, payload and signature are required"
            )

        attestation_result = await self.db.execute(
            select(NodeAttestation)
            .where(
                NodeAttestation.node_id == publisher,
                NodeAttestation.verified.is_(True),
                NodeAttestation.result == "trusted",
            )
            .order_by(NodeAttestation.created_at.desc())
        )
        attestation = attestation_result.scalar_one_or_none()
        if not attestation:
            raise AttestationError("publisher is not a trusted node")

        digest = content_hash(payload_data)
        signed = canonical_payload(
            {
                "publisher_node_id": publisher,
                "object_type": object_type,
                "content_hash": digest,
            }
        )
        try:
            Ed25519PublicKey.from_public_bytes(
                base64.b64decode(attestation.public_key, validate=True)
            ).verify(base64.b64decode(signature_b64, validate=True), signed)
        except (ValueError, InvalidSignature, TypeError) as exc:
            raise AttestationError("invalid signature on sync object") from exc

        record = SyncObject(
            publisher_node_id=attestation.node_id,
            object_type=object_type,
            content_hash=digest,
            payload=payload_data,
            signature=signature_b64,
            verified=True,
        )
        self.db.add(record)
        self.db.add(
            AuditEvent(
                event_type="sync_object_received",
                actor=actor,
                target=publisher,
                details={"object_type": object_type, "content_hash": digest},
            )
        )
        await self.db.commit()
        await self.db.refresh(record)
        return {
            "id": str(record.id),
            "content_hash": digest,
            "verified": True,
            "untrusted_data": True,
        }

    async def list_objects(self, since: Optional[str] = None) -> List[Dict[str, Any]]:
        query = select(SyncObject)
        if since:
            query = query.where(SyncObject.created_at >= _parse_time(since))
        result = await self.db.execute(query.order_by(SyncObject.created_at.desc()))
        return [
            {
                "id": str(obj.id),
                "publisher_node_id": str(obj.publisher_node_id),
                "object_type": obj.object_type,
                "content_hash": obj.content_hash,
                "payload": obj.payload,
                "verified": obj.verified,
                "untrusted_data": True,
                "created_at": obj.created_at.isoformat() if obj.created_at else None,
            }
            for obj in result.scalars().all()
        ]

    async def sync_status(self) -> Dict[str, Any]:
        result = await self.db.execute(select(SyncObject))
        count = len(result.scalars().all())
        return {
            "objects": count,
            "mode": "store_and_forward_ready",
            "data_trust": "untrusted_until_locally_verified",
        }

    async def _node(self, node_id: str) -> RegisteredNode:
        result = await self.db.execute(
            select(RegisteredNode).where(RegisteredNode.id == node_id)
        )
        node = result.scalar_one_or_none()
        if not node:
            raise AttestationError("node not found")
        return node
