"""Autonomous AI research foundations — Phase 0 (OD-41).

Do not enable paid compute. Platform adapters in Phase 1 must implement the
existing `ProviderAdapter` protocol from `free_sandboxes`.
"""

from .artifacts import (
    ArtifactKind,
    ArtifactStore,
    FileSystemArtifactStore,
    ResearchArtifact,
    artifact_key,
    new_experiment_id,
    persist_manifest,
    sha256_bytes,
)
from .base import (
    CredentialLeak,
    DigestMismatch,
    InvalidResearchJob,
    IsolationViolation,
    NoImprovement,
    PaidUpgradeRequested,
    PrivateDataLeak,
    ResearchError,
)
from .benchmarks import (
    BenchmarkResult,
    BenchmarkRunner,
    BenchmarkSpec,
    BenchmarkUnstable,
    LMEvalDriver,
)
from .profiles import CapabilityProfile, CapabilityRegistry, NoCapableModel, UnknownModel
from .adapters import (
    ColabResearchAdapter,
    HuggingFaceResearchAdapter,
    KaggleResearchAdapter,
    LightningAIResearchAdapter,
    ResearchAdapterBase,
    ResearchPlatformAdapter,
)
from .coordinator import METHOD_CAPABILITY, ResearchCoordinator, ResearchRun
from .credentials import CredentialRef, CredentialVault
from .jobs import HardwareRequirement, ResearchJob, ResearchMethod, new_job, validate_job
from .quotas import ResearchQuotaGuard, ResearchQuotaSnapshot
from .lifecycle import (
    ACTIVE,
    DEGRADED,
    DISCOVERED,
    RETIRED,
    PlatformLifecycle,
    PlatformRecord,
)
from .recovery import FailureRecord, JobRecovery, RecoveryPolicy
from .scheduler import ResearchScheduler, SchedulingDecision, WorkloadProfile
from .serving import (
    OpenAICompatibleClient,
    ServingDriver,
    ServingEndpoint,
    ServingExperimentRunner,
    ServingReport,
    ServingSpec,
    ServingUnsupported,
    validate_serving_spec,
)
from .training import FineTuneSpec, TRAINING_METHODS, TrainingService
from .s3_store import S3ArtifactStore
from .security import (
    DEFAULT_ISOLATION_POLICY,
    IsolationPolicy,
    assert_isolation_policy,
    assert_no_private_data,
    verify_digest,
    wrap_research_output,
)
from .service import PreparedJob, prepare_job

__all__ = [
    "BenchmarkResult",
    "BenchmarkRunner",
    "BenchmarkSpec",
    "BenchmarkUnstable",
    "CapabilityProfile",
    "CapabilityRegistry",
    "LMEvalDriver",
    "NoCapableModel",
    "NoImprovement",
    "UnknownModel",
    "ACTIVE",
    "DEGRADED",
    "DISCOVERED",
    "RETIRED",
    "FailureRecord",
    "JobRecovery",
    "PlatformLifecycle",
    "PlatformRecord",
    "RecoveryPolicy",
    "ResearchScheduler",
    "SchedulingDecision",
    "WorkloadProfile",
    "FineTuneSpec",
    "TRAINING_METHODS",
    "TrainingService",
    "OpenAICompatibleClient",
    "ServingDriver",
    "ServingEndpoint",
    "ServingExperimentRunner",
    "ServingReport",
    "ServingSpec",
    "ServingUnsupported",
    "validate_serving_spec",
    "ColabResearchAdapter",
    "HuggingFaceResearchAdapter",
    "KaggleResearchAdapter",
    "LightningAIResearchAdapter",
    "METHOD_CAPABILITY",
    "ResearchAdapterBase",
    "ResearchCoordinator",
    "ResearchPlatformAdapter",
    "ResearchRun",
    "S3ArtifactStore",
    "ArtifactKind",
    "ArtifactStore",
    "CredentialLeak",
    "CredentialRef",
    "CredentialVault",
    "DEFAULT_ISOLATION_POLICY",
    "DigestMismatch",
    "FileSystemArtifactStore",
    "HardwareRequirement",
    "InvalidResearchJob",
    "IsolationPolicy",
    "IsolationViolation",
    "PaidUpgradeRequested",
    "PreparedJob",
    "PrivateDataLeak",
    "ResearchArtifact",
    "ResearchError",
    "ResearchJob",
    "ResearchMethod",
    "ResearchQuotaGuard",
    "ResearchQuotaSnapshot",
    "artifact_key",
    "assert_isolation_policy",
    "assert_no_private_data",
    "new_experiment_id",
    "new_job",
    "persist_manifest",
    "prepare_job",
    "sha256_bytes",
    "validate_job",
    "verify_digest",
    "wrap_research_output",
]
