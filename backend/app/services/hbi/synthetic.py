"""Document 27 (proposed OD-47): original synthetic research generation.

Creates IAM-owned behavioural scenarios from permitted free research material.
Synthetic outputs are never presented as empirical evidence and are excluded
from validation case derivation.
"""

from hashlib import sha256
from typing import Any, Dict, List, cast

from app.services.hbi.schemas import EvidenceClass, KnowledgeRecordInput

SCENARIO_TEMPLATES = [
    "A community receives {topic}; how might trust and participation change?",
    "A team faces {topic}; what decision biases could appear under uncertainty?",
    "During {topic}, which social norms could amplify or reduce cooperation?",
    "A leader communicates {topic}; what emotional and rhetorical responses are plausible?",
    "After {topic}, how might information sharing differ across cultural contexts?",
]


def build_scenarios(claims: List[str], count: int = 5) -> List[str]:
    topics = []
    for claim in claims:
        topic = claim.strip().rstrip(".")
        if 20 <= len(topic) <= 240:
            topics.append(topic[:200])
        if len(topics) >= count:
            break
    if not topics:
        return []
    scenarios = []
    for index in range(count):
        template = SCENARIO_TEMPLATES[index % len(SCENARIO_TEMPLATES)]
        scenarios.append(template.format(topic=topics[index % len(topics)]))
    return list(dict.fromkeys(scenarios))


def to_records(scenarios: List[str], study_ref: str) -> List[KnowledgeRecordInput]:
    records = []
    for index, scenario in enumerate(scenarios):
        digest = sha256(f"{study_ref}:{scenario}".encode("utf-8")).hexdigest()[:12]
        records.append(KnowledgeRecordInput(
            claim=scenario,
            epistemic_type=cast(Any, "hypothesis"),
            evidence_class=EvidenceClass.SPECULATION,
            alternatives=["not_supported_without_empirical_test"],
            falsifier="empirical study shows no such response pattern",
            confidence=0.0,
            provenance_kind="synthetic",
            module_ids=[15],
            evidence=cast(Any, [{
                "source_id": f"synthetic_{digest}",
                "source_type": "synthetic_scenario",
                "locator": study_ref,
                "grade": "speculation",
                "licence": "iam_original",
                "permitted_purpose": "research",
            }]),
        ))
    return records
