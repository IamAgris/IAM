"""Document 26 (OD-45): module 15 — Behavioural Learning and Evaluation.

Reports evaluation state from the Validation, Drift and Registry engines.
It does not promote models or rewrite predictions.
"""

from typing import Any, Dict, List


def analyse(records: List[Dict[str, Any]], predictor: Any) -> Dict[str, Any]:
    from app.services.hbi import lifecycle, validation

    models = []
    for model_id in predictor.models:
        record = predictor.validation.get(model_id, {})
        scores = record.get("scores", {})
        models.append({
            "model_id": model_id,
            "active_version": predictor.active_version(model_id),
            "validated": bool(record.get("validated")),
            "brier": scores.get("brier"),
            "backtest_cases": scores.get("n", 0),
        })
    bias = validation.bias_report(records)
    drift = lifecycle.drift_report(records)
    return {
        "module_id": 15,
        "name": "Behavioural Learning and Evaluation",
        "status": "implemented",
        "models": models,
        "bias_flag": bias["flag"],
        "drift_detected": drift["drift_detected"],
        "caveat": "Evaluation evidence; not an authorisation to promote a model.",
        "note": "Failed predictions are retained as learning assets, never deleted.",
    }
