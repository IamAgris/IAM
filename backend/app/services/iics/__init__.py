"""IICS foundation services — overlay modules, pending proposal.

Reuses InternetAccessService, IPLCI's legal gate and the OD-08 ARQ runtime.
Does not create a new top-level system or a second queue.
"""

from .egress import EgressDecision, EgressGateway
from .permissions import PermissionGate
from .ledger import ActionLedger, BudgetGovernor, BudgetLimit
from .source_registry import FRESHNESS_TTL_HOURS, SourceRegistry, label_for_confidence
from .qa import BenchmarkSuite, BenchmarkCase
from .creator_email import CreatorEmailBridge
from .search_strategy import ConfidenceCalibrator, StrategyDecision, StrategySelector
from .scheduler import ScheduledResearchError, ScheduledResearchService
from .media import MediaDocumentService, MediaError, sanitize_metadata
from .threat_intel import (
    AdvisoryIngestor,
    CredentialRef,
    CredentialRotationPolicy,
    DLPEngine,
)
from .site_policy import PrivacyLifecycle, SitePolicyStore, policy_hash

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
    "CreatorEmailBridge",
    "ConfidenceCalibrator",
    "StrategyDecision",
    "StrategySelector",
    "ScheduledResearchError",
    "ScheduledResearchService",
    "MediaDocumentService",
    "MediaError",
    "AdvisoryIngestor",
    "CredentialRef",
    "CredentialRotationPolicy",
    "DLPEngine",
    "PrivacyLifecycle",
    "SitePolicyStore",
    "policy_hash",
    "sanitize_metadata",
]
