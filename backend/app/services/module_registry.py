"""Central, declarative contract registry for IAM's dispatchable modules.

This is the capability-discovery surface the autonomy graph consults. It does
not add a new execution path: ``orchestration/dispatch.py`` remains the single
adapter to existing services. The registry only names what is callable, its
authority level, and the keywords used to map an objective to an action.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


@dataclass(frozen=True)
class ModuleContract:
    action: str
    service: str
    description: str
    authority: str  # autonomous | authorized | explicit
    side_effect: bool
    keywords: Tuple[str, ...] = ()

    def as_dict(self) -> Dict[str, Any]:
        return {
            "action": self.action,
            "service": self.service,
            "description": self.description,
            "authority": self.authority,
            "side_effect": self.side_effect,
        }


MODULES: Dict[str, ModuleContract] = {
    contract.action: contract
    for contract in (
        ModuleContract("memory_recall", "MemoryService", "Recall governed memory", "autonomous", False, ("memory", "recall")),
        ModuleContract("capability_inspect", "CapabilityService", "Inspect measured capabilities", "autonomous", False, ("capab",)),
        ModuleContract("governance_check", "GovernanceService", "Check authority for an action", "autonomous", False, ("permission", "authority")),
        ModuleContract("model_probe", "InferenceService", "Report active model readiness", "autonomous", False, ()),
        ModuleContract("research", "ResearchService", "Web research with provenance", "authorized", True, ("research",)),
        ModuleContract("tone_analyze", "IAMToolExecutor", "Analyse tone defensively", "authorized", False, ("tone", "influence")),
        ModuleContract("network_inspect", "IAMToolExecutor", "Inspect external AI registry", "authorized", False, ("network", "external ai")),
        ModuleContract("sandbox_status", "IAMToolExecutor", "Inspect free sandbox state", "authorized", False, ("sandbox", "free infrastructure")),
        ModuleContract("finance_research_read", "IAMToolExecutor", "Read-only finance research", "authorized", False, ("market", "investment", "ledger")),
        ModuleContract("iics_egress_check", "IAMToolExecutor", "Check URL egress policy", "authorized", False, ("egress", "url policy")),
    )
}


def contract(action: str) -> Optional[ModuleContract]:
    return MODULES.get(action)


def available_actions() -> Tuple[str, ...]:
    return tuple(MODULES)


def discover(*, authority: Optional[str] = None) -> List[Dict[str, Any]]:
    """List callable modules, optionally filtered by authority level."""
    return [
        item.as_dict()
        for item in MODULES.values()
        if authority is None or item.authority == authority
    ]


def action_for_objective(title: str) -> Optional[str]:
    """Map an objective title to a registered action using declared keywords."""
    text = title.lower()
    for item in MODULES.values():
        if any(keyword in text for keyword in item.keywords):
            return item.action
    return None
