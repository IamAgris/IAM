"""Tokenizer data + BPE sequence parity check (research only).

Two independent sources are compared:
  * the real served GGUF (tokenizer.ggml.tokens / merges arrays), parsed locally
  * the official public Qwen2.5-3B-Instruct tokenizer.json via `tokenizers`

No model is executed and no backend code is imported. This is tokenizer parity,
not engine parity.

Usage:
    python tokenizer_parity_check.py <gguf-path> <hf-tokenizer.json> <out.json>
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from gguf_probe import parse
from tokenizers import Tokenizer


def main() -> int:
    gguf_path = Path(sys.argv[1])
    hf_path = Path(sys.argv[2])
    out_path = Path(sys.argv[3])

    kv = parse(gguf_path)["kv"]
    gguf_tokens: list[str] = list(kv["tokenizer.ggml.tokens"])
    gguf_merges: list[str] = list(kv["tokenizer.ggml.merges"])

    hf_raw = json.loads(hf_path.read_text(encoding="utf-8"))
    hf_vocab: dict[str, int] = hf_raw["model"]["vocab"]
    hf_merges: list[str] = hf_raw["model"]["merges"]
    def hf_token_to_raw(token: str) -> str:
        # GGUF token bytes were decoded latin-1; HF tokens are UTF-8 text.
        return token.encode("utf-8").decode("latin-1")

    # HF keeps added tokens in a separate section; GGUF stores them inline and
    # additionally reserves [PAD...] slots up to vocab_size. Classify all three.
    id_to_name = {value: name for name, value in hf_vocab.items()}
    for item in hf_raw.get("added_tokens", []):
        id_to_name[item["id"]] = item["content"]
    unexplained = []
    pad_tokens = []
    hf_added_seen = []
    for token_id, token in enumerate(gguf_tokens):
        if token.startswith("[PAD"):
            pad_tokens.append(token_id)
        elif token_id not in id_to_name or hf_token_to_raw(id_to_name[token_id]) != token:
            unexplained.append(token_id)
        elif token_id >= len(hf_vocab):
            hf_added_seen.append(token_id)

    hf_merges_raw = [" ".join(hf_token_to_raw(part) for part in line.split()) for line in hf_merges]
    merge_mismatch_count = sum(a != b for a, b in zip(gguf_merges, hf_merges_raw))

    tokenizer = Tokenizer.from_file(str(hf_path))
    prompts = ["Hello", "OK", "IAM"]
    sequences = {}
    for prompt in prompts:
        ids = tokenizer.encode(prompt, add_special_tokens=False).ids
        sequences[prompt] = {
            "ids": ids,
            "gguf_tokens": [gguf_tokens[token_id] for token_id in ids],
            "decodes_to_prompt": "".join(gguf_tokens[token_id] for token_id in ids) == prompt,
        }
    template_ids = {
        marker: tokenizer.encode(marker, add_special_tokens=False).ids
        for marker in ("<|im_start|>", "<|im_end|>", "<|endoftext|>")
    }

    # Minimal BPE encoder using only GGUF merges/vocab, no regex pre-tokenizer.
    rank = {tuple(line.split()): index for index, line in enumerate(gguf_merges)}
    vocab = {token: index for index, token in enumerate(gguf_tokens)}

    def bpe(text: str) -> list[int]:
        parts = list(text)
        ids = [vocab[part] for part in parts]
        while len(ids) > 1:
            pairs = [(ids[i], ids[i + 1]) for i in range(len(ids) - 1)]
            best = min((p for p in pairs if p in rank), key=lambda p: rank[p], default=None)
            if best is None:
                break
            out = []
            i = 0
            while i < len(ids):
                if i < len(ids) - 1 and (ids[i], ids[i + 1]) == best:
                    merged = gguf_tokens[best[0]] + gguf_tokens[best[1]]
                    if merged not in vocab:
                        return []
                    out.append(vocab[merged])
                    i += 2
                else:
                    out.append(ids[i])
                    i += 1
            ids = out
        return ids

    minimal = {prompt: bpe(prompt) for prompt in prompts}
    sequence_match = {
        prompt: minimal[prompt] == sequences[prompt]["ids"] for prompt in prompts
    }

    report = {
        "sources": {
            "gguf": str(gguf_path),
            "hf_tokenizer_json": str(hf_path),
            "hf_source_url": "https://huggingface.co/Qwen/Qwen2.5-3B-Instruct/raw/main/tokenizer.json",
        },
        "vocab_size_gguf": len(gguf_tokens),
        "vocab_size_hf": len(hf_vocab),
        "vocab_classification": {
            "hf_model_vocab_entries": len(hf_vocab),
            "hf_added_tokens": len(hf_raw.get("added_tokens", [])),
            "gguf_inline_added_tokens": len(hf_added_seen),
            "gguf_only_padding_tokens": len(pad_tokens),
            "padding_first": pad_tokens[0] if pad_tokens else None,
            "padding_last": pad_tokens[-1] if pad_tokens else None,
            "unexplained_mismatch_count": len(unexplained),
            "unexplained_ids_sample": unexplained[:10],
        },
        "merge_count_gguf": len(gguf_merges),
        "merge_count_hf": len(hf_merges),
        "merge_mismatch_count": merge_mismatch_count,
        "hf_reference_sequences": sequences,
        "hf_template_marker_ids": template_ids,
        "minimal_bpe_sequences": minimal,
        "minimal_bpe_matches_hf": sequence_match,
        "limits": [
            "minimal BPE has no regex pre-tokenizer; mismatches on complex text are expected",
            "no native engine was executed; this is tokenizer data/sequence parity only",
        ],
    }
    out_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
