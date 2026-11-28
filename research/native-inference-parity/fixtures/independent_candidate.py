"""Independent implementation of the seven G2 operations (research control).

Does NOT import ``reference_ops`` or ``oracle_ops``. Uses plain Python float64
with different summation order and formulas (math.fsum, exp/log rather than the
strict per-step FP32 rounding of the reference).

This is a *control implementation*, not an engine and not evidence of model
parity. Its purpose is to test whether the calibrated G2 tolerances can pass a
genuinely different implementation, rather than only a wrapper of the reference.
"""

from __future__ import annotations

import math
import struct


def rmsnorm(x, weight, eps=1e-6):
    mean_square = math.fsum(v * v for v in x) / len(x)
    inv = 1.0 / math.sqrt(mean_square + eps)
    return [w * (v * inv) for v, w in zip(x, weight)]


def rope_inv_freq(head_dim, theta=1e6):
    return [math.exp(-math.log(theta) * (2 * i) / head_dim) for i in range(head_dim // 2)]


def rope_cos_sin(position, head_dim, theta=1e6):
    freqs = rope_inv_freq(head_dim, theta)
    angles = [position * f for f in freqs]
    return [math.cos(a) for a in angles], [math.sin(a) for a in angles]


def rope_apply(x, cos, sin):
    half = len(x) // 2
    first = [x[i] * cos[i] - x[i + half] * sin[i] for i in range(half)]
    second = [x[i + half] * cos[i] + x[i] * sin[i] for i in range(half)]
    return first + second


def attention_causal(q, k, v, kv_heads):
    n_heads = len(q)
    seq = len(q[0])
    dim = len(q[0][0])
    ratio = n_heads // kv_heads
    scale = 1.0 / math.sqrt(dim)
    out = []
    for head in range(n_heads):
        kv = head // ratio
        head_out = []
        for pos in range(seq):
            scores = [
                math.fsum(a * b for a, b in zip(q[head][pos], k[kv][j])) * scale
                for j in range(pos + 1)
            ]
            peak = max(scores)
            weights = [math.exp(s - peak) for s in scores]
            total = math.fsum(weights)
            probs = [w / total for w in weights]
            value = [
                math.fsum(probs[j] * v[kv][j][d] for j in range(pos + 1))
                for d in range(dim)
            ]
            head_out.append(value)
        out.append(head_out)
    return out


def _matvec(matrix, vector):
    return [math.fsum(row[d] * vector[d] for d in range(len(vector))) for row in matrix]


def swiglu(x, w_gate, w_up, w_down):
    gate = _matvec(w_gate, x)
    up = _matvec(w_up, x)
    activated = [(g / (1.0 + math.exp(-g))) * u for g, u in zip(gate, up)]
    return _matvec(w_down, activated)


def dequant_q8_0_row(row, scales_fp16=True):
    block = 32
    stride = block + (2 if scales_fp16 else 4)
    if len(row) % stride:
        raise ValueError("row length is not a whole number of Q8_0 blocks")
    out = []
    for offset in range(0, len(row), stride):
        if scales_fp16:
            scale = struct.unpack("<e", row[offset + block : offset + block + 2])[0]
        else:
            scale = struct.unpack("<f", row[offset + block : offset + block + 4])[0]
        for byte in row[offset : offset + block]:
            signed = byte - 256 if byte > 127 else byte
            out.append(signed * scale)
    return out
