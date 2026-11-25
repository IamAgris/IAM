"""SQLAlchemy ORM models - Project AURA / IAM"""

from app.models.identity import AIIdentity, AIPersonality, IdentityHistory
from app.models.memory import (
    MemoryItem, MemoryEmbedding, MemoryRelationship, Experience,
    Conversation, ConversationMessage, KnowledgeItem, KnowledgeSource,
    LanguageProfile, Skill,
)
from app.models.autonomy import (
    Goal, Plan, Task, TaskExecution, DecisionRecord,
    ToolRegistry, ToolPermission, WorkflowCheckpoint, ScheduledActivity,
)
from app.models.development import (
    ModelRegistry, ModelVersion, ModelEvaluation, Experiment,
    SoftwareProject, CodeChange, DeploymentRecord, ResourceMetric, UpgradeHistory,
)
from app.models.business import (
    BusinessOpportunity, BusinessProject, BusinessPerformance,
    FinancialLedger, FinancialBudget, FinancialTransaction,
    CryptoActivity, OperatingExpense,
)
from app.models.security import (
    IntegrationRegistry, IntegrationPermission,
    AuditEvent, SecurityIncident, CredentialReference,
)
from app.models.lifemanagement import AIIdentityGenesis, LifeCycle, DailyRoutine, LifeHistory, GoalLifecycle
from app.models.worldmodel import (
    WorldEntity, EntityRelationship, CauseEffectChain, WorldEvent, CapabilityLimitation,
)
from app.models.resilience import HealthCheck, RecoveryLog, BackupVerification, IncidentRecord, CredentialRotation
from app.models.capability import CapabilityDefinition, CapabilityAssessment, LearningPath
from app.models.researchlab import ResearchHypothesis, ResearchExperiment, ExperimentResult, ResearchPublication
from app.models.socialintel import ConversationContext, SocialProfile, InteractionPreference, ToneAnalysis, ScamDetectionLog
from app.models.businessengine import BusinessBudget, CustomerRecord, SalesRecord, BusinessReport, ProjectPortfolio
from app.models.digitalassets import DigitalAsset, AssetLicence, DomainRegistration, IPRecord
from app.models.modelindependence import ModelComparison, ModelPortabilityExport, FallbackConfig
from app.models.governance import AuthorityBoundary, ApprovalPolicy, SecurityBoundary
from app.models.reflection import ReflectionEntry, OperatingPrinciple
from app.models.globalaccess import (
    AnonymousVisitor, VisitorSession, VisitorLocation, ConversationThread,
    VisitorMessage, VisitorPreference, VisitorConsent, VisitorMemoryPermission,
    RequestJob, RequestUsage, VisitorRateLimit, RegionalSetting,
)
from app.models.ainetwork import (
    ExternalAgent, AgentInteraction, AgentInterview, AgentTrustRecord, AgentCollaboration,
    ExternalIntegration, InternetResource, CloudWorkload,
)
from app.models.ownerauth import OwnerAuthorization
from app.models.internetaccess import (
    InternetSession, BrowserAction, OnlineAccount, PublishedContent,
    MonitoredTarget, RetrievedFile, InternetPermission, InternetEvent,
)
from app.models.modelrouter import AIProvider, DiscoveredModel, RoutingDecision, ProviderUsage
from app.models.skillforge import (
    SkillPackage,
    SkillVersion,
    SkillTestResult,
    SkillAuditEvent,
    SkillPermissionGrant,
)
from app.models.securityengines import (
    ExternalSecurityEngine,
    SecurityEngineScope,
    SecurityEngineTask,
    SecurityFinding,
    SecurityEngineAudit,
)
from app.models.skillruntime import SkillRuntimeExecution
from app.models.auth import ApiCredential
from app.models.creatorapproval import (
    CreatorRequest,
    SignedChallenge,
    CreatorApproval,
    CreatorAuthorization,
    CreatorEmailOutbox,
    CreatorMessage,
    CommunicationAudit,
)
from app.models.sdk import RegisteredNode, NodeResourceReport
from app.models.storage import StoredObject
from app.models.uwaie import WebsiteWorkflow
from app.models.integrity import IntegrityManifest, NodeAttestation, SyncObject
from app.models.freesandbox import (
    FreeSandboxProvider,
    FreeSandboxQuotaSnapshot,
    FreeSandboxEnvironment,
    FreeSandboxResult,
)
from app.models.publicrecords import PublicSource, PublicRecord, RecordRelationship
from app.models.legal import LegalSource, LegalInstrument, LegalVersion, LegalChange, LegalImpact
from app.models.geo import (
    GeoProvider, GeoPlace, GeoDataFile, LiveGeoFeed, MapTileCache, LocationPermission,
)
from app.models.humanpresence import (
    PublicPerson, PublicProfile, PresenceClaim, IdentityMatch, PublicRelationship,
)

