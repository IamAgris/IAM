"""Signed P2P skill exchange.

A published release is an envelope signed by the local node. A received release
is always an untrusted candidate: it is never activated until it has passed a
fresh security inspection and the normal Skill Forge gates.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.p2p_skills import P2PSkillCandidate
from app.models.skillforge import SkillPackage
from app.services.p2p_transport import transport
from app.services.skillforge.engine import SkillBuildRequest
from app.services.skillforge.service import SkillForgeService
from app.services.whitehat_policy import WhiteHatPolicyError


class SkillExchangeError(PermissionError):
    """Raised when a skill release cannot be safely published or accepted."""


class SkillExchangeService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.forge = SkillForgeService(db)

    @staticmethod
    def _dict(row: P2PSkillCandidate) -> Dict[str, Any]:
        return {
            "id": str(row.id),
            "envelope_id": row.envelope_id,
            "publisher": row.publisher,
            "skill_id": row.skill_id,
            "version": row.version,
            "permissions": row.permissions or [],
            "checksum": row.checksum,
            "status": row.status,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }

    async def _package(self, skill_id: str) -> SkillPackage:
        result = await self.db.execute(
            select(SkillPackage).where(SkillPackage.skill_id == skill_id)
        )
        package = result.scalar_one_or_none()
        if not package:
            raise LookupError(f"Skill not found: {skill_id}")
        return package

    async def publish(self, skill_id: str, peer_id: Optional[str] = None) -> Dict[str, Any]:
        """Broadcast a signed release of an active, checksummed skill."""
        package = await self._package(skill_id)
        if package.status != "active":
            raise SkillExchangeError("only active skills can be published to peers")
        directory = self.forge.engine.layout.current_dir(skill_id)
        skill_md = directory / "SKILL.md"
        if not skill_md.is_file():
            raise SkillExchangeError("skill instructions are missing")
        actual = self.forge.engine.layout.checksum(skill_id)
        if package.checksum and actual != package.checksum:
            raise SkillExchangeError("checksum mismatch — refusing to publish")
        payload = {
            "skill_id": package.skill_id,
            "version": package.version,
            "instructions": skill_md.read_text(encoding="utf-8")[:50000],
            "permissions": list(package.permissions or []),
            "checksum": actual,
        }
        if peer_id:
            result = await transport.send_to(peer_id, "skill_release", payload)
        else:
            result = await transport.broadcast("skill_release", payload)
        return result

    async def receive(
        self, envelope: Dict[str, Any], peer_secret: Optional[str] = None
    ) -> Dict[str, Any]:
        """Verify an envelope and store its skill release as an untrusted candidate."""
        try:
            verdict = transport.accept(envelope, peer_secret=peer_secret)
        except (WhiteHatPolicyError, TypeError, ValueError) as exc:
            raise SkillExchangeError(str(exc)) from exc
        if not verdict.get("accepted"):
            raise SkillExchangeError(str(verdict.get("reason", "envelope rejected")))
        if envelope.get("topic") != "skill_release":
            raise SkillExchangeError("envelope is not a skill release")

        data = envelope.get("payload") or {}
        required = ("skill_id", "version", "instructions", "permissions")
        if not all(k in data for k in required):
            raise SkillExchangeError("skill release is missing required fields")
        if not isinstance(data["permissions"], list):
            raise SkillExchangeError("permissions must be a list")

        existing = await self.db.execute(
            select(P2PSkillCandidate).where(
                P2PSkillCandidate.envelope_id == envelope["id"]
            )
        )
        if existing.scalar_one_or_none():
            raise SkillExchangeError("duplicate skill release")

        candidate = P2PSkillCandidate(
            envelope_id=envelope["id"],
            publisher=str(envelope.get("sender")),
            skill_id=str(data["skill_id"]),
            version=str(data["version"]),
            instructions=str(data["instructions"])[:50000],
            permissions=[str(p) for p in data["permissions"]],
            checksum=data.get("checksum"),
        )
        self.db.add(candidate)
        await self.db.commit()
        await self.db.refresh(candidate)
        return self._dict(candidate) | {"status": "candidate_untrusted"}

    async def candidates(self) -> List[Dict[str, Any]]:
        result = await self.db.execute(select(P2PSkillCandidate).order_by(P2PSkillCandidate.created_at.desc()))
        return [self._dict(row) for row in result.scalars().all()]

    async def _candidate(self, candidate_id: str) -> P2PSkillCandidate:
        result = await self.db.execute(
            select(P2PSkillCandidate).where(P2PSkillCandidate.id == candidate_id)
        )
        candidate = result.scalar_one_or_none()
        if not candidate:
            raise LookupError(f"Skill candidate not found: {candidate_id}")
        return candidate

    async def approve(self, candidate_id: str) -> Dict[str, Any]:
        """Re-inspect a candidate and create a gated imported skill from it."""
        candidate = await self._candidate(candidate_id)
        if candidate.status != "candidate":
            raise SkillExchangeError(f"candidate is already {candidate.status}")

        findings = self.forge.engine.security.scan_text(
            candidate.instructions, "SKILL.md"
        )
        if self.forge.engine.security.has_blocking_findings(findings):
            raise SkillExchangeError("candidate failed security inspection")

        suffix = uuid4().hex[:8]
        leaf = "".join(c for c in candidate.skill_id.split(".")[-1] if c.isalnum() or c in "_-") or "skill"
        imported_id = f"iam.imported.community.{leaf}_{suffix}"
        request = SkillBuildRequest(
            skill_id=imported_id,
            name=f"P2P candidate {suffix}",
            version=candidate.version,
            description=f"Untrusted candidate received from {candidate.publisher}",
            classification="sensitive",
            permissions=candidate.permissions,
            requires_creator_approval=True,
            instructions=candidate.instructions,
            provider="community",
            created_by="iam",
            change_note="received via signed P2P skill exchange",
        )
        created = await self.forge.create(request)
        candidate.status = "approved"
        candidate.resolved_at = datetime.now(timezone.utc)
        await self.db.commit()
        return {
            "candidate_id": str(candidate.id),
            "skill_id": created["skill_id"],
            "status": created["status"],
            "requires_creator_approval": True,
        }

    async def reject(self, candidate_id: str) -> Dict[str, Any]:
        candidate = await self._candidate(candidate_id)
        candidate.status = "rejected"
        candidate.resolved_at = datetime.now(timezone.utc)
        await self.db.commit()
        return {"candidate_id": str(candidate.id), "status": "rejected"}
