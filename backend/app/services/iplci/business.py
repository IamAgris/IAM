"""Pure business and legal-operations compliance logic (IL-14).

IAM may research, prepare documents and identify obligations independently. It
must not sign contracts, form legal entities, accept settlements, transfer
ownership, waive rights, register IP in its own name or initiate proceedings
without authorised human approval.
"""

from __future__ import annotations

from typing import Any, Dict, List, Mapping

from app.services.iplci.core import IPLCIError

BUSINESS_DOMAINS = (
    "contract", "corporate", "tax", "employment", "consumer",
    "advertising", "competition", "financial", "ecommerce",
    "export_control", "sanctions", "recordkeeping",
)
BINDING_ACTIONS = (
    "sign_contract", "form_entity", "accept_settlement", "transfer_ownership",
    "waive_rights", "initiate_proceedings", "register_ip",
)

DOMAIN_OBLIGATIONS: Dict[str, List[str]] = {
    "contract": ["review obligations, termination clauses and authority limits"],
    "corporate": ["confirm company structure, registration and governance records"],
    "tax": ["identify applicable taxes, filing dates and records"],
    "employment": ["confirm contractor/employee classification and labour obligations"],
    "consumer": ["verify consumer rights, refunds and product representations"],
    "advertising": ["substantiate claims and record required disclosures"],
    "competition": ["screen for anti-competitive conduct and market restrictions"],
    "financial": ["identify payment, investment and financial-service obligations"],
    "ecommerce": ["record online selling terms and digital transaction obligations"],
    "export_control": ["screen controlled technology and destination restrictions"],
    "sanctions": ["screen restricted persons, entities and jurisdictions"],
    "recordkeeping": ["apply statutory records, retention and reporting duties"],
}


def assess_business_activity(activity: Mapping[str, Any]) -> Dict[str, Any]:
    """Screen a proposed business or legal operation."""
    domain = str(activity.get("domain") or "")
    if domain not in BUSINESS_DOMAINS:
        raise IPLCIError("IPLCI_INVALID_INPUT", "invalid business domain")

    obligations = list(DOMAIN_OBLIGATIONS[domain])
    blockers: List[str] = []
    action = str(activity.get("action") or "")
    if action in BINDING_ACTIONS and not activity.get("human_approval_reference"):
        blockers.append(f"{action} requires human authorisation")
    if activity.get("restricted_party") or activity.get("restricted_jurisdiction"):
        blockers.append("sanctions screening identified a restricted party or jurisdiction")
    if activity.get("controlled_technology") and activity.get("restricted_destination"):
        blockers.append("export-controlled technology may not be transferred to this destination")
    if activity.get("unsubstantiated_claim"):
        blockers.append("advertising or product claim is unsubstantiated")

    risk = "LOW"
    if blockers:
        risk = "CRITICAL"
    elif activity.get("regulated") or domain in ("tax", "financial", "export_control", "sanctions"):
        risk = "MODERATE"
    elif activity.get("cross_border"):
        risk = "MODERATE"
        obligations.append("resolve applicable jurisdictions before proceeding")

    if activity.get("professional_review_required"):
        risk = "HIGH" if risk != "CRITICAL" else risk
        obligations.append("obtain qualified professional review")

    outcome = "blocked_pending_human_authorisation" if blockers else (
        "conditional" if risk in ("MODERATE", "HIGH") else "permitted_with_conditions"
    )
    return {
        "domain": "business_compliance",
        "business_domain": domain,
        "action": action or "review",
        "risk": risk,
        "outcome": outcome,
        "blockers": blockers,
        "obligations": obligations,
        "human_approval_required": bool(blockers) or bool(activity.get("human_approval_reference")),
        "can_iam_execute_independently": not blockers and not activity.get("regulated"),
        "reasons": [
            "Legal research and document preparation are independent; binding commitments are not.",
        ],
        "policy_version": "4.0",
    }
