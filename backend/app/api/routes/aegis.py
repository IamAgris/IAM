"""IAM Aegis routes — defensive security engine.

All endpoints are defensive: analyse untrusted content, verify scope,
audit local paths, check egress policy, run safe self-tests.
No offensive operation is exposed.
"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Dict, Any

from app.services.aegis import aegis

router = APIRouter(prefix="/api/v1/aegis", tags=["aegis"])


class TextRequest(BaseModel):
    text: str
    source: str = "input"


class ScopeRequest(BaseModel):
    target: str
    authorized_targets: List[str]
    action: str = "read"


class PathRequest(BaseModel):
    path: str


class EgressRequest(BaseModel):
    url: str
    allowed_hosts: List[str]


class FindingRequest(BaseModel):
    finding: Dict[str, Any]


@router.post("/analyze")
async def analyze(request: TextRequest):  # type: ignore[no-untyped-def]
    """Detect prompt injection, extraction and sensitive data in untrusted text."""
    return aegis.analyze_text(request.text, request.source)


@router.post("/verify-scope")
async def verify_scope(request: ScopeRequest):  # type: ignore[no-untyped-def]
    """Verify a target is within authorized scope before assessment."""
    return aegis.verify_scope(request.target, request.authorized_targets, request.action)


@router.post("/audit-path")
async def audit_path(request: PathRequest):  # type: ignore[no-untyped-def]
    """Defensive local file/directory permission audit."""
    return aegis.audit_path(request.path)


@router.get("/recommendation/{finding_type}")
async def recommend(finding_type: str):  # type: ignore[no-untyped-def]
    """Safe, non-destructive remediation advice (never auto-applied)."""
    return {"finding_type": finding_type, "recommendation": aegis.recommend_fix(finding_type)}


@router.post("/check-egress")
async def check_egress(request: EgressRequest):  # type: ignore[no-untyped-def]
    """Prevent SSRF/internal/metadata access — allowlist enforcement."""
    return aegis.scan_outbound(request.url, request.allowed_hosts)


@router.post("/shareable-finding")
async def shareable(request: FindingRequest):  # type: ignore[no-untyped-def]
    """Convert a finding to privacy-safe shareable threat intelligence."""
    return aegis.shareable_finding(request.finding)


@router.post("/self-test")
async def self_test():  # type: ignore[no-untyped-def]
    """Run safe local defensive tests."""
    return aegis.self_test()


@router.get("/report")
async def report():  # type: ignore[no-untyped-def]
    """Aegis operational report."""
    return aegis.report()
