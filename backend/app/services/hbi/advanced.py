"""Document 26 (OD-45): advanced capabilities A1–A5.

A1 self-directed research, A2 theory comparison, A3 hypothesis generation,
A4 historical-to-modern comparison, A5 predictive self-evaluation.
All outputs are candidates or diagnoses with explicit falsifiers and audit.
"""

from typing import Any, Dict, List

from app.services.hbi.prediction import brier

ANALOGY_WEIGHTS = {
    "contextual": 0.20,
    "economic": 0.15,
    "political": 0.15,
    "social": 0.15,
    "behavioural": 0.15,
    "technological": 0.10,
    "evidence_quality": 0.05,
    "differences_penalty": 0.05,
}


def research_from_gaps(gap_result: Dict[str, Any]) -> Dict[str, Any]:
    """A1: turn detected gaps into bounded research triggers."""
    triggers = [
        {
            "gap": gap,
            "query": f"systematic review: {gap.replace('::', ' ')}",
            "status": "candidate",
            "gate": "licence_and_provenance_required",
        }
        for gap in gap_result.get("gaps", [])
    ]
    return {
        "triggers": triggers,
        "count": len(triggers),
        "note": "Candidates are research directions, not findings. A gap never licenses speculation.",
    }


def compare_theories(theories: List[Dict[str, Any]], cases: List[Dict[str, Any]]) -> Dict[str, Any]:
    """A2: compare competing theories by differential predictive accuracy."""
    outcomes = {str(c["case_id"]): int(c["outcome"]) for c in cases}
    results = []
    for theory in theories:
        predictions = theory.get("predictions") or {}
        pairs = [
            (float(predictions[case_id]), outcome)
            for case_id, outcome in outcomes.items()
            if case_id in predictions
        ]
        results.append({
            "theory_id": theory.get("id"),
            "name": theory.get("name"),
            "evidence_class": theory.get("evidence_class", "unverified"),
            "scope": theory.get("scope", "general"),
            "n_cases": len(pairs),
            "brier": brier(pairs) if pairs else None,
        })
    ranked = sorted(results, key=lambda item: (item["brier"] is None, item["brier"] or 1.0))
    return {
        "ranked": ranked,
        "current_best_supported": ranked[0]["theory_id"] if ranked and ranked[0]["brier"] is not None else None,
        "still_viable": [item["theory_id"] for item in ranked if item["brier"] is not None],
        "note": "No theory is finally proven; alternatives are retained until evidence discriminates.",
    }


def generate_hypotheses(records: List[Dict[str, Any]], gap_result: Dict[str, Any],
                        contradictions_result: Dict[str, Any]) -> List[Dict[str, Any]]:
    """A3: abductive candidate hypotheses, each with mechanism and falsifier."""
    hypotheses = []
    for gap in gap_result.get("gaps", [])[:6]:
        hypotheses.append({
            "claim": f"A missing factor ({gap}) may influence the observed behaviour",
            "mechanism": "contextual_variable_not_yet_recorded",
            "falsifier": "adding the factor does not improve held-out prediction",
            "test_design": "preregistered comparison with and without the factor",
            "status": "hypothesis",
        })
    for conflict in contradictions_result.get("contradictions", [])[:4]:
        hypotheses.append({
            "claim": f"Context may reconcile conflicting claims: {conflict['claim_a_ref']} vs {conflict['claim_b_ref']}",
            "mechanism": "moderator_variable_or_population_difference",
            "falsifier": "no moderator predicts which claim holds across cases",
            "test_design": "stratified comparison across contexts",
            "status": "hypothesis",
        })
    weak = [r for r in records if r.get("evidence_class") in {"unverified", "speculation"}]
    if weak:
        hypotheses.append({
            "claim": "Low-confidence claims may reflect source bias rather than behaviour",
            "mechanism": "measurement_or_selection_bias",
            "falsifier": "independent high-quality sources reproduce the same claim",
            "test_design": "replication with verified sources",
            "status": "hypothesis",
        })
    return hypotheses


