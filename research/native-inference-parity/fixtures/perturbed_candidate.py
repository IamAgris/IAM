"""Negative-control candidate for validating the G2 gate (research only).

Wraps ``reference_ops`` unchanged except for ``rmsnorm``, which adds a small
deterministic bias. Running this through ``g2_gate.py --adapter`` must produce
an overall FAIL with ``rmsnorm`` as the only failing operation. This proves the
gate is sensitive to a wrong kernel rather than vacuously passing.

This is not an engine candidate and must never be used as evidence of parity.
"""

from __future__ import annotations

import reference_ops

BIAS = 1e-3


def rmsnorm(x, weight, eps=1e-6):
    return [value + BIAS for value in reference_ops.rmsnorm(x, weight, eps)]


rope_inv_freq = reference_ops.rope_inv_freq
rope_cos_sin = reference_ops.rope_cos_sin
rope_apply = reference_ops.rope_apply
attention_causal = reference_ops.attention_causal
swiglu = reference_ops.swiglu
dequant_q8_0_row = reference_ops.dequant_q8_0_row
