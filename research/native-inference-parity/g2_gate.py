"""G2 candidate-parity gate driver (research only).

Isolated from backend/ and frontend/. No model runtime, no network, no weights.

Two modes:

    python research/native-inference-parity/g2_gate.py --calibrate
    python research/native-inference-parity/g2_gate.py --self-test
    python research/native-inference-parity/g2_gate.py --adapter path/to/candidate_ops.py

``--calibrate`` measures the strict FP32 reference against the independent FP64
oracle over a deterministic extended case set and writes ``tolerances.json``.
Those per-operation tolerances replace compare.py's generic defaults.

``--adapter`` loads a candidate module exposing the same function names and
signatures as ``reference_ops.py`` (rmsnorm, rope_inv_freq, rope_cos_sin,
rope_apply, attention_causal, swiglu, dequant_q8_0_row), compares each output
array with the reference, enforces the calibrated tolerances, and records
evidence under ``results/``.

Token-sequence parity and GGUF/tokeniser fixtures are deliberately not here;
they belong to G3/G4. A PASS from this gate means numeric parity on small
synthetic inputs only -- not that an engine is correct or deployable.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import math
import random
import struct
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import compare
import oracle_ops
import reference_ops

OPS: tuple[str, ...] = (
    "rmsnorm",
    "rope_inv_freq",
    "rope_cos_sin",
    "rope_apply",
    "attention_causal",
    "swiglu",
    "dequant_q8_0_row",
)
SEED = 20261128
CASES_PER_OP = 32
DEFAULT_COS_MIN = 0.9999
ABS_FLOOR = 1e-6
EXACT_OPS = frozenset({"dequant_q8_0_row"})


def _vec(rng: random.Random, n: int, low: float = -2.0, high: float = 2.0) -> list[float]:
    return [rng.uniform(low, high) for _ in range(n)]


def _matrix(rng: random.Random, rows: int, cols: int, low: float = -1.0, high: float = 1.0) -> list[list[float]]:
    return [[rng.uniform(low, high) for _ in range(cols)] for _ in range(rows)]


def build_cases() -> dict[str, list[dict[str, Any]]]:
    """Deterministic synthetic inputs; identical for reference, oracle and candidate."""
    rng = random.Random(SEED)
    cases: dict[str, list[dict[str, Any]]] = {name: [] for name in OPS}
    for _ in range(CASES_PER_OP):
        cases["rmsnorm"].append(
            {"x": _vec(rng, 64), "weight": _vec(rng, 64, 0.5, 1.5), "eps": 1e-6}
        )
        cases["rope_inv_freq"].append({"head_dim": 32, "theta": 1e6})
        position = rng.randrange(0, 64)
        cases["rope_cos_sin"].append({"position": position, "head_dim": 32, "theta": 1e6})
        cos, sin = reference_ops.rope_cos_sin(position, 32)
        cases["rope_apply"].append({"x": _vec(rng, 32), "cos": cos, "sin": sin})
        cases["attention_causal"].append(
            {
                "q": [[_vec(rng, 8) for _ in range(3)] for _ in range(4)],
                "k": [[_vec(rng, 8) for _ in range(3)] for _ in range(2)],
                "v": [[_vec(rng, 8) for _ in range(3)] for _ in range(2)],
                "kv_heads": 2,
            }
        )
        cases["swiglu"].append(
            {
                "x": _vec(rng, 8),
                "w_gate": _matrix(rng, 16, 8),
                "w_up": _matrix(rng, 16, 8),
                "w_down": _matrix(rng, 8, 16),
            }
        )
        fp16_scale = bool(rng.randrange(2))
        scale = rng.choice([0.5, 2.0, 4.0])
        packed = struct.pack("<H", 0x4000) if fp16_scale else struct.pack("<f", scale)
        row = bytes(rng.randrange(128) for _ in range(32)) + packed
        cases["dequant_q8_0_row"].append({"row": row, "scales_fp16": fp16_scale})
    return cases


def _flat(value: Any) -> list[float]:
    if isinstance(value, tuple):
        value = list(value)
    return compare.flatten(value)


def _call(module: Any, op: str, kwargs: dict[str, Any]) -> Any:
    fn = module if callable(module) else getattr(module, op, None)
    if fn is None or not callable(fn):
        raise ValueError(f"candidate is missing operation {op!r}")
    return fn(**kwargs)


def _inv_freq_oracle(head_dim: int, theta: float) -> list[float]:
    return [1.0 / math.pow(theta, 2 * i / head_dim) for i in range(head_dim // 2)]


def _dequant_oracle(row: bytes, scales_fp16: bool = True) -> list[float]:
    block = 32
    stride = block + (2 if scales_fp16 else 4)
    if len(row) % stride:
        raise ValueError("row length is not a whole number of Q8_0 blocks")
    out: list[float] = []
    for offset in range(0, len(row), stride):
        if scales_fp16:
            scale = struct.unpack("<e", row[offset + block : offset + block + 2])[0]
        else:
            scale = struct.unpack("<f", row[offset + block : offset + block + 4])[0]
        for byte in row[offset : offset + block]:
            signed = byte - 256 if byte > 127 else byte
            out.append(signed * scale)
    return out


def _oracle_for(op: str) -> Callable[..., Any]:
    return {
        "rmsnorm": oracle_ops.rmsnorm,
        "rope_inv_freq": _inv_freq_oracle,
        "rope_cos_sin": oracle_ops.rope_cos_sin,
        "rope_apply": oracle_ops.rope_apply,
        "attention_causal": oracle_ops.attention_causal,
        "swiglu": oracle_ops.swiglu,
        "dequant_q8_0_row": _dequant_oracle,
    }[op]


def calibrate() -> dict[str, Any]:
    cases = build_cases()
    table: dict[str, Any] = {
        "gate": "G2",
        "method": (
            "For each operation, strict FP32 reference outputs are compared with an "
            "independent FP64 oracle over deterministic synthetic cases. abs_tol = "
            "max(2x observed max_abs_diff, 1e-6); cos_min = min(0.9999, observed "
            "minimum cosine). Q8_0 dequant is exact: abs_tol 0 plus an element-wise "
            "exact_matches check (cosine in float64 is not bit-exact for identical "
            "arrays), so cos_min stays at 0.9999."
        ),
        "seed": SEED,
        "cases_per_op": CASES_PER_OP,
        "operations": {},
    }
    for op in OPS:
        worst = 0.0
        min_cos = 1.0
        for kwargs in cases[op]:
            expected = _flat(_call(_oracle_for(op), op, kwargs))
            got = _flat(_call(reference_ops, op, kwargs))
            result = compare.compare_arrays(expected, got)
            worst = max(worst, result["max_abs_diff"])
            min_cos = min(min_cos, result["cosine_similarity"])
        if op in EXACT_OPS:
            # Q8_0 dequant is an integer x scale operation: demand exact values.
            # Cosine is computed in float64 and can be 0.9999999999999998 even
            # for identical arrays, so exactness is enforced element-wise.
            abs_tol, cos_min = 0.0, DEFAULT_COS_MIN
        else:
            abs_tol = max(round(worst * 2, 9), ABS_FLOOR)
            cos_min = min(DEFAULT_COS_MIN, round(min_cos, 9))
        table["operations"][op] = {
            "abs_tol": abs_tol,
            "cos_min": cos_min,
            "exact_required": op in EXACT_OPS,
            "observed_ref_vs_oracle_max_abs_diff": worst,
            "observed_ref_vs_oracle_min_cosine": min_cos,
        }
    return table


def load_adapter(path: Path | None) -> Any:
    if path is None:
        return reference_ops
    spec = importlib.util.spec_from_file_location("g2_candidate", str(path))
    if spec is None or spec.loader is None:
        raise ValueError(f"cannot load adapter: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_gate(adapter_path: Path | None, name: str) -> dict[str, Any]:
    tolerance_path = HERE / "tolerances.json"
    if not tolerance_path.exists():
        raise SystemExit("tolerances.json missing: run --calibrate first")
    tolerances = json.loads(tolerance_path.read_text(encoding="utf-8"))
    cases = build_cases()
    adapter = load_adapter(adapter_path)
    report: dict[str, Any] = {
        "gate": "G2",
        "adapter": name,
        "reference": "reference_ops.py (strict FP32)",
        "tolerances": "tolerances.json",
        "seed": SEED,
        "cases_per_op": CASES_PER_OP,
        "operations": {},
    }
    all_pass = True
    for op in OPS:
        limits = tolerances["operations"][op]
        abs_tol = float(limits["abs_tol"])
        cos_min = float(limits["cos_min"])
        exact_required = bool(limits.get("exact_required", False))
        worst_diff = 0.0
        worst_cosine = 1.0
        exact_total = 0
        n = 0
        expected_n = 0
        error: str | None = None
        try:
            for kwargs in cases[op]:
                expected = _flat(_call(reference_ops, op, kwargs))
                got = _flat(_call(adapter, op, kwargs))
                result = compare.compare_arrays(expected, got)
                worst_diff = max(worst_diff, result["max_abs_diff"])
                worst_cosine = min(worst_cosine, result["cosine_similarity"])
                exact_total += result["exact_matches"]
                n += result["n"]
                expected_n += len(expected)
        except (ValueError, TypeError, AttributeError) as exc:
            error = f"{type(exc).__name__}: {exc}"
        passed = (
            error is None
            and worst_diff <= abs_tol
            and worst_cosine >= cos_min
            and n == expected_n
            and (not exact_required or exact_total == n)
        )
        all_pass = all_pass and passed
        report["operations"][op] = {
            "case_count": len(cases[op]),
            "elements_compared": n,
            "max_abs_diff": worst_diff,
            "min_cosine": worst_cosine,
            "exact_matches": exact_total,
            "abs_tol": abs_tol,
            "cos_min": cos_min,
            "error": error,
            "pass": passed,
        }
    report["overall_pass"] = all_pass
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--calibrate", action="store_true", help="write tolerances.json")
    parser.add_argument("--self-test", action="store_true", help="use reference_ops as candidate")
    parser.add_argument("--adapter", type=Path, help="candidate module path")
    args = parser.parse_args()
    if args.calibrate:
        table = calibrate()
        (HERE / "tolerances.json").write_text(
            json.dumps(table, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        print(json.dumps(table, indent=2, sort_keys=True))
        return 0
    name = "self-test:reference_ops" if args.self_test else str(args.adapter)
    report = run_gate(args.adapter, name)
    results_dir = HERE / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    if args.self_test:
        label = "g2_selftest"
    else:
        label = "g2_" + "".join(
            ch if ch.isalnum() or ch in "-_" else "_" for ch in Path(str(args.adapter)).stem
        )
    out = results_dir / f"{label}.json"
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    print("PASS" if report["overall_pass"] else "FAIL")
    return 0 if report["overall_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
