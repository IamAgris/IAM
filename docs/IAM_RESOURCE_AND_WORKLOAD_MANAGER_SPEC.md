# IAM — Intelligent Resource and Workload Manager (IRWM)

**Status:** CONFIRMED — owner decision OD-39, 25 November 2026 (part of the frozen baseline)  
**Type:** Core capability inside existing system 13 (Infrastructure and Operational Resilience), system 2 (Intelligence and Reasoning) and OD-37 (traffic/workload distribution)  
**Related:** `IAM_FOUNDATION_MODEL_AND_INTELLIGENCE_SPEC.md` (Doc 23 / OD-38), `IAM_INFRASTRUCTURE_TRAFFIC_AND_DISTRIBUTED_PROCESSING_SPEC.md` (Doc 21 / OD-37), `IAM_DYNAMIC_NODE_NETWORK_SPEC.md` (OD-26), `docker-compose.ram-profile.yml`

---

## 1. Purpose

Let IAM use stronger models without exhausting the server's memory, especially on the 4 vCPU / 8 GB Contabo core. The manager controls how much memory each AI model and service may consume, chooses where work runs, and protects essential services.

**Permanent rule:** IAM must never sacrifice its core services just to keep a large AI model running.

## 2. Starting limits for the 8 GB core

| Setting | Starting value |
|---------|----------------|
| Maximum resident models | 1 |
| Parallel model requests | 1 |
| Loaded-model RAM target | 5–5.5 GB (hard container ceiling 6 GB) |
| Model keep-alive | 1–2 minutes |
| Context window | 4,096 tokens initially |
| Concurrent generations | 1 |

A hard container memory limit is a ceiling, not a guarantee the model fits comfortably. Reaching it can fail or kill the container — hence the softer 5–5.5 GB target and one-model residency.

Applied via `docker-compose.ram-profile.yml`:

```yaml
services:
  ollama:
    mem_limit: 6g
    cpus: 4
    environment:
      OLLAMA_MAX_LOADED_MODELS: "1"
      OLLAMA_NUM_PARALLEL: "1"
      OLLAMA_KEEP_ALIVE: "2m"
```

Context size is a per-request inference option (`num_ctx=4096`), not a daemon setting.

## 3. Model selection by task

| Task | Strategy |
|------|----------|
| Simple text processing | Small local model |
| Basic coding | 3B local model |
| Complex coding | 7B local model |
| Difficult reasoning | Hosted specialist, if authorised |
| Research | Local model coordinating research agents |
| Embeddings | Small dedicated embedding model |

IAM unloads a model when its work ends and loads another only when needed.

## 4. Manager loop

1. **Monitor** — available RAM, CPU, swap, GPU memory, model residency and usage.
2. **Evaluate** — does the requested model fit alongside essential services?
3. **Allocate** — choose model, context size and concurrency limit; queue if necessary.
4. **Optimise** — unload idle models, reduce context, queue work or delegate to another node.

## 5. Node distribution

- Primary intelligence and essential memory services stay on the core server.
- Specialist models run on trusted nodes where hardware permits.
- Tasks go to nodes with available RAM and suitable processors.
- Hosted models only when authorised.
- RAM on different machines is **never** treated as one pool; only separate model instances/workloads are distributed.

## 6. Initial 8 GB allocation target (planning budget)

| Component | RAM budget |
|-----------|-----------:|
| Ubuntu and system services | 1 GB |
| PostgreSQL | 1 GB |
| Redis and backend services | 1 GB |
| Ollama model | 4 GB initially |
| Headroom | 1 GB |

This is a planning target, not a guaranteed fit. If a 7B model exceeds its allocation, IAM falls back to the 3B model or another node rather than destabilising the server.

## 7. Capabilities to implement

1. RAM monitoring and prediction.
2. Per-model memory limits.
3. Dynamic model loading and unloading.
4. Context-window management.
5. Request queues and concurrency control.
6. CPU/GPU resource scheduling.
7. Distributed node workload allocation.
8. Automatic low-memory protection.
9. Model eviction and recovery.
10. Resource usage history and optimisation.

## 8. Implementation hooks in the current codebase

- `backend/app/core/config.py` — new settings for RAM ceilings, keep-alive, context size, max concurrent generations.
- `backend/app/services/intel_router_service.py` — allocation decisions before routing.
- `backend/app/models/modelrouter.py` / `modelindependence.py` — resource metadata on provider/model records.
- `infra/litellm/config.yaml` — model aliases; per-request `num_ctx` and concurrency.
- `docker-compose.yml` + `docker-compose.ram-profile.yml` — hard limits and daemon settings.
- `tests/model_competition/hardware_evidence.py`, `run_constrained.py` — measurement and verification harness.

## 9. Measurement already collected

Dev-host evidence under a 4 vCPU / 8 GB cgroup showed a single 3B model peaking ~2.5–3.2 GB cold and ~4.7 GB when two models were resident, ~150 MB swap, 1.88 GB host RAM available, and zero OOM kills. This supports one-model residency and a short keep-alive as the starting policy. Final tuning must be repeated on the Contabo VPS.
