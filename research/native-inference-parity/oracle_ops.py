"""Independent double-precision oracle for validating the FP32 reference.

Deliberately written with different expressions and summation order from
``reference_ops.py``. It is only a test oracle: future optimised kernels must
be compared against the strict FP32 reference, not against this file.
"""

from __future__ import annotations

import math


def rmsnorm(x, weight, eps=1e-6):
    scale = 1.0 / math.sqrt(sum(v * v for v in x) / len(x) + eps)
    return [w * (v * scale) for v, w in zip(x, weight)]


def rope_cos_sin(position, head_dim, theta=1e6):
    angles = [position / math.pow(theta, 2 * i / head_dim) for i in range(head_dim // 2)]
    return [math.cos(a) for a in angles], [math.sin(a) for a in angles]


def rope_apply(x, cos, sin):
    half = len(x) // 2
    out = []
    for i, value in enumerate(x):
        if i < half:
            out.append(value * cos[i] - x[i + half] * sin[i])
        else:
            j = i - half
            out.append(value * cos[j] + x[j] * sin[j])
    return out


def softmax(values):
    peak = max(values)
    weights = [math.exp(v - peak) for v in values]
    total = sum(weights)
    return [w / total for w in weights]


def attention_causal(q, k, v, kv_heads):
    n_heads = len(q)
    seq = len(q[0])
    dim = len(q[0][0])
    scale = 1.0 / math.sqrt(dim)
    out = []
    for head in range(n_heads):
        kv = head // (n_heads // kv_heads)
        head_out = []
        for pos in range(seq):
            scores = [sum(a * b for a, b in zip(q[head][pos], k[kv][j])) * scale for j in range(pos + 1)]
            probs = softmax(scores)
            head_out.append(
                [sum(probs[j] * v[kv][j][d] for j in range(pos + 1)) for d in range(dim)]
            )
        out.append(head_out)
    return out


def matvec(matrix, vector):
    return [sum(row[d] * vector[d] for d in range(len(vector))) for row in matrix]


def swiglu(x, w_gate, w_up, w_down):
    silu = [g / (1.0 + math.exp(-g)) for g in matvec(w_gate, x)]
    return matvec(w_down, [s * u for s, u in zip(silu, matvec(w_up, x))])
