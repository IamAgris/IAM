"""Trusted local evaluator for benchmark evidence (OD-40/OD-41).

The model under test answers a versioned, exact-match question set; scoring is
deterministic and never delegated to another model. The dataset checksum is
included in the benchmark config hash so evidence cannot be silently replayed
against a different eval set.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

import httpx

from app.core.config import settings

from .artifacts import sha256_bytes
from .base import ResearchError


class LMEvalError(ResearchError):
    """The configured evaluator or eval set is unusable."""


def _resolve_path(value: str) -> Path:
    path = Path(value)
    if path.is_absolute() and path.is_file():
        return path
    candidates = (Path.cwd() / path, Path(__file__).resolve().parents[3] / path, path)
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise LMEvalError(f"eval dataset not found: {value}")


class OllamaLMEvalDriver:
    """Exact-match evaluator against an Ollama OpenAI-compatible model endpoint."""

    def __init__(
        self,
        dataset_path: str,
        *,
        base_url: Optional[str] = None,
        timeout: Optional[float] = None,
        client_factory: Any=None,
    ) -> None:
        self.client_factory = client_factory
        path = _resolve_path(dataset_path)
        self.raw = path.read_bytes()
        self.path = str(path)
        self.checksum = sha256_bytes(self.raw)
        self.records: list[dict[str, str]] = []
        for line in self.raw.decode("utf-8").splitlines():
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except ValueError as exc:
                raise LMEvalError(f"invalid eval record in {path}") from exc
            if not record.get("prompt") or "expected" not in record:
                raise LMEvalError("eval records require prompt and expected")
            self.records.append(
                {"prompt": str(record["prompt"]), "expected": str(record["expected"])}
            )
        if not self.records:
            raise LMEvalError("eval dataset is empty")
        self.base_url = (base_url or settings.ollama_base_url).rstrip("/")
        self.timeout = timeout or settings.lm_eval_timeout_seconds

    @staticmethod
    def _normalise(text: str) -> str:
        return " ".join(text.strip().lower().split())

    def evaluate(self, spec: Any, model: str) -> float:
        scores = []
        factory = self.client_factory or httpx.Client
        with factory(timeout=self.timeout) as client:
            for record in self.records:
                response = client.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": model,
                        "prompt": record["prompt"],
                        "stream": False,
                        "options": {"temperature": 0},
                    },
                )
                if response.status_code != 200:
                    raise LMEvalError(
                        f"evaluator provider returned {response.status_code}"
                    )
                answer = self._normalise(str(response.json().get("response", "")))
                scores.append(1.0 if answer == self._normalise(record["expected"]) else 0.0)
        return sum(scores) / len(scores)


def default_lm_eval_driver() -> Optional[OllamaLMEvalDriver]:
    """Build the configured trusted evaluator, or None when not configured."""
    if not settings.lm_eval_dataset_path:
        return None
    return OllamaLMEvalDriver(settings.lm_eval_dataset_path)


def eval_config(driver: OllamaLMEvalDriver) -> dict[str, Any]:
    return {"dataset": driver.path, "dataset_sha256": driver.checksum}


DEFAULT_SUITE_MANIFEST = "app/services/ai_research/eval_sets/manifest.json"


class EvaluationSuite:
    """Versioned multi-domain benchmark with mandatory thresholds and regression checks.

    A single five-question set cannot establish capability. This suite scores
    reasoning, planning, tool use, safety and instruction following separately,
    refuses a domain whose score falls below its threshold, and can compare a
    candidate against a recorded baseline before promotion.
    """

    def __init__(self, manifest_path: str = DEFAULT_SUITE_MANIFEST, client_factory: Any=None) -> Any:
        path = _resolve_path(manifest_path)
        raw = path.read_bytes()
        self.path = str(path)
        self.checksum = sha256_bytes(raw)
        self.root = path.parent
        self.client_factory = client_factory
        try:
            manifest = json.loads(raw.decode("utf-8"))
        except ValueError as exc:
            raise LMEvalError("invalid eval manifest") from exc
        suites = manifest.get("suites") or []
        if not suites:
            raise LMEvalError("eval manifest has no suites")
        self.suites = []
        for item in suites:
            name = str(item.get("name") or "")
            dataset = str(item.get("dataset") or "")
            if not name or not dataset or not (self.root / dataset).is_file():
                raise LMEvalError(f"invalid eval suite entry: {name or dataset}")
            self.suites.append(
                {
                    "name": name,
                    "dataset": dataset,
                    "threshold": float(item.get("threshold", 0.0)),
                    "weight": float(item.get("weight", 1.0)),
                }
            )
        self.last_report: Optional[dict[str, Any]] = None

    def evaluate_detailed(self, spec: Any, model: str) -> Dict[str, Any]:
        domains: Dict[str, Any] = {}
        for suite in self.suites:
            driver = OllamaLMEvalDriver(
                str(self.root / suite["dataset"]), client_factory=self.client_factory
            )
            score = driver.evaluate(spec, model)
            domains[suite["name"]] = {
                "score": round(score, 4),
                "threshold": suite["threshold"],
                "dataset_sha256": driver.checksum,
                "passed": score >= suite["threshold"],
            }
        total_weight = sum(suite["weight"] for suite in self.suites) or 1.0
        overall = sum(
            domains[suite["name"]]["score"] * suite["weight"] for suite in self.suites
        ) / total_weight
        report = {
            "model": model,
            "manifest_sha256": self.checksum,
            "domains": domains,
            "overall_score": round(overall, 4),
            "passed": all(item["passed"] for item in domains.values()),
        }
        self.last_report = report
        return report

    def evaluate(self, spec: Any, model: str) -> float:
        return float(self.evaluate_detailed(spec, model)["overall_score"])

    @staticmethod
    def compare(
        baseline: Dict[str, Dict[str, Any]],
        candidate: Dict[str, Dict[str, Any]],
        max_drop: float = 0.05,
    ) -> Dict[str, Any]:
        """Detect any domain that regressed beyond the allowed margin."""
        regressions = []
        for name, previous in (baseline or {}).items():
            current = (candidate or {}).get(name)
            if not current:
                regressions.append({"domain": name, "reason": "missing_candidate_score"})
                continue
            drop = float(previous.get("score", 0.0)) - float(current.get("score", 0.0))
            if drop > max_drop:
                regressions.append(
                    {"domain": name, "drop": round(drop, 4), "max_allowed": max_drop}
                )
        return {"regressions": regressions, "passed": not regressions}


def default_eval_suite(client_factory: Any=None) -> Optional[EvaluationSuite]:
    if not settings.lm_eval_suite_enabled:
        return None
    return EvaluationSuite(client_factory=client_factory)


def eval_suite_config(suite: EvaluationSuite) -> dict[str, Any]:
    return {"eval_manifest": suite.path, "eval_manifest_sha256": suite.checksum,
            "eval_domains": [item["name"] for item in suite.suites]}
