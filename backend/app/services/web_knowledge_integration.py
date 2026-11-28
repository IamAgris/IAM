"""Web Knowledge Integration — governed research-to-knowledge bridge (Doc 29 P4).

Browser research never becomes trusted knowledge automatically. A claim becomes
a proposal only after evidence-backed source verification and a legal gate;
promotion requires signed Creator authority and still leaves the actual write
to the caller.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.web_knowledge import BrowserKnowledgeProposal
from app.services.browser_evidence_service import BrowserEvidenceService
from app.services.creatorapproval_service import CreatorApprovalService
from app.services.iplci.service import IPLCIService

PROMOTION_ACTION = "knowledge.promote"
ALLOWED_DECISIONS = {"ALLOWED", "PERMITTED"}


class WebKnowledgeIntegrationError(PermissionError):
    """Raised when research cannot be proposed or promoted safely."""


def domain_of(url: str) -> str:
    try:
        return (urlparse(str(url)).hostname or "").lower()
    except ValueError:
        return ""


class WebKnowledgeIntegrationService:
    """Evidence-backed proposals with legal gating and explicit promotion."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.evidence = BrowserEvidenceService(db)

    async def verify_sources(
        self,
        claim: str,
        sources: List[Dict[str, Any]],
        task_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Cross-check sources against preserved browser evidence."""
        if not claim or not sources:
            return {
                "verified": False, "state": "unverified",
                "reason": "claim and at least one source are required",
                "independent_count": 0, "evidence_refs": [], "domains": [],
            }
        preserved = await self.evidence.evidence_for(task_id) if task_id else []
        evidence_ids = {item["evidence_id"] for item in preserved}
        evidence_urls = {str(item.get("url") or "") for item in preserved}
        confirmed = [
            source for source in sources
            if str(source.get("evidence_id") or "") in evidence_ids
            or str(source.get("url") or "") in evidence_urls
        ]
        domains = {domain_of(str(source.get("url") or "")) for source in confirmed}
        domains.discard("")
        independent = len(domains)
        state = (
            "verified" if independent >= 2
            else "single_source" if independent == 1
            else "unverified"
        )
        reasons = []
        if not confirmed:
            reasons.append("no source has preserved browser evidence")
        if independent < 2:
            reasons.append("fewer than two independent source domains")
        return {
            "verified": state == "verified",
            "state": state,
            "reason": "; ".join(reasons) or "independent evidence-backed sources agree",
            "independent_count": independent,
            "evidence_refs": [str(s.get("evidence_id")) for s in confirmed
                              if s.get("evidence_id")],
            "domains": sorted(domains),
        }

    async def propose(
        self,
        *,
        task_id: str,
        claim: str,
        sources: List[Dict[str, Any]],
        created_by: str,
        legal_source_id: Optional[str] = None,
        jurisdiction: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a proposal; never write to memory or knowledge here."""
        verification = await self.verify_sources(claim, sources, task_id)
        legal = await IPLCIService(self.db).gate_check(  # type: ignore[arg-type]
            {
                "operation": "store",
                "source_id": legal_source_id,
                "jurisdiction": jurisdiction,
            },
            actor=created_by,
        )
        legal_decision = str(legal.get("decision") or "BLOCKED")
        permitted = legal_decision in ALLOWED_DECISIONS
        status = (
            "pending_review"
            if permitted and verification["state"] == "verified"
            else "quarantined"
        )
        row = BrowserKnowledgeProposal(
            task_id=str(task_id),
            claim=str(claim),
            source_urls=[str(s.get("url") or "") for s in sources],
            evidence_refs=verification["evidence_refs"],
            independent_source_count=verification["independent_count"],
            verification_state=verification["state"],
            legal_decision=legal_decision,
            status=status,
            created_by=str(created_by),
            payload={
                "verification": verification,
                "legal": {
                    "decision": legal_decision,
                    "decision_class": legal.get("decision_class"),
                    "reason": legal.get("reason"),
                    "policy_version": legal.get("policy_version"),
                },
                "note": "proposal only; no knowledge or model write performed",
            },
        )
        self.db.add(row)
        await self.db.flush()
        await self.db.commit()
        if task_id:
            await self.evidence.append_audit(
                task_id, actor=created_by, action="browser.knowledge.propose",
                target=str(row.id),
                outcome={"status": status, "verification": verification["state"],
                         "legal_decision": legal_decision},
            )
        return self._row_dict(row)

    async def get(self, proposal_id: str) -> Dict[str, Any]:
        row = await self._proposal(proposal_id)
        return self._row_dict(row)

    async def list(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        result = await self.db.execute(select(BrowserKnowledgeProposal))
        rows = result.scalars().all() if hasattr(result, "scalars") else result.all()
        if status:
            rows = [row for row in rows if row.status == status]
        return [self._row_dict(row) for row in rows]  # type: ignore[arg-type]

    async def approve(self, proposal_id: str, actor: str) -> Dict[str, Any]:
        """Signed Creator approval produces a promotion payload, not a silent write."""
        auth = await CreatorApprovalService(self.db).check_authorization(
            PROMOTION_ACTION, "3"
        )
        if not auth.get("authorized"):
            raise WebKnowledgeIntegrationError(
                "promoting browser research requires signed Creator authorization"
            )
        row = await self._proposal(proposal_id)
        if row.status != "pending_review":
            raise WebKnowledgeIntegrationError(
                f"cannot promote a proposal with status {row.status}"
            )
        if row.verification_state != "verified" or row.legal_decision not in ALLOWED_DECISIONS:
            raise WebKnowledgeIntegrationError(
                "proposal is not verified and legally cleared"
            )
        row.status = "approved"  # type: ignore[assignment]
        row.reviewed_by = str(actor)  # type: ignore[assignment]
        row.reviewed_at = datetime.now(timezone.utc)  # type: ignore[assignment]
        row.promotion_ref = f"proposal:{row.id}"  # type: ignore[assignment]
        await self.db.commit()
        return {
            "status": "approved",
            "promotion_ref": row.promotion_ref,
            "promotion": {
                "claim": row.claim,
                "source_urls": row.source_urls,
                "evidence_refs": row.evidence_refs,
                "authorization_id": auth.get("authorization_id"),
                "signer_id": auth.get("signer_id"),
                "note": "caller must write to knowledge explicitly; this endpoint does not",
            },
        }

    async def reject(self, proposal_id: str, actor: str, reason: str = "") -> Dict[str, Any]:
        row = await self._proposal(proposal_id)
        if row.status not in ("pending_review", "quarantined"):
            raise WebKnowledgeIntegrationError("proposal is already final")
        row.status = "rejected"  # type: ignore[assignment]
        row.reviewed_by = str(actor)  # type: ignore[assignment]
        row.reviewed_at = datetime.now(timezone.utc)  # type: ignore[assignment]
        row.payload = {**(row.payload or {}), "rejection_reason": reason[:1000]}  # type: ignore[assignment]
        await self.db.commit()
        return self._row_dict(row)

    async def _proposal(self, proposal_id: str) -> BrowserKnowledgeProposal:
        from uuid import UUID

        try:
            identifier = UUID(str(proposal_id))
        except (ValueError, TypeError) as exc:
            raise ValueError("Invalid proposal ID") from exc
        result = await self.db.execute(
            select(BrowserKnowledgeProposal).where(
                BrowserKnowledgeProposal.id == identifier
            )
        )
        row = result.scalar_one_or_none()
        if not row:
            raise ValueError("Browser knowledge proposal not found")
        return row

    @staticmethod
    def _row_dict(row: BrowserKnowledgeProposal) -> Dict[str, Any]:
        return {
            "id": str(row.id),
            "task_id": row.task_id,
            "claim": row.claim,
            "source_urls": row.source_urls,
            "evidence_refs": row.evidence_refs,
            "independent_source_count": row.independent_source_count,
            "verification_state": row.verification_state,
            "legal_decision": row.legal_decision,
            "status": row.status,
            "promotion_ref": row.promotion_ref,
            "created_by": row.created_by,
            "reviewed_by": row.reviewed_by,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "reviewed_at": row.reviewed_at.isoformat() if row.reviewed_at else None,
            "payload": row.payload,
        }
