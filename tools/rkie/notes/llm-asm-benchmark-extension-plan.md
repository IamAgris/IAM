# Benchmark baseline plan — local inference metrics (27 November 2026)

Untrusted historical context. Re-verify against the current tree before relying on it.

- **Question:** How do we measure the current Ollama Qwen2.5-3B primary so a future engine can be compared fairly?
- **Authoritative context:** OD-38 / OD-46 make `qwen2.5:3b` the local primary via Ollama; OD-41 freezes requirements; benchmark results already recorded in `tests/model_competition/RESULTS.md`.
- **Verified against:** IAM working tree `4025c5c` plus uncommitted user work. No code has been changed.
- **Scope:** test-only. Do not modify `backend/`, `infra/`, model selection, or any source-of-truth document.

## What the existing harness already measures

| Source | Present | Missing |
|---|---|---|
| `tests/model_competition/full_benchmark.py` | `ttft_ms`, `latency_ms`, raw `usage`, cgroup CPU/swap/OOM via `Sampler`, cold/warm alternation, 5 warm trials | decode tok/s, prefill tok/s, explicit prompt/completion token counts, prompt-length control |
| `tests/model_competition/concurrent_check.py` | 3 simultaneous requests, per-request latency/TTFT, peak memory, throttling | same throughput metrics under concurrency |
| `tests/model_competition/run_constrained.py` | `docker stats` peak RAM, tokens | separation of prompt vs generation cost |
| `tests/model_competition/RESULTS.md` | warm medians ~6.98 s / 7.49 s, cold TTFT, ~4.7 GB peak, concurrency ~14.9 s, scorecard | comparable cross-engine figures |

`full_benchmark.call_stream()` (L155-204) records TTFT at the first non-empty `delta.content` and latency at `[DONE]`. `usage` is captured only if a streamed chunk supplies it.

## Metric definitions to add (test-only)

- `prompt_tokens` / `completion_tokens`: from `usage` when available; otherwise `null` — never estimated into a headline number.
- `decode_tps = completion_tokens / ((latency_ms - ttft_ms) / 1000)`.
- `prefill_tps_observed = prompt_tokens / (ttft_ms / 1000)`. Label as **observed**, not pure prefill: TTFT includes gateway, queueing and network. Keep it for relative comparison only, never as a claims-grade figure.
- `ttft_ms`: unchanged, first non-empty delta.
- `peak_mem_mb`, `swap`, `throttling`, `oom_kill`: keep `Sampler` values.
- Correctness: keep `extract_code()` / `run_candidate()` pass flag as an accuracy guard; record it alongside throughput so a "faster" engine cannot win by producing wrong output.
- Concurrency: reuse `concurrent_check.py` with the same added fields; report median and max latency plus per-request throughput.

## Implementation order

1. Verify that streamed responses from LiteLLM → Ollama actually populate `usage.prompt_tokens` / `usage.completion_tokens` (one short manual stream, no code change). If absent, make all token-derived metrics optional and record the gap explicitly.
2. Add a small pure helper in `tests/model_competition/` that turns `call_stream()` output into the fields above. Keep it dependency-free and unit-testable.
3. Extend `run_trial()` records and `summarise()` in `full_benchmark.py` with the new fields and min/median/max/stdev, without removing existing fields or altering `RESULTS.md`.
4. Extend `concurrent_check.py` records with the same fields.
5. Collect a baseline for `local-qwen-3b` only, under `docker-compose.benchmark.yml` (4 vCPU / 8 GB), cold plus 5 warm trials, order alternated as the harness already does. Write to the existing `results/` JSONL files.
6. Record the baseline in a new subsection of `tests/model_competition/RESULTS.md` (append only), stating commit, hardware, container limits and any missing `usage` data.

## Constraints

- No production code, no model switch, no Ollama replacement.
- No new benchmark framework: extend the existing scripts.
- No public performance claim from single runs; use median across the existing five warm trials and report variability.
- No private repository content or secrets may be sent externally.

