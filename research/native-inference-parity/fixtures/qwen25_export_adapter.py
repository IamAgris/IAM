"""Research adapter for the llm.asm exporter's Qwen3-only assumptions.

Not imported by backend/ or frontend/. Does not modify upstream llm.asm.

Addresses two verified blockers at upstream commit 48feccbf:
  * ``scripts/export_weights.py:235`` -- ``head_dim = int(cfg["head_dim"])``
    unconditionally, but the real Qwen2.5-3B GGUF metadata has no head_dim key.
  * ``scripts/export_weights.py:279-285`` -- unconditional q_norm/k_norm tensors
    and asserts, but the real GGUF has no attn_q_norm/attn_k_norm tensors.

The adapter derives head_dim from hidden_size / num_attention_heads and reports
QK-Norm support from supplied tensor names. Chat-template token IDs are NOT
resolved here: the real <|im_start|> ID was not present in the available
artifacts, so it must not be guessed.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

UPSTREAM_HEAD_DIM_LINE = "scripts/export_weights.py:235"
UPSTREAM_QK_NORM_LINES = "scripts/export_weights.py:279-285"


def upstream_head_dim(cfg: dict[str, Any]) -> int:
    """Reproduce the upstream unconditional requirement (raises KeyError here)."""
    return int(cfg["head_dim"])


def resolve_head_dim(cfg: dict[str, Any]) -> int:
    """Use config head_dim when present, otherwise derive it from dim / heads."""
    if "head_dim" in cfg and cfg["head_dim"] not in (None, ""):
        return int(cfg["head_dim"])
    dim = int(cfg["hidden_size"])
    heads = int(cfg["num_attention_heads"])
    if heads <= 0 or dim <= 0 or dim % heads:
        raise ValueError(f"cannot derive head_dim from hidden_size={dim}, heads={heads}")
    return dim // heads


def qk_norm_support(tensor_names: Iterable[str]) -> bool:
    names = set(tensor_names)
    return any("attn_q_norm" in name or "attn_k_norm" in name for name in names)


def resolve_export_config(cfg: dict[str, Any], special_ids: dict[str, int] | None = None) -> dict[str, Any]:
    """Resolve every header field the upstream exporter needs from a real config."""
    fields = resolve_header_fields(cfg, [])
    fields["vocab_size"] = int(cfg["vocab_size"])
    fields["tie_emb"] = bool(cfg.get("tie_word_embeddings", True))
    if special_ids:
        fields["special_ids"] = {name: int(token_id) for name, token_id in special_ids.items()}
    return fields


def resolve_header_fields(cfg: dict[str, Any], tensor_names: Iterable[str]) -> dict[str, Any]:
    """Fields required by the upstream .asmbin header (except unknown vocab)."""
    return {
        "dim": int(cfg["hidden_size"]),
        "hidden_dim": int(cfg["intermediate_size"]),
        "n_layers": int(cfg["num_hidden_layers"]),
        "n_heads": int(cfg["num_attention_heads"]),
        "n_kv_heads": int(cfg["num_key_value_heads"]),
        "head_dim": resolve_head_dim(cfg),
        "rms_norm_eps": float(cfg["rms_norm_eps"]),
        "rope_theta": float(cfg["rope_theta"]),
        "qk_norm": qk_norm_support(tensor_names),
        "tie_emb_default": bool(cfg.get("tie_word_embeddings", True)),
        "head_dim_source": "config" if "head_dim" in cfg else "derived: hidden_size / num_attention_heads",
        "upstream_references": [UPSTREAM_HEAD_DIM_LINE, UPSTREAM_QK_NORM_LINES],
    }
