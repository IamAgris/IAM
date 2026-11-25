"""Build the deployment-suitability scorecard from collected evidence.

No new model calls. Uses constrained_results.jsonl, assertion_diagnosis.json,
benchmark_summary.json and hardware evidence. Criteria/weights follow the
owner's OD-38 instruction. N/A criteria are excluded and the weighted average
is taken over measured criteria only; coverage is reported explicitly.

Usage: python tests/model_competition/final_report.py
"""

import json
import statistics
from pathlib import Path

from full_benchmark import MODELS

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results"
ROWS = [
    json.loads(line)
    for line in (RESULTS / "constrained_results.jsonl").read_text(encoding="utf-8").splitlines()
    if '"order"' in line
]
DIAGNOSIS = json.loads((RESULTS / "assertion_diagnosis.json").read_text(encoding="utf-8"))
OUT = RESULTS / "final_report.json"

CRITERIA = [
    ("Coding correctness", "Critical", 3),
    ("Reasoning quality", "Critical", 3),
    ("RAM consumption", "Critical", 3),
    ("CPU efficiency", "High", 2),
    ("Cold-start latency", "High", 2),
    ("Warm inference speed", "High", 2),
    ("Long-running stability", "High", 2),
    ("ARM64 compatibility", "High", 2),
    ("Tool calling", "High", 2),
]


def in_scope(model, row):
    """Bracket trials (order>=16) are contaminated by multi-model residency.

    The original two-model matrix is orders 1-15; the qwen3.5:4b focused
    think=false matrix is orders 16+. Keep each model on its own clean set.
    """
    return row["order"] < 16 if model != "local-qwen3.5-4b" else row["order"] >= 16


def warm_stats(model):
    rows = [
        r
        for r in ROWS
        if r["model"] == model
        and in_scope(model, r)
        and r["phase"] == "warm"
        and r["loaded_before"]
    ]
    lat = [r["latency_ms"] for r in rows]
    return {
        "n": len(rows),
        "min_ms": round(min(lat), 1),
        "median_ms": round(statistics.median(lat), 1),
        "max_ms": round(max(lat), 1),
        "stdev_ms": round(statistics.stdev(lat), 1),
        "peak_mem_median_mb": round(statistics.median([r["peak_mem_mb"] for r in rows]), 1),
        "avg_cpu_cores": round(statistics.median([r["avg_cpu_cores"] for r in rows]), 2),
        "swap_max_mb": max([r["swap_peak_mb"] for r in rows]),
        "excluded_reloads": len(
            [
                r
                for r in ROWS
                if r["model"] == model
                and in_scope(model, r)
                and r["phase"] == "warm"
                and not r["loaded_before"]
            ]
        ),
        "correct": sum(r["passed"] for r in rows),
    }


def cold_stats(model):
    rows = [
        r
        for r in ROWS
        if r["model"] == model and in_scope(model, r) and r["phase"] == "cold"
    ]
    return {
        "n": len(rows),
        "median_ms": round(statistics.median([r["latency_ms"] for r in rows]), 1),
        "median_ttft_ms": round(
            statistics.median([r["ttft_ms"] for r in rows if r["ttft_ms"] is not None]), 1
        ),
        "correct": sum(r["passed"] for r in rows),
    }


def ram_score(peak_mb):
    if peak_mb < 3000:
        return 5
    if peak_mb < 4000:
        return 4
    if peak_mb < 5000:
        return 3
    if peak_mb < 6000:
        return 2
    return 1


def stability_score(stats):
    score = 5
    if stats["swap_max_mb"] > 100:
        score -= 1
    if stats["excluded_reloads"]:
        score -= 1
    if stats["stdev_ms"] > 1000:
        score -= 1
    return score


def main() -> None:
    models = MODELS
    warm = {m: warm_stats(m) for m in models}
    cold = {m: cold_stats(m) for m in models}

    best_warm = min(s["median_ms"] for s in warm.values())
    best_cold = min(s["median_ms"] for s in cold.values())
    best_cores = min(s["avg_cpu_cores"] for s in warm.values())

    scores = {}
    for model in models:
        diag = DIAGNOSIS["models"][model]
        pass_rate = 1 - diag["cases_failed"] / diag["cases_total"]
        raw = {
            "Coding correctness": round(5 * pass_rate, 2),
            "Reasoning quality": None,
            "RAM consumption": ram_score(warm[model]["peak_mem_median_mb"]),
            "CPU efficiency": round(5 * best_cores / warm[model]["avg_cpu_cores"], 2),
            "Cold-start latency": round(5 * best_cold / cold[model]["median_ms"], 2),
            "Warm inference speed": round(5 * best_warm / warm[model]["median_ms"], 2),
            "Long-running stability": stability_score(warm[model]),
            "ARM64 compatibility": None,
            "Tool calling": None,
        }
        measured = [
            (name, weight, raw[name])
            for name, _importance, weight in CRITERIA
            if raw[name] is not None
        ]
        total_w = sum(w for _, w, _ in measured)
        weighted = round(sum(w * s for _, w, s in measured) / total_w, 2)
        scores[model] = {
            "scores": raw,
            "weighted_score_measured_only": weighted,
            "measured_weight": total_w,
            "total_weight": sum(w for _, _, w in CRITERIA),
            "coverage_pct": round(100 * total_w / sum(w for _, _, w in CRITERIA), 1),
        }

    report = {
        "method": (
            "Score 0-5 per criterion; weights Critical=3, High=2. N/A criteria "
            "excluded; weighted average taken over measured criteria only. "
            "No new model calls; all values derived from recorded evidence."
        ),
        "inference_modes": {
            model: (
                "think=false (thinking disabled — default mode exhausted the "
                "512-token budget with no code in 314 s)"
                if any(r.get("thinking_disabled") for r in ROWS if r["model"] == model)
                else "default (non-thinking model)"
            )
            for model in models
        },
        "cold": cold,
        "warm": warm,
        "scorecard": scores,
        "recommendation": {
            "initial_local_brain": max(
                scores, key=lambda m: scores[m]["weighted_score_measured_only"]
            ),
            "rationale": (
                "Highest weighted score over measured criteria. This is a relative "
                "choice for the private/low-resource baseline, not approval as the "
                "primary brain: correctness, concurrency and hosted comparison all "
                "remain constrained. See RESULTS.md for the written interpretation."
            ),
            "caveats": [
                "Dev-host emulation only; final decision requires the Contabo VPS 4 run with --target.",
                "Hosted contenders were unavailable (no API keys), so no cross-provider comparison exists.",
                "Reasoning quality, ARM64 compatibility and tool calling were not measured.",
                "qwen3.5:4b requires think=false to produce code within the unchanged "
                "512-token budget; its default thinking mode failed completely.",
                "Multiple resident models push swap to ~150 MB and host RAM available "
                "down to 0.69 GB; run one model at a time on the 8 GB VPS.",
            ],
        },
    }
    OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    print(f"\nWrote {OUT.relative_to(HERE.parents[2])}")


if __name__ == "__main__":
    main()
