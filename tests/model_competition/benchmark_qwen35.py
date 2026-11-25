"""Focused OD-38 benchmark for qwen3.5:4b with thinking disabled.

Task, prompt, assertions, models, quantisation and 512-token budget are unchanged
from the other trials. Only the inference mode differs (`think=false`), required
because the default thinking mode consumed the entire token budget with no code.
Coder trials bracket the new model to detect drift and reduce ordering bias.

Usage: python tests/model_competition/benchmark_qwen35.py
"""

from full_benchmark import run_trial

NEW = "local-qwen3.5-4b"
REF = "local-qwen-coder-3b"
NO_THINK = {"think": False}

PLAN = [
    ("cold", NEW, 16), ("cold", REF, 17),
    ("cold", NEW, 18), ("cold", REF, 19),
    ("warm", NEW, 20), ("warm", REF, 21),
    ("warm", REF, 22), ("warm", NEW, 23),
    ("warm", NEW, 24), ("warm", REF, 25),
    ("warm", REF, 26), ("warm", NEW, 27),
    ("warm", NEW, 28), ("warm", REF, 29),
]


def main() -> None:
    for phase, model, order in PLAN:
        extra = NO_THINK if model == NEW else None
        run_trial(model, phase, order, extra_body=extra)


if __name__ == "__main__":
    main()
