# OD-38 local-model benchmark — final report (dev-host emulation)

**Date:** 25 November 2026  
**Status:** Benchmark complete. **Not** a deployment decision until repeated on the Contabo VPS 4 with `--target`.  
**Hardware:** Windows dev host, 16 GB RAM / 12 CPUs, emulating 4 vCPU / 8 GB via a Compose override. All numbers here are dev-box evidence.

## 1. Method — fixed conditions

Nothing in the comparison was changed between models:

- model tags: `qwen2.5-coder:3b` and `qwen2.5:3b` (same quantisation as pulled from Ollama);
- prompt, coding task, temperature 0 and `max_tokens` imported unchanged from `smoke_coding.py`;
- assertions: the original `normalise_path` test, unchanged;
- routing: all requests through LiteLLM (`local-qwen-coder-3b` / `local-qwen-3b`);
- resource profile: 4 vCPU / 8 GB enforced by cgroup, verified after container recreation.

Design: two cold rounds per model (Ollama restarted each time, order alternated), five valid warm trials per model (order alternated each round), `docker stats`/cgroup sampling every ~0.2 s, streaming TTFT captured for load-overhead estimation. One general-model warm trial was invalidated by an in-run model reload and was excluded; an extra valid warm trial was run so each model has **five valid warm trials**.

## 2. Constraint verification — CPU mystery resolved

| Check | Evidence |
|-------|----------|
| Effective cgroup quota | `/sys/fs/cgroup/cpu.max` = `400000 100000` → **4.0 cores** |
| Memory limit | `memory.max` = 8589934592 → **8 GiB** |
| Container runtime | `NanoCpus=4000000000`, `Memory=8589934592` |
| Compose after `--force-recreate` | `docker-compose.benchmark.yml` override preserves 4 CPU / 8 GB |
| Docker Desktop `docker stats` | reported 573% / 401% — **not** a cgroup quota breach |
| cgroup CPU accounting | peak 4.18–4.87 cores; avg ~4.0 cores; throttled periods 1322/1634 in final snapshot |
| Swap / OOM | swap peaked ~150 MB; `oom_kill=0` throughout |
| Host RAM | 15.79 GB total, **1.88 GB available** at end of run |
| Other containers | backend 182 MiB, LiteLLM 327 MiB, Postgres 56 MiB, Redis 13 MiB, MinIO 110 MiB |
| Resident models | both 3B models loaded → Ollama 4.40 GiB + 150 MB swap |

Conclusion: the >400% figures were a Docker Desktop display artefact. The cgroup enforces four cores and throttles ~80% of periods under load. The real constraint is **memory**, not CPU: a single 3B model peaks ~2.5–3.2 GB on cold load and ~4.7 GB when both models are resident, leaving host RAM nearly exhausted.

## 3. Results

### Cold start (2 rounds per model, order alternated)

| Model | Median total | Median TTFT | Correct | Peak RAM |
|-------|-------------:|------------:|---------:|---------:|
| `local-qwen-coder-3b` | 17,697 ms | 10,788 ms | 0/2 | 2,655–3,204 MB |
| `local-qwen-3b` | 16,345 ms | 9,222 ms | 0/2 | 2,714–2,991 MB |

Estimated model-loading overhead (cold TTFT − warm median TTFT): **~10,206 ms** (coder), **~8,837 ms** (general).

### Warm (5 valid trials per model, order alternated)

| Model | Min | Median | Max | Stdev | Peak RAM (median) | Avg CPU | Correct |
|-------|----:|-------:|----:|------:|------------------:|--------:|--------:|
| `local-qwen-coder-3b` | 6,818 ms | **6,979 ms** | 7,391 ms | 218 ms | 4,750 MB | 4.00 cores | 0/5 |
| `local-qwen-3b` | 7,276 ms | 7,485 ms | 7,684 ms | 155 ms | 4,711 MB | 4.01 cores | 0/5 |

Coder is ~7% faster warm; general is ~8% faster cold. Both saturate the four-core quota and swap ~150 MB. The general model's discarded warm trial showed `loaded_before=False`, TTFT 13,565 ms and 4,919 MB — an eviction/reload, not a genuine warm result.

### Third contender — `local-qwen3.5-4b` (`qwen3.5:4b`, 3.3 GB on disk)

