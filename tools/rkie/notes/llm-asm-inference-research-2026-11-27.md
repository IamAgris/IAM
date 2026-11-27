# `llm.asm` as an IAM inference-engine reference (27 November 2026)

Untrusted historical context. Re-verify against the current tree before relying on it.

- **Question:** What can IAM reuse from `alesha-pro/llm.asm`, what needs rewriting, and what must IAM develop independently?
- **Search modes / queries used:** upstream GitHub API tree + pinned raw files; local `grep` for `llm.asm`, `AVX2`, `inference engine`; `tools/rkie/notes/`. No GitHub code search (see AGENTS.md §2).
- **Authoritative spec and decisions:** OD-38 / OD-46 (local primary `qwen2.5:3b` via Ollama, LiteLLM gateway, replaceability + creator approval), OD-41 (research requirements frozen, no new subsystems), OD-11 (core source is protected), OD-36 (free SDK/framework research in isolated environments). `AGENTS.md` §1: architecture frozen at feature level; report gaps, do not silently change source-of-truth docs.
- **Verified against:** upstream `alesha-pro/llm.asm` commit `48feccbfd57cb669440f31ff64958d95bb8b848e` (files listed below) and IAM working tree at `4025c5c` plus uncommitted user work. Upstream HEAD `e7d4883` (27 Nov) added a fourth project, `04-ring1-kernel-surgeon`, after the inspected commit — re-check before reuse. No files outside `tools/rkie/notes/` were changed.

## What upstream actually contains (pinned commit)

Three pure-x86-64 NASM projects, MIT licensed, zero libc/runtime:

| Directory | Content |
|---|---|
| `01-qwen3-inference/` | Qwen3-0.6B Q8_0 static Linux ELF, AVX2/FMA/F16C, built-in Fibonacci-hashed BPE tokenizer, GQA + QK-Norm + split-half NeoX RoPE + SwiGLU, `clone()`/`futex()` pool, multi-turn KV-cache chat |
| `02-baremetal-os/` | Multiboot bare-metal OS booting the same model; VGA/PS2/COM1, ACPI/APIC SMP |
| `03-minigpt-train/` | From-scratch FP32 Mini-GPT trainer, analytical backward pass, AdamW, per-tensor grad-check, Braille TUI |

Verified source anchors: `shared/constants.inc` (`HDR_FLAG_QK_NORM`, FP16 block scales), `shared/transformer.asm` (unconditional QK-Norm step 3c and split-half RoPE step 3d), `scripts/export_weights.py` (requires `cfg["head_dim"]` and `self_attn.q_norm`/`k_norm`), `shared/tokenizer.asm` (Qwen3 chat-template token IDs), `scripts/{test_math,verify_ref,verify_train_ref,verify_os}.py`.

Speed claims are self-reported on one AMD EPYC 7642 host, 34 prompt / 64 generated tokens, decode only. The Phase 1 README explicitly notes prefill is token-by-token GEMV (26.7–160.8 tok/s) versus batched GEMM in `llama.cpp` `pp34` (56–1113 tok/s). It is Linux x86-64 only, requires AVX2+FMA+F16C, has no GPU backend, no batching/cancellation/streaming API.

## Reuse / rewrite / build

- **Reusable as method, not code:** independent parity harnesses (kernel tolerance tests, logits + 64-token greedy comparison vs PyTorch FP32, bit-exact determinism 1–40 threads); per-row split Q8_0 with FP16 block scales and 64-byte-aligned mmap layout; contiguous head-major KV cache; spin/futex thread pool with deterministic partitioning; SIMD exp/sincos/RMSNorm/RoPE/SiLU/softmax/top-p; analytical backward + grad-check discipline.
- **Needs rewrite:** every model-specific path. Qwen3-0.6B is 28 layers / dim 1024 / intermediate 3072 / 16Q-8KV / QK-Norm / `head_dim` in config; Qwen2.5-3B is 36 layers / dim 2048 / intermediate 11008 / 16Q-**2KV** / **no QK-Norm** / no `head_dim` key. Shared: vocab 151936, tied embeddings, head_dim 128, `rope_theta=1e6`. Also needs a new Qwen2.5 tokenizer/template and GGUF (the format Ollama actually loads).
- **Build independently:** model loader/converter, GPU backend, ARM64/AVX-512 portability, continuous batching, cancellation, hot-swap with signed rollback, and a real 3B fine-tuning pipeline.

Rough Q8 footprint for 3B: ~3.3–3.5 GiB weights plus ~300 MB KV at 4096 context. Current Ollama container limit is 4 GB (`docker-compose.yml:119-125`) and IRWM ceiling 6000 MB (`backend/app/services/irwm.py`); measured peak in `tests/model_competition/RESULTS.md` is ~4.7 GB. Measure, do not assume.

## IAM integration surface (source truth)

- `backend/app/services/model_inference.py`: `resolve()` L433-485, `chat()` L487-563, `stream()` L756-892. Hosted → LiteLLM L637-643; local → Ollama `/v1/chat/completions` L644-646.
- `backend/app/api/routes/models.py`: `/chat` L261-315, `/chat/stream` L318-406, `/readiness` L232-235; SSE `start`/`delta`/`done`/`error`.
- Gates on every call: Aegis input inspection, IRWM admission/lease, model policy, credential vault, usage accounting.
- Release control: `backend/app/services/serving_model.py` `current()`/`activate()`/`rollback()` feeds `resolve()` at L435.
- No GGUF/Safetensors loader, tokenizer, KV cache or quantization code in `backend/`; quantization is metadata only (`backend/app/services/ai_research/training.py:40`). Ollama performs all local execution.
- Ollama is also used for `/api/embed` (`memory_service.py:425-450`) and `/api/generate` (`ai_research/lm_eval.py`), so a replacement engine must supply those endpoints or be configured separately.
- Benchmark harness already exists: `tests/model_competition/full_benchmark.py`, `concurrent_check.py`, `run_constrained.py`, `RESULTS.md`. Extend it; do not create a second framework.

## Known gaps / open questions

- A native engine is a new subsystem and a protected-core change: not implementable as production without owner decision under OD-11/OD-41/OD-46. Permissible as isolated research under OD-36/OD-41.
- The newly added `04-ring1-kernel-surgeon` (upstream HEAD, not inspected here) is a Ring -1 SVM hypervisor that writes patches into a running Linux kernel. It is an explicit **do-not-adopt** example for IAM: host/hypervisor control, kernel memory patching and live code modification are outside any IAM boundary.
- Baseline metrics (TTFT, decode tok/s, prefill tok/s, peak RAM, concurrency) have not been collected for the current Ollama Qwen2.5-3B primary in a form usable for engine comparison. See `llm-asm-benchmark-extension-plan.md`.
