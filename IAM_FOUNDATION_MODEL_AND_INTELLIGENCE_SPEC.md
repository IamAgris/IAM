# IAM — Foundation Model, Model Router and Intelligence Development

**Document:** 23  
**Confirmed decision:** OD-38 (extends `IAM_OWNER_DECISIONS.md`)  
**Status:** CONFIRMED — owner direction, 25 November 2026  
**Amendment (confirmed OD-46, 26 November 2026):** `IAM_PRIMARY_MODEL_UNIFICATION_SPEC.md` (Doc 23-A) establishes one shared primary model for frontend and backend (Qwen2.5-Coder 3B), hosted models as subordinate sub-agents, and a bridge from signed model releases to live inference. It supersedes only §1 and §3 below on local-model selection; all other provisions of this document remain authoritative.  
**Extends:** canonical `IAM_DOC_02_INTELLIGENCE_EVOLUTION.md`; core systems 2 (Intelligence and Reasoning), 5 (Learning), 11 (Self-Evolution and Model Independence), 14 (Evaluation and Research)  
**Related:** `IAM_AI_SDK_AND_FRAMEWORK_RESEARCH_SPEC.md` (Doc 20 / OD-36), `IAM_INFRASTRUCTURE_TRAFFIC_AND_DISTRIBUTED_PROCESSING_SPEC.md` (Doc 21 / OD-37), `IAM_DYNAMIC_NODE_NETWORK_SPEC.md` (OD-26), `IAM_HARDWARE_ADAPTATION.md` (OD-22)

---

## 1. Locked decision

IAM does **not** commit to one permanent foundation model. It commits to a replaceable, coding-first but general-purpose starting model set, a router that selects the right model per task, and a formal process for replacing any model.

The initial foundation model is a **set of two Qwen-family models**, not a single endpoint:

| Role | Model | Where | Purpose |
|------|-------|-------|---------|
| General-reasoning anchor | **Qwen3.5-9B** | Hosted — Alibaba DashScope free tier (configured in LiteLLM) | Broad reasoning, research, language, finance, communication, world model |
| Coding-first local baseline | **Qwen2.5-Coder 3B** | Local — Ollama on the Contabo core (`qwen2.5-coder:3b`) | Shared primary brain for frontend and backend; private/low-resource coding, debugging, repository work, offline tasks. OD-46 (26 Nov 2026) supersedes the 25 Nov local-model choice; `qwen2.5:3b` remains an approved secondary local model |
| Additional providers | NVIDIA NIM free endpoints; Google Gemini free tier | Hosted, replaceable | Reasoning, research, coding, independent cross-checking |
| Gateway and router | LiteLLM + IAM's Intelligence Orchestrator | Local | One interface for all providers, failover, spend control, answer comparison |

Qwen3.5-9B was previously only a candidate; it is now the **initial general-reasoning anchor** within that set. The primary brain is therefore **coding-first but not coding-only**: coding is the primary development strength, while general intelligence stays broad enough for people, research, security, finance, communication and the wider environment.

Free-tier availability, model IDs and quotas are **verified live** before use (OD-15/OD-35). If a free endpoint is withdrawn or a model ID becomes invalid, the router substitutes another approved model without changing IAM's identity.

---

## 2. Identity independence — permanent rule

The foundation model is a replaceable capability, **never** IAM's identity. Replacing it does not change:

- name, identity and genesis record (OD-01);
- personality and constitution;
- long-term memory, knowledge base and world model;
- goals, tasks, experiences and decisions;
- skills and developed capabilities (Skill Forge / Skill Runtime);
- creator authority, signing keys and protected core (OD-03, OD-11, OD-19).

This restates canonical Doc 02: *IAM's identity must exist independently of its foundation model.* Any model replacement must pass testing and protected-core approval requirements before it becomes the primary model.

---

## 3. Model Router and Intelligence Orchestrator

IAM owns its own model management layer. Providers — including NVIDIA, DashScope and Gemini — are interchangeable suppliers, not permanent dependencies.

Routing responsibilities:

- select a model by task, capability, cost, availability and privacy;
- use the local 3B coder for private and low-resource work;
- use hosted models for heavy reasoning, research and larger repository work;
- compare answers from multiple models, independently verify results and choose the best one;
- preserve the previous model for rollback;
- keep free-only mode active (OD-04: no standing paid budget).

LiteLLM remains the single gateway (`infra/litellm/config.yaml`). Adding or removing a provider is a configuration change; changing the **primary** model is a protected-core change (section 6).

---

## 4. Hardware and distribution

**Contabo VPS 4 (4 vCPU / 8 GB RAM):** hosted inference for heavy reasoning. Local models are small (3–4B, quantized) and CPU-only. A large model must not be forced onto this host.

**Distributed nodes** run separate model instances and workloads:

| Node | Intended model workload |
|------|------------------------|
| Contabo — IAM Core | Local foundation/coding baseline, identity, memory, reasoning, planning, model management |
| Umbrel node | Lightweight local models, experiments, development |
| AWS ARM64 | ARM compatibility testing and lightweight inference (OD-22) |
| AWS x86-64 | Coding models and software testing |
| Trusted nodes | Specialist models, evaluation, research |
| Hosted sub-agents | NVIDIA · Gemini · other authorised providers — optional assistance and independent evaluation |

