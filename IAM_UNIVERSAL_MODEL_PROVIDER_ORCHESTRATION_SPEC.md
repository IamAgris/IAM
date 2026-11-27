# IAM — Universal Model Provider & Intelligence Orchestration System: Audit and Implementation Plan

**Document:** 32 (companion to Documents 23 / 23-A / 31)  
**Version:** 1.0 · 27 November 2026  
**Status:** **PROPOSED — repository audit and implementation task plan. Not part of the frozen baseline.**  
**Type:** Architecture proposal and work breakdown; **not** an implementation claim  
**Parent:** `ARCHITECTURE_INDEX.md`, `IAM_FINAL_CONSOLIDATION.md`  
**Related:** `IAM_FOUNDATION_MODEL_AND_INTELLIGENCE_SPEC.md` (Doc 23 / OD-38), `IAM_PRIMARY_MODEL_UNIFICATION_SPEC.md` (Doc 23-A / OD-46), `IAM_MULTI_MODEL_INTELLIGENCE_GOVERNANCE_SPEC.md` (Doc 31 / OD-51), `IAM_API_CONTRACTS.md`  
**Proposed decision:** **OD-52** — Universal Model Provider & Intelligence Orchestration System. **Not confirmed.**

> This document records what already exists in the repository, maps it to the requested architecture, and turns the four critical gaps into precise tasks. It authorises no code change and no paid model usage. The working tree was dirty and concurrently edited during the audit; all findings must be re-verified before implementation.

---

## 1. Non-negotiable preserved architecture

- IAM's identity, genesis record and constitution (OD-01) are unchanged.
- `Qwen2.5-Coder 3B` remains the local shared primary (OD-46); hosted models are subordinate specialists (OD-38).
- LiteLLM remains the single gateway. Dynamic model registration happens *through* LiteLLM, not around it.
- The frontend remains one sphere (`/` only); no dashboard and no new page.
- No provider credential in browser JavaScript, browser storage, prompts, logs or model responses.
- No standing paid budget (OD-04). Free endpoints allowed; paid endpoints blocked by default; unknown pricing blocked.
- No automatic model promotion (OD-11/OD-40), and no hosted access to private IAM memory.
- NVIDIA is the first provider, not a special case inside agents. The same architecture must accept other OpenAI-compatible providers and local Ollama.

---

## 2. Repository audit — what already exists

| Spec capability | Existing code | Gap |
|-----------------|---------------|-----|
| One encrypted provider credential | `services/crypto_service.py` (AES-GCM `enc:v1:`), `services/model_credential_vault.py`, migration 052 | Vault holds per-connection **gateway** credentials; provider-side NVIDIA key still lives in LiteLLM env. Registration requires signed `model.provider_key_manage` approval (OD-19). |
| Live NVIDIA discovery | `services/intel_router_service.py::discover_nvidia_models()` uses one `nvidia_api_key`, calls `/v1/models`, persists `DiscoveredModel`; route `POST /api/v1/models/router/discover/nvidia` | `is_free` is a name heuristic; no Models.dev metadata source; no periodic refresh; no availability probe; no last-known-good catalogue. |
| Model registry | `models/modelrouter.py::DiscoveredModel` — `model_id`, `display_name`, `capabilities`, `context_length`, `is_free`, `is_available`, cost fields, `quality_score`, `last_checked_at` | Missing model type, access type, endpoint status, input/output capabilities, tool calling, reasoning flag, API protocol, restrictions, last-tested result, provider metadata. |
| Model execution | `services/model_inference.py` (`resolve`, `_route`, `chat`, `stream`) routes explicit model ids through LiteLLM; `infra/litellm/config.yaml` defines static aliases | **A discovered model cannot be called until it is declared in LiteLLM.** `store_model_in_db` is not enabled; no `/model/new` registration; only two static NVIDIA aliases exist. |
| Model selection | `InteligenceRouter.select_model()` (catalog scoring), `adaptive_model_selector.py`, `RoutingDecision` | Catalog router is not called by chat; selection is not capability-to-subagent assignment. |
| Sub-agents | `services/delegation.py` (verified single specialist), `services/delegation_orchestrator.py` (OD-51 bounded fan-out: 3/120 s/512 MB/4) | Models are chosen by explicit id or a single default; no capability-based assignment, comparison or conflict detection across multiple models. |
| Fail-closed usage | `services/model_usage.py` — signed authority + determinable price + positive budget; writes `ProviderUsage` / `RequestUsage`; `iam_inference` attribution | Paid protection exists; unknown pricing is denied; no free-vs-paid reclassification watcher if an endpoint changes. |
| Sphere model UI | `frontend/components/iam/interface.tsx` options panel — active/previous model, Manual/Auto/Hybrid, free-model list, read-only key health, delegated-task status | No catalogue browser/search/inspection; no agent-assignment view; no last-sync/last-tested display. |
| Background work | `workers/autonomy_worker.py` (in-process 30 s cycle), optional ARQ workers under `profiles` | No model-catalogue refresh worker; no availability-monitor schedule. |

