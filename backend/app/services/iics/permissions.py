"""IICS permission model (gap closure §2.0).

Free lawful public access is autonomous: InternetAccessService permits the
exploration class, and the OD-48 legal gateway decides rights. Creator approval
is required only for consequential actions or a fail-closed legal decision.
No permission is granted by the model to itself.
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, Mapping, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.internetaccess_service import InternetAccessService
from app.services.iplci.service import IPLCIService

CONSEQUENTIAL_ACTIONS = frozenset(
    {
        "send_message",
        "register_account",
        "publish_content",
        "spend_money",
        "access_private_service",
        "join_community",
        "uwai_upload_file",
        "uwai_computer_use",
    }
)

OPERATION_BY_ACTION: Dict[str, str] = {
    "browse_public": "analyse",
    "search_web": "analyse",
    "read_public_content": "read",
    "download_public_file": "read",
    "call_public_api": "analyse",
    "send_message": "disclose",
    "publish_content": "distribute",
    "spend_money": "commercialise",
    "register_account": "disclose",
    "access_private_service": "disclose",
}

BLOCKING_DECISIONS = frozenset({"BLOCKED", "QUARANTINED", "REVOKED", "EXPIRED"})
HIGH_CLASSES = frozenset({"HIGH", "CRITICAL"})


class PermissionGate:
    """Combine internet permissions with the mandatory IPLCI legal gate."""

    def __init__(
        self,
        db: AsyncSession,
        *,
        internet_service: Optional[InternetAccessService] = None,
        legal_service: Optional[IPLCIService] = None,
    ) -> None:
        self.db = db
        self._internet = internet_service
        self._legal = legal_service

    @property
    def internet(self) -> InternetAccessService:
        if self._internet is None:
            self._internet = InternetAccessService(self.db)
        return self._internet

    @property
    def legal(self) -> IPLCIService:
        if self._legal is None:
            self._legal = IPLCIService(db=self.db)
        return self._legal

    @staticmethod
    def source_id_for(url: str) -> str:
        return str(uuid.uuid5(uuid.NAMESPACE_URL, url))

    async def _ensure_source(self, url: str) -> str:
        """Register a conservative public-web source in the legal store once.

        OPEN_RESEARCH with a commercial-licence posture permits read/analyse
        while leaving store/train unknown — missing permission is not approval.
        """
        source_id = self.source_id_for(url)
        existing = await self.legal.store.get_source(source_id)
        if existing:
            return source_id
        await self.legal.register_source(
            {
                "id": source_id,
                "uri": url,
                "rights_status": "COMMERCIAL_LICENCE",
                "source_class": "OPEN_RESEARCH",
                "acquisition_method": "public_web",
                "attribution_required": True,
                "permission_evidence": "publicly accessible page; rights subject to law",
            },
            actor="iics",
        )
        return source_id

    def _deny(self, reason: str, *, approval_required: bool = False, **extra: Any) -> Dict[str, Any]:
        result = {
            "permitted": False,
            "approval_required": approval_required,
            "reason": reason,
            "source": "legal_gateway",
        }
        result.update(extra)
        return result

    async def authorize(
        self,
        action_type: str,
        url: Optional[str] = None,
        *,
        purpose: str = "public research",
        jurisdiction: Optional[str] = None,
        source_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Return a combined permission decision for one external action."""
        internet = await self.internet.check_permission(action_type)
        if not internet.get("permitted"):
            return self._deny(
                f"action '{action_type}' is not autonomously permitted",
                approval_required=True,
                internet_permission=internet,
            )

        operation = OPERATION_BY_ACTION.get(action_type, "analyse")
        legal_source_id = source_id
        if not legal_source_id and url:
            try:
                legal_source_id = await self._ensure_source(url)
            except Exception:
                return self._deny("legal source registration unavailable", approval_required=True)
        if not legal_source_id:
            return self._deny("legal source required", approval_required=True)

        payload: Mapping[str, Any] = {
            "agent_id": "iics",
            "operation": operation,
            "source_id": legal_source_id,
            "jurisdiction": jurisdiction,
            "purpose": purpose,
            "context": {"action_type": action_type, "url": url},
        }
        try:
            legal = await self.legal.gate_check(payload, actor="iics")
        except Exception:
            return self._deny("legal gateway unavailable", approval_required=True)

        if legal.get("error_code") or legal.get("decision") in BLOCKING_DECISIONS:
            return self._deny(
                str(legal.get("reason") or legal.get("error_code") or "legal gateway denied"),
                approval_required=True,
                legal_decision=legal,
            )
        if (
            legal.get("reviewer_required")
            or str(legal.get("decision_class", "")).upper() in HIGH_CLASSES
            or action_type in CONSEQUENTIAL_ACTIONS
        ):
            return self._deny(
                "consequential action requires Creator approval",
                approval_required=True,
                legal_decision=legal,
            )

        return {
            "permitted": True,
            "approval_required": False,
            "source": "legal_gateway",
            "operation": operation,
            "decision": legal.get("decision"),
            "decision_class": legal.get("decision_class"),
            "conditions": list(legal.get("conditions") or []),
            "legal_audit_event_id": legal.get("audit_event_id"),
            "rights_evaluated": dict(legal.get("rights_evaluated") or {}),
        }