__all__ = [
    # Identity
    "AIIdentity", "AIPersonality", "IdentityHistory",
    # Memory
    "MemoryItem", "MemoryEmbedding", "MemoryRelationship", "Experience",
    "Conversation", "ConversationMessage", "KnowledgeItem", "KnowledgeSource",
    "LanguageProfile", "Skill",
    # Autonomy
    "Goal", "Plan", "Task", "TaskExecution", "DecisionRecord",
    "ToolRegistry", "ToolPermission", "WorkflowCheckpoint", "ScheduledActivity",
    # Development
    "ModelRegistry", "ModelVersion", "ModelEvaluation", "Experiment",
    "SoftwareProject", "CodeChange", "DeploymentRecord", "ResourceMetric", "UpgradeHistory",
    # Business
    "BusinessOpportunity", "BusinessProject", "BusinessPerformance",
    "FinancialLedger", "FinancialBudget", "FinancialTransaction",
    "CryptoActivity", "OperatingExpense",
    # Security
    "IntegrationRegistry", "IntegrationPermission",
    "AuditEvent", "SecurityIncident", "CredentialReference",
    # Life Management
    "AIIdentityGenesis", "LifeCycle", "DailyRoutine", "LifeHistory", "GoalLifecycle",
    # World Model
    "WorldEntity", "EntityRelationship", "CauseEffectChain", "WorldEvent", "CapabilityLimitation",
    # Resilience
    "HealthCheck", "RecoveryLog", "BackupVerification", "IncidentRecord", "CredentialRotation",
    # Capability
    "CapabilityDefinition", "CapabilityAssessment", "LearningPath",
    # Research Lab
    "ResearchHypothesis", "ResearchExperiment", "ExperimentResult", "ResearchPublication",
    # Social Intelligence
    "ConversationContext", "SocialProfile", "InteractionPreference", "ScamDetectionLog",
    # Business Engine
    "BusinessBudget", "CustomerRecord", "SalesRecord", "BusinessReport", "ProjectPortfolio",
    # Digital Assets
    "DigitalAsset", "AssetLicence", "DomainRegistration", "IPRecord",
    # Model Independence
    "ModelComparison", "ModelPortabilityExport", "FallbackConfig",
    # Governance
    "AuthorityBoundary", "ApprovalPolicy", "SecurityBoundary",
    # Reflection
    "ReflectionEntry", "OperatingPrinciple",
    # Global Access
    "AnonymousVisitor", "VisitorSession", "VisitorLocation", "ConversationThread",
    "VisitorMessage", "VisitorPreference", "VisitorConsent", "VisitorMemoryPermission",
    "RequestJob", "RequestUsage", "VisitorRateLimit", "RegionalSetting",
    # AI Network
    "ExternalAgent", "AgentInteraction", "AgentTrustRecord", "AgentCollaboration",
    "ExternalIntegration", "InternetResource", "CloudWorkload",
    # Internet Access
    "InternetSession", "BrowserAction", "OnlineAccount", "PublishedContent",
    "MonitoredTarget", "RetrievedFile", "InternetPermission", "InternetEvent",
    # Model Router
    "AIProvider", "DiscoveredModel", "RoutingDecision", "ProviderUsage",
    # IAM Skill Forge
    "SkillPackage", "SkillVersion", "SkillTestResult", "SkillAuditEvent",
    "SkillPermissionGrant",
    # External Security Engines
    "ExternalSecurityEngine", "SecurityEngineScope", "SecurityEngineTask",
    "SecurityFinding", "SecurityEngineAudit",
    # Creator approval by email
    "CreatorRequest", "SignedChallenge", "CreatorApproval",
    "CreatorAuthorization", "CreatorEmailOutbox", "CommunicationAudit",
    # API authentication
    "ApiCredential",
    # Owner authorization
    "OwnerAuthorization",
    # Skill Runtime
    "SkillRuntimeExecution",
    # Node registry (OD-26)
    "RegisteredNode", "NodeResourceReport",
    # Storage and website interaction
    "StoredObject", "WebsiteWorkflow",
    # Integrity, attestation and sync
    "IntegrityManifest", "NodeAttestation", "SyncObject",
    # Public records research
    "PublicSource", "PublicRecord", "RecordRelationship",
    # Legal intelligence
    "LegalSource", "LegalInstrument", "LegalVersion", "LegalChange", "LegalImpact",
    # Geospatial
    "GeoProvider", "GeoPlace", "GeoDataFile", "LiveGeoFeed", "MapTileCache",
    "LocationPermission",
    # Human public presence
    "PublicPerson", "PublicProfile", "PresenceClaim", "IdentityMatch",
    "PublicRelationship",
    # OEDIE free infrastructure adapters (Doc 22)
    "FreeSandboxProvider", "FreeSandboxQuotaSnapshot",
    "FreeSandboxEnvironment", "FreeSandboxResult",
]
