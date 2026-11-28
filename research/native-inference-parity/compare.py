"""Comparison utilities for candidate-engine outputs against the FP32 reference.

Pure standard library. Accepts flat or nested JSON arrays of numbers (or token
IDs) so an optimised kernel can dump its results without depending on NumPy.

Usage:
    python compare.py reference.json candidate.json
    python compare.py reference_tokens.json candidate_tokens.json --tokens
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any


def flatten(value: Any) -> list[float]:
    """Flatten nested lists of numbers into one list."""
    if isinstance(value, list):
        out: list[float] = []
        for item in value:
            out.extend(flatten(item))
        return out
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return [float(value)]
    raise ValueError(f"unsupported array element: {type(value).__name__}")


def load_arrays(path: str) -> list[float]:
    return flatten(json.loads(Path(path).read_text(encoding="utf-8")))


def compare_arrays(reference: list[float], candidate: list[float]) -> dict:
    """Return absolute/relative-free similarity metrics for two numeric arrays."""
    if len(reference) != len(candidate):
        raise ValueError(f"length mismatch: {len(reference)} vs {len(candidate)}")
    if not reference:
        raise ValueError("empty arrays cannot be compared")
    diffs = [abs(float(a) - float(b)) for a, b in zip(reference, candidate)]
    dot = sum(float(a) * float(b) for a, b in zip(reference, candidate))
    norm_a = math.sqrt(sum(float(a) * float(a) for a in reference))
    norm_b = math.sqrt(sum(float(b) * float(b) for b in candidate))
    cosine = 1.0 if norm_a == 0.0 and norm_b == 0.0 else (
        dot / (norm_a * norm_b) if norm_a and norm_b else 0.0
    )
    return {
        "n": len(reference),
        "max_abs_diff": max(diffs),
        "mean_abs_diff": sum(diffs) / len(diffs),
        "cosine_similarity": cosine,
        "exact_matches": sum(d == 0.0 for d in diffs),
    }


def compare_tokens(reference: list[int], candidate: list[int]) -> dict:
    """Compare generated token ID sequences position by position."""
    if len(reference) != len(candidate):
        raise ValueError(f"token length mismatch: {len(reference)} vs {len(candidate)}")
    matches = sum(int(a) == int(b) for a, b in zip(reference, candidate))
    return {"n": len(reference), "exact_matches": matches, "exact_sequence": matches == len(reference)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reference")
    parser.add_argument("candidate")
    parser.add_argument("--tokens", action="store_true", help="compare integer token IDs")
    parser.add_argument("--abs-tol", type=float, default=1e-5)
    parser.add_argument("--cos-min", type=float, default=0.9999)
    args = parser.parse_args()

    left, right = load_arrays(args.reference), load_arrays(args.candidate)
    if args.tokens:
        result = compare_tokens(left, right)
        ok = result["exact_sequence"]
    else:
        result = compare_arrays(left, right)
        ok = result["max_abs_diff"] <= args.abs_tol and result["cosine_similarity"] >= args.cos_min
    print(json.dumps(result, indent=2))
    print("PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