def analogy(current: Dict[str, Any], precedent: Dict[str, Any]) -> Dict[str, Any]:
    """A4: weighted analogy scoring with a mandatory weak-comparison verdict."""
    similarities = current.get("similarities") or precedent.get("similarities") or {}
    differences = current.get("differences") or precedent.get("differences") or []
    score = 0.0
    for dimension in ("contextual", "economic", "political", "social", "behavioural", "technological"):
        score += ANALOGY_WEIGHTS[dimension] * float(similarities.get(dimension, 0.0))
    evidence = str(precedent.get("evidence_class", "unverified"))
    evidence_weight = {
        "verified": 1.0, "well_supported": 0.8, "contested": 0.5,
        "unverified": 0.2, "speculation": 0.0,
    }.get(evidence, 0.0)
    score += ANALOGY_WEIGHTS["evidence_quality"] * evidence_weight
    score -= ANALOGY_WEIGHTS["differences_penalty"] * len(differences)
    score = round(max(0.0, min(1.0, score)), 3)
    if evidence in {"unverified", "speculation"}:
        verdict = "weak_or_misleading"
    elif score >= 0.75:
        verdict = "applicable"
    elif score >= 0.50:
        verdict = "partially_applicable"
    elif score >= 0.30:
        verdict = "weak"
    else:
        verdict = "misleading"
    return {
        "score": score,
        "verdict": verdict,
        "precedent": precedent.get("event_id"),
        "differences": differences,
        "evidence_class": evidence,
        "note": "History supplies context, not a guarantee of repetition.",
    }


def evaluate_analogies(current: Dict[str, Any], precedents: List[Dict[str, Any]],
                       cases: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Backtest whether strong analogies actually predicted documented outcomes."""
    outcomes = {str(c["case_id"]): int(c["outcome"]) for c in cases}
    evaluated = []
    for precedent in precedents:
        case_id = str(precedent.get("case_id") or precedent.get("event_id"))
        if case_id not in outcomes:
            continue
        result = analogy(current, precedent)
        predicted_positive = result["score"] >= 0.75 and result["verdict"] == "applicable"
        evaluated.append({
            "case_id": case_id,
            "score": result["score"],
            "verdict": result["verdict"],
            "predicted_positive": predicted_positive,
            "observed_positive": outcomes[case_id] == 1,
        })
    hits = sum(1 for item in evaluated if item["predicted_positive"] == item["observed_positive"])
    baseline = sum(1 for value in outcomes.values() if value == 1) / len(outcomes) if outcomes else 0.0
    hit_rate = hits / len(evaluated) if evaluated else 0.0
    return {
        "evaluated": evaluated,
        "hit_rate": round(hit_rate, 3),
        "baseline_positive_rate": round(baseline, 3),
        "lift": round(hit_rate - baseline, 3),
        "note": "Analogy quality is measured against a no-analogy baseline, not assumed.",
    }


def diagnose_prediction(prediction: Dict[str, Any], outcome: Any) -> Dict[str, Any]:
    """A5: classify why a prediction was wrong, with corrective actions."""
    refusal = prediction.get("refusal")
    if refusal:
        return {
            "error_type": "withheld_prediction",
            "reason": refusal.get("code"),
            "corrective_actions": refusal.get("what_would_change", []),
            "note": "A withheld prediction is not a failed prediction.",
        }
    probability = prediction.get("probability") or {}
    p = float(probability.get("positive", 0.5))
    observed = 1 if outcome in {1, "positive", True} else 0
    error = round(abs(p - observed), 3)
    uncertainty = prediction.get("uncertainty") or {}
    causes = []
    if uncertainty.get("evidence_gap") in {"high", "unknown"}:
        causes.append("evidence_gap")
    if uncertainty.get("distribution_shift") == "high":
        causes.append("distribution_shift")
    if uncertainty.get("model") == "unvalidated":
        causes.append("model_unvalidated")
    if not causes:
        causes.append("calibration_or_irreducible_variation")
    return {
        "error": error,
        "error_type": causes,
        "probability": p,
        "observed": observed,
        "corrective_actions": [
            "review_source_quality", "recalibrate_model", "re-test_on_held_out_cases",
        ],
        "note": "Diagnosis feeds knowledge evolution A7; it never rewrites the original prediction.",
    }
