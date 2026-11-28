"""Minimal read-only GGUF metadata/tensor probe (research only).

Reads a GGUF file with the Python standard library. No model execution, no
writes to the model file. Used to verify vocab size, special token IDs and
tied embeddings from the actual served Qwen2.5-3B artifact.

Usage:
    python research/native-inference-parity/gguf_probe.py <gguf-path> <out-json>
"""

from __future__ import annotations

import hashlib
import json
import struct
import sys
from pathlib import Path

MAGIC = b"GGUF"


class Reader:
    def __init__(self, data: bytes) -> None:
        self.data = data
        self.pos = 0

    def take(self, n: int) -> bytes:
        out = self.data[self.pos : self.pos + n]
        if len(out) != n:
            raise ValueError(f"unexpected EOF at {self.pos}: wanted {n} bytes")
        self.pos += n
        return out

    def u8(self) -> int:
        return self.take(1)[0]

    def i8(self) -> int:
        return struct.unpack("<b", self.take(1))[0]

    def u16(self) -> int:
        return struct.unpack("<H", self.take(2))[0]

    def i16(self) -> int:
        return struct.unpack("<h", self.take(2))[0]

    def u32(self) -> int:
        return struct.unpack("<I", self.take(4))[0]

    def i32(self) -> int:
        return struct.unpack("<i", self.take(4))[0]

    def u64(self) -> int:
        return struct.unpack("<Q", self.take(8))[0]

    def i64(self) -> int:
        return struct.unpack("<q", self.take(8))[0]

    def f32(self) -> float:
        return struct.unpack("<f", self.take(4))[0]

    def f64(self) -> float:
        return struct.unpack("<d", self.take(8))[0]

    def string(self) -> str:
        # GGUF byte-level token strings may contain invalid UTF-8; latin-1
        # preserves every byte so vocab/merges can be compared with HF tokens.
        return self.take(self.u64()).decode("latin-1")

    def value(self, kind: int):
        return {
            0: self.u8,
            1: self.i8,
            2: self.u16,
            3: self.i16,
            4: self.u32,
            5: self.i32,
            6: self.f32,
            7: lambda: bool(self.u8()),
            8: self.string,
            9: self.array,
            10: self.u64,
            11: self.i64,
            12: self.f64,
        }[kind]()

    def array(self):
        kind = self.u32()
        count = self.u64()
        return [self.value(kind) for _ in range(count)]


def parse(path: Path) -> dict:
    with path.open("rb") as fh:
        head = fh.read(64 * 1024 * 1024)
    r = Reader(head)
    if r.take(4) != MAGIC:
        raise ValueError("not a GGUF file")
    version = r.u32()
    tensor_count = r.u64()
    kv_count = r.u64()
    kv: dict[str, object] = {}
    for _ in range(kv_count):
        key = r.string()
        kv[key] = r.value(r.u32())
    tensors: dict[str, dict] = {}
    for _ in range(tensor_count):
        name = r.string()
        n_dims = r.u32()
        dims = [r.u64() for _ in range(n_dims)]
        dtype = r.u32()
        offset = r.u64()
        tensors[name] = {"dims": dims, "dtype": dtype, "offset": offset}
    return {
        "version": version,
        "tensor_count": tensor_count,
        "kv": kv,
        "tensors": tensors,
        "header_end": r.pos,
        "data_start": (r.pos + 31) & ~31,
        "file_size": path.stat().st_size,
    }


def sha_range(path: Path, start: int, end: int) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        fh.seek(start)
        remaining = end - start
        while remaining:
            chunk = fh.read(min(1024 * 1024, remaining))
            if not chunk:
                raise ValueError("unexpected EOF while hashing tensor")
            h.update(chunk)
            remaining -= len(chunk)
    return h.hexdigest()


def main() -> int:
    path = Path(sys.argv[1])
    out_path = Path(sys.argv[2])
    parsed = parse(path)
    kv = parsed["kv"]
    tokens = kv.get("tokenizer.ggml.tokens") or []
    by_token = {token: index for index, token in enumerate(tokens)}
    special = {
        name: by_token.get(name)
        for name in ("<|endoftext|>", "<|im_start|>", "<|im_end|>", "<tool_call>", "</tool_call>")
    }
    names = sorted(parsed["tensors"])
    qk_norm = [name for name in names if "attn_q_norm" in name or "attn_k_norm" in name]

    ordered = sorted(parsed["tensors"].items(), key=lambda item: item[1]["offset"])
    digests: dict[str, str] = {}
    for i, (name, info) in enumerate(ordered):
        if name not in ("token_embd.weight", "output.weight"):
            continue
        start = parsed["data_start"] + info["offset"]
        end = (
            parsed["data_start"] + ordered[i + 1][1]["offset"]
            if i + 1 < len(ordered)
            else parsed["file_size"]
        )
        digests[name] = sha_range(path, start, end)

    report = {
        "source": str(path),
        "file_size": parsed["file_size"],
        "gguf_version": parsed["version"],
        "tensor_count": parsed["tensor_count"],
        "vocab_size_from_tokens_array": len(tokens),
        "special_token_ids": special,
        "qk_norm_tensor_names": qk_norm,
        "standalone_output_weight_present": "output.weight" in parsed["tensors"],
        "tied_embedding_consistent_with_gguf": "output.weight" not in parsed["tensors"],
        "tied_embedding_note": (
            "GGUF has no standalone output.weight; only token_embd.weight is present. "
            "This is consistent with tied embeddings (no separate tensor to hash)."
        ),
        "tensor_sha256": digests,
        "tensor_dims": {
            name: parsed["tensors"][name]["dims"]
            for name in ("token_embd.weight", "output.weight")
            if name in parsed["tensors"]
        },
        "selected_metadata": {
            key: kv.get(key)
            for key in (
                "general.architecture",
                "general.parameter_count",
                "general.file_type",
                "qwen2.block_count",
                "qwen2.embedding_length",
                "qwen2.feed_forward_length",
                "qwen2.attention.head_count",
                "qwen2.attention.head_count_kv",
                "qwen2.context_length",
                "tokenizer.ggml.eos_token_id",
                "tokenizer.ggml.bos_token_id",
            )
        },
    }
    out_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
