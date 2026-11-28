"""Document 26 (OD-45): research ingestion with provenance and verification.

Phase 1 continuation. Documents are licensed, purpose-checked, language- and
culture-tagged, split into candidate claims, and graded before they enter the
knowledge store. Weak or unlicensed material is quarantined, not silently used.
"""

import re
from typing import Any, Callable, Dict, List, Optional

from app.services.hbi.evidence import rate_source, verify_claim
from app.services.hbi.schemas import KnowledgeRecordInput, ResearchDocumentInput

_SENTENCE = re.compile(r"(?<=[.!?])\s+")
_CUE = re.compile(
    r"\b(people|person|community|group|society|trust|fear|emotion|behavio[u]?r|"
    r"decision|choice|cooperat|conflict|increase|reduce|respond|adapt|believe|norm|leader)",
    re.I,
)
_LANGUAGE_MARKERS = {
    "en": {"the", "and", "people", "research", "community"},
    "fr": {"les", "des", "une", "personnes", "recherche"},
    "de": {"die", "der", "und", "menschen", "forschung"},
    "es": {"los", "las", "una", "personas", "investigacion"},
    "pt": {"os", "as", "uma", "pessoas", "pesquisa"},
    "af": {"die", "en", "mense", "navorsing", "gemeenskap"},
    "zu": {"aba", "izinga", "abantu", "ucwaningo"},
    "ar": {"الناس", "البحث", "المجتمع"},
    "zh": {"人们", "研究", "社会", "社区"},
    "ja": {"人々", "研究", "社会", "地域"},
}
_REGION_TAGS = {
    "africa": ["african_context", "regional_diversity_required"],
    "south_africa": ["south_african_context", "popia_relevant"],
    "europe": ["european_context", "gdpr_relevant"],
    "asia": ["asian_context"],
    "middle_east": ["middle_eastern_context"],
    "americas": ["americas_context"],
    "indigenous": ["indigenous_knowledge_restrictions", "cultural_heritage"],
}
_CAVEAT = (
    "Aggregate research claim. Not a psychological diagnosis or a statement "
    "about any identifiable person. Cultural generalisation is constrained."
)


def detect_language(text: str, supplied: Optional[str] = None) -> str:
    if supplied:
        return supplied
    lowered = text.lower()
    best, best_score = "und", 0
    for code, markers in _LANGUAGE_MARKERS.items():
        score = sum(1 for marker in markers if marker in lowered)
        if score > best_score:
            best, best_score = code, score
    return best if best_score >= 2 else "und"


def cultural_tags(region: Optional[str]) -> List[str]:
    if not region:
        return ["region_not_recorded"]
    return list(_REGION_TAGS.get(region.lower(), ["regional_context_unmapped"]))


def extract_claims(text: str, limit: int = 8) -> List[str]:
    candidates = []
    for sentence in _SENTENCE.split(text.strip()):
        sentence = sentence.strip()
        if 30 <= len(sentence) <= 500 and _CUE.search(sentence):
            candidates.append(sentence)
        if len(candidates) >= limit:
            break
    return candidates


_SCRIPTS = [
    ("latin", re.compile(r"[A-Za-zÀ-ÿ]")),
    ("cyrillic", re.compile(r"[\u0400-\u04FF]")),
    ("arabic", re.compile(r"[\u0600-\u06FF]")),
    ("devanagari", re.compile(r"[\u0900-\u097F]")),
    ("han", re.compile(r"[\u4E00-\u9FFF]")),
    ("kana", re.compile(r"[\u3040-\u30FF]")),
]


def detect_language_detail(text: str, supplied: Optional[str] = None) -> Dict[str, Any]:
    """Language and script identification with an explicit confidence marker."""
    script = "unknown"
    for name, pattern in _SCRIPTS:
        if pattern.search(text):
            script = name
            break
    lowered = text.lower()
    scores = {}
    for code, markers in _LANGUAGE_MARKERS.items():
        scores[code] = sum(1 for marker in markers if marker in lowered)
    best = max(scores, key=lambda code: scores[code]) if scores else "und"
    best_score = scores.get(best, 0)
    if supplied:
        return {"language": supplied, "script": script, "confidence": 1.0, "basis": "supplied"}
    confidence = round(min(0.95, 0.4 + 0.15 * best_score), 2) if best_score else 0.2
    return {
        "language": best if best_score >= 2 else "und",
        "script": script,
        "confidence": confidence,
        "basis": "lexical_markers",
    }


def translate_snippet(text: str, translator: Optional[Callable[[str], str]] = None) -> Dict[str, Any]:
    """Optional translation with provenance; never silently replaces the source."""
    if translator is None:
        return {
            "translated": None, "status": "translation_not_performed",
            "note": "Original text retained; translation requires an authorised provider.",
        }
    return {
        "translated": translator(text), "status": "translated",
        "note": "Translation is a derivative; original source remains authoritative.",
    }