### The four critical gaps, addressed

**A. Executable catalogue entries.** Keep IAM's `DiscoveredModel` as the authoritative registry, but mirror each eligible free model into LiteLLM so the id is routable. Register with `POST /model/new` and `model_info` metadata; keep exactly one static bootstrap alias (`nvidia-nemotron-3.5-lightning`) so the gateway can start before discovery runs. Remove the ten static deployments just added for the multi-key experiment once dynamic registration is verified.

**B. Dynamic registration.** Enable `store_model_in_db: true` and set `LITELLM_SALT_KEY` in the LiteLLM service so registrations persist and provider credentials stay encrypted. Add a backend `ProviderModelRegistrar` that uses the LiteLLM master key (backend-only) to:
- create/update models with `litellm_params: {model: "openai/<id>", api_key: "os.environ/NVIDIA_API_KEY", api_base: settings.nvidia_base_url}`;
- attach `model_info` with provider, free status, capabilities, source and discovered_at;
- delete retired models via `POST /model/delete` while keeping IAM's historical `DiscoveredModel` row.
Never send a key through the model-registration payload; reference the env variable.

**C. Availability checks.** Add `EndpointAvailabilityMonitor`. Catalogue presence is not endpoint availability (older aliases in `config.yaml` already document HTTP 410). The monitor:
- reconciles IAM's registry against `/v1/models`;
- performs a bounded probe per free model (configurable, no paid model probed);
- classifies failures as `auth`, `rate_limit`, `model_outage`, `network` or `unsupported_capability`;
- sets `endpoint_status` (`available|unavailable|unknown`) and `last_tested`, and keeps a `last_known_good` snapshot for use when discovery is down;
- removes unavailable models from active selection without deleting history, and rechecks them with backoff.

