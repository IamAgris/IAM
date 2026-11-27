"""IEEE-754 binary32 rounding helpers for the parity harness.

Pure standard library. Every reference operation rounds after each arithmetic
step so the result is a strict FP32 evaluation, not Python's native float64.
"""

from __future__ import annotations

import struct

_F32 = struct.Struct("<f")
_F16 = struct.Struct("<e")


def f32(value: float) -> float:
    """Round a Python float to the nearest representable binary32 value."""
    return _F32.unpack(_F32.pack(float(value)))[0]


def f32_sum(values) -> float:
    """Sum in FP32, one addition at a time (no compiled FMA, no double accumulation)."""
    total = f32(0.0)
    for value in values:
        total = f32(total + f32(value))
    return total


def f32_dot(a, b) -> float:
    """Dot product in FP32, one multiplication and addition at a time."""
    if len(a) != len(b):
        raise ValueError("dot product requires equal-length vectors")
    return f32_sum(f32(x * y) for x, y in zip(a, b))


def fp16_to_f32(bits: int) -> float:
    """Decode a raw IEEE-754 binary16 bit pattern to binary32."""
    return f32(_F16.unpack(struct.pack("<H", int(bits) & 0xFFFF))[0])
