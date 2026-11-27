"""Mandatory legal-policy enforcement gateway (CE-02, P6).

Every permission-controlled execution crosses this gateway. There is no path
from an agent, sub-agent, plugin, external model or self-improvement workflow
to an execution surface that bypasses it. The gateway fails closed when the
policy, the assessment or the store is unavailable.
"""

from __future__ import annotations

from typing import Any, Dict, Mapping, Optional

from app.services.iplci import policy
from app.services.iplci.service import IPLCIService

_ALLOWED = ("APPROVED", "CONDITIONAL")


class GovernanceRefusal(Exception):
    """Raised when an operation is not permitted under IPLCI policy."""

    def __init__(
        self,
        code: str,
        decision: str,
        decision_class: str,
        message: str,
        audit_event_id: Optional[str] = None,
    ):
        super().__init__(message)
        self.code = code
        self.decision = decision
        self.decision_class = decision_class
        self.audit_event_id = audit_event_id


class ComplianceGateway:
    def __init__(self, service: Optional[IPLCIService] = None):
        self.service = service or IPLCIService()
        self._policy: Optional[Dict[str, Any]] = None

    def set_policy(self, document: Mapping[str, Any]) -> Dict[str, Any]:
        if not policy.verify_policy(document):
            raise policy.PolicyError("IPLCI_POLICY_INVALID", "policy signature or safeguards invalid")
        self._policy = dict(document)
        return self._policy

    def active_policy(self) -> Optional[Dict[str, Any]]:
        return self._policy

    def _verify_policy(self) -> None:
        if self._policy is None:
            raise GovernanceRefusal(
                "IPLCI_POLICY_UNAVAILABLE", "BLOCKED", "CRITICAL",
                "no active signed compliance policy; enforcement fails closed",
            )
        if not policy.verify_policy(self._policy):
            raise GovernanceRefusal(
                "IPLCI_POLICY_INVALID", "BLOCKED", "CRITICAL",
                "active compliance policy is invalid or tampered with",
            )

    @staticmethod
    def _refuse(result: Mapping[str, Any], operation: str) -> None:
        decision = str(result.get("decision") or "BLOCKED")
        if decision in _ALLOWED and result.get("eligible", True):
            return
        missing = result.get("missing") or result.get("blockers") or []
        detail = ", ".join(str(item) for item in missing) if missing else (
            str(result.get("reason")) if result.get("reason") else decision
        )
        raise GovernanceRefusal(
            str(result.get("error_code") or "IPLCI_DENIED"),
            decision,
            str(result.get("decision_class") or "UNKNOWN"),
            f"{operation} refused: {detail}",
            result.get("audit_event_id"),
        )

    async def enforce(
        self,
        operation: str,
        *,
        source_id: Optional[str] = None,
        agent_id: str = "main",
        jurisdiction: Optional[str] = None,
        resource_id: Optional[str] = None,
        purpose: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generic pre-execution permission check. Fail-closed on any error."""
        self._verify_policy()
        try:
            result = await self.service.gate_check({
                "operation": operation,
                "source_id": source_id or resource_id,
                "agent_id": agent_id,
                "jurisdiction": jurisdiction,
                "purpose": purpose,
            }, agent_id)
        except Exception as exc:  # pragma: no cover - defensive boundary
            raise GovernanceRefusal(
                "IPLCI_POLICY_UNAVAILABLE", "BLOCKED", "UNKNOWN",
                f"gateway unavailable: {type(exc).__name__}",
            )
        self._refuse(result, operation)
        return result

    async def enforce_training(
        self,
        *,
        source_id: Optional[str],
        dataset_id: Optional[str],
        approval_id: Optional[str] = None,
        agent_id: str = "main",
        jurisdiction: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Independent training gate — analysis approval is not sufficient."""
        self._verify_policy()
        if not source_id or not dataset_id:
            raise GovernanceRefusal(
                "IPLCI_PROVENANCE_REQUIRED", "BLOCKED", "CRITICAL",
                "training requires a registered source, dataset and provenance",
            )
        try:
            result = await self.service.training_gate({
                "source_id": source_id,
                "dataset_id": dataset_id,
                "approval_id": approval_id,
                "jurisdiction": jurisdiction,
            }, agent_id)
        except Exception as exc:  # pragma: no cover - defensive boundary
            raise GovernanceRefusal(
                "IPLCI_POLICY_UNAVAILABLE", "BLOCKED", "UNKNOWN",
                f"training gate unavailable: {type(exc).__name__}",
            )
        self._refuse(result, "train")
        return result

    async def enforce_publication(self, *, source_id: Optional[str], agent_id: str = "main") -> Dict[str, Any]:
        return await self.enforce("distribute", source_id=source_id, agent_id=agent_id, purpose="publication")

    async def enforce_egress(self, *, source_id: Optional[str], agent_id: str = "main") -> Dict[str, Any]:
        return await self.enforce("disclose", source_id=source_id, agent_id=agent_id, purpose="external_provider")

    async def enforce_collection(self, *, source_id: Optional[str], agent_id: str = "main") -> Dict[str, Any]:
        return await self.enforce("store", source_id=source_id, agent_id=agent_id, purpose="collection")

    async def enforce_agent_action(
        self,
        *,
        agent_id: str,
        action: str,
        source_id: Optional[str] = None,
        jurisdiction: Optional[str] = None,
    ) -> Dict[str, Any]:
        """No agent identity or sub-agent may skip the gateway."""
        return await self.enforce(action, source_id=source_id, agent_id=agent_id, jurisdiction=jurisdiction)

    async def enforce_retention(self, *, evidence_id: str, now: Optional[str] = None) -> Dict[str, Any]:
        """Refuse deletion while a legal hold or retention duty applies."""
        self._verify_policy()
        decision = await self.service.retention_decision(evidence_id, now)
        if decision.get("action") not in ("delete_if_lawful",):
            raise GovernanceRefusal(
                "IPLCI_EVIDENCE_PRESERVED", "BLOCKED", decision.get("risk") or "HIGH",
                f"deletion refused: {decision.get('action')}",
            )
        return decision


_gateway: Optional[ComplianceGateway] = None


def configure_gateway(gateway: Optional[ComplianceGateway]) -> None:
    """Inject the production gateway; ``None`` resets to fail-closed defaults."""
    global _gateway
    _gateway = gateway


def get_gateway() -> ComplianceGateway:
    """Return the configured gateway, or a fail-closed in-memory default."""
    return _gateway or ComplianceGateway()