## Open questions

- Does `usage` survive SSE through LiteLLM for the Ollama backend, and does Ollama count prompt tokens for a 512-token `max_tokens` coding task consistently? **Resolved for `local-qwen-3b`: only when `stream_options.include_usage` is sent** (see implementation status). Consistency for the full 512-token coding task is still unmeasured.
- Should the benchmark add a short fixed prompt (e.g. 32 tokens) alongside `TASK` to separate prefill cost from the long coding prompt? Decide only after step 1.
- What is the exact hardware profile this baseline must be repeated on to be comparable with the upstream EPYC 7642 numbers? Not established.

## Implementation status (28 November 2026)

All six steps are implemented. Step 5 produced both a warm-only baseline and a cold baseline after explicit go-ahead for the `aura-ollama` restart; step 6 (`RESULTS.md` append) is complete.

| Step | Status | Evidence |
|---|---|---|
| 1 — verify `usage` survives LiteLLM SSE | **Verified** | First probe used an 8 s timeout and timed out; that was a probe error, not an unreachable stack — `docker ps` shows `aura-litellm`, `aura-ollama` and `aura-backend` healthy and port 4000 listening. With a longer timeout the stream succeeded but carried `usage_chunks=0`. Adding `stream_options: {"include_usage": true}` produced `{"prompt_tokens": 35, "completion_tokens": 8, ...}`. `full_benchmark.call_stream()` now sends that flag; token-derived metrics remain optional so other backends cannot produce fabricated numbers. |
| 2 — pure metrics helper | Done | `tests/model_competition/metrics.py` (`derive_metrics`) + `tests/model_competition/test_metrics.py` (6 unittest cases) |
| 3 — extend `full_benchmark.py` | Done | records carry the four derived fields; `summarise()` adds min/median/max/stdev for each in cold and warm sections |
| 4 — extend `concurrent_check.py` | Done | per-request derived fields plus median decode/prefill arrays |
| 5 — collect baseline | Done | 5 warm trials (no restart) + 2 cold trials (restart before each), Compose default 2 vCPU / 4 GB. `results/warm_baseline_2026-11-28.json`, `results/cold_baseline_2026-11-28.json` and appended `results/constrained_results.jsonl`. Warm median TTFT 3,967.1 ms / decode 2.1 tok/s / peak RAM 2,991.4 MB; cold median TTFT 20,530.3 ms / decode 2.5 tok/s / peak RAM 3,128.1 MB; cold load overhead ~16.6 s. 0/5 and 0/2 correct (known §4 coding error). |
| 6 — append to `RESULTS.md` | Done | New §8 (warm) and §9 (cold) sections, with conditions, limits and interpretation caveats |

Verification: `python -m pytest tests/model_competition/test_metrics.py -q` → 6 passed; `python -m py_compile` on all four files → clean. `python -m ruff check` on the four files → **all checks passed**. The four pre-existing findings in `full_benchmark.py` (`F401` unused `sys`, `PLW1510`, `S110`, `BLE001`) were also fixed: removed the unused import, set `check=False` explicitly, narrowed the cgroup sampler exception to `(OSError, ValueError, RuntimeError, subprocess.SubprocessError)` and logged at debug level instead of `pass`.

End-to-end smoke (not a baseline): one warm `call_stream('local-qwen-3b')` with the new flag returned `ttft_ms=33746.4`, `latency_ms=47358.0` and derived `{'prompt_tokens': 98, 'completion_tokens': 40, 'decode_tps': 2.9, 'prefill_tps_observed': 2.9}`. Single run, unconstrained container profile, model load likely included — do not treat these numbers as a benchmark result.

Cold phase completed after explicit go-ahead; `aura-ollama` was restarted before each of two trials and confirmed healthy afterward. Neither warm nor cold figures are comparable with the historical 4 vCPU / 8 GB results or with upstream EPYC 7642 claims — all future engine candidates must be measured under the same 2 vCPU / 4 GB Compose default to be comparable with §§8–9.
