"""IP & Legal Intelligence governance routes (proposed OD-48, Phase 1).

Every agent reaches execution only through ``POST /gate/check``. The endpoint
returns a decision rather than raising for blocked material, so callers cannot
mistake an HTTP error for permission. Legal research is not legal advice and no
route here creates legal authority or a binding commitment.
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session
from app.services.iplci import IPLCIError, IPLCIService

router = APIRouter(prefix="/api/v1/iplci", tags=["ip-legal-intelligence"])


class SourceRequest(BaseModel):
    uri: str
    title: Optional[str] = None
    description: Optional[str] = None
    rights_status: str = "UNKNOWN_OWNERSHIP"
    source_class: str = "UNVERIFIED"
    acquisition_method: str = "other"
    author: Optional[str] = None
    publisher: Optional[str] = None
    jurisdiction: Optional[str] = None
    permission_evidence: Optional[str] = None
    licence_id: Optional[str] = None
    expiry_date: Optional[str] = None
    territory: Optional[List[str]] = None
    personal_data_present: bool = False
    privacy_lawful_basis: Optional[str] = None
    attribution_required: bool = False
    licence_flags: Dict[str, Any] = Field(default_factory=dict)


class PermissionRequest(BaseModel):
    source_id: str
    right: str
    state: str = "UNKNOWN"
    basis: Optional[str] = None
    conditions: List[str] = Field(default_factory=list)
    evidence_ref: Optional[str] = None


class AssessmentRequest(BaseModel):
    source_id: Optional[str] = None
    operation: str
    jurisdiction: Optional[str] = None
    agent_id: Optional[str] = None


class GateCheckRequest(BaseModel):
    agent_id: str = "main"
    operation: str
    resource_id: Optional[str] = None
    source_id: Optional[str] = None
    jurisdiction: Optional[str] = None
    purpose: Optional[str] = None
    project_id: Optional[str] = None


class RevokeRequest(BaseModel):
    reason: str = ""


class AssetRequest(BaseModel):
    asset_type: str = "software"
    title: str
    legal_owner: str
    created_by: Optional[str] = None
    origin: str = "iam"
    inventorship: Optional[Dict[str, Any]] = None
    transfer_reference: Optional[str] = None
    third_party_contributions: List[Any] = Field(default_factory=list)
    ownership_status: str = "unknown"
    registration_status: Optional[str] = None


class DatasetRequest(BaseModel):
    dataset_version: str
    source_ids: List[str] = Field(default_factory=list)
    assessment_ids: List[str] = Field(default_factory=list)
    collection_history: Optional[str] = None
    privacy_classification: str = "unknown"
    permitted_purposes: List[str] = Field(default_factory=list)
    retention_policy: Optional[str] = None


def _actor(request: Request) -> str:
    credential = getattr(request.state, "credential", None)
    return str(credential.get("name", "sdk")) if credential else "sdk"


def _service(db: AsyncSession) -> IPLCIService:
    return IPLCIService(db=db)


def _handle(exc: IPLCIError) -> HTTPException:
    status = 404 if exc.code == "IPLCI_NOT_FOUND" else 400
    return HTTPException(status_code=status, detail={"code": exc.code, "message": exc.message})


@router.get("/status")
async def status() -> Any:
    return IPLCIService().status()


@router.post("/sources")
async def register_source(
    payload: SourceRequest, request: Request, db: AsyncSession = Depends(get_db_session)
) -> Any:
    try:
        return await _service(db).register_source(payload.model_dump(), _actor(request))
    except IPLCIError as exc:
        raise _handle(exc)


@router.get("/sources")
async def list_sources(db: AsyncSession = Depends(get_db_session)) -> Any:
    return await _service(db).store.list_sources()


@router.get("/sources/{source_id}/permissions")
async def source_permissions(source_id: str, db: AsyncSession = Depends(get_db_session)) -> Any:
    return await _service(db).store.list_permissions(source_id)


@router.post("/sources/{source_id}/revoke")
async def revoke_source(
    source_id: str,
    payload: RevokeRequest,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
) -> Any:
    try:
        return await _service(db).revoke_permission(source_id, _actor(request), payload.reason)
    except IPLCIError as exc:
        raise _handle(exc)


@router.post("/permissions")
async def set_permission(
    payload: PermissionRequest, request: Request, db: AsyncSession = Depends(get_db_session)
) -> Any:
    try:
        return await _service(db).set_permission(payload.model_dump(), _actor(request))
    except IPLCIError as exc:
        raise _handle(exc)


@router.post("/assessments")
async def create_assessment(
    payload: AssessmentRequest, request: Request, db: AsyncSession = Depends(get_db_session)
) -> Any:
    try:
        return await _service(db).assess(payload.model_dump(exclude_none=True), _actor(request))
    except IPLCIError as exc:
        raise _handle(exc)


@router.get("/assessments/{assessment_id}")
async def get_assessment(assessment_id: str, db: AsyncSession = Depends(get_db_session)) -> Any:
    assessment = await _service(db).store.get_assessment(assessment_id)
    if not assessment:
        raise HTTPException(status_code=404, detail={"code": "IPLCI_NOT_FOUND"})
    return assessment


@router.post("/gate/check")
async def gate_check(
    payload: GateCheckRequest, request: Request, db: AsyncSession = Depends(get_db_session)
) -> Any:
    data = payload.model_dump(exclude_none=True)
    data["source_id"] = data.get("source_id") or data.get("resource_id")
    return await _service(db).gate_check(data, _actor(request))


@router.post("/assets")
async def register_asset(
    payload: AssetRequest, request: Request, db: AsyncSession = Depends(get_db_session)
) -> Any:
    try:
        return await _service(db).register_asset(payload.model_dump(), _actor(request))
    except IPLCIError as exc:
        raise _handle(exc)


@router.get("/assets")
async def list_assets(db: AsyncSession = Depends(get_db_session)) -> Any:
    return await _service(db).store.list_assets()


@router.post("/datasets")
async def register_dataset(
    payload: DatasetRequest, request: Request, db: AsyncSession = Depends(get_db_session)
) -> Any:
    try:
        return await _service(db).register_dataset(payload.model_dump(), _actor(request))
    except IPLCIError as exc:
        raise _handle(exc)


@router.get("/datasets/{dataset_id}/lineage")
async def dataset_lineage(dataset_id: str, db: AsyncSession = Depends(get_db_session)) -> Any:
    try:
        return await _service(db).lineage(dataset_id)
    except IPLCIError as exc:
        raise _handle(exc)


@router.get("/audit")
async def audit_tail(limit: int = 100, db: AsyncSession = Depends(get_db_session)) -> Any:
    return await _service(db).audit(limit)


# --- Phase 2: trademark, patent, design-right and software IP intelligence ---

class TrademarkRequest(BaseModel):
    mark_text: str
    owner: str
    jurisdiction: Optional[str] = None
    classes: List[str] = Field(default_factory=list)
    status: str = "registered"
    registration_number: Optional[str] = None
    goods_services: Optional[str] = None
    logo_hash: Optional[str] = None
    territory: Optional[List[str]] = None
    filed_at: Optional[str] = None
    registered_at: Optional[str] = None
    expires_at: Optional[str] = None


class TrademarkCheckRequest(BaseModel):
    proposed: str
    jurisdiction: Optional[str] = None
    classes: List[str] = Field(default_factory=list)
    use_context: str = "brand_use"
    now: Optional[str] = None


class PatentRequest(BaseModel):
    publication_number: str
    title: str
    owner: Optional[str] = None
    jurisdiction: List[str] = Field(default_factory=list)
    status: str = "pending"
    claims: List[str] = Field(default_factory=list)
    filed_at: Optional[str] = None
    priority_at: Optional[str] = None
    expires_at: Optional[str] = None
    family_id: Optional[str] = None


class PatentCheckRequest(BaseModel):
    activity: str
    implementation: str = ""
    features: List[str] = Field(default_factory=list)
    jurisdiction: Optional[str] = None
    now: Optional[str] = None


class DesignRequest(BaseModel):
    subject: str
    right_type: str
    owner: Optional[str] = None
    jurisdiction: Optional[str] = None
    registration_number: Optional[str] = None
    status: str = "unregistered"
    expires_at: Optional[str] = None


class DesignCheckRequest(BaseModel):
    subject: str
    right_type: Optional[str] = None
    jurisdiction: Optional[str] = None
    now: Optional[str] = None


class DependencyRequest(BaseModel):
    project_id: str
    name: str
    version: Optional[str] = None
    licence_id: Optional[str] = None
    source_url: Optional[str] = None
    origin: str = "third_party"
    vulnerability_status: Optional[str] = None


class DependencyCheckRequest(BaseModel):
    licence_id: Optional[str] = None
    distribution: str = "internal"
    project_licence: Optional[str] = None
    modification: bool = False
    network_service: bool = False
    vulnerability_status: Optional[str] = None
    dependency_id: Optional[str] = None


class OriginCheckRequest(BaseModel):
    origin: str
    third_party_licence: Optional[str] = None


class SbomRequest(BaseModel):
    project_id: str
    components: List[Dict[str, Any]] = Field(default_factory=list)
    generated_at: Optional[str] = None


@router.post("/trademarks")
async def register_trademark(
    payload: TrademarkRequest, request: Request, db: AsyncSession = Depends(get_db_session)
) -> Any:
    try:
        return await _service(db).register_trademark(payload.model_dump(), _actor(request))
    except IPLCIError as exc:
        raise _handle(exc)


@router.get("/trademarks")
async def list_trademarks(db: AsyncSession = Depends(get_db_session)) -> Any:
    return await _service(db).store.list_trademarks()


@router.post("/trademarks/check")
async def check_trademark(
    payload: TrademarkCheckRequest, request: Request, db: AsyncSession = Depends(get_db_session)
) -> Any:
    try:
        return await _service(db).check_trademark(payload.model_dump(exclude_none=True), _actor(request))
    except IPLCIError as exc:
        raise _handle(exc)


@router.post("/patents")
async def register_patent(
    payload: PatentRequest, request: Request, db: AsyncSession = Depends(get_db_session)
) -> Any:
    try:
        return await _service(db).register_patent(payload.model_dump(), _actor(request))
    except IPLCIError as exc:
        raise _handle(exc)


@router.post("/patents/check")
async def check_patent(
    payload: PatentCheckRequest, request: Request, db: AsyncSession = Depends(get_db_session)
) -> Any:
    try:
        return await _service(db).check_patent(payload.model_dump(exclude_none=True), _actor(request))
    except IPLCIError as exc:
        raise _handle(exc)


@router.post("/designs")
async def register_design(
    payload: DesignRequest, request: Request, db: AsyncSession = Depends(get_db_session)
) -> Any:
    try:
        return await _service(db).register_design(payload.model_dump(), _actor(request))
    except IPLCIError as exc:
        raise _handle(exc)


@router.post("/designs/check")
async def check_design(
    payload: DesignCheckRequest, request: Request, db: AsyncSession = Depends(get_db_session)
) -> Any:
    try:
        return await _service(db).check_design(payload.model_dump(exclude_none=True), _actor(request))
    except IPLCIError as exc:
        raise _handle(exc)


@router.post("/dependencies")
async def record_dependency(
    payload: DependencyRequest, request: Request, db: AsyncSession = Depends(get_db_session)
) -> Any:
    try:
        return await _service(db).record_dependency(payload.model_dump(), _actor(request))
    except IPLCIError as exc:
        raise _handle(exc)


@router.get("/dependencies")
async def list_dependencies(project_id: str, db: AsyncSession = Depends(get_db_session)) -> Any:
    return await _service(db).store.list_dependencies(project_id)


@router.post("/dependencies/check")
async def check_dependency(
    payload: DependencyCheckRequest, request: Request, db: AsyncSession = Depends(get_db_session)
) -> Any:
    try:
        return await _service(db).check_dependency(payload.model_dump(exclude_none=True), _actor(request))
    except IPLCIError as exc:
        raise _handle(exc)


@router.post("/source-origin/check")
async def check_source_origin(
    payload: OriginCheckRequest, request: Request, db: AsyncSession = Depends(get_db_session)
) -> Any:
    try:
        return await _service(db).check_source_origin(payload.model_dump(exclude_none=True), _actor(request))
    except IPLCIError as exc:
        raise _handle(exc)


@router.post("/sboms")
async def record_sbom(
    payload: SbomRequest, request: Request, db: AsyncSession = Depends(get_db_session)
) -> Any:
    try:
        return await _service(db).record_sbom(payload.model_dump(), _actor(request))
    except IPLCIError as exc:
        raise _handle(exc)


@router.get("/sboms/{sbom_id}/report")
async def sbom_report(sbom_id: str, db: AsyncSession = Depends(get_db_session)) -> Any:
    try:
        return await _service(db).sbom_report(sbom_id)
    except IPLCIError as exc:
        raise _handle(exc)


@router.get("/risk-decisions/{decision_id}")
async def get_risk_decision(decision_id: str, db: AsyncSession = Depends(get_db_session)) -> Any:
    decision = await _service(db).risk_decision(decision_id)
    if not decision:
        raise HTTPException(status_code=404, detail={"code": "IPLCI_NOT_FOUND"})
    return decision


# --- Phase 3: collection legality, privacy and AI-training governance ---

class CollectionCheckRequest(BaseModel):
    source_uri: str
    intended_use: str = "research"
    flags: Dict[str, Any] = Field(default_factory=dict)


class PrivacyRequest(BaseModel):
    source_id: Optional[str] = None
    jurisdiction: str = "ZA"
    purpose: str = "research"
    operation: str = "analyse"
    personal_data_present: bool = False
    data_categories: List[str] = Field(default_factory=list)
    lawful_basis: Optional[str] = None
    explicit_consent: bool = False
    dpia_completed: bool = False
    minimisation_applied: bool = False
    retention_period: Optional[str] = None
    deletion_supported: bool = False
    deletion_requested: bool = False
    deletion_completed: bool = False
    dsar_requested: bool = False
    dsar_completed: bool = False
    international_transfer: bool = False
    transfer_mechanism: Optional[str] = None
    disclosure_permitted: bool = False


class PrivacyCheckRequest(BaseModel):
    subject: str = "privacy_record"
    jurisdiction: str = "ZA"
    purpose: str = "research"
    operation: str = "analyse"
    personal_data_present: bool = False
    data_categories: List[str] = Field(default_factory=list)
    lawful_basis: Optional[str] = None
    explicit_consent: bool = False
    dpia_completed: bool = False
    minimisation_applied: bool = False
    retention_period: Optional[str] = None
    deletion_supported: bool = False
    deletion_requested: bool = False
    deletion_completed: bool = False
    international_transfer: bool = False
    transfer_mechanism: Optional[str] = None
    disclosure_permitted: bool = False


class TrainingApprovalRequest(BaseModel):
    source_id: Optional[str] = None
    dataset_id: Optional[str] = None
    approver: str
    ingestion_reviewer: str
    decision: str = "approved"
    basis: Optional[str] = None
    purpose: Optional[str] = None
    expires_at: Optional[str] = None


class TrainingGateRequest(BaseModel):
    source_id: str
    dataset_id: str
    approval_id: Optional[str] = None
    jurisdiction: Optional[str] = None
    now: Optional[str] = None


class FoundationModelRequest(BaseModel):
    model_id: str
    licence_id: Optional[str] = None
    commercial: bool = False
    modify: bool = False
    redistribute: bool = False


class ProviderRequest(BaseModel):
    provider: str = "external_provider"
    retains_prompts: bool = False
    retains_prompts_without_permission: bool = False
    uses_submissions_for_training: bool = False
    output_ownership_unclear: bool = False
    confidential_data: bool = False
    confidential_processing_permitted: bool = False
    international_transfer: bool = False
    transfer_mechanism: Optional[str] = None
    international_transfer_unauthorised: bool = False
    terms_do_not_permit_operation: bool = False
    terms_verified: bool = False


class LineageRequest(BaseModel):
    model_id: str
    base_model: str
    base_model_version: Optional[str] = None
    base_model_licence: Optional[str] = None
    dataset_ids: List[str] = Field(default_factory=list)
    approval_ids: List[str] = Field(default_factory=list)
    evaluation_ref: Optional[str] = None
    promotion_status: str = "candidate"


@router.post("/collection/check")
async def check_collection(
    payload: CollectionCheckRequest, request: Request, db: AsyncSession = Depends(get_db_session)
) -> Any:
    data = payload.model_dump()
    data.update(data.pop("flags"))
    try:
        return await _service(db).assess_collection(data, _actor(request))
    except IPLCIError as exc:
        raise _handle(exc)


@router.get("/collection/checks/{check_id}")
async def get_collection_check(check_id: str, db: AsyncSession = Depends(get_db_session)) -> Any:
    check = await _service(db).collection_check(check_id)
    if not check:
        raise HTTPException(status_code=404, detail={"code": "IPLCI_NOT_FOUND"})
    return check


@router.post("/privacy/records")
async def record_privacy(
    payload: PrivacyRequest, request: Request, db: AsyncSession = Depends(get_db_session)
) -> Any:
    try:
        return await _service(db).record_privacy(payload.model_dump(), _actor(request))
    except IPLCIError as exc:
        raise _handle(exc)


@router.get("/privacy/records/{record_id}")
async def get_privacy_record(record_id: str, db: AsyncSession = Depends(get_db_session)) -> Any:
    record = await _service(db).privacy_record(record_id)
    if not record:
        raise HTTPException(status_code=404, detail={"code": "IPLCI_NOT_FOUND"})
    return record


@router.post("/privacy/check")
async def check_privacy(
    payload: PrivacyCheckRequest, request: Request, db: AsyncSession = Depends(get_db_session)
) -> Any:
    try:
        return await _service(db).assess_privacy(payload.model_dump(), _actor(request))
    except IPLCIError as exc:
        raise _handle(exc)


@router.post("/training-approvals")
async def record_training_approval_route(
    payload: TrainingApprovalRequest, request: Request, db: AsyncSession = Depends(get_db_session)
) -> Any:
    try:
        return await _service(db).record_training_approval(payload.model_dump(exclude_none=True), _actor(request))
    except IPLCIError as exc:
        raise _handle(exc)


@router.post("/training/gate")
async def training_gate_route(
    payload: TrainingGateRequest, request: Request, db: AsyncSession = Depends(get_db_session)
) -> Any:
    try:
        return await _service(db).training_gate(payload.model_dump(exclude_none=True), _actor(request))
    except IPLCIError as exc:
        raise _handle(exc)


@router.post("/models/check")
async def check_foundation_model(
    payload: FoundationModelRequest, request: Request, db: AsyncSession = Depends(get_db_session)
) -> Any:
    try:
        return await _service(db).assess_foundation_model(payload.model_dump(), _actor(request))
    except IPLCIError as exc:
        raise _handle(exc)


@router.post("/providers/check")
async def check_provider(
    payload: ProviderRequest, request: Request, db: AsyncSession = Depends(get_db_session)
) -> Any:
    return await _service(db).assess_provider(payload.model_dump(), _actor(request))


@router.post("/lineage")
async def register_lineage(
    payload: LineageRequest, request: Request, db: AsyncSession = Depends(get_db_session)
) -> Any:
    try:
        return await _service(db).register_lineage(payload.model_dump(), _actor(request))
    except IPLCIError as exc:
        raise _handle(exc)


@router.get("/lineage/{lineage_id}/check")
async def check_lineage(
    lineage_id: str, request: Request, db: AsyncSession = Depends(get_db_session)
) -> Any:
    try:
        return await _service(db).check_lineage(lineage_id, _actor(request))
    except IPLCIError as exc:
        raise _handle(exc)


# --- Phase 4: jurisdiction, verification, business compliance and ethics ---

class JurisdictionRequest(BaseModel):
    origin: Optional[str] = None
    processing_locations: List[str] = Field(default_factory=list)
    target_markets: List[str] = Field(default_factory=list)
    establishment: Optional[str] = None


class JurisdictionRuleRequest(BaseModel):
    jurisdiction: str
    domain: str
    provision: str
    source_ref: Optional[str] = None
    effective_from: Optional[str] = None


class OfficialSourceRequest(BaseModel):
    authority: str
    authority_type: str = "regulator"
    jurisdiction: str
    url: str
    verified_by: Optional[str] = None
    verified_at: Optional[str] = None
    last_checked_at: Optional[str] = None


class LegalSourceVerifyRequest(BaseModel):
    claim: Optional[str] = None
    authority: str
    jurisdiction: str
    url: str
    provision_ref: str
    document_type: str = "guidance"
    verified_by: Optional[str] = None
    verified_at: Optional[str] = None
    prediction: bool = False


class LegalChangeRequest(BaseModel):
    title: Optional[str] = None
    jurisdiction: Optional[str] = None
    document_type: str = "announcement"
    effective_date: Optional[str] = None
    transitional_provisions: bool = False
    affects_legal_operation: bool = False
    prediction: bool = False


class BusinessRequest(BaseModel):
    description: Optional[str] = None
    domain: str
    action: str = "review"
    jurisdiction: Optional[str] = None
    regulated: bool = False
    cross_border: bool = False
    restricted_party: bool = False
    restricted_jurisdiction: bool = False
    controlled_technology: bool = False
    restricted_destination: bool = False
    unsubstantiated_claim: bool = False
    professional_review_required: bool = False
    human_approval_reference: Optional[str] = None


class ObligationRequest(BaseModel):
    obligation: str
    domain: str = "contract"
    jurisdiction: Optional[str] = None
    source_ref: Optional[str] = None
    responsible_party: Optional[str] = None
    due_at: Optional[str] = None
    evidence_ref: Optional[str] = None


class ResearchEthicsRequest(BaseModel):
    subject: str = "research_activity"
    jurisdiction: Optional[str] = None
    informed_consent: bool = False
    ethics_review_required: bool = False
    ethics_review_completed: bool = False
    children: bool = False
    vulnerable_participants: bool = False
    deception: bool = False
    deception_justified: bool = False
    withdrawal_process: bool = False
    minimisation_applied: bool = False
    harm_risk: bool = False


class IdentityUseRequest(BaseModel):
    subject: str = "identity_use"
    jurisdiction: Optional[str] = None
    impersonation: bool = False
    unauthorised_creator_identity: bool = False
    misleading_endorsement: bool = False
    unauthorised_brand_use: bool = False
    public_statement: bool = False
    authorised: bool = False
    reference_only: bool = False


class CrossBorderRequest(BaseModel):
    origin: str = ""
    destinations: List[str] = Field(default_factory=list)
    jurisdiction: Optional[str] = None
    data_categories: List[str] = Field(default_factory=list)
    transfer_mechanism: Optional[str] = None
    residency_required: bool = False
    onward_transfer: bool = False
    onward_transfer_controls: bool = False
    minimisation_applied: bool = False


@router.post("/jurisdiction/resolve")
async def resolve_jurisdiction(
    payload: JurisdictionRequest, request: Request, db: AsyncSession = Depends(get_db_session)
) -> Any:
    return await _service(db).resolve_jurisdiction(payload.model_dump(exclude_none=True), _actor(request))


@router.get("/jurisdiction/laws")
async def applicable_laws(
    jurisdictions: str, domain: str, db: AsyncSession = Depends(get_db_session)
) -> Any:
    return await _service(db).applicable_laws(jurisdictions.split(","), domain)


@router.post("/jurisdiction/rules")
async def register_jurisdiction_rule(
    payload: JurisdictionRuleRequest, request: Request, db: AsyncSession = Depends(get_db_session)
) -> Any:
    try:
        return await _service(db).register_jurisdiction_rule(payload.model_dump(), _actor(request))
    except IPLCIError as exc:
        raise _handle(exc)


@router.post("/official-sources")
async def register_official_source(
    payload: OfficialSourceRequest, request: Request, db: AsyncSession = Depends(get_db_session)
) -> Any:
    try:
        return await _service(db).register_official_source(payload.model_dump(), _actor(request))
    except IPLCIError as exc:
        raise _handle(exc)


@router.post("/legal-sources/verify")
async def verify_legal_source(
    payload: LegalSourceVerifyRequest, request: Request, db: AsyncSession = Depends(get_db_session)
) -> Any:
    return await _service(db).verify_legal_source(payload.model_dump(exclude_none=True), _actor(request))


@router.get("/legal-sources/verify/{verification_id}")
async def get_knowledge_verification(verification_id: str, db: AsyncSession = Depends(get_db_session)) -> Any:
    record = await _service(db).knowledge_verification(verification_id)
    if not record:
        raise HTTPException(status_code=404, detail={"code": "IPLCI_NOT_FOUND"})
    return record


@router.post("/legal-changes/check")
async def check_legal_change(
    payload: LegalChangeRequest, request: Request, db: AsyncSession = Depends(get_db_session)
) -> Any:
    try:
        return await _service(db).assess_legal_change(payload.model_dump(exclude_none=True), _actor(request))
    except IPLCIError as exc:
        raise _handle(exc)


@router.post("/business/check")
async def check_business(
    payload: BusinessRequest, request: Request, db: AsyncSession = Depends(get_db_session)
) -> Any:
    try:
        return await _service(db).assess_business(payload.model_dump(exclude_none=True), _actor(request))
    except IPLCIError as exc:
        raise _handle(exc)


@router.get("/business/reviews/{review_id}")
async def get_business_review(review_id: str, db: AsyncSession = Depends(get_db_session)) -> Any:
    record = await _service(db).business_review(review_id)
    if not record:
        raise HTTPException(status_code=404, detail={"code": "IPLCI_NOT_FOUND"})
    return record


@router.post("/obligations")
async def record_obligation(
    payload: ObligationRequest, request: Request, db: AsyncSession = Depends(get_db_session)
) -> Any:
    try:
        return await _service(db).record_obligation(payload.model_dump(exclude_none=True), _actor(request))
    except IPLCIError as exc:
        raise _handle(exc)


@router.get("/obligations")
async def list_obligations(db: AsyncSession = Depends(get_db_session)) -> Any:
    return await _service(db).obligations()


@router.post("/ethics/research")
async def check_research_ethics(
    payload: ResearchEthicsRequest, request: Request, db: AsyncSession = Depends(get_db_session)
) -> Any:
    return await _service(db).assess_research_ethics(payload.model_dump(), _actor(request))


@router.post("/ethics/identity")
async def check_identity_use(
    payload: IdentityUseRequest, request: Request, db: AsyncSession = Depends(get_db_session)
) -> Any:
    return await _service(db).assess_identity_use(payload.model_dump(), _actor(request))


@router.post("/ethics/cross-border")
async def check_cross_border(
    payload: CrossBorderRequest, request: Request, db: AsyncSession = Depends(get_db_session)
) -> Any:
    return await _service(db).assess_cross_border(payload.model_dump(), _actor(request))


@router.get("/ethics/reviews/{review_id}")
async def get_ethics_review(review_id: str, db: AsyncSession = Depends(get_db_session)) -> Any:
    record = await _service(db).ethics_review(review_id)
    if not record:
        raise HTTPException(status_code=404, detail={"code": "IPLCI_NOT_FOUND"})
    return record


# --- Phase 5: disputes, incidents, holds, monitoring and continuity ---

class DisputeRequest(BaseModel):
    case_type: str
    complainant: Optional[str] = None
    identity_ref: Optional[str] = None
    authority_evidence: Optional[str] = None
    asserted_right: Optional[str] = None
    owner_match: bool = False
    register_match: bool = False
    claim_ref: Optional[str] = None
    affected_assets: List[str] = Field(default_factory=list)
    affected_datasets: List[str] = Field(default_factory=list)
    affected_models: List[str] = Field(default_factory=list)
    evidence_refs: List[str] = Field(default_factory=list)
    deadlines: List[str] = Field(default_factory=list)


class DisputeStatusRequest(BaseModel):
    status: str
    note: str = ""


class IncidentRequest(BaseModel):
    incident_type: str
    detected_at: Optional[str] = None
    stopped_at: Optional[str] = None
    affected_sources: List[str] = Field(default_factory=list)
    affected_projects: List[str] = Field(default_factory=list)
    affected_models: List[str] = Field(default_factory=list)
    exposure_assessment: Optional[str] = None
    notification_required: bool = False
    notification_decision: Optional[str] = None
    disclosure_type: Optional[str] = None


class LegalHoldRequest(BaseModel):
    reason: str
    case_id: Optional[str] = None
    scope: List[str] = Field(default_factory=list)


class RightsContactRequest(BaseModel):
    party_id: Optional[str] = None
    request_type: str
    requested_rights: List[str] = Field(default_factory=list)
    agreement_ref: Optional[str] = None
    review_date: Optional[str] = None


class DeadlineRequest(BaseModel):
    deadline_type: str
    source_ref: Optional[str] = None
    jurisdiction: Optional[str] = None
    due_at: Optional[str] = None
    notify_before: Optional[str] = None
    proof_ref: Optional[str] = None


class ReassessmentRequest(BaseModel):
    licence_changed: bool = False
    law_changed: bool = False
    ownership_changed: bool = False
    permission_revoked: bool = False
    jurisdiction_changed: bool = False


class EvidenceRequest(BaseModel):
    asset_id: Optional[str] = None
    case_id: Optional[str] = None
    legal_hold_id: Optional[str] = None
    source_url: Optional[str] = None
    document_ref: Optional[str] = None
    legal_provision_ref: Optional[str] = None
    licence_version: Optional[str] = None
    captured_at: Optional[str] = None
    jurisdiction: Optional[str] = None
    content_hash: Optional[str] = None
    retention_until: Optional[str] = None


class ContinuityRequest(BaseModel):
    signed_policy_version: Optional[str] = None
    evidence_complete: bool = False
    gateway_unavailable: bool = False


@router.post("/disputes")
async def register_dispute(
    payload: DisputeRequest, request: Request, db: AsyncSession = Depends(get_db_session)
) -> Any:
    try:
        return await _service(db).register_dispute(payload.model_dump(), _actor(request))
    except IPLCIError as exc:
        raise _handle(exc)


@router.get("/disputes")
async def list_disputes(db: AsyncSession = Depends(get_db_session)) -> Any:
    return await _service(db).disputes()


@router.get("/disputes/{dispute_id}")
async def get_dispute(dispute_id: str, db: AsyncSession = Depends(get_db_session)) -> Any:
    record = await _service(db).dispute(dispute_id)
    if not record:
        raise HTTPException(status_code=404, detail={"code": "IPLCI_NOT_FOUND"})
    return record


@router.post("/disputes/{dispute_id}/status")
async def update_dispute_status(
    dispute_id: str,
    payload: DisputeStatusRequest,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
) -> Any:
    try:
        return await _service(db).update_dispute_status(
            dispute_id, payload.status, _actor(request), payload.note
        )
    except IPLCIError as exc:
        raise _handle(exc)


@router.post("/incidents")
async def open_incident(
    payload: IncidentRequest, request: Request, db: AsyncSession = Depends(get_db_session)
) -> Any:
    try:
        return await _service(db).open_incident(payload.model_dump(), _actor(request))
    except IPLCIError as exc:
        raise _handle(exc)


@router.get("/incidents/{incident_id}")
async def get_incident(incident_id: str, db: AsyncSession = Depends(get_db_session)) -> Any:
    record = await _service(db).incident(incident_id)
    if not record:
        raise HTTPException(status_code=404, detail={"code": "IPLCI_NOT_FOUND"})
    return record


@router.post("/legal-holds")
async def place_legal_hold(
    payload: LegalHoldRequest, request: Request, db: AsyncSession = Depends(get_db_session)
) -> Any:
    try:
        return await _service(db).place_legal_hold(payload.model_dump(), _actor(request))
    except IPLCIError as exc:
        raise _handle(exc)


@router.post("/legal-holds/{hold_id}/release")
async def release_legal_hold(
    hold_id: str, request: Request, db: AsyncSession = Depends(get_db_session)
) -> Any:
    try:
        return await _service(db).release_legal_hold(hold_id, _actor(request))
    except IPLCIError as exc:
        raise _handle(exc)


@router.get("/evidence/guard")
async def evidence_guard(
    hold_id: Optional[str] = None, db: AsyncSession = Depends(get_db_session)
) -> Any:
    try:
        return await _service(db).evidence_guard(hold_id)
    except IPLCIError as exc:
        raise _handle(exc)


@router.post("/rights-contacts")
async def record_rights_contact(
    payload: RightsContactRequest, request: Request, db: AsyncSession = Depends(get_db_session)
) -> Any:
    try:
        return await _service(db).record_rights_contact(payload.model_dump(), _actor(request))
    except IPLCIError as exc:
        raise _handle(exc)


@router.get("/rights-contacts")
async def list_rights_contacts(db: AsyncSession = Depends(get_db_session)) -> Any:
    return await _service(db).rights_contacts()


@router.post("/deadlines")
async def record_deadline(
    payload: DeadlineRequest, request: Request, db: AsyncSession = Depends(get_db_session)
) -> Any:
    try:
        return await _service(db).record_deadline(payload.model_dump(), _actor(request))
    except IPLCIError as exc:
        raise _handle(exc)


@router.get("/calendar")
async def compliance_calendar(
    now: Optional[str] = None, db: AsyncSession = Depends(get_db_session)
) -> Any:
    return await _service(db).compliance_calendar(now)


@router.get("/permission-changes")
async def permission_changes(
    now: Optional[str] = None, db: AsyncSession = Depends(get_db_session)
) -> Any:
    return await _service(db).permission_changes(now)


@router.post("/reassessment/check")
async def check_reassessment(
    payload: ReassessmentRequest, request: Request, db: AsyncSession = Depends(get_db_session)
) -> Any:
    return await _service(db).check_reassessment(payload.model_dump(), _actor(request))


@router.post("/evidence")
async def record_evidence(
    payload: EvidenceRequest, request: Request, db: AsyncSession = Depends(get_db_session)
) -> Any:
    return await _service(db).record_evidence(payload.model_dump(exclude_none=True), _actor(request))


@router.post("/evidence/{evidence_id}/retention")
async def retention_decision(
    evidence_id: str, now: Optional[str] = None, db: AsyncSession = Depends(get_db_session)
) -> Any:
    try:
        return await _service(db).retention_decision(evidence_id, now)
    except IPLCIError as exc:
        raise _handle(exc)


@router.post("/continuity/check")
async def continuity_check_route(
    payload: ContinuityRequest, request: Request, db: AsyncSession = Depends(get_db_session)
) -> Any:
    return await _service(db).continuity_check(payload.model_dump(), _actor(request))


@router.get("/continuity/{record_id}")
async def get_continuity(record_id: str, db: AsyncSession = Depends(get_db_session)) -> Any:
    record = await _service(db).continuity_record(record_id)
    if not record:
        raise HTTPException(status_code=404, detail={"code": "IPLCI_NOT_FOUND"})
    return record


# --- Phase 6: signed policies and enforcement status ---

class PolicyRequest(BaseModel):
    version: str
    rules: Dict[str, Any] = Field(default_factory=dict)
    signed_by: Optional[str] = None
    signed_at: Optional[str] = None
    human_approval_reference: Optional[str] = None


@router.post("/policies")
async def record_policy(
    payload: PolicyRequest, request: Request, db: AsyncSession = Depends(get_db_session)
) -> Any:
    try:
        return await _service(db).record_policy(payload.model_dump(exclude_none=True), _actor(request))
    except IPLCIError as exc:
        raise _handle(exc)


@router.get("/policies/active")
async def active_policy(db: AsyncSession = Depends(get_db_session)) -> Any:
    return await _service(db).verify_active_policy()


@router.post("/policies/relaxation/check")
async def policy_relaxation_check(
    payload: PolicyRequest, request: Request, db: AsyncSession = Depends(get_db_session)
) -> Any:
    return await _service(db).check_policy_relaxation(payload.model_dump(exclude_none=True), _actor(request))


# --- Legal validation workflow (counsel completion track) ---

class ValidationTaskRequest(BaseModel):
    domain: str
    subject: str
    question: str
    jurisdiction: Optional[str] = None
    official_source_url: Optional[str] = None
    provision_ref: Optional[str] = None
    assigned_counsel: Optional[str] = None
    notes: Optional[str] = None


class ValidationEvidenceRequest(BaseModel):
    evidence_ref: str
    assigned_counsel: Optional[str] = None


class ValidationVerifyRequest(BaseModel):
    reviewer_reference: str
    valid_until: Optional[str] = None
    official_source_url: Optional[str] = None
    provision_ref: Optional[str] = None


@router.post("/validation/seed-free-evidence")
async def seed_free_validation_evidence(
    request: Request, db: AsyncSession = Depends(get_db_session)
) -> Any:
    """Attach free official-source URLs as evidence; never verifies tasks."""
    from app.services.iplci.free_evidence import seed_validation_evidence

    return await seed_validation_evidence(_service(db), _actor(request))


@router.post("/validation/tasks")
async def open_validation_task(
    payload: ValidationTaskRequest, request: Request, db: AsyncSession = Depends(get_db_session)
) -> Any:
    try:
        return await _service(db).open_validation_task(payload.model_dump(exclude_none=True), _actor(request))
    except IPLCIError as exc:
        raise _handle(exc)


@router.get("/validation/tasks")
async def list_validation_tasks(db: AsyncSession = Depends(get_db_session)) -> Any:
    return await _service(db).validation_tasks()


@router.post("/validation/tasks/{task_id}/evidence")
async def record_validation_evidence(
    task_id: str,
    payload: ValidationEvidenceRequest,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
) -> Any:
    try:
        return await _service(db).record_validation_evidence(
            task_id, payload.model_dump(exclude_none=True), _actor(request)
        )
    except IPLCIError as exc:
        raise _handle(exc)


@router.post("/validation/tasks/{task_id}/verify")
async def verify_validation_task(
    task_id: str,
    payload: ValidationVerifyRequest,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
) -> Any:
    try:
        return await _service(db).verify_validation_task(
            task_id, payload.model_dump(exclude_none=True), _actor(request)
        )
    except IPLCIError as exc:
        raise _handle(exc)


@router.get("/validation/readiness")
async def validation_readiness(db: AsyncSession = Depends(get_db_session)) -> Any:
    return await _service(db).readiness_report()