**D. Refresh and provider generalisation.** Add a scheduled ARQ worker (or extend the autonomy worker's tick) for discovery → metadata merge → registration → availability check. Introduce a `BaseProvider` contract (`discover`, `metadata`, `probe`, `register`, `chat`) with implementations for NVIDIA, DashScope, Gemini-compatible and local Ollama. Metadata sources: NVIDIA Build catalogue (authoritative ids), Models.dev API (specifications/capabilities), provider `/v1/models` (live eligibility). Merge with documented precedence: live endpoint check > NVIDIA catalogue > Models.dev metadata. Agents never call a provider directly; they use the shared registry and gateway.

---

## 3. Model registry fields to add

Extend `DiscoveredModel` (new migration) with:

| Field | Purpose |
|-------|---------|
| `provider` / `provider_id` | Provider ownership |
| `display_name`, `model_id` | Human-readable name and exact API id |
| `model_type` | `llm`, `embedding`, `vision`, `speech`, `image` |
| `access_type` | `free`, `paid`, `local` |
| `endpoint_status` | `available`, `unavailable`, `unknown` |
| `alias` | LiteLLM `model_name` used for execution |
| `context_length` | Actual window |
| `input_capabilities`, `output_capabilities` | text / image / audio / video, text / audio / image |
| `tool_calling`, `reasoning`, `structured_output` | booleans, never assumed |
| `api_protocol` | `chat_completions` or other |
| `last_tested`, `test_result` | result of the most recent probe |
| `restrictions` | JSON: rate limits, endpoint conditions |
| `metadata_source`, `discovered_at` | provenance of each field |
| `last_known_good` | snapshot usable during provider outage |

---

## 4. Capability-based sub-agent assignment

Assignment is a registry lookup plus router scoring, never random distribution:

| Sub-agent | Preferred capability |
|-----------|----------------------|
| Research | long context, reasoning |
| Coding | code generation, tool calling |
| Security | reasoning, critical evaluation |
| Mathematics | reasoning |
| Translation | multilingual |
| Vision | image input |
| Independent reviewer | reasoning, different model family |
| Data extraction | structured output |

`delegation_orchestrator.py` gains an assignment table and selects from `endpoint_status=available`, `access_type=free`, tool/context compatible models. IAM's local primary reviews and consolidates all results; conflicts are surfaced, not silently merged.

---

## 5. Financial and operational rules

- Free endpoints allowed; paid blocked by default; unknown pricing blocked. A free endpoint becoming paid must never silently spend.
- One credential per provider; shared account rate limits are respected via a global concurrency limiter, priority queue and exponential backoff with jitter.
- Per-request timeouts, context-window fitting, streamed responses where supported, tool-call normalisation to IAM's common format, and response validation.
- Agent isolation: one agent's private task context is never another agent's input.
- Audit: every external call records agent, model, provider, key fingerprint, reason and outcome.
- Provider health distinguishes auth failure, rate limit, model outage and network failure.
- No private conversations, credentials or confidential project data to NVIDIA free endpoints.

---

## 6. Advanced capabilities (later phases)

Automatic benchmark of newly discovered models (speed, reasoning, coding, reliability), performance rankings and duplicate detection; multi-model collaboration with conflict detection; provider migration without rewriting agents; shared-quota-aware resource management preferring local Qwen; controlled self-improvement proposals that check licensing/data-use terms and never auto-replace the production model or train on provider outputs without authorisation.

---

## 7. Implementation task breakdown

| Phase | Task | Concrete files | Acceptance |
|-------|------|----------------|------------|
| A | Extend model registry + migration 060 | `models/modelrouter.py`, `db/migrations/060_model_catalog.sql`, `MIGRATION_ORDER.json` | New fields queryable; existing rows backfilled; migration check passes |
| B | Provider abstraction + dual discovery | `services/providers/base.py`, `providers/nvidia.py`, `services/model_discovery.py` | NVIDIA `/v1/models` + Models.dev API merged with provenance; free-only filter; one key |
| C | LiteLLM dynamic registration | `infra/litellm/config.yaml` (`store_model_in_db`, `LITELLM_SALT_KEY`), `services/provider_model_registrar.py` | A discovered free model becomes callable without config edit; retired models removed; key never in payload |
| D | Availability monitor + last-known-good | `services/endpoint_availability.py`, `workers/arq_model_catalog.py` | Outages classified; unavailable models excluded from selection; catalogue survives provider outage |
| E | Capability evaluator + assignment | `services/capability_evaluator.py`, `delegation_orchestrator.py` | Sub-agent assigned by capability; local primary reviews; conflicts surfaced |
| F | Operational hardening | `services/provider_request_queue.py`, `model_inference.py`, `delegation.py` | Concurrency cap, backoff, timeouts, context fitting, tool-call normalisation, validation, audit |
| G | Sphere catalogue view | `frontend/components/iam/interface.tsx` | Browse/search/inspect models, last sync, endpoint status, agent assignments — same single sphere |
| H | Benchmarks & controlled self-improvement | `services/model_benchmark.py`, `services/model_improvement.py` | Rankings evidence-based; proposals only; no auto-promotion or unauthorised training |

Each phase requires its own tests and must pass the repo gates: `pytest backend/tests -q --cov=app --cov-fail-under=60`, `ruff`, migration order check, OpenAPI drift check, frontend `tsc`/`build`.

---

## 8. Governance gate

OD-51 (Doc 31) is confirmed and covers encrypted credentials, isolation, fail-closed usage and bounded delegation. This document proposes **OD-52** for the universal provider/orchestration scope. Until the owner confirms OD-52:

- no provider-registration code is enabled in production;
- no paid endpoint is activated;
- no frozen decision is altered;
- the ten static NVIDIA deployments remain the working fallback.

---

### Implementation status

Phases A and B are implemented. Phase B adds `services/providers/base.py` (`BaseProvider` / `ModelSpec`), `providers/nvidia.py` (live `/v1/models`, one key, free-only filter), `providers/models_dev.py` (specifications only), `services/model_discovery.py` (merge precedence: live catalogue for access, Models.dev for capabilities), `POST /api/v1/models/discovery/{provider}`, config for the Models.dev endpoint and tests. Discovered entries always persist with `endpoint_status='unknown'` — no availability is claimed.

Phase A only was implemented first: `DiscoveredModel` registry fields and migration `060_model_catalog.sql` (registered in `MIGRATION_ORDER.json`) with conservative defaults — `endpoint_status='unknown'`, capabilities false until tested, `access_type='free'`, and a backfill that never claims legacy rows were availability-tested. Evidence tests are in `backend/tests/test_model_catalog.py`. No dynamic model registration, availability monitor, provider registration or paid access is enabled; OD-52 remains proposed.

## 9. Decision request

| Item | Decision needed |
|------|-----------------|
| OD-52 universal provider architecture | Approve / reject / amend |
| Replace static multi-key deployments with one-key dynamic catalogue | Approve / reject / amend |
| New registry fields and migration 060 | Approve / reject / amend |
| Phase order A–H | Approve / amend |
| Paid NVIDIA access | **Not requested — remains blocked under OD-04** |
