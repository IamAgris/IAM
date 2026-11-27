"""Document 26 (OD-45): HBI Phase 1 schemas.

Epistemic objects are typed and graded. Observations, interpretations,
hypotheses and predictions are never interchangeable.
"""

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class EpistemicType(str, Enum):
    OBSERVATION = "observation"
    INTERPRETATION = "interpretation"
    HYPOTHESIS = "hypothesis"
    PREDICTION = "prediction"


class EvidenceClass(str, Enum):
    VERIFIED = "verified"
    WELL_SUPPORTED = "well_supported"
    CONTESTED = "contested"
    UNVERIFIED = "unverified"
    SPECULATION = "speculation"


class Scope(str, Enum):
    AGGREGATE = "aggregate"
    INDIVIDUAL = "individual"


class Tier(str, Enum):
    T0_PUBLIC = "T0"
    T1_CURATED = "T1"
    T2_AGGREGATE = "T2"
    T3_INDIVIDUAL = "T3"


class CausalStatus(str, Enum):
    CAUSAL = "causal"
    CORRELATIONAL = "correlational"
    SPECULATIVE = "speculative"


class EvidenceItem(BaseModel):
    source_id: str
    source_type: str
    locator: Optional[str] = None
    grade: str = "unknown"
    licence: Optional[str] = None
    collection_date: Optional[str] = None
    permitted_purpose: Optional[str] = None


class Uncertainty(BaseModel):
    aleatoric: float = Field(default=0.0, ge=0.0, le=1.0)
    epistemic: float = Field(default=0.0, ge=0.0, le=1.0)
    evidence_gap: str = "low"
    distribution_shift: str = "low"


class KnowledgeRecordInput(BaseModel):
    claim: str = Field(min_length=1, max_length=4000)
    epistemic_type: EpistemicType
    evidence_class: Optional[EvidenceClass] = None
    scope: Scope = Scope.AGGREGATE
    population: Optional[str] = None
    context_dimensions: Dict[str, Any] = Field(default_factory=dict)
    evidence: List[EvidenceItem] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    uncertainty: Uncertainty = Field(default_factory=Uncertainty)
    alternatives: List[str] = Field(default_factory=list)
    falsifier: Optional[str] = None
    causal_status: CausalStatus = CausalStatus.CORRELATIONAL
    module_ids: List[int] = Field(default_factory=list)
    tier: Tier = Tier.T0_PUBLIC
    provenance_kind: str = "direct_observation"


class ResearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    purpose: str = Field(min_length=1)
    scope: Scope = Scope.AGGREGATE
    language: Optional[str] = None
    period: Optional[str] = None
    region: Optional[str] = None


class AnalysisRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    purpose: str = Field(min_length=1)
    scope: Scope = Scope.AGGREGATE
    context: Dict[str, Any] = Field(default_factory=dict)


class PredictionRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    target: str = Field(min_length=1, max_length=2000)
    purpose: str = Field(min_length=1)
    scope: Scope = Scope.AGGREGATE
    time_horizon: Optional[str] = None
    context_refs: List[str] = Field(default_factory=list)
    model_id: Optional[str] = None
    features: Dict[str, float] = Field(default_factory=dict)


class ChronologyInput(BaseModel):
    events: List[Dict[str, Any]] = Field(default_factory=list)
    uncertain_periods: List[Dict[str, Any]] = Field(default_factory=list)
    conflicting_accounts: List[Dict[str, Any]] = Field(default_factory=list)


class ResearchDocumentInput(BaseModel):
    """A licensed research or historical document submitted for ingestion."""

    source_id: str = Field(min_length=1)
    title: str = Field(min_length=1, max_length=1000)
    text: str = Field(min_length=1, max_length=20000)
    source_type: str = "peer_reviewed_journal"
    licence: Optional[str] = None
    permitted_purpose: str = "research"
    collection_date: Optional[str] = None
    language: Optional[str] = None
    period: Optional[str] = None
    region: Optional[str] = None
    population: Optional[str] = None
    scope: Scope = Scope.AGGREGATE
    tier: Tier = Tier.T0_PUBLIC
    module_ids: List[int] = Field(default_factory=list)


class ModuleAnalysisRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    purpose: str = Field(min_length=1)
    scope: Scope = Scope.AGGREGATE
    context: Dict[str, Any] = Field(default_factory=dict)


class TemporalRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    purpose: str = Field(min_length=1)
    context_key: str = "time"
    limit: int = 200


class CrossDisciplinaryRequest(BaseModel):
    question: str = Field(min_length=1)
    claims_by_discipline: Dict[str, List[Dict[str, Any]]] = Field(default_factory=dict)
    calibration_weights: Dict[str, float] = Field(default_factory=dict)


