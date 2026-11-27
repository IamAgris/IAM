# Native inference parity harness (28 November 2026)

- **Question:** Where is the independent numerical reference for future Qwen2.5 inference-kernel work?
- **Search modes / queries used:** local `grep` for `parity|gradcheck|rmsnorm|rotate_half` in `*.py`; glob of `research/**`. No existing parity harness found.
- **Authoritative spec and decisions:** OD-41 (research requirements frozen; no new subsystems), OD-36 (isolated research/benchmark permitted), OD-11 (protected core — nothing here touches it).
- **Key files (path):** `research/native-inference-parity/{f32,reference_ops,oracle_ops,compare,test_parity}.py`, `README.md`. Isolated research only; no imports from `backend/` or `frontend/`.
- **Dependencies and call sites:** none. Pure standard library because NumPy is not installed on this host. Candidate engines call `compare.py` with JSON dumps.
- **Known gaps / open questions:** synthetic small shapes only; no real Qwen2.5-3B weights, no full layer stack, no GPU, no tokeniser. Strict FP32 rounding is harsher than fused hardware kernels, so tolerances must be chosen per operation. Not evidence of correctness until a candidate is actually compared.
- **Verified against:** working tree `4025c5c` plus uncommitted user work on 28 November 2026. `python -m pytest research/native-inference-parity/test_parity.py -q` → 14 passed; `python -m ruff check research/native-inference-parity` → clean; `compare.py` CLI smoke → PASS on identical arrays. Re-verify before reuse.
