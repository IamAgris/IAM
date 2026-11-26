"""Document 26 (OD-45): versioned backtest case library.

The shipped cases are explicitly illustrative fixtures for pipeline testing,
not real historical evidence. Scientific claims require licensed historical data.
"""

import json
from pathlib import Path
from typing import Any, Dict, List

from app.services.hbi.prediction import HistoricalCase

LIBRARY_PATH = Path(__file__).parent / "data" / "backtest_library.json"


def load(path: Path = LIBRARY_PATH) -> Dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload


def cases(payload: Dict[str, Any] = None) -> List[HistoricalCase]:
    data = payload or load()
    return [
        HistoricalCase(
            case_id=str(item["case_id"]),
            cutoff_year=int(item["cutoff_year"]),
            outcome_year=int(item["outcome_year"]),
            features={str(k): float(v) for k, v in item["features"].items()},
            outcome=int(item["outcome"]),
            target=str(item.get("domain", "aggregate_event")),
        )
        for item in data["cases"]
    ]


def summary(payload: Dict[str, Any] = None) -> Dict[str, Any]:
    data = payload or load()
    items = data["cases"]
    return {
        "status": data.get("status"),
        "purpose": data.get("purpose"),
        "count": len(items),
        "domains": sorted({item.get("domain", "unknown") for item in items}),
        "leakage_precondition": all(int(c["outcome_year"]) > int(c["cutoff_year"]) for c in items),
        "note": "Replace illustrative fixtures with licensed historical data before scientific claims.",
    }
