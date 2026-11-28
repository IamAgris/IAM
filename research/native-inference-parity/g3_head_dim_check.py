"""G3 head_dim / QK-Norm blocker check against real Qwen2.5-3B artifacts.

Reads fixtures captured from the running aura-ollama container and compares the
upstream llm.asm exporter path with the research adapter. Records JSON evidence.

This is structural research evidence only. It does not export weights, run the
model or authorise any production change.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "fixtures"))

from qwen25_export_adapter import (
    qk_norm_support,
    resolve_head_dim,
    resolve_header_fields,
    upstream_head_dim,
)

FIXTURES = HERE / "fixtures"
RESULTS = HERE / "results"


def main() -> int:
    info = json.loads((FIXTURES / "qwen25_3b_modelinfo.json").read_text(encoding="utf-8-sig"))
    meta = info["model_info"]
    names = [
        line.strip()
        for line in (FIXTURES / "qwen25_3b_tensor_names.txt").read_text(encoding="utf-8-sig").splitlines()
        if line.strip()
    ]

    cfg = {
        "hidden_size": meta["qwen2.embedding_length"],
        "intermediate_size": meta["qwen2.feed_forward_length"],
        "num_hidden_layers": meta["qwen2.block_count"],
        "num_attention_heads": meta["qwen2.attention.head_count"],
        "num_key_value_heads": meta["qwen2.attention.head_count_kv"],
        "rms_norm_eps": meta["qwen2.attention.layer_norm_rms_epsilon"],
        "rope_theta": meta["qwen2.rope.freq_base"],
    }

    checks: list[dict[str, object]] = []
    try:
        upstream_head_dim(cfg)
        upstream_error = None
    except KeyError as exc:
        upstream_error = f"KeyError: {exc.args[0]!r}"
    checks.append(
        {
            "name": "upstream exporter head_dim requirement fails on real Qwen2.5 metadata",
            "expected": "KeyError: 'head_dim'",
            "actual": upstream_error,
            "pass": upstream_error == "KeyError: 'head_dim'",
        }
    )

    derived = resolve_head_dim(cfg)
    checks.append({"name": "derived head_dim", "expected": 128, "actual": derived, "pass": derived == 128})

    qk = qk_norm_support(names)
    checks.append(
        {
            "name": "QK-Norm tensors absent from real GGUF header",
            "expected": False,
            "actual": qk,
            "pass": qk is False,
        }
    )

    fields = resolve_header_fields(cfg, names)
    for key, expected in (
        ("dim", 2048),
        ("hidden_dim", 11008),
        ("n_layers", 36),
        ("n_heads", 16),
        ("n_kv_heads", 2),
        ("head_dim", 128),
    ):
        actual = fields[key]
        checks.append({"name": f"resolved header field {key}", "expected": expected, "actual": actual, "pass": actual == expected})

    checks.append(
        {
            "name": "real GGUF has no head_dim key",
            "expected": [],
            "actual": [key for key in info["provenance"]["all_model_info_keys"] if "head_dim" in key.lower()],
            "pass": not any("head_dim" in key.lower() for key in info["provenance"]["all_model_info_keys"]),
        }
    )

    overall = all(bool(item["pass"]) for item in checks)
    report = {
        "gate": "G3-head_dim",
        "provenance": info["provenance"],
        "tensor_names_source": "first 8 MiB of GGUF blob sha256:5ee4f07c... via grep -a on aura-ollama",
        "upstream": "alesha-pro/llm.asm @ 48feccbf (export_weights.py:235,279-285)",
        "resolved_fields": fields,
        "limits": [
            "vocab_size not present in GGUF metadata; not resolved here",
            "tie_word_embeddings not verified from available artifacts; default only",
            "<|im_start|> token ID not available; chat IDs must not be guessed",
            "no weights exported and no engine run",
        ],
        "checks": checks,
        "overall_pass": overall,
    }
    RESULTS.mkdir(parents=True, exist_ok=True)
    out = RESULTS / "g3_head_dim_check.json"
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    print("PASS" if overall else "FAIL")
    return 0 if overall else 1


if __name__ == "__main__":
    raise SystemExit(main())
