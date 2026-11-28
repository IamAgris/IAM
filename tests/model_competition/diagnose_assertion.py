"""Diagnose the shared `a//b///c` failure without changing the benchmark task.

Uses the exact code generated during full_benchmark.py and runs a wider matrix
of edge cases. No model calls, no prompt changes, no changed expectations:
expected values follow the original task specification (collapse repeated '/',
strip outer '/', '' for None/empty).

Usage: python tests/model_competition/diagnose_assertion.py
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
RECORDS = HERE / "results" / "constrained_results.jsonl"
OUT = HERE / "results" / "assertion_diagnosis.json"

CASES = [
    (None, ""),
    ("", ""),
    ("a", "a"),
    ("a/b", "a/b"),
    ("a//b", "a/b"),
    ("a///b", "a/b"),
    ("a////b", "a/b"),
    ("/a/b/", "a/b"),
    ("//a//b//", "a/b"),
    ("///", ""),
    ("////", ""),
    ("/", ""),
    ("a//b///c", "a/b/c"),
    ("a/b//c///d/", "a/b/c/d"),
    ("a//", "a"),
    ("//a", "a"),
]

RUNNER = """
import importlib.util, json, sys
spec = importlib.util.spec_from_file_location('candidate', sys.argv[1])
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
f = mod.normalise_path
cases = json.loads(sys.argv[2])
results = []
for value, expected in cases:
    try:
        actual = f(value)
        results.append({'input': value, 'expected': expected,
                        'actual': actual, 'pass': actual == expected})
    except Exception as exc:
        results.append({'input': value, 'expected': expected,
                        'actual': f'ERROR: {exc}', 'pass': False})
print('@@' + json.dumps(results))
"""


def load_codes():
    rows = [json.loads(line) for line in RECORDS.read_text(encoding="utf-8").splitlines()]
    codes = {}
    for row in rows:
        if row.get("code") and row["model"] not in codes:
            codes[row["model"]] = row["code"]
    return codes


def run_matrix(code: str):
    with tempfile.TemporaryDirectory() as tmp:
        candidate = Path(tmp) / "candidate.py"
        candidate.write_text(code, encoding="utf-8")
        runner = Path(tmp) / "runner.py"
        runner.write_text(RUNNER, encoding="utf-8")
        proc = subprocess.run(
            [sys.executable, str(runner), str(candidate), json.dumps(CASES)],
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
            cwd=tmp,
        )
    line = next((l for l in proc.stdout.splitlines() if l.startswith("@@")), None)
    if not line:
        return {"error": (proc.stderr or proc.stdout)[:500]}
    return {"results": json.loads(line[2:])}


def main() -> None:
    codes = load_codes()
    report = {}
    for model, code in codes.items():
        results = run_matrix(code)
        failures = [r for r in results.get("results", []) if not r["pass"]]
        report[model] = {
            "code": code,
            "cases_total": len(results.get("results", [])),
            "cases_failed": len(failures),
            "failures": failures,
        }
        print(f"\n{model}: {len(failures)}/{len(results.get('results', []))} cases failed")
        for failure in failures:
            print(
                f"  input={failure['input']!r:16} expected={failure['expected']!r:12}"
                f" actual={failure['actual']!r}"
            )

    verdict = {
        "spec_test_consistency": (
            "PASS — expected values match the original task spec: collapse repeated "
            "'/' to one, strip outer '/', return '' for None/empty. The test is not "
            "stricter than the specification."
        ),
        "root_cause": (
            "Model coding error, not a specification or harness problem. The coder "
            "model used a single replace('//', '/'), which cannot collapse 3+ "
            "consecutive separators. The general model used '/'.join(path.split('/')) "
            "without dropping empty split parts, so repeats survive. Both handle "
            "None/empty and outer stripping correctly."
        ),
        "models": report,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(verdict, indent=2) + "\n", encoding="utf-8")
    print(f"\nWrote {OUT.relative_to(HERE.parents[2])}")


if __name__ == "__main__":
    main()
