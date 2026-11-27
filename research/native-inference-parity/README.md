# Native inference parity harness (research only)

Isolated, zero-dependency harness for checking future low-level inference kernels against
an independent numerical reference. It is **not** a model runtime and is not imported by
`backend/` or `frontend/`.

## Why it exists

Before any assembly/SIMD/quantisation optimisation is considered for IAM's Qwen2.5-3B
inference, there must be a stable answer to "does the optimisation preserve the maths?".
This directory provides that reference and a common comparison interface.

## Files

| File | Role |
|---|---|
| `f32.py` | IEEE-754 binary32 rounding helpers; rounds after each arithmetic step |
| `reference_ops.py` | Strict FP32 reference: RMSNorm, split-half RoPE, causal GQA attention, SwiGLU, per-row Q8_0 dequantisation |
| `oracle_ops.py` | Independent double-precision implementations with different formulas; used only to validate the reference |
| `compare.py` | Generic array/token comparator and CLI for candidate-engine outputs |
| `test_parity.py` | Self-validation: reference vs oracle, analytic cases, comparator behaviour |

## Run

```powershell
python -m pytest research/native-inference-parity/test_parity.py -q
python -m ruff check research/native-inference-parity
```

Both commands currently pass (14 tests). No NumPy, PyTorch or model weights are needed.

## Using it with a candidate engine

1. Dump the candidate kernel's outputs as a JSON array of numbers (flat or nested).
2. Produce the same array from `reference_ops.py` using identical inputs.
3. Compare:

```powershell
python research/native-inference-parity/compare.py reference.json candidate.json
python research/native-inference-parity/compare.py ref_tokens.json candidate_tokens.json --tokens
```

`compare.py` reports max/mean absolute difference, cosine similarity and exact-match count.
Defaults: `--abs-tol 1e-5`, `--cos-min 0.9999`; adjust per operation after observing the
reference's own FP32 rounding behaviour.

## Scope and limits

- Shapes are small and synthetic (e.g. head_dim 32, 4 heads / 2 KV heads, seq 3). They
  exercise Qwen2.5 arithmetic patterns, not real Qwen2.5-3B weights or a full layer stack.
- Strict per-operation FP32 rounding is intentionally harsher than hardware kernels that
  fuse multiply-add. Small differences are expected; the comparator is for relative
  regression detection, not for declaring bit-exactness.
- RoPE follows the Qwen2.5/HF split-half (`rotate_half`) convention. It does not cover
  Qwen3 QK-Norm or multimodal rotary variants.
- Faiss/GGUF/Safetensors parsing, GPU execution and tokenisation are out of scope.
- Nothing here is evidence that a faster engine is correct until a candidate is actually
  run through this harness and the results are recorded.
