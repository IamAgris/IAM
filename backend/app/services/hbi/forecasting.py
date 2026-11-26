"""Document 26 (OD-45): module 13 — Behavioural Forecasting.

A forecast is a probability distribution over labelled scenarios, emitted only
after A8 context approval and explicit model validation. Never a verdict.
"""

import uuid
from typing import Any, Dict, Optional


def scenario_distribution(probability: Dict[str, float], scenarios: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    labels = scenarios or {
        "positive": "Positive response",
        "mixed": "Mixed response",
        "negative": "Negative response",
        "little_response": "Little or no response",
    }
    distribution = []
    for key, value in probability.items():
        distribution.append({
            "outcome": key,
            "description": labels.get(key, key),
            "probability": value,
        })
    total = round(sum(item["probability"] for item in distribution), 4)
    return {
        "scenarios": distribution,
        "probability_sum": total,
        "normalised": abs(total - 1.0) < 0.02,
    }


def forecast(request: Dict[str, Any], model_result: Dict[str, Any]) -> Dict[str, Any]:
    """Wrap a validated model result as a module-13 forecast record."""
    if model_result.get("refusal"):
        return {
            "module_id": 13,
            "prediction_id": None,
            "target": request.get("target"),
            "refusal": model_result["refusal"],
        }
    distribution = scenario_distribution(model_result["probability"])
    return {
        "module_id": 13,
        "prediction_id": "pred_" + uuid.uuid4().hex,
        "target": request.get("target"),
        "time_horizon": request.get("time_horizon"),
        "probability": model_result["probability"],
        "confidence": model_result["confidence"],
        "uncertainty": model_result.get("uncertainty", {}),
        "causal_status": model_result.get("causal_status", "correlational"),
        **distribution,
        "note": "Possibilities under stated assumptions, not guaranteed outcomes.",
    }
