"""Q6_K dequantisation derived from pinned ggml-quants.c (research only).

Source: ggml-org/ggml master, ggml/src/ggml-quants.c
  dequantize_row_q6_K at lines 1949-1978
  block_q6_K layout: ql[128] qh[64] scales[16] (int8) d (fp16) = 210 bytes,
  256 values per block (QK_K = 256).

Used only to convert a few real GGUF rows to FP32 for the export round-trip
check. Not imported by backend/ or frontend/.
"""

from __future__ import annotations

import struct

BLOCK_BYTES = 210
BLOCK_VALUES = 256


def dequant_block(block: bytes) -> list[float]:
    if len(block) != BLOCK_BYTES:
        raise ValueError(f"Q6_K block must be {BLOCK_BYTES} bytes, got {len(block)}")
    d = struct.unpack("<e", block[208:210])[0]
    ql = block[0:128]
    qh = block[128:192]
    sc = [value - 256 if value > 127 else value for value in block[192:208]]
    out = [0.0] * BLOCK_VALUES
    for n in range(0, BLOCK_VALUES, 128):
        ql_off, qh_off, sc_off = n // 2, n // 4, n // 16
        for l in range(32):
            is_ = l // 16
            q1 = ((ql[ql_off + l] & 0x0F) | (((qh[qh_off + l] >> 0) & 3) << 4)) - 32
            q2 = ((ql[ql_off + l + 32] & 0x0F) | (((qh[qh_off + l] >> 2) & 3) << 4)) - 32
            q3 = ((ql[ql_off + l] >> 4) | (((qh[qh_off + l] >> 4) & 3) << 4)) - 32
            q4 = ((ql[ql_off + l + 32] >> 4) | (((qh[qh_off + l] >> 6) & 3) << 4)) - 32
            out[n + l + 0] = d * sc[sc_off + is_ + 0] * q1
            out[n + l + 32] = d * sc[sc_off + is_ + 2] * q2
            out[n + l + 64] = d * sc[sc_off + is_ + 4] * q3
            out[n + l + 96] = d * sc[sc_off + is_ + 6] * q4
    return out


def dequant_row(raw: bytes, values: int) -> list[float]:
    if values % BLOCK_VALUES:
        raise ValueError("Q6_K row length must be a multiple of 256")
    out: list[float] = []
    for offset in range(0, len(raw), BLOCK_BYTES):
        out.extend(dequant_block(raw[offset : offset + BLOCK_BYTES]))
    return out[:values]