Default thinking mode is **not viable** on this profile: with the unchanged 512-token budget it spent all tokens thinking, emitted no code, and took **314 s** (prompt 84 / completion 512 tokens). With `extra_body: {"think": false}` — the only changed condition; task, prompt, assertions, models and budget unchanged — it produces code.

Focused bracketed matrix (orders 16–31), think disabled; coder trials interleaved to detect drift:

| Measure | Value |
|---------|-------|
| Cold median (2 rounds) | 29,772 ms — ~1.7× slower than the coder |
| Warm, 5 valid trials | 16,323–22,256 ms, median ~18,200 ms — ~2.6× slower than the coder |
| Peak RAM (warm median) | ~5,440 MB — leaves far less headroom than the 3B models |
| Swap | up to 579 MB in this phase |
| Correctness | 0/7 on the original assertion; 12/16 on the expanded edge cases (same as coder) |
| Stability | one warm trial was an eviction/reload and was excluded |

The bracket coder trials also degraded (46 s outlier, 808 MB swap) because two models were resident; those contaminated trials are excluded from the scorecard. This is direct evidence for OD-39's one-resident-model rule.

### Feasibility probe at 6 vCPU / 12 GB (one resident model)

`docker update --cpus 6 --memory 12g --memory-swap 12g aura-ollama`, verified via cgroup (`600000 100000`, 12 GiB). Same task and assertions, one cold + one warm trial per model, no other model resident. Raw records: `results/probe_12gb.jsonl`.

| Model | Cold | Warm | Peak RAM | Swap | Peak CPU | Correct |
|-------|-----:|-----:|---------:|-----:|---------:|--------:|
| `local-qwen-coder-3b` | 10,499 ms | **4,476 ms** | 2,556 MB | 0 MB | 6.2 cores | 0/2 |
| `local-qwen-3b` | 12,932 ms | 4,616 ms | 3,373 MB | 0 MB | 6.3 cores | 0/2 |
| `local-qwen3.5-4b` (think off) | 20,209 ms | 9,911 ms | 4,608 MB | 0 MB | 6.3 cores | 0/2 |

All three **work** at 12 GB / 6 vCPU with zero swap. Warm latency improves ~35–45% versus 4 vCPU / 8 GB; peak RAM drops to 2.6–4.6 GB because only one model is resident. Correctness is unchanged — all still fail `a//b///c`, so extra hardware fixes speed and headroom, not reasoning. Limits were restored to 4 vCPU / 8 GB after the probe.

At 12 GB, `qwen2.5-coder:7b` (~4.7 GB weights, ~5.5–6 GB runtime) becomes a realistic local option with headroom; `qwen3.5:9b` local (~6.6 GB weights) is possible but tight with services and long context; `qwen3-coder:30b` (~19 GB) still does not fit.

### Concurrent requests (3 simultaneous, identical task)

| Model | Latencies | Median | Max | Correct | Peak RAM | Swap | OOM |
|-------|-----------|-------:|----:|--------:|---------:|-----:|----:|
| `local-qwen-coder-3b` | 7.1 / 21.2 / 13.9 s | 13.9 s | 21.2 s | 0/3 | 4,639 MB | 150 MB | 0 |
| `local-qwen-3b` | 7.5 / 14.9 / 23.1 s | 14.9 s | 23.1 s | 0/3 | 4,644 MB | 150 MB | 0 |

No crashes or OOM kills; requests queue and latency degrades roughly linearly. Neither model is suitable for concurrent development workloads on this profile.

## 4. Assertion diagnosis — reasoning vs specification

Expanded to 16 edge cases against the *unchanged* spec (collapse repeated `/`, strip outer `/`, `''` for None/empty). Expected outputs match the spec, so the test is **not** stricter than the requirement.

| Model | Failed cases | Observed behaviour |
|-------|-------------:|--------------------|
| `local-qwen-coder-3b` | 4/16 | `replace('//', '/')` — single pass; fails only on **3+** consecutive slashes |
| `local-qwen-3b` | 6/16 | `'/'.join(path.split('/'))` — keeps empty parts; fails on **all** repeats |
| `local-qwen3.5-4b` (think off) | 4/16 | same single-pass failure pattern as the coder, but ~2.6× slower |

All handle `None`/empty and outer stripping correctly. This is a **model coding error**, not a harness or specification error. The coder and the 4B model are materially better than the general 3B on this task, but neither is correct.

