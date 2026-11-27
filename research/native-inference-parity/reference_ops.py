"""Strict FP32 reference implementations of Qwen2.5 transformer operations.

Shapes use plain nested lists:

* vectors: ``[float, ...]``
* matrices: ``[[float, ...], ...]`` row-major
* attention inputs: ``q[kv_head][seq][dim]`` style nested lists described per function

This is a *reference*, not a fast implementation. Each arithmetic step is
rounded to binary32 via :func:`f32`, so an optimised kernel can be compared
against a deterministic, architecture-independent result.
"""

from __future__ import annotations

import math

from f32 import f32, f32_dot, f32_sum


def rmsnorm(x: list[float], weight: list[float], eps: float = 1e-6) -> list[float]:
    """RMSNorm: x / sqrt(mean(x^2) + eps) * weight."""
    if len(x) != len(weight) or not x:
        raise ValueError("rmsnorm requires non-empty equal-length vectors")
    mean_square = f32(f32_sum(f32(v * v) for v in x) / f32(len(x)))
    inv = f32(1.0 / f32(math.sqrt(f32(mean_square + f32(eps)))))
    return [f32(f32(f32(v * inv) * w)) for v, w in zip(x, weight)]


def rope_inv_freq(head_dim: int, theta: float = 1e6) -> list[float]:
    """Qwen2.5 inverse frequencies, one per even index of a head."""
    if head_dim <= 0 or head_dim % 2:
        raise ValueError("head_dim must be positive and even")
    return [f32(1.0 / f32(math.pow(f32(theta), f32(2 * i / head_dim)))) for i in range(head_dim // 2)]


def rope_cos_sin(position: int, head_dim: int, theta: float = 1e6) -> tuple[list[float], list[float]]:
    """RoPE cos/sin tables for one position, matching HF split-half rotation."""
    freqs = rope_inv_freq(head_dim, theta)
    angle = [f32(f32(position) * f) for f in freqs]
    return [f32(math.cos(a)) for a in angle], [f32(math.sin(a)) for a in angle]


def rope_apply(
    x: list[float], cos: list[float], sin: list[float]
) -> list[float]:
    """Split-half (NeoX) RoPE: out = x * cos + rotate_half(x) * sin."""
    dim = len(x)
    if dim % 2 or len(cos) != dim // 2 or len(sin) != dim // 2:
        raise ValueError("RoPE needs an even vector and dim/2 cos/sin tables")
    half = dim // 2
    out = []
    for i in range(half):
        out.append(f32(f32(f32(x[i] * cos[i]) - f32(x[i + half] * sin[i]))))
    for i in range(half):
        out.append(f32(f32(f32(x[i + half] * cos[i]) + f32(x[i] * sin[i]))))
    return out


def repeat_kv_head_index(head: int, kv_heads: int, n_heads: int) -> int:
    """Map a query head to its KV head for grouped-query attention."""
    if kv_heads <= 0 or n_heads % kv_heads:
        raise ValueError("n_heads must be a positive multiple of kv_heads")
    return head // (n_heads // kv_heads)


def softmax(values: list[float]) -> list[float]:
    """Numerically stable softmax in FP32."""
    if not values:
        raise ValueError("softmax requires a non-empty vector")
    peak = max(values)
    exps = [f32(math.exp(f32(v - peak))) for v in values]
    total = f32_sum(exps)
    return [f32(e / total) for e in exps]


def attention_causal(
    q: list[list[list[float]]],
    k: list[list[list[float]]],
    v: list[list[list[float]]],
    kv_heads: int,
) -> list[list[list[float]]]:
    """Causal GQA attention.

    ``q`` is ``[n_heads][seq][dim]``; ``k`` and ``v`` are ``[kv_heads][seq][dim]``.
    Returns ``[n_heads][seq][dim]``.
    """
    n_heads = len(q)
    seq = len(q[0])
    dim = len(q[0][0])
    if len(k) != kv_heads or len(v) != kv_heads or len(k[0]) != seq or len(v[0]) != seq:
        raise ValueError("inconsistent attention shapes")
    scale = f32(1.0 / f32(math.sqrt(f32(dim))))
    out = []
    for head in range(n_heads):
        kv = repeat_kv_head_index(head, kv_heads, n_heads)
        head_out = []
        for pos in range(seq):
            scores = [
                f32(f32(f32_dot(q[head][pos], k[kv][j]) * scale)) for j in range(pos + 1)
            ]
            probs = softmax(scores)
            value = [f32(0.0)] * dim
            for j, prob in enumerate(probs):
                for d in range(dim):
                    value[d] = f32(value[d] + f32(prob * v[kv][j][d]))
            head_out.append(value)
        out.append(head_out)
    return out


def matvec(matrix: list[list[float]], vector: list[float]) -> list[float]:
    """Row-major matrix-vector product in FP32."""
    if matrix and len(matrix[0]) != len(vector):
        raise ValueError("matvec shape mismatch")
    return [f32_dot(row, vector) for row in matrix]


def swiglu(
    x: list[float],
    w_gate: list[list[float]],
    w_up: list[list[float]],
    w_down: list[list[float]],
) -> list[float]:
    """SwiGLU MLP: down(silu(x @ gate) * (x @ up))."""
    gate = matvec(w_gate, x)
    up = matvec(w_up, x)
    activated = [
        f32(f32(f32(g / f32(1.0 + f32(math.exp(f32(-g))))) * u)) for g, u in zip(gate, up)
    ]
    return matvec(w_down, activated)


def dequant_q8_0_row(row: bytes, scales_fp16: bool = True) -> list[float]:
    """Dequantise one per-row split Q8_0 weight row (block size 32).

    Layout is ``[32 int8 values][1 scale]`` repeated across the row. Scale is
    raw binary16 when ``scales_fp16`` is true, otherwise raw binary32.
    """
    from f32 import fp16_to_f32

    block = 32
    stride = block + (2 if scales_fp16 else 4)
    if len(row) % stride:
        raise ValueError("row length is not a whole number of Q8_0 blocks")
    out: list[float] = []
    for offset in range(0, len(row), stride):
        if scales_fp16:
            scale = fp16_to_f32(int.from_bytes(row[offset + block : offset + block + 2], "little"))
        else:
            scale = f32(struct_unpack_f32(row[offset + block : offset + block + 4]))
        for byte in row[offset : offset + block]:
            signed = byte - 256 if byte > 127 else byte
            out.append(f32(f32(signed) * scale))
    return out


def struct_unpack_f32(raw: bytes) -> float:
    import struct

    return struct.unpack("<f", raw)[0]
