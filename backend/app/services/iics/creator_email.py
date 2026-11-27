"""Creator email channel for IICS control-centre notifications.

Uses the existing OD-18/OD-19 email layer. Informational messages never create
authority; consequential actions become signed ED25519 challenge requests via
CreatorApprovalService. A plain email reply never authorises anything.
"""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional, Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.creator_communication import CreatorCommunicationService
from app.services.creatorapproval_service import CreatorApprovalService


class CreatorEmailBridge:
    """Creator-facing email notifications and approval requests for IICS."""

    def __init__(
        self,
        db: AsyncSession,
        *,
        communication: Optional[CreatorCommunicationService] = None,
        approvals: Optional[CreatorApprovalService] = None,
    ) -> None:
        self.db = db
        self._communication = communication
        self._approvals = approvals

    @property
    def communication(self) -> CreatorCommunicationService:
        if self._communication is None:
            self._communication = CreatorCommunicationService(self.db)
        return self._communication

    @property
    def approvals(self) -> CreatorApprovalService:
        if self._approvals is None:
            self._approvals = CreatorApprovalService(self.db)
        return self._approvals

    async def notify(self, update: str, context: Optional[str] = None) -> Dict[str, Any]:
        """Send an informational status update. No authority is created."""
        return dict(await self.communication.send_status(update, context=context))

    async def qa_alert(
        self,
        regressions: List[str],
        results: Optional[Sequence[Mapping[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Report QA regressions without changing any gate or model."""
        if not regressions:
            return {"status": "skipped", "reason": "no_regressions"}
        summary = "IICS QA regression gate blocked a change:\n" + "\n".join(
            f"- {item}" for item in regressions[:20]
        )
        if results:
            failed = [
                f"{row.get('benchmark')}: {row.get('score')} < {row.get('threshold')}"
                for row in results
                if not row.get("passed", True)
            ]
            if failed:
                summary += "\n\nFailed benchmarks:\n" + "\n".join(failed[:20])
        return await self.notify(summary, context="iics_qa_regression_gate")

    async def monitoring_digest(self, items: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
        """Summarise monitored public sources; informational only."""
        if not items:
            return {"status": "skipped", "reason": "no_changes"}
        lines = []
        for item in items[:20]:
            lines.append(
                f"- {item.get('target') or item.get('url') or 'unknown'}: "
                f"{item.get('status') or item.get('change') or 'updated'}"
            )
        return await self.notify(
            "IICS monitoring digest:\n" + "\n".join(lines),
            context="iics_public_source_monitoring",
        )

    async def approval_request(
        self,
        action_type: str,
        summary: str,
        *,
        target_ref: Optional[str] = None,
        consequences: Optional[List[str]] = None,
        risk_level: str = "3",
        reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Raise a signed Creator challenge and deliver it by email.

        The request stays pending until a verified ED25519 signature is
        recorded by CreatorApprovalService.decide(). This bridge never grants
        authority itself.
        """
        request = await self.approvals.create_request(
            action_type=action_type,
            summary=summary,
            consequences=list(consequences or []),
            risk_level=risk_level,
            target_ref=target_ref,
            reason=reason,
            requester="iics",
            channel="creator_email",
        )
        request_id = str(request.get("request_id") or "")
        delivery = await self.approvals.deliver_request(request_id)
        return {
            "request_id": request_id,
            "request_status": request.get("status"),
            "delivery": delivery,
            "authority_bearing": False,
            "note": "Pending signed Creator decision; email delivery alone grants no authority.",
        }