## 5. Deployment suitability scorecard

Weights: Critical = 3, High = 2; score 0–5. N/A criteria excluded; weighted average over measured criteria only (66.7% coverage).

| Criterion | Importance | `local-qwen-coder-3b` | `local-qwen-3b` | `local-qwen3.5-4b` |
|-----------|-----------|----------------------:|----------------:|-------------------:|
| Coding correctness | Critical | 3.75 (12/16) | 3.12 (10/16) | 3.75 (12/16) |
| Reasoning quality | Critical | N/A — no independent benchmark | N/A | N/A |
| RAM consumption | Critical | 3.00 (~4,750 MB) | 3.00 (~4,711 MB) | 2.00 (~5,440 MB) |
| CPU efficiency | High | 4.99 (4.00 cores) | 4.98 (4.01 cores) | 5.00 (4.00 cores) |
| Cold-start latency | High | 4.62 | 5.00 | 2.74 |
| Warm inference speed | High | 5.00 | 4.66 | 1.75 |
| Long-running stability | High | 4.00 (no eviction) | 3.00 (1 eviction) | 2.00 (1 eviction, swap) |
| ARM64 compatibility | High | N/A (AMD64 host only) | N/A | N/A |
| Tool calling | High | N/A (not tested) | N/A | N/A |
| **Weighted score (measured only)** | | **4.10** | **3.83** | **2.87** |

## 6. Recommendation (historical benchmark — superseded by owner direction)

**Owner direction, 25 November 2026 (OD-38 reopening):** only `qwen2.5:3b` is kept locally;
`qwen2.5-coder:3b` and `qwen3.5:4b` are removed from the local set. The benchmark below
remains valid historical evidence and is not rewritten; the owner knowingly accepted the
measured coding-quality trade-off in favour of a single-model footprint. Re-benchmark before
approving another local model.

**Original benchmark recommendation:** for IAM's initial local brain, prefer `local-qwen-coder-3b` — coding-first, as OD-38 then required. It wins on the only measured correctness evidence, is ~7% faster warm, and showed no eviction across five valid warm trials. Its disadvantages (slower cold start by ~1.35 s, ~40 MB more RAM) are minor by comparison.

`qwen3.5:4b` is **not** recommended as the local brain here: its edge-case correctness equals the coder's, but it is ~2.6× slower warm, uses ~700 MB more RAM and fails entirely in default thinking mode. It remains a candidate for a machine with more RAM/CPU or with thinking explicitly disabled.

This is a **relative** choice, not approval as primary brain: none of the three passes the original assertion, none handles concurrency well, and hosted contenders could not be tested (no API keys). Per OD-38 the hosted Qwen3.5-9B remains the general-reasoning anchor; the local coder is the private/low-resource baseline. OD-39 (one resident model, 6 GB ceiling, short keep-alive) and OD-40 (controlled model development) were confirmed on 25 November 2026 and now govern deployment and future improvement.

**Deployment caveats for the 8 GB VPS:**
- Run **one model at a time**; with three models available and two resident, swap reached ~579–809 MB and host RAM available fell to 0.69 GB — this is now a locked OD-39 rule.
- Apply `docker-compose.ram-profile.yml` (6 GB hard cap, one resident model, one parallel request, 2-minute keep-alive) and leave headroom for Postgres, Redis, backend and LiteLLM.
- The benchmark override does not bound `memory.swap` (default 16 GB) — set it explicitly if swap must be constrained.
- Final decision must repeat this suite on the Contabo VPS with `python tests/model_competition/hardware_evidence.py --target` and the full benchmark there.

## 7. Evidence files

- `full_benchmark.py`, `run_constrained.py`, `smoke_coding.py`, `concurrent_check.py`, `diagnose_assertion.py`, `provider_readiness.py`, `hardware_evidence.py`, `final_report.py`, `benchmark_qwen35.py`, `probe_think.py`
- `results/constrained_results.jsonl` — every trial (including the excluded reload)
- `results/benchmark_summary.json`, `results/final_report.json`
- `results/assertion_diagnosis.json`, `results/concurrent_results.jsonl`
- `results/provider_readiness.json`, `results/hardware_KOJOPAPO.json`
- `../docker-compose.benchmark.yml` — benchmark-only 4 vCPU / 8 GB override
- `../docker-compose.ram-profile.yml` — OD-39 production RAM profile (6 GB cap, one model, short keep-alive)