class RevisionRequest(BaseModel):
    old_ref: str
    rationale: str = Field(min_length=1)
    payload: KnowledgeRecordInput


class DeprecateRequest(BaseModel):
    record_ref: str
    reason: str = Field(min_length=1)


class ManipulationRequest(BaseModel):
    texts: List[str] = Field(default_factory=list)


class CorpusSourceMeta(BaseModel):
    title: str = Field(min_length=1)
    origin: str = Field(min_length=1)
    collection_date: str = Field(min_length=1)


class CorpusLicensing(BaseModel):
    licence_id: Optional[str] = None
    licence_url: Optional[str] = None
    permission_evidence: Optional[str] = None
    commercial_use_allowed: bool = False
    attribution_required: bool = False
    ingestion_allowed: bool = False
    storage_allowed: bool = False
    analysis_allowed: bool = False
    model_training_allowed: bool = False
    derivative_allowed: bool = False
    licence_expires_at: Optional[str] = None
    revocation_reference: Optional[str] = None


class CorpusLawfulBasis(BaseModel):
    applies_to_living_persons: bool = False
    basis: str = "not_applicable"
    evidence_reference: Optional[str] = None


class CorpusPrivacy(BaseModel):
    contains_personal_information: bool = False
    contains_sensitive_personal_information: bool = False
    identifiable_profiles: bool = False
    sensitive_trait_inference: bool = False


class CorpusGovernance(BaseModel):
    validation_status: str = "pending"
    validated_by: Optional[str] = None
    validation_date: Optional[str] = None
    restrictions: List[str] = Field(default_factory=list)


class CorpusSourceManifest(BaseModel):
    source_id: str = Field(min_length=1)
    path: Optional[str] = None
    rights_holder: Optional[str] = None
    acquisition_method: str = "open_access"
    source: CorpusSourceMeta
    licensing: CorpusLicensing
    permitted_purposes: List[str] = Field(default_factory=list)
    lawful_basis: CorpusLawfulBasis = Field(default_factory=CorpusLawfulBasis)
    privacy: CorpusPrivacy = Field(default_factory=CorpusPrivacy)
    governance: CorpusGovernance = Field(default_factory=CorpusGovernance)
    retention_period: Optional[str] = None
    territory: Optional[str] = None
    expiry_date: Optional[str] = None
    revocation_conditions: List[str] = Field(default_factory=list)


class CorpusReviewRequest(BaseModel):
    manifest: CorpusSourceManifest
    intended_purpose: str = "research"
    approved_by: str = "corpus_ingestion_gate"
    model_training: bool = False


class CorpusRestrictionRequest(BaseModel):
    source_id: str
    reason: str = Field(min_length=1)


class TrainingRequest(BaseModel):
    source_id: str
    intended_model: str = Field(min_length=1)
    purpose: str = "research"
    proposed_retention: Optional[str] = None


class TrainingApprovalRequest(BaseModel):
    source_id: str
    approver: str = Field(min_length=1)
    decision: str = Field(min_length=1)
    basis: str = Field(min_length=1)


class PartnershipRequest(BaseModel):
    organisation: str = Field(min_length=1)
    contact_reference: Optional[str] = None
    requested_rights: List[str] = Field(default_factory=list)
    safeguards: List[str] = Field(default_factory=list)
    agreement_reference: Optional[str] = None


class TranslationRequest(BaseModel):
    text: str = Field(min_length=1, max_length=20000)
    source_language: Optional[str] = None
    target_language: str = "en"
    purpose: str = Field(min_length=1)
    model: Optional[str] = None


class MultilingualSemanticsRequest(BaseModel):
    text: str = Field(min_length=1, max_length=20000)
    language: Optional[str] = None
    region: Optional[str] = None
    purpose: str = Field(min_length=1)


class StudyCreateRequest(BaseModel):
    title: str = Field(min_length=1)
    research_question: str = Field(min_length=1)
    ethics_reference: Optional[str] = None
    human_participants: bool = True
    retention_days: int = 90
    consent_purposes: List[str] = Field(default_factory=lambda: ["research"])


class ParticipantConsentRequest(BaseModel):
    study_id: str
    participant_ref: str = Field(min_length=1)
    purposes: List[str] = Field(default_factory=list)
    basis: str = "informed_consent"
    retention_days: Optional[int] = None


class StudyResponseRequest(BaseModel):
    study_id: str
    participant_ref: str
    response: str = Field(min_length=1, max_length=10000)


class ParticipantWithdrawalRequest(BaseModel):
    study_id: str
    participant_ref: str
    reason: str = "withdrawn_by_participant"


class OpenSourceIngestRequest(BaseModel):
    adapter: str
    query: str = Field(min_length=1)
    limit: int = 5


class SyntheticStudyRequest(BaseModel):
    study_ref: str = Field(min_length=1)
    count: int = 5
    purpose: str = "research"