Separate instances are distributed; the RAM of unrelated servers is **not** pooled as one machine. Splitting one model across hosts requires specialised inference infrastructure and fast networking and is out of scope for the initial deployment.

---

## 5. Formal model competition (selection method)

IAM runs a competition before confirming or changing its primary brain. All contenders receive identical tasks in isolated development environments, never in the protected production core.

**Phase 1 — Hardware and compatibility.** Detect RAM, CPU, GPU, storage and architecture; test ARM64 and x86-64; measure real model storage needs; test inference engines; establish memory and CPU limits.

**Phase 2 — Coding capability.** Code generation that actually runs; debugging; repository understanding; multi-file development; useful tests; terminal/tool use; multi-step autonomous development; self-correction after failure; security of generated code; RAM/CPU/time consumption.

**Phase 3 — Real-world testing.** In a dedicated IAM development repository: build a Python SDK feature; build the equivalent TypeScript SDK feature; diagnose a deliberately introduced bug; write automated tests; fix a failing suite; review another model's code; build a small IAM component from a specification.

**Phase 4 — Scoring.** Proposed weights (owner-adjustable; they sum to 100):

| Criterion | Weight |
|-----------|-------:|
| Coding correctness | 25 |
| Repository engineering | 15 |
| Autonomous tool use | 15 |
| Reasoning and problem solving | 20 |
| Security | 10 |
| Hardware efficiency | 5 |
| Reliability | 10 |

These are proposed decision weights, **not measured model performance**.

**Phase 5 — Selection and continuous improvement.** Compare each contender against the current primary; select the best model that fits the available hardware; preserve the previous model; test upgrades before deployment; require creator approval for protected-core changes; keep researching new releases.

---

## 6. Replacement and approval gate

Changing the **primary** model or the foundation-model architecture is a protected-core change:

1. benchmark evidence from the competition (section 5);
2. isolated dev-environment trial and rollback plan;
3. preservation of the previous model;
4. owner/creator approval under OD-11 and the signed-challenge flow in OD-19;
5. recorded reason and date in `IAM_OWNER_DECISIONS.md`.

Provider additions, free-tier substitutions and temporary routing changes that do not alter the primary model are configuration decisions under OD-15/OD-36, not protected-core changes.

---

## 7. Model-development programme (long-term objective)

The goal is not merely downloading better models; it is progressively developing IAM's own specialised intelligence:

1. fine-tune existing coding models;
2. create specialised Python, TypeScript, security and infrastructure models;
3. develop smaller models through distillation;
4. optimise inference for ARM64 and x86-64;
5. experiment with LoRA and other parameter-efficient training;
6. build training and evaluation datasets from appropriately licensed material;
7. develop new architectures when resources and expertise permit;
8. evaluate whether IAM's own models outperform the originals.

Hosted models may explain techniques, review experiments and suggest improvements. IAM's local intelligence remains responsible for evaluating the results.

Roadmap:

| Stage | Action |
|-------|--------|
| Start — Contabo | Benchmark Qwen2.5-Coder-3B-Instruct as the coding baseline; test the 9B hosted general model for broader reasoning |
| Expand — nodes | Test larger coding models (e.g. Qwen3-Coder-30B-A3B) only when sufficient memory and compatible hardware exist |
| Develop — distributed IAM | Run specialist models on trusted nodes, share validated results, distribute development tasks |
| Evolve — IAM models | Fine-tune, compress and develop IAM's own models while retaining the ability to replace the foundation model |

---

## 8. Implementation references

- `infra/litellm/config.yaml` — `qwen3.5-9b`, `local-qwen-3b` (only local alias), NVIDIA and fallback entries; Gemini entry is a gated template.
- `docker-compose.yml` — Ollama service with a 4 GB / 2 vCPU ceiling and a persistent model volume.
- `backend/app/core/config.py` — `ollama_base_url`, `nvidia_free_only`, `iam_sdk_default_model` (gateway alias, not a permanent model).
- `backend/app/services/intel_router_service.py` — provider registry, including `ollama` as a local provider.
- Pull the single approved local model before first use: `docker exec aura-ollama ollama pull qwen2.5:3b`.
- `tests/model_competition/` — `provider_readiness.py` (credential/reachability check), `hardware_evidence.py` (Phase 1 facts; use `--target` on the Contabo core), `smoke_coding.py` / `full_benchmark.py` / `benchmark_qwen35.py` (bounded Phase 2 task, cold/warm matrix), `run_constrained.py` (resource sampling), `concurrent_check.py`, `diagnose_assertion.py`, `final_report.py`; evidence in `tests/model_competition/RESULTS.md`.
- Evaluated local aliases (historical benchmark): `local-qwen-coder-3b` (best score), `local-qwen-3b`, `local-qwen3.5-4b` (requires `think=false`; slower and more memory-hungry on CPU). Owner direction of 25 Nov 2026 kept only `local-qwen-3b` active; **OD-46 (26 Nov 2026) reopens that choice and makes `local-qwen-coder-3b` the shared primary**, with `local-qwen-3b` retained as an approved secondary alias. `local-qwen3.5-4b` remains inactive without a new decision.
