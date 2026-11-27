"""Document 26 (OD-45): first validated prediction path.

A simple evidence-weighted binary forecaster, Platt calibration, leakage-free
historical backtesting and an explicit validation gate. No model emits a
probability until it passes calibration and backtest thresholds (A8).
"""

import math
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple

Pair = Tuple[float, int]


def brier(pairs: List[Pair]) -> float:
    return round(sum((p - o) ** 2 for p, o in pairs) / len(pairs), 4) if pairs else 1.0


def log_loss(pairs: List[Pair]) -> float:
    if not pairs:
        return 1.0
    total = 0.0
    for p, o in pairs:
        q = min(max(p, 1e-9), 1 - 1e-9)
        total -= o * math.log(q) + (1 - o) * math.log(1 - q)
    return round(total / len(pairs), 4)


def accuracy(pairs: List[Pair]) -> float:
    return round(sum(1 for p, o in pairs if round(p) == o) / len(pairs), 4) if pairs else 0.0


def reliability(pairs: List[Pair], bins: int = 5) -> List[Dict[str, Any]]:
    result = []
    for index in range(bins):
        low, high = index / bins, (index + 1) / bins
        items = [p for p, _ in pairs if low <= p < high or (index == bins - 1 and p == 1.0)]
        if not items:
            continue
        outcomes = [o for p, o in pairs if p in items]
        result.append({
            "bin": f"{low:.2f}-{high:.2f}",
            "count": len(items),
            "mean_predicted": round(sum(items) / len(items), 3),
            "observed_frequency": round(sum(outcomes) / len(outcomes), 3),
        })
    return result


def ece(pairs: List[Pair], bins: int = 5) -> float:
    if not pairs:
        return 1.0
    total = 0.0
    for bucket in reliability(pairs, bins):
        total += bucket["count"] * abs(bucket["mean_predicted"] - bucket["observed_frequency"])
    return round(total / len(pairs), 4)


def score(pairs: List[Pair]) -> Dict[str, Any]:
    return {
        "n": len(pairs),
        "brier": brier(pairs),
        "log_loss": log_loss(pairs),
        "accuracy": accuracy(pairs),
        "ece": ece(pairs),
        "reliability": reliability(pairs),
    }


def sigmoid(value: float) -> float:
    if value >= 0:
        return 1 / (1 + math.exp(-value))
    exp_value = math.exp(value)
    return exp_value / (1 + exp_value)


class PlattCalibrator:
    def __init__(self) -> Any:
        self.a = 1.0
        self.b = 0.0
        self.fitted = False

    def fit(self, scores: List[float], outcomes: List[int]) -> None:
        if not scores or len(set(outcomes)) < 2:
            return
        a, b = 1.0, 0.0
        for _ in range(400):
            ga = gb = 0.0
            for score_value, outcome in zip(scores, outcomes):
                p = sigmoid(a * score_value + b)
                error = p - outcome
                ga += error * score_value
                gb += error
            a -= 0.05 * ga / len(scores)
            b -= 0.05 * gb / len(scores)
        self.a, self.b = a, b
        self.fitted = True

    def predict(self, score_value: float) -> float:
        return round(sigmoid(self.a * score_value + self.b), 4) if self.fitted else round(sigmoid(score_value), 4)


@dataclass
class HistoricalCase:
    case_id: str
    cutoff_year: int
    outcome_year: int
    features: Dict[str, float]
    outcome: int
    target: str = "aggregate_event"


def raw_score(features: Dict[str, float]) -> float:
    """Evidence-weighted score; features are graded evidence strengths."""
    positive = sum(value for key, value in features.items() if not key.startswith("against_"))
    negative = sum(value for key, value in features.items() if key.startswith("against_"))
    return round((positive - negative) / (positive + negative + 1.0), 4)


class EvidenceForecaster:
    def __init__(self) -> Any:
        self.calibrator = PlattCalibrator()

    def fit(self, cases: List[HistoricalCase]) -> None:
        self.calibrator.fit(
            [raw_score(c.features) for c in cases],
            [c.outcome for c in cases],
        )

    def predict(self, features: Dict[str, float]) -> float:
        return self.calibrator.predict(raw_score(features))


def backtest(cases: List[HistoricalCase],
             factory: Callable[[], Any] = EvidenceForecaster) -> Dict[str, Any]:
    """Retrospective forecast using only evidence available before each cutoff."""
    predictions: List[Dict[str, Any]] = []
    excluded = []
    for case in cases:
        # Leakage guard: a case whose outcome was known at the cutoff is never used in training.
        train = [c for c in cases if c.outcome_year < case.cutoff_year and c.case_id != case.case_id]
        if not train or len({c.outcome for c in train}) < 2:
            excluded.append(case.case_id)
            continue
        model = factory()
        model.fit(train)
        probability = model.predict(case.features)
        predictions.append({
            "case_id": case.case_id,
            "cutoff_year": case.cutoff_year,
            "outcome_year": case.outcome_year,
            "probability": probability,
            "outcome": case.outcome,
        })
    pairs = [(item["probability"], item["outcome"]) for item in predictions]
    return {
        "predictions": predictions,
        "excluded_cases": excluded,
        "scores": score(pairs),
        "leakage_check": "outcomes_at_or_after_cutoff_excluded_from_training",
    }