class TargetVerificationRequest(BaseModel):
    name: str
    verified_by: str = Field(min_length=1)
    reference: str = Field(min_length=1)


class ContributionRequest(BaseModel):
    contributor: str = Field(min_length=1)
    material_type: str = Field(min_length=1)
    ownership_retained: bool = True
    training_rights: bool = False
    commercial_use: bool = False
    attribution_required: bool = True
    withdrawal_permitted: bool = True
    personal_data_present: bool = False
    ethics_reference: Optional[str] = None
    agreement_reference: Optional[str] = None


class FederatedRequest(BaseModel):
    institution: str = Field(min_length=1)
    analysis_description: str = Field(min_length=1)
    safeguards: List[str] = Field(default_factory=list)


class FederatedApprovalRequest(BaseModel):
    institution: str
    approver: str = Field(min_length=1)
    reference: str = Field(min_length=1)


class LabProjectRequest(BaseModel):
    title: str = Field(min_length=1)
    research_question: str = Field(min_length=1)
    human_participants: bool = False
    ethics_reference: Optional[str] = None
    consent_plan: Optional[str] = None


class TransformationRequest(BaseModel):
    source_ids: List[str] = Field(default_factory=list)
    output_type: str = Field(min_length=1)


class LegalContextVerificationRequest(BaseModel):
    topic: str
    verified_by: str = Field(min_length=1)
    reference: str = Field(min_length=1)


class DPIASignoffRequest(BaseModel):
    reviewer: str = Field(min_length=1)
    decision: str = Field(min_length=1)
    basis: str = Field(min_length=1)


class DualUseRequest(BaseModel):
    capability: str
    markers: List[str] = Field(default_factory=list)
    purpose: str = Field(min_length=1)
    scope: Scope = Scope.AGGREGATE


class OversightRequest(BaseModel):
    decision_type: str
    evidence: Dict[str, Any] = Field(default_factory=dict)


class CorpusIngestRequest(BaseModel):
    manifest_path: str
    root: str = ""


class SourceCalibrationRequest(BaseModel):
    cases: List[Dict[str, Any]] = Field(default_factory=list)


class MultilingualIngestRequest(BaseModel):
    documents: List[ResearchDocumentInput] = Field(default_factory=list)


class ForecastRequest(BaseModel):
    question: str = Field(min_length=1)
    target: str = Field(min_length=1)
    purpose: str = Field(min_length=1)
    scope: Scope = Scope.AGGREGATE
    time_horizon: Optional[str] = None
    model_id: Optional[str] = None
    features: Dict[str, float] = Field(default_factory=dict)
    context_refs: List[str] = Field(default_factory=list)


class AnalogyEvaluationRequest(BaseModel):
    current: Dict[str, Any] = Field(default_factory=dict)
    precedents: List[Dict[str, Any]] = Field(default_factory=list)
    cases: List[Dict[str, Any]] = Field(default_factory=list)


class TheoryComparisonRequest(BaseModel):
    theories: List[Dict[str, Any]] = Field(default_factory=list)
    cases: List[Dict[str, Any]] = Field(default_factory=list)


class AnalogyRequest(BaseModel):
    current: Dict[str, Any] = Field(default_factory=dict)
    precedent: Dict[str, Any] = Field(default_factory=dict)


class PredictionEvaluationRequest(BaseModel):
    prediction: Dict[str, Any] = Field(default_factory=dict)
    outcome: Any = None


class GraphNodeRequest(BaseModel):
    node_ref: Optional[str] = None
    node_type: str = "historical_event"
    label: str = Field(min_length=1)
    period: Optional[str] = None
    region: Optional[str] = None
    date_value: Optional[Any] = None
    properties: Dict[str, Any] = Field(default_factory=dict)
    evidence_class: str = "unverified"


class GraphEdgeRequest(BaseModel):
    from_ref: str
    to_ref: str
    relation: str
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    evidence_class: str = "unverified"


class BacktestRequest(BaseModel):
    cases: List[Dict[str, Any]] = Field(default_factory=list)
    model_id: str = "baseline"


class SourceRegisterRequest(BaseModel):
    source_id: str = Field(min_length=1)
    domain: str = Field(min_length=1)
    source_type: str = "news"
    licence: str = Field(min_length=1)
    permitted_purpose: str = "research"
    require_robots: bool = True


PROHIBITED_PURPOSES = {
    "manipulation",
    "targeting",
    "secret_profiling",
    "sensitive_trait_inference",
    "criminality_prediction",
    "emotion_based_decision",
    "psychological_warfare",
}

INDIVIDUAL_ALLOWED_PURPOSES = {
    "assist_user",
    "user_requested_reflection",
    "consented_task",
}