## 8. Warm throughput baseline for the OD-46 primary (28 November 2026)

Scope: **warm-only, no container restart**, five trials of `local-qwen-3b` through `full_benchmark.py`. This is a baseline for future engine comparison, not a repeat of the historical three-model competition in §§2–5.

Conditions: `aura-ollama` at the Compose default **2 vCPU / 4 GB** (not the 4 vCPU / 8 GB `docker-compose.benchmark.yml` override); one resident model confirmed before and after every trial; no OOM kills. `usage` token counts were captured by sending `stream_options: {"include_usage": true}` through LiteLLM — without that flag the SSE stream carries no usage object.

| Metric (5 trials) | Median | Min | Max | Std dev |
|---|---:|---:|---:|---:|
| Time to first token | 3,967.1 ms | 3,392.1 ms | 4,255.5 ms | 359.9 ms |
| Total latency | 25,076.7 ms | 21,879.6 ms | 26,672.8 ms | 2,100.0 ms |
| Prompt tokens | 98 | 98 | 98 | 0.0 |
| Completion tokens | 45 | 45 | 45 | 0.0 |
| Decode throughput | 2.1 tok/s | 2.0 tok/s | 2.5 tok/s | 0.2 |
| Observed prefill rate | 24.7 tok/s | 23.0 tok/s | 28.9 tok/s | 2.4 |
| Peak container RAM | 2,991.4 MB | 2,753.8 MB | 3,044.5 MB | 120.6 MB |
| Peak CPU cores | 2.3 | 2.2 | 2.4 | 0.0 |

Correctness guard: **0/5** passed the unchanged `normalise_path` assertion. This matches the known model coding error documented in §4 and is not a regression.

Interpretation limits: decode throughput is measured on a 2 vCPU / 4 GB container, so it is **not comparable** with the §§2–5 figures (4 vCPU / 8 GB) or with upstream EPYC 7642 assembly-engine claims. "Observed prefill rate" divides prompt tokens by TTFT, which includes gateway, queueing and network time; use it only for relative comparison. Cold-start performance was **not** measured — the cold phase deliberately restarts `aura-ollama` and was not authorised.

Evidence: `results/warm_baseline_2026-11-28.json` (summary and container limits) and the five appended records in `results/constrained_results.jsonl`.

## 9. Cold baseline for the OD-46 primary (28 November 2026)

Scope: two cold trials of `local-qwen-3b`, with `aura-ollama` restarted before each trial by `full_benchmark.restart_ollama()`. Conditions match §8 (Compose default 2 vCPU / 4 GB, same prompt, same `usage` capture). The container was confirmed healthy after the run. Model was absent before each trial and present after each; no OOM kills.

| Metric (2 trials) | Median | Min | Max |
|---|---:|---:|---:|
| Time to first token | 20,530.3 ms | 18,056.4 ms | 23,004.3 ms |
| Total latency | 36,635.9 ms | 34,548.4 ms | 38,723.5 ms |
| Prompt tokens | 98 | 98 | 98 |
| Completion tokens | 39 | 39 | 39 |
| Decode throughput | 2.5 tok/s | 2.4 tok/s | 2.5 tok/s |
| Observed prefill rate | 4.8 tok/s | 4.3 tok/s | 5.4 tok/s |
| Peak container RAM | 3,128.1 MB | 2,887.8 MB | 3,368.3 MB |
| Peak CPU cores | 2.2 | 2.2 | 2.3 |

Cold TTFT is ~16.6 s above the §8 warm median, which includes container restart plus model load. Only two cold trials were run (the harness's standard cold-round count), so variability is wider than the five-trial warm baseline. Correctness guard remains 0/5-equivalent (0/2 here), consistent with §4. Same comparability limits as §8: not comparable with the historical 4 vCPU / 8 GB results or upstream EPYC claims; observed prefill includes gateway, queueing and network time.

Evidence: `results/cold_baseline_2026-11-28.json` and the two appended cold records in `results/constrained_results.jsonl`. Together §8 and §9 complete the baseline for the current Ollama Qwen2.5-3B primary; future engine candidates should be measured against these figures under the same container limits.
