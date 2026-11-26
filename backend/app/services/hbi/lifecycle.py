"""Document 26 (OD-45): operational lifecycle monitoring.

Detects confidence drift, plans periodic re-evaluation and exercises rollback
without weakening the validation gate.
"""

from collections import defaultdict
from typing import Any, Dict, List

from app.services.hbi.chronology import _year

DRIFT_THRESHOLD = 0.20
MIN_PERIOD_RECORDS = 3


def _record_year(record: Dict[str, Any]) -> int | None:
    dims = record.get("context_dimensions") or {}
    candidates = [
        dims.get("time"),
        (dims.get("environment") or {}).get("period"),
    ]
    for evidence in record.get("evidence") or []:
        candidates.append(evidence.get("collection_date"))
    for candidate in candidates:
        if isinstance(candidate, dict):
            candidate = candidate.get("value") or candidate.get("observed_at")
        year = _year(candidate)
        if year is not None:
            return int(year)
    return None


def drift_report(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compare mean confidence across dated periods."""
    buckets = defaultdict(list)
    undated = 0
    for record in records:
        year = _record_year(record)
        if year is None:
            undated += 1
        else:
            buckets[year // 10 * 10].append(float(record.get("confidence", 0.0)))
    periods = [
        {"period": f"{decade}s", "n": len(values),
         "mean_confidence": round(sum(values) / len(values), 3)}
        for decade, values in sorted(buckets.items())
    ]
    usable = [item for item in periods if item["n"] >= MIN_PERIOD_RECORDS]
    flag = False
    delta = None
    if len(usable) >= 2:
        delta = round(usable[-1]["mean_confidence"] - usable[0]["mean_confidence"], 3)
        flag = delta <= -DRIFT_THRESHOLD
    return {
        "periods": periods,
        "undated_records": undated,
        "confidence_delta": delta,
        "threshold": DRIFT_THRESHOLD,
        "drift_detected": flag,
        "note": "Drift is a re-evaluation trigger, not proof that a model is wrong.",
    }


def re_evaluation_plan(service: Any) -> Dict[str, Any]:
    """List models needing re-evaluation."""
    records = service.store.all()
    drift = drift_report(records)
    tasks = []
    for model_id in service.predictor.models:
        record = service.predictor.validation.get(model_id, {})
        reasons = []
        if not record.get("validated"):
            reasons.append("not_validated")
        if drift["drift_detected"]:
            reasons.append("confidence_drift")
        if record.get("scores", {}).get("n", 0) < 10:
            reasons.append("small_backtest_sample")
        if reasons:
            tasks.append({"model_id": model_id, "reasons": reasons})
    return {
        "tasks": tasks,
        "count": len(tasks),
        "drift_report": drift,
        "note": "Re-evaluation tasks never auto-promote a model.",
    }


def rollback_drill(predictor: Any, model_id: str = "ensemble") -> Dict[str, Any]:
    """Promote a candidate version, then verify rollback restores the active model."""
    original = predictor.models.get(model_id)
    if original is None:
        return {"passed": False, "reason": "unknown_model"}
    before_version = predictor.active_version(model_id)
    predictor.register_version(model_id, "drill-candidate", object())
    candidate_active = predictor.active_version(model_id) == "drill-candidate"
    result = predictor.rollback(model_id)
    restored = predictor.models.get(model_id) is original
    passed = candidate_active and result.get("rolled_back") and restored
    return {
        "passed": passed,
        "before_version": before_version,
        "after_version": predictor.active_version(model_id),
        "rollback": result,
        "note": "Failed versions remain in immutable history.",
    }
