"""G3 structural fixture check using REAL Qwen2.5-3B artifacts (research only).

Artifacts were copied read-only from the running ``aura-ollama`` container:
  * ``fixtures/qwen25_3b_manifest.json`` -- Ollama model manifest
  * ``fixtures/qwen25_3b_template.txt`` -- template layer blob
  * ``fixtures/qwen25_3b_modelinfo.json`` -- curated GGUF metadata from /api/show

This checks architecture facts, template special-token markers, artifact
integrity and the Qwen3 -> Qwen2.5 incompatibilities it reveals. It does NOT
claim full BPE/token-sequence parity: ``tokenizer.ggml.tokens`` and ``merges``
were returned empty by /api/show, and no GGUF weight tensor is loaded here.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
FIXTURES = HERE / "fixtures"
RESULTS = HERE / "results"


def _text(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8-sig")


def main() -> int:
    manifest = json.loads(_text("qwen25_3b_manifest.json"))
    modelinfo = json.loads(_text("qwen25_3b_modelinfo.json"))
    template = _text("qwen25_3b_template.txt")
    meta = modelinfo["model_info"]
    all_keys = modelinfo["provenance"]["all_model_info_keys"]

    checks: list[dict[str, object]] = []

    def check(name: str, expected: object, actual: object) -> None:
        checks.append({"name": name, "expected": expected, "actual": actual, "pass": expected == actual})

    template_digest = "sha256:" + hashlib.sha256(template.encode("utf-8")).hexdigest()
    declared = next(
        layer["digest"]
        for layer in manifest["layers"]
        if layer["mediaType"] == "application/vnd.ollama.image.template"
    )
    check("template blob digest matches manifest", declared, template_digest)

    check("GGUF architecture", "qwen2", meta["general.architecture"])
    check("block_count (layers)", 36, meta["qwen2.block_count"])
    check("embedding_length (dim)", 2048, meta["qwen2.embedding_length"])
    check("feed_forward_length (intermediate)", 11008, meta["qwen2.feed_forward_length"])
    check("attention heads", 16, meta["qwen2.attention.head_count"])
    check("KV heads", 2, meta["qwen2.attention.head_count_kv"])
    check("rope theta", 1000000, meta["qwen2.rope.freq_base"])
    check("rms norm epsilon", 0.000001, meta["qwen2.attention.layer_norm_rms_epsilon"])
    check("tokenizer pre", "qwen2", meta["tokenizer.ggml.pre"])
    check("add_bos_token", False, meta["tokenizer.ggml.add_bos_token"])
    check("bos token id", 151643, meta["tokenizer.ggml.bos_token_id"])
    check("eos token id", 151645, meta["tokenizer.ggml.eos_token_id"])

    head_dim_keys = [key for key in all_keys if "head_dim" in key.lower()]
    check("GGUF metadata has no head_dim key", [], head_dim_keys)
    check("chat template has im_start marker", True, "<|im_start|>" in template)
    check("chat template has im_end marker", True, "<|im_end|>" in template)

    # Upstream llm.asm @ 48feccbf, shared/constants.inc:86-95 (Qwen3 IDs).
    upstream_qwen3_ids = [151644, 151645, 151667, 151668]
    real_qwen25_ids = [
        meta["tokenizer.ggml.bos_token_id"],
        meta["tokenizer.ggml.eos_token_id"],
    ]
    check(
        "upstream Qwen3 chat IDs cannot be reused unchanged",
        True,
        not all(value in real_qwen25_ids for value in upstream_qwen3_ids),
    )

    overall = all(bool(item["pass"]) for item in checks)
    report = {
        "gate": "G3-structural",
        "provenance": modelinfo["provenance"],
        "upstream_reference": "alesha-pro/llm.asm @ 48feccbf, shared/constants.inc:86-95",
        "limits": [
            "tokenizer.ggml.tokens/merges empty in /api/show; no BPE sequence parity",
            "no GGUF weight tensor loaded; no logit or token-sequence comparison",
            "structural evidence only, not an engine or deployment claim",
        ],
        "checks": checks,
        "overall_pass": overall,
    }
    RESULTS.mkdir(parents=True, exist_ok=True)
    out = RESULTS / "g3_fixture_check.json"
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    print("PASS" if overall else "FAIL")
    return 0 if overall else 1


if __name__ == "__main__":
    raise SystemExit(main())
