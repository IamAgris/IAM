"""G3 resolution of the three previously open unknowns (research only).

Uses real artifacts only:
  * local GGUF metadata captured from aura-ollama (qwen25_3b_modelinfo.json)
  * official public Qwen2.5-3B(-Instruct) config.json and tokenizer_config.json

Resolves vocab_size, tie_word_embeddings and the real special-token IDs without
guessing, and cross-corroborates local metadata against the official config.
No weights are exported and no engine is run.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
FIXTURES = HERE / "fixtures"
RESULTS = HERE / "results"
sys.path.insert(0, str(FIXTURES))

from qwen25_export_adapter import resolve_export_config

BASE = "https://huggingface.co/Qwen/Qwen2.5-3B"
INSTRUCT = "https://huggingface.co/Qwen/Qwen2.5-3B-Instruct"


def _load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8-sig"))


def main() -> int:
    local = _load("qwen25_3b_modelinfo.json")
    meta = local["model_info"]
    instruct = _load("qwen25_3b_instruct_config.json")
    base = _load("qwen25_3b_base_config.json")
    tok = _load("qwen25_3b_instruct_tokenizer_config.json")
    probe = json.loads((RESULTS / "gguf_probe.json").read_text(encoding="utf-8"))
    decoder = {int(k): v["content"] for k, v in tok["added_tokens_decoder"].items()}
    by_content = {content: token_id for token_id, content in decoder.items()}

    checks: list[dict[str, object]] = []

    def check(name: str, expected: object, actual: object) -> None:
        checks.append({"name": name, "expected": expected, "actual": actual, "pass": expected == actual})

    check("GGUF eos identifies Instruct variant", 151645, meta["tokenizer.ggml.eos_token_id"])
    check("Instruct config eos matches GGUF", meta["tokenizer.ggml.eos_token_id"], instruct["eos_token_id"])
    check("base config eos differs (variant distinction)", 151643, base["eos_token_id"])
    check("vocab_size resolved from official config", 151936, instruct["vocab_size"])
    check("tie_word_embeddings resolved from official config", True, instruct["tie_word_embeddings"])
    check("official config has no head_dim key", False, "head_dim" in instruct)

    resolved = resolve_export_config(instruct, by_content)
    check("adapter resolves vocab_size from real config", 151936, resolved["vocab_size"])
    check("adapter resolves tie_word_embeddings from real config", True, resolved["tie_emb"])
    check("adapter resolves head_dim from real config", 128, resolved["head_dim"])
    check("adapter resolves im_start token id", 151644, resolved["special_ids"]["<|im_start|>"])

    check("hidden_size corroborated", meta["qwen2.embedding_length"], instruct["hidden_size"])
    check("intermediate_size corroborated", meta["qwen2.feed_forward_length"], instruct["intermediate_size"])
    check("layers corroborated", meta["qwen2.block_count"], instruct["num_hidden_layers"])
    check("attention heads corroborated", meta["qwen2.attention.head_count"], instruct["num_attention_heads"])
    check("KV heads corroborated", meta["qwen2.attention.head_count_kv"], instruct["num_key_value_heads"])
    check("rope theta corroborated", meta["qwen2.rope.freq_base"], instruct["rope_theta"])
    check("rms eps corroborated", meta["qwen2.attention.layer_norm_rms_epsilon"], instruct["rms_norm_eps"])

    check("local GGUF vocab matches official config", instruct["vocab_size"], probe["vocab_size_from_tokens_array"])
    for content, expected_id in (
        ("<|endoftext|>", 151643),
        ("<|im_start|>", 151644),
        ("<|im_end|>", 151645),
        ("<tool_call>", 151657),
        ("</tool_call>", 151658),
    ):
        check(f"official special token {content}", expected_id, by_content.get(content))
        check(f"local GGUF special token {content}", expected_id, probe["special_token_ids"].get(content))

    check("local GGUF has no QK-Norm tensors", [], probe["qk_norm_tensor_names"])
    check("local GGUF has no standalone output.weight", False, probe["standalone_output_weight_present"])
    check(
        "tied embeddings corroborated by official config and GGUF layout",
        True,
        bool(instruct["tie_word_embeddings"]) and probe["tied_embedding_consistent_with_gguf"],
    )

    # Upstream llm.asm @ 48feccbf, shared/constants.inc:86-95 (Qwen3 values).
    check("Qwen3 TOK_IM_START equals Qwen2.5 im_start", 151644, 151644)
    check("Qwen3 TOK_IM_END equals Qwen2.5 im_end", 151645, 151645)
    check("Qwen3 think-start 151667 absent from Qwen2.5 specials", False, 151667 in decoder)
    check("Qwen3 think-end 151668 absent from Qwen2.5 specials", False, 151668 in decoder)
    check("Qwen3 TOK_USER 872 absent from Qwen2.5 specials", False, 872 in decoder)
    check("Qwen3 TOK_ASSISTANT 77091 absent from Qwen2.5 specials", False, 77091 in decoder)

    overall = all(bool(item["pass"]) for item in checks)
    report = {
        "gate": "G3-remaining",
        "local_provenance": local["provenance"],
        "local_gguf_probe": {
            "source": probe["source"],
            "file_size": probe["file_size"],
            "gguf_version": probe["gguf_version"],
            "tied_embedding_note": probe["tied_embedding_note"],
        },
        "official_sources": [
            f"{BASE}/raw/main/config.json",
            f"{INSTRUCT}/raw/main/config.json",
            f"{INSTRUCT}/raw/main/tokenizer_config.json",
        ],
        "adapter_resolved": resolved,
        "resolved": {
            "vocab_size": instruct["vocab_size"],
            "tie_word_embeddings": instruct["tie_word_embeddings"],
            "head_dim": "not in official config or GGUF metadata; derive as hidden_size / heads = 128",
            "variant": "Qwen2.5-3B-Instruct (eos_token_id 151645 matches local GGUF)",
            "special_token_ids": {
                token: by_content.get(token)
                for token in ("<|endoftext|>", "<|im_start|>", "<|im_end|>", "<tool_call>", "</tool_call>")
            },
        },
        "limits": [
            "official configs were fetched from public Hugging Face, not from the local model blob",
            "no GGUF weight tensor or full BPE token sequence was loaded or compared",
            "this is structural resolution of three unknowns, not a full exporter or engine validation",
        ],
        "checks": checks,
        "overall_pass": overall,
    }
    RESULTS.mkdir(parents=True, exist_ok=True)
    out = RESULTS / "g3_remaining_check.json"
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    print("PASS" if overall else "FAIL")
    return 0 if overall else 1


if __name__ == "__main__":
    raise SystemExit(main())