def cross_lingual_duplicates(documents: List[Any], threshold: float = 0.8) -> List[Dict[str, Any]]:
    """Detect near-duplicate documents by shared normalised vocabulary."""
    token_sets = []
    for document in documents:
        tokens = set(re.findall(r"[^\W\d_]{4,}", document.text.lower()))
        token_sets.append((document.source_id, tokens))
    duplicates = []
    for index in range(len(token_sets)):
        for other in range(index + 1, len(token_sets)):
            a, b = token_sets[index], token_sets[other]
            union = a[1] | b[1]
            if not union:
                continue
            similarity = len(a[1] & b[1]) / len(union)
            if similarity >= threshold:
                duplicates.append({"source_a": a[0], "source_b": b[0],
                                   "similarity": round(similarity, 3)})
    return duplicates


class ResearchIngestionService:
    def __init__(self, store: Any, learned_weights: Dict[str, Any] = None):  # type: ignore[assignment]
        self.store = store
        self.learned_weights = learned_weights or {}

    async def ingest(self, document: ResearchDocumentInput) -> Dict[str, Any]:
        """Ingest one licensed document; return accepted/quarantined records."""
        source_rating = rate_source(
            document.source_type, document.licence, document.permitted_purpose,
            learned_weights=self.learned_weights,
        )
        quarantine_reasons: List[str] = []
        if not document.licence:
            quarantine_reasons.append("licence_missing")
        if document.permitted_purpose not in {"research", "historical", "aggregate_analysis"}:
            quarantine_reasons.append("purpose_not_permitted")
        if document.scope.value == "individual":
            quarantine_reasons.append("individual_scope_not_permitted_for_ingestion")
        if source_rating["reliability"] < 0.4:
            quarantine_reasons.append("source_below_reliability_threshold")

        language = detect_language(document.text, document.language)
        tags = cultural_tags(document.region)
        claims = extract_claims(document.text)
        result: Dict[str, Any] = {
            "source_id": document.source_id,
            "title": document.title,
            "language": language,
            "cultural_tags": tags,
            "source_rating": source_rating,
            "candidate_claims": len(claims),
            "accepted": [],
            "quarantined": [],
        }
        if quarantine_reasons or not claims:
            if not claims:
                quarantine_reasons.append("no_behavioural_claims_extracted")
            result["quarantined"] = quarantine_reasons
            self.store.quarantine.append({"source_id": document.source_id, "reasons": quarantine_reasons})
            return result

        for claim in claims:
            evidence = [{
                "source_id": document.source_id,
                "source_type": document.source_type,
                "locator": document.title,
                "grade": source_rating["grade"],
                "licence": document.licence,
                "collection_date": document.collection_date,
                "permitted_purpose": document.permitted_purpose,
            }]
            verification = verify_claim(evidence)
            if verification["evidence_class"] == "unverified":
                result["quarantined"].append(claim[:200])
                self.store.quarantine.append({"source_id": document.source_id, "claim": claim[:200], "reasons": ["unverified"]})
                continue
            payload = KnowledgeRecordInput(
                claim=claim,
                epistemic_type="interpretation",  # type: ignore[arg-type]
                evidence_class=verification["evidence_class"],
                alternatives=["alternative_explanation_not_established_by_this_source"],
                scope=document.scope,
                tier=document.tier,
                population=document.population,
                context_dimensions={
                    "environment": {"region": document.region, "period": document.period},
                    "culture": {"tags": tags},
                    "language": language,
                },
                evidence=evidence,  # type: ignore[arg-type]
                confidence=round(source_rating["reliability"] * 0.8, 2),
                causal_status="correlational",  # type: ignore[arg-type]
                module_ids=document.module_ids,
                provenance_kind="licensed_corpus",
            )
            record = await self.store.add(payload)
            result["accepted"].append({
                "record_ref": record["record_ref"],
                "evidence_class": record["evidence_class"],
                "caveat": _CAVEAT,
            })
        return result

    async def ingest_multilingual(self, documents: List[ResearchDocumentInput],
                                  translator: Optional[Callable[[str], str]] = None) -> Dict[str, Any]:
        """Batch ingestion with language/script detection and duplicate screening."""
        duplicates = cross_lingual_duplicates(documents)
        duplicate_ids = {d["source_b"] for d in duplicates}
        results = []
        for document in documents:
            if document.source_id in duplicate_ids:
                results.append({
                    "source_id": document.source_id,
                    "status": "skipped_duplicate",
                    "note": "Near-duplicate of another source in this batch.",
                })
                continue
            detail = detect_language_detail(document.text, document.language)
            translation = translate_snippet(document.text[:500], translator)
            result = await self.ingest(document)
            result["language_detail"] = detail
            result["translation"] = translation
            results.append(result)
        return {
            "documents": len(documents),
            "duplicates": duplicates,
            "results": results,
            "note": "Public availability does not remove licence, purpose or privacy obligations.",
        }
