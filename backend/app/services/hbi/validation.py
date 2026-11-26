"""Document 26 (OD-45): scientific validation from graded evidence.

Backtest cases are derived only from verified, dated records with documented
outcomes. Where real evidence is insufficient, the pipeline refuses to claim
validation instead of falling back to synthetic fixtures.
"""

from collections import defaultdict
from typing import Any, Dict, List, Set, Tuple

from app.services.hbi.chronology import _year
from app.services.hbi.prediction import HistoricalCase, backtest, brier

MIN_CASES = 10
MIN_GROUP_N = 5
DISPARITY_THRESHOLD = 0.15


def _first_year(record: Dict[str, Any], *paths: Tuple[str, ...]) -> int | None:
    dims = record.get("context_dimensions") or {}
    for path in paths:
        value: Any = dims
        for key in path:
            if not isinstance(value, dict):
                value = None
                break
            value = value.get(key)
        if value is not None:
            if isinstance(value, dict):
                value = value.get("value") or value.get("observed_at")
            year = _year(value)
            if year is not None:
                return int(year)
    for evidence in record.get("evidence") or []:
        year = _year(evidence.get("collection_date"))
        if year is not None:
            return int(year)
    return None


def _outcome(record: Dict[str, Any]) -> int | None:
    dims = record.get("context_dimensions") or {}
    outcome = dims.get("outcome")
    if isinstance(outcome, dict):
        outcome = outcome.get("value")
    if outcome in {1, "1", "positive", True}:
        return 1
    if outcome in {0, "0", "negative", False}:
        return 0
    return None


def build_cases(records: List[Dict[str, Any]], approved_ids: Set[str] = None) -> Dict[str, Any]:
    """Derive leakage-safe cases from dated, verified records only."""
    cases = []
    excluded = []
    for record in records:
        if record.get("provenance_kind") == "licensed_corpus" and approved_ids is not None:
            evidence = record.get("evidence") or []
            source_id = str(evidence[0].get("source_id")) if evidence else ""
            if source_id not in approved_ids:
                excluded.append({"record_ref": record.get("record_ref"), "reason": "source_not_approved"})
                continue
        if record.get("provenance_kind") == "illustrative_fixture":
            excluded.append({"record_ref": record.get("record_ref"), "reason": "illustrative_fixture_excluded"})
            continue
        if record.get("evidence_class") not in {"verified", "well_supported"}:
            excluded.append({"record_ref": record.get("record_ref"), "reason": "insufficient_evidence_grade"})
            continue
        cutoff = _first_year(record, ("time",), ("environment", "observed_at"), ("context", "observed_at"))
        outcome_year = _first_year(record, ("outcome", "observed_at"), ("outcome", "date"))
        outcome = _outcome(record)
        if cutoff is None or outcome_year is None or outcome is None:
            excluded.append({"record_ref": record.get("record_ref"), "reason": "missing_date_or_outcome"})
            continue
        if outcome_year <= cutoff:
            excluded.append({"record_ref": record.get("record_ref"), "reason": "outcome_not_after_cutoff"})
            continue
        features = {"support": float(record.get("confidence", 0.5))} if outcome == 1 else {"against_support": float(record.get("confidence", 0.5))}
        cases.append(HistoricalCase(
            case_id=record["record_ref"], cutoff_year=cutoff,
            outcome_year=outcome_year, features=features, outcome=outcome,
        ))
    return {
        "cases": cases,
        "count": len(cases),
        "excluded": excluded,
        "provenance": "derived_from_graded_records",
        "note": "Synthetic fixtures are never mixed into validation cases.",
    }


def bias_report(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Measure performance disparities across recorded populations, not sensitive traits."""
    groups = defaultdict(list)
    for record in records:
        population = record.get("population") or "unrecorded"
        groups[str(population)].append(record)
    results = []
    for population, items in groups.items():
        pairs = []
        for record in items:
            outcome = _outcome(record)
            if outcome is not None:
                pairs.append((float(record.get("confidence", 0.5)), outcome))
        results.append({
            "population": population,
            "n": len(items),
            "n_with_outcomes": len(pairs),
            "brier": brier(pairs) if pairs else None,
            "mean_confidence": round(sum(r.get("confidence", 0.0) for r in items) / len(items), 3),
            "sufficient": len(pairs) >= MIN_GROUP_N,
        })
    scored = [item for item in results if item["brier"] is not None and item["sufficient"]]
    disparity = None
    if len(scored) >= 2:
        disparity = round(max(item["brier"] for item in scored) - min(item["brier"] for item in scored), 3)
    return {
        "groups": results,
        "disparity": disparity,
        "disparity_threshold": DISPARITY_THRESHOLD,
        "flag": disparity is not None and disparity > DISPARITY_THRESHOLD,
        "note": "Population labels are descriptive cohorts; sensitive traits are never inferred.",
    }


def corpus_readiness(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Report whether licensed evidence, not fixtures, is available for validation."""
    counts = defaultdict(int)
    for record in records:
        counts[str(record.get("provenance_kind", "direct_observation"))] += 1
    licensed = counts["licensed_corpus"]
    blockers = []
    if licensed < MIN_CASES:
        blockers.append(f"licensed_corpus_records_below_{MIN_CASES}")
    return {
        "provenance_counts": dict(counts),
        "licensed_records": licensed,
        "illustrative_fixtures": counts["illustrative_fixture"],
        "ready_for_validation": not blockers,
        "blockers": blockers,
        "note": "Illustrative fixtures never satisfy validation; only licensed evidence counts.",
    }


def report(service: Any, model_id: str = "ensemble") -> Dict[str, Any]:
    """Combine case derivation, backtesting and bias into a validation verdict."""
    from app.services.hbi.prediction import EvidenceForecaster

    records = service.store.all()
    governance = getattr(service, "corpus_governance", None)
    approved_ids = governance.approved_ids() if governance is not None else None
    derived = build_cases(records, approved_ids)
    bias = bias_report(records)
    blockers = []

    if derived["count"] < MIN_CASES:
        blockers.append("insufficient_real_backtest_cases")
    if bias["flag"]:
        blockers.append("group_disparity_above_threshold")

    scores = None
    if derived["cases"]:
        factory = type(service.predictor.models.get(model_id, EvidenceForecaster()))
        result = backtest(derived["cases"], factory=factory)
        scores = result["scores"]
        if scores["brier"] > 0.30:
            blockers.append("brier_above_threshold")
        if scores["ece"] > 0.20:
            blockers.append("calibration_above_threshold")

    return {
        "verdict": "validated" if not blockers else "not_validated",
        "blockers": blockers,
        "cases": derived["count"],
        "excluded_records": len(derived["excluded"]),
        "scores": scores,
        "bias": bias,
        "provenance": derived["provenance"],
        "note": "No validation claim is made from illustrative fixtures or unverified records.",
    }
