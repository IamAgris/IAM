"""Self-validation of the FP32 parity harness.

Run: python -m pytest research/native-inference-parity/test_parity.py -q
No third-party dependencies.
"""

from __future__ import annotations

import random
import struct
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from compare import compare_arrays, compare_tokens
from f32 import f32
from oracle_ops import (
    attention_causal as oracle_attention,
)
from oracle_ops import (
    rmsnorm as oracle_rmsnorm,
)
from oracle_ops import (
    rope_apply as oracle_rope,
)
from oracle_ops import (
    rope_cos_sin as oracle_rope_cs,
)
from oracle_ops import (
    swiglu as oracle_swiglu,
)
from reference_ops import (
    attention_causal,
    dequant_q8_0_row,
    repeat_kv_head_index,
    rmsnorm,
    rope_apply,
    rope_cos_sin,
    swiglu,
)


def max_diff(left, right) -> float:
    return max(abs(float(a) - float(b)) for a, b in zip(left, right))


def flatten_heads(nested):
    """Flatten [heads][seq][dim] into a single vector without quadratic concat."""
    return [value for head in nested for row in head for value in row]


class ReferenceValidationTests(unittest.TestCase):
    def setUp(self):
        self.rng = random.Random(20261128)

    def rand_vec(self, n: int, low: float = -2.0, high: float = 2.0) -> list[float]:
        return [self.rng.uniform(low, high) for _ in range(n)]

    def test_rmsnorm_matches_independent_oracle(self):
        x = self.rand_vec(64)
        weight = self.rand_vec(64, 0.5, 1.5)
        self.assertLess(max_diff(rmsnorm(x, weight), oracle_rmsnorm(x, weight)), 2e-6)

    def test_rope_at_position_zero_is_identity(self):
        x = self.rand_vec(32)
        cos, sin = rope_cos_sin(0, 32)
        out = rope_apply(x, cos, sin)
        self.assertEqual(out, [f32(v) for v in x])

    def test_rope_matches_independent_oracle(self):
        x = self.rand_vec(32)
        cos, sin = rope_cos_sin(7, 32)
        oracle_cos, oracle_sin = oracle_rope_cs(7, 32)
        self.assertLess(max_diff(rope_apply(x, cos, sin), oracle_rope(x, oracle_cos, oracle_sin)), 2e-6)

    def test_gqa_head_mapping(self):
        self.assertEqual(repeat_kv_head_index(0, 2, 16), 0)
        self.assertEqual(repeat_kv_head_index(7, 2, 16), 0)
        self.assertEqual(repeat_kv_head_index(8, 2, 16), 1)
        self.assertEqual(repeat_kv_head_index(15, 2, 16), 1)

    def test_causal_attention_matches_oracle(self):
        heads, kv_heads, seq, dim = 4, 2, 3, 8
        q = [[self.rand_vec(dim) for _ in range(seq)] for _ in range(heads)]
        k = [[self.rand_vec(dim) for _ in range(seq)] for _ in range(kv_heads)]
        v = [[self.rand_vec(dim) for _ in range(seq)] for _ in range(kv_heads)]
        got = attention_causal(q, k, v, kv_heads)
        want = oracle_attention(q, k, v, kv_heads)
        self.assertLess(max_diff(flatten_heads(got), flatten_heads(want)), 1e-5)

    def test_causal_mask_hides_future_values(self):
        heads, kv_heads, seq, dim = 2, 1, 3, 4
        q = [[self.rand_vec(dim) for _ in range(seq)] for _ in range(heads)]
        k = [[self.rand_vec(dim) for _ in range(seq)] for _ in range(kv_heads)]
        v = [[self.rand_vec(dim) for _ in range(seq)] for _ in range(kv_heads)]
        before = attention_causal(q, k, v, kv_heads)
        v[0][2] = [99.0] * dim
        after = attention_causal(q, k, v, kv_heads)
        for head in range(heads):
            self.assertEqual(before[head][0], after[head][0])
            self.assertEqual(before[head][1], after[head][1])

    def test_swiglu_matches_oracle(self):
        dim, hidden = 8, 16
        x = self.rand_vec(dim)
        gate = [[self.rng.uniform(-1, 1) for _ in range(dim)] for _ in range(hidden)]
        up = [[self.rng.uniform(-1, 1) for _ in range(dim)] for _ in range(hidden)]
        down = [[self.rng.uniform(-1, 1) for _ in range(hidden)] for _ in range(dim)]
        self.assertLess(max_diff(swiglu(x, gate, up, down), oracle_swiglu(x, gate, up, down)), 2e-4)

    def test_dequant_fp16_scale(self):
        row = bytes([3] * 32) + struct.pack("<H", 0x4000)  # binary16 2.0
        self.assertEqual(dequant_q8_0_row(row), [6.0] * 32)

    def test_dequant_fp32_scale(self):
        row = bytes([3] * 32) + struct.pack("<f", 0.5)
        self.assertEqual(dequant_q8_0_row(row, scales_fp16=False), [1.5] * 32)

    def test_dequant_rejects_partial_block(self):
        with self.assertRaises(ValueError):
            dequant_q8_0_row(bytes([1] * 10))


class ComparatorTests(unittest.TestCase):
    def test_identical_arrays(self):
        result = compare_arrays([1.0, 2.0, 3.0], [1.0, 2.0, 3.0])
        self.assertEqual(result["max_abs_diff"], 0.0)
        self.assertEqual(result["cosine_similarity"], 1.0)
        self.assertEqual(result["exact_matches"], 3)

    def test_different_arrays_are_detected(self):
        result = compare_arrays([1.0, 2.0], [1.0, 9.0])
        self.assertEqual(result["max_abs_diff"], 7.0)
        self.assertEqual(result["exact_matches"], 1)

    def test_token_sequence(self):
        result = compare_tokens([1, 2, 3], [1, 2, 3])
        self.assertTrue(result["exact_sequence"])
        self.assertFalse(compare_tokens([1, 2, 3], [1, 9, 3])["exact_sequence"])

    def test_length_mismatch_is_rejected(self):
        with self.assertRaises(ValueError):
            compare_arrays([1.0], [1.0, 2.0])


if __name__ == "__main__":
    unittest.main()
