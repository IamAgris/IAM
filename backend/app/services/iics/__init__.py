"""IICS foundation services — overlay modules, pending proposal.

Reuses InternetAccessService, IPLCI's legal gate and the OD-08 ARQ runtime.
Does not create a new top-level system or a second queue.
"""

from .egress import EgressDecision, EgressGateway
from .permissions import PermissionGate
from .ledger import ActionLedger, BudgetGovernor, BudgetLimit
from .source_registry import FRESHNESS_TTL_HOURS, SourceRegistry, label_for_confidence
from .qa import BenchmarkSuite, BenchmarkCase

__all__ = [
    "EgressDecision",
    "EgressGateway",
    "PermissionGate",
    "ActionLedger",
    "BudgetGovernor",
    "BudgetLimit",
    "FRESHNESS_TTL_HOURS",
    "SourceRegistry",
    "label_for_confidence",
    "BenchmarkSuite",
    "BenchmarkCase",
]
