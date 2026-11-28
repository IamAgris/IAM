# IAM free-GPU research notebook

**Notebook:** `IAM_vLLM_Qwen_Coder_3B.ipynb`  
**Purpose:** WP9 / acceptance A8 — vLLM serving experiment using a temporary free GPU. The notebook historically serves `Qwen2.5-Coder-3B-Instruct`; the current shared primary under OD-46 is `qwen2.5:3b`.  
**Decision: OD-41** — free platforms are temporary research workers, not IAM's permanent home.

## Readiness observed on this machine (25 November 2026)

- No `COLAB_TOKEN`, `KAGGLE_API_TOKEN`, `HF_TOKEN`, `LIGHTNING_API_KEY`, `GOOGLE_API_KEY`, `NVIDIA_API_KEY` or `DASHSCOPE_API_KEY` is configured.
- `vllm`, `torch`, `transformers` and `lm_eval` are not installed locally.
- Local GPU: NVIDIA GeForce GTX 1660 Ti, 6 GB, Turing compute capability 7.5 — vLLM-capable in principle, but vLLM is Linux/CUDA and this host only has Python 3.15 on Windows. So no local serving run was attempted.

## How to use the notebook

1. Open it in Google Colab with a GPU runtime (T4 or newer). Check the first cell: it asserts compute capability >= 7.5.
2. Run cells in order. The vLLM server is started in the background and shut down in the final cell.
3. The coding task, prompt and assertions are copied unchanged from `tests/model_competition/smoke_coding.py` so results are comparable with the local Ollama benchmark.
4. The report records min/median/max latency, peak VRAM and token usage. It is **untrusted external output** until IAM Core validates it.
5. Set `IAM_S3_ENDPOINT`, `IAM_S3_BUCKET`, `IAM_S3_ACCESS_KEY`, `IAM_S3_SECRET_KEY` and `IAM_EXPERIMENT_ID` as Colab secrets/environment variables to upload the report. Never put credentials in the notebook itself.

## Important rules

- Do not enable paid compute or Colab Pro upgrades.
- Do not store IAM identity, private memory or protected-core data in the notebook.
- Kaggle's P100 (compute capability 6.0) is **not** suitable for vLLM — it is training/benchmark only.
- Free sessions expire; save artifacts to IAM-controlled storage before the session ends.

## How results feed IAM

The uploaded JSON has the same shape consumed by `ServingReport` in `backend/app/services/ai_research/serving.py`. Feed it into `BenchmarkRunner` / `CapabilityRegistry` to create a measured capability profile, then into `ModelRegistry` for approval and rollback. No model is promoted on serving speed alone — coding correctness and quality gates still apply.

## Status

Notebook authored; **not executed** (no free-platform credentials available). This is prepared infrastructure, not a completed vLLM benchmark.
