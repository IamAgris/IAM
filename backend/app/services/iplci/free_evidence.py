"""Free official sources for IPLCI validation evidence (OD-48).

These are publicly accessible, official pages — no paid register, no scraping,
no generated legal opinion. This module opens validation tasks and attaches the
source URL as evidence. It deliberately never calls ``verify_validation_task``:
a qualified human reviewer remains mandatory. Free evidence reduces manual
collection work; it does not replace counsel.
"""

from __future__ import annotations

from typing import Any, Dict, List, Mapping

FREE_OFFICIAL_SOURCES: tuple[Mapping[str, str], ...] = (
    {
        "domain": "privacy",
        "subject": "POPIA",
        "jurisdiction": "ZA",
        "url": "https://www.gov.za/documents/protection-personal-information-act",
        "question": "Confirm the current POPIA provisions relevant to data collection and retention.",
    },
    {
        "domain": "privacy",
        "subject": "GDPR",
        "jurisdiction": "EU",
        "url": "https://eur-lex.europa.eu/eli/reg/2016/679/oj",
        "question": "Confirm the current GDPR lawful-basis and data-subject provisions.",
    },
    {
        "domain": "privacy",
        "subject": "UK GDPR",
        "jurisdiction": "UK",
        "url": "https://www.legislation.gov.uk/eur/2016/679/contents",
        "question": "Confirm the retained UK GDPR provisions after Brexit.",
    },
    {
        "domain": "ai_governance",
        "subject": "EU AI Act",
        "jurisdiction": "EU",
        "url": "https://eur-lex.europa.eu/eli/reg/2024/1689/oj",
        "question": "Confirm the current AI Act obligations relevant to IAM's research and deployment.",
    },
    {
        "domain": "privacy",
        "subject": "CCPA",
        "jurisdiction": "US-CA",
        "url": "https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?sectionNum=1798.100.&lawCode=CIV",
        "question": "Confirm the current CCPA consumer-rights provisions.",
    },
    {
        "domain": "copyright",
        "subject": "DMCA",
        "jurisdiction": "US",
        "url": "https://www.copyright.gov/legislation/dmca.pdf",
        "question": "Confirm the current DMCA notice-and-takedown and anti-circumvention provisions.",
    },
    {
        "domain": "copyright",
        "subject": "EU Copyright Directive",
        "jurisdiction": "EU",
        "url": "https://eur-lex.europa.eu/eli/dir/2019/790/oj",
        "question": "Confirm text-and-data-mining exceptions and rights-management provisions.",
    },
    {
        "domain": "ip",
        "subject": "WIPO Nice Classification",
        "jurisdiction": "INTL",
        "url": "https://www.wipo.int/classifications/nice/en/",
        "question": "Confirm the current Nice classification version relevant to trademark risk signals.",
    },
)


def seed_payloads() -> List[Dict[str, Any]]:
    """Return task payloads with free official evidence URLs attached."""
    return [
        {
            "domain": item["domain"],
            "subject": item["subject"],
            "jurisdiction": item["jurisdiction"],
            "question": item["question"],
            "official_source_url": item["url"],
            "provision_ref": "official_public_text",
            "notes": "Free official source; human verification still required.",
            "evidence": item["url"],
        }
        for item in FREE_OFFICIAL_SOURCES
    ]


async def seed_validation_evidence(service: Any, actor: str = "free-source-adapter") -> Dict[str, Any]:
    """Open tasks and attach evidence; never verify on behalf of a human."""
    created: List[Dict[str, Any]] = []
    for payload in seed_payloads():
        task = await service.open_validation_task(payload, actor=actor)
        record = await service.record_validation_evidence(
            str(task["id"]),
            {"evidence_ref": payload["evidence"]},
            actor=actor,
        )
        created.append({"task_id": str(task["id"]), "status": record["status"]})
    return {
        "created": len(created),
        "tasks": created,
        "note": "All tasks remain in_review; a qualified human reviewer must verify each one.",
    }
