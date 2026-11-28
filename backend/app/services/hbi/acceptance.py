"""Document 26 (OD-45): automated end-to-end acceptance gates.

Runs the mandatory acceptance conditions from §11.7 against a live HBI service
instance. Every gate returns evidence; no gate silently passes.
"""

from typing import Any, Dict, List

from app.services.hbi.prediction import HistoricalCase, backtest, brier
from app.services.hbi.schemas import AnalysisRequest, ChronologyInput, PredictionRequest


async def run_acceptance(service: Any) -> Dict[str, Any]:
    gates: List[Dict[str, Any]] = []

    def check(name: str, passed: bool, evidence: Any) -> None:
        gates.append({"gate": name, "passed": bool(passed), "evidence": evidence})

    records = service.store.all()
    check(
        "schema_records",
        all({"record_ref", "claim", "epistemic_type", "evidence_class", "scope", "tier", "version"} <= set(r) for r in records),
        {"records": len(records)},
    )
    check(
        "epistemic_discipline",
        all(
            (r["epistemic_type"] != "observation" or r.get("evidence"))
            and (r["epistemic_type"] != "interpretation" or r.get("alternatives"))
            and (r["epistemic_type"] != "hypothesis" or r.get("falsifier"))
            for r in records
        ),
        {"checked": len(records)},
    )

    governance_ok = False
    try:
        await service.analyse(AnalysisRequest(question="test", purpose="manipulation"))
    except Exception as error:
        governance_ok = getattr(error, "code", None) == "PURPOSE_MISMATCH"
    check("governance_purpose_gate", governance_ok, {"purpose": "manipulation"})

    governance_scope = False
    try:
        await service.analyse(AnalysisRequest(question="test", purpose="research", scope="individual"))  # type: ignore[arg-type]
    except Exception as error:
        governance_scope = getattr(error, "code", None) == "SCOPE_VIOLATION"
    check("governance_scope_gate", governance_scope, {"scope": "individual"})

    refusal = await service.predict(PredictionRequest(
        question="test", target="event", purpose="research", features={"support": 1.0},
    ))
    check("a8_prediction_refusal", "refusal" in refusal, {"code": refusal.get("refusal", {}).get("code")})

    modules = service.list_modules()
    status = service.status()
    check("module_and_engine_counts",
          modules["count"] == 38 and status["modules"] == 38 and status["technical_engines"] == 13,
          {"modules": modules["count"], "engines": status["technical_engines"]})

    known_pairs = [(0.9, 1), (0.1, 0)]
    check("calibration_scoring", brier(known_pairs) <= 0.05, {"brier": brier(known_pairs)})

    leaked = HistoricalCase("leaked", 2020, 2021, {"support": 1.0}, 1)
    usable = HistoricalCase("usable", 2030, 2021, {"against_support": 1.0}, 0)
    backtest_result = backtest([leaked, usable])
    check("backtest_no_leakage", "leaked" in backtest_result["excluded_cases"],
          {"excluded": backtest_result["excluded_cases"]})

    chronology = service.resolve_chronology(ChronologyInput(
        events=[{"event_id": "e", "name": "E", "date": {"value": "1900", "precision": "year"}}],
        conflicting_accounts=[{"account_a": "A", "account_b": "B"}],
    ))
    check("historical_conflicts_preserved", len(chronology["conflicting_accounts"]) == 1,
          {"count": len(chronology["conflicting_accounts"])})

    check("auditability", len(service.core.audit_log) > 0, {"events": len(service.core.audit_log)})

    failed = [gate["gate"] for gate in gates if not gate["passed"]]
    return {
        "gates": gates,
        "passed": not failed,
        "failed": failed,
        "count": len(gates),
        "note": "A failed gate blocks production promotion.",
    }
