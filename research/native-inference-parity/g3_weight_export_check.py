"""G3 weight-export parity check on real Qwen2.5-3B GGUF rows (research only).

Reads the actual served GGUF, dequantises a few Q6_K rows using the pinned
ggml-quants.c layout, quantises them to upstream llm.asm per-row Q8_0 (FP16
block scales), then dequantises with the G2 reference and compares to FP32.

This proves the format path on real weights. It does not export a full model
or run an engine.

Usage: python g3_weight_export_check.py <gguf> <out.json> [rows]
"""

from __future__ import annotations

import json
import math
import struct
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "fixtures"))

from gguf_probe import parse
from q6k_dequant import BLOCK_BYTES, dequant_row
from reference_ops import dequant_q8_0_row


def quant_q8_0_row(values: list[float]) -> tuple[bytes, float]:
    raw = bytearray()
    max_scale = 0.0
    for offset in range(0, len(values), 32):
        block = values[offset : offset + 32]
        amax = max(abs(value) for value in block)
        scale = amax / 127.0 if amax else 0.0
        packed = struct.pack("<e", scale)
        scale_fp16 = struct.unpack("<e", packed)[0]
        max_scale = max(max_scale, scale_fp16)
        for value in block:
            quantised = round(value / scale_fp16) if scale_fp16 else 0
            raw.append(max(-127, min(127, quantised)) & 0xFF)
        raw.extend(packed)
    return bytes(raw), max_scale


def main() -> int:
    gguf = Path(sys.argv[1])
    out_path = Path(sys.argv[2])
    n_rows = int(sys.argv[3]) if len(sys.argv) > 3 else 4

    parsed = parse(gguf)
    tensors = parsed["tensors"]
    info = tensors["token_embd.weight"]
    if info["dtype"] != 14:
        raise SystemExit(f"expected GGML_TYPE_Q6_K (14), got {info['dtype']}")
    k, rows = info["dims"]
    if k % 256:
        raise SystemExit(f"row width {k} is not a multiple of 256")
    row_bytes = (k // 256) * BLOCK_BYTES

    ordered = sorted(tensors.items(), key=lambda item: item[1]["offset"])
    position = next(i for i, (name, _) in enumerate(ordered) if name == "token_embd.weight")
    next_offset = (
        ordered[position + 1][1]["offset"] if position + 1 < len(ordered) else gguf.stat().st_size
    )
    expected_bytes = rows * row_bytes
    byte_count_ok = expected_bytes == (next_offset - info["offset"])

    results = []
    with gguf.open("rb") as fh:
        fh.seek(parsed["data_start"] + info["offset"])
        for _ in range(min(n_rows, rows)):
            raw = fh.read(row_bytes)
            if len(raw) != row_bytes:
                raise SystemExit("short read from GGUF tensor")
            fp32 = dequant_row(raw, k)
            q8, max_scale = quant_q8_0_row(fp32)
            restored = dequant_q8_0_row(q8, scales_fp16=True)
            diffs = [abs(a - b) for a, b in zip(fp32, restored)]
            dot = sum(a * b for a, b in zip(fp32, restored))
            norm_a = math.sqrt(sum(a * a for a in fp32))
            norm_b = math.sqrt(sum(b * b for b in restored))
            cosine = dot / (norm_a * norm_b) if norm_a and norm_b else 0.0
            results.append(
                {
                    "max_abs_diff": max(diffs),
                    "mean_abs_diff": sum(diffs) / len(diffs),
                    "cosine": cosine,
                    "max_q8_scale": max_scale,
                    "within_2x_scale": max(diffs) <= 2 * max_scale,
                    "cosine_ok": cosine >= 0.9999,
                }
            )

    overall = byte_count_ok and all(item["within_2x_scale"] and item["cosine_ok"] for item in results)
    report = {
        "gate": "G3-weight-export",
        "source": str(gguf),
        "tensor": "token_embd.weight",
        "ggml_type": info["dtype"],
        "ggml_type_name": "GGML_TYPE_Q6_K (14), file_type 15 = MOSTLY_Q4_K_M",
        "derived": {
            "dims": info["dims"],
            "row_values": k,
            "blocks_per_row": k // 256,
            "block_bytes": BLOCK_BYTES,
            "row_bytes": row_bytes,
            "expected_tensor_bytes": expected_bytes,
            "actual_tensor_range_bytes": next_offset - info["offset"],
            "byte_count_ok": byte_count_ok,
        },
        "source_reference": "ggml-org/ggml ggml/src/ggml-quants.c dequantize_row_q6_K lines 1949-1978",
        "rows_checked": len(results),
        "rows": results,
        "overall_pass": overall,
        "limits": [
            "only a few embedding rows, not the full model",
            "Q8_0 output is a research format check, not a written .asmbin file",
            "no engine run or logit comparison",
        ],
    }
    out_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    print("PASS" if overall else "FAIL")
    return 0 if overall else 1


if __name__ == "__main__":
    raise SystemExit(main())