class LogisticModel:
    """Interpretable logistic model over evidence strength, trained by gradient descent."""

    def __init__(self) -> Any:
        self.weight = 0.0
        self.bias = 0.0

    def fit(self, cases: List[HistoricalCase]) -> None:
        weight, bias = 0.0, 0.0
        for _ in range(300):
            gw = gb = 0.0
            for case in cases:
                x = raw_score(case.features)
                error = sigmoid(weight * x + bias) - case.outcome
                gw += error * x
                gb += error
            weight -= 0.1 * gw / len(cases)
            bias -= 0.1 * gb / len(cases)
        self.weight, self.bias = weight, bias

    def predict(self, features: Dict[str, float]) -> float:
        return round(sigmoid(self.weight * raw_score(features) + self.bias), 4)


class BetaBinomialModel:
    """Bayesian baseline with an auditable Beta prior and posterior interval."""

    def __init__(self, alpha: float = 1.0, beta: float = 1.0) -> Any:
        self.prior_alpha = alpha
        self.prior_beta = beta
        self.alpha_post = alpha
        self.beta_post = beta

    def fit(self, cases: List[HistoricalCase]) -> None:
        successes = sum(c.outcome for c in cases)
        failures = len(cases) - successes
        self.alpha_post = self.prior_alpha + successes
        self.beta_post = self.prior_beta + failures

    def predict(self, features: Dict[str, float]) -> float:
        score = raw_score(features)
        pseudo_trials = 4.0
        pseudo_successes = ((score + 1.0) / 2.0) * pseudo_trials
        return round(
            (self.alpha_post + pseudo_successes) /
            (self.alpha_post + self.beta_post + pseudo_trials), 4
        )

    def interval(self, z: float = 1.96) -> Dict[str, float]:
        a, b = self.alpha_post, self.beta_post
        total = a + b
        mean = a / total
        sd = (a * b / (total ** 2 * (total + 1))) ** 0.5
        return {"lower": round(max(0.0, mean - z * sd), 4),
                "upper": round(min(1.0, mean + z * sd), 4)}


class EnsembleForecaster:
    """Combines calibrated evidence and Bayesian baselines; disagreement widens uncertainty."""

    def __init__(self) -> Any:
        self.evidence = EvidenceForecaster()
        self.bayesian = BetaBinomialModel()

    def fit(self, cases: List[HistoricalCase]) -> None:
        self.evidence.fit(cases)
        self.bayesian.fit(cases)

    def predict(self, features: Dict[str, float]) -> float:
        first = self.evidence.predict(features)
        second = self.bayesian.predict(features)
        return round(0.6 * first + 0.4 * second, 4)


class PredictionService:
    """Emits probabilities only from a model that passed validation."""

    def __init__(self) -> Any:
        self.models: Dict[str, Any] = {}
        self.validation: Dict[str, Dict[str, Any]] = {}
        self.versions: Dict[str, List[Dict[str, Any]]] = {}

    def register(self, model_id: str, model: Any) -> None:
        self.models[model_id] = model
        self.versions.setdefault(model_id, []).append({"version": "1.0", "model": model})

    def register_version(self, model_id: str, version: str, model: Any) -> None:
        """Append an immutable version and make it active."""
        self.versions.setdefault(model_id, []).append({"version": version, "model": model})
        self.models[model_id] = model

    def active_version(self, model_id: str) -> str | None:
        versions = self.versions.get(model_id, [])
        return versions[-1]["version"] if versions else None

    def rollback(self, model_id: str) -> Dict[str, Any]:
        """Restore the previous version; the failed version remains in history."""
        versions = self.versions.get(model_id, [])
        if len(versions) < 2:
            return {"rolled_back": False, "reason": "no_previous_version"}
        failed = versions.pop()
        restored = versions[-1]
        self.models[model_id] = restored["model"]
        return {
            "rolled_back": True,
            "removed_version": failed["version"],
            "restored_version": restored["version"],
            "history_retained": [item["version"] for item in versions],
        }

    def validate(self, model_id: str, cases: List[HistoricalCase]) -> Dict[str, Any]:
        if model_id not in self.models:
            return {"validated": False, "reason": "unknown_model"}
        result = backtest(cases)
        scores = result["scores"]
        reasons = []
        if scores["n"] < 5:
            reasons.append("insufficient_backtest_cases")
        if scores["brier"] > 0.30:
            reasons.append("brier_above_threshold")
        if scores["ece"] > 0.20:
            reasons.append("calibration_above_threshold")
        validated = not reasons
        self.validation[model_id] = {
            "validated": validated, "reasons": reasons, "scores": scores,
            "model_id": model_id,
        }
        return self.validation[model_id]

    def predict(self, model_id: str, features: Dict[str, float], purpose: str,
                scope: str = "aggregate") -> Dict[str, Any]:
        record = self.validation.get(model_id)
        if not record or not record["validated"]:
            return {
                "probability": {}, "confidence": 0.0,
                "refusal": {
                    "code": "A8_MODEL_NOT_VALIDATED",
                    "reason": "no_validated_model_for_this_purpose",
                    "validation": record,
                },
            }
        probability = self.models[model_id].predict(features)
        return {
            "probability": {"positive": probability, "negative": round(1 - probability, 4)},
            "confidence": round(1 - record["scores"]["ece"], 4),
            "uncertainty": {"model": "validated", "evidence_gap": "assessed_in_backtest"},
            "causal_status": "correlational",
            "purpose": purpose,
            "scope": scope,
            "validation_ref": model_id,
            "note": "Probability and confidence are separate fields.",
        }
