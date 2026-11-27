# IAM — Primary Model Unification and Shared Intelligence Amendment

**Document:** 23-A — amendment to Document 23 / OD-38  
**Status:** **CONFIRMED** — OD-46, 26 November 2026, recorded in `IAM_OWNER_DECISIONS.md`. Supersedes OD-38 §1 and §3 on local-model selection only; all other OD-38 provisions remain in force. Part of the frozen baseline.  
**Type:** Architecture amendment spanning systems 2 (Intelligence and Reasoning), 5 (Learning), 11 (Self-Evolution and Model Independence) and 14 (Evaluation and Research)  
**Extends:** `IAM_FOUNDATION_MODEL_AND_INTELLIGENCE_SPEC.md` (Doc 23 / OD-38), `IAM_MODEL_EVOLUTION_AND_FINE_TUNING_SPEC.md` (OD-40), `IAM_INDEPENDENT_AI_RESEARCH_DEVELOPMENT_AND_EVOLUTION_ARCHITECTURE.md` (OD-41)  
**Related:** `ARCHITECTURE_INDEX.md`, `IAM_API_CONTRACTS.md`, `IAM_OPENAPI.json`

---

## 1. Purpose

Unify the model used by IAM's frontend and backend under one shared primary, and connect the self-improvement cycle to live inference. This does **not** change IAM's identity, memory, knowledge, planning, governance or decision authority — those remain owned by IAM and independent of any model.

> **Core principle (unchanged):** IAM owns its intelligence. Models provide intelligence capabilities.

## 2. Locked decisions

1. **One primary model across IAM.** Frontend conversation and backend reasoning, planning, memory retrieval, tool orchestration and decisions use the same primary model configuration. There is no separate "frontend model".
2. **The frontend never pins a model.** Chat clients omit the `model` field; the backend resolves the primary. This is the mechanism that keeps both sides on one brain.
3. **Hosted models are subordinate specialists.** They are optional API sub-agents, reachable only by explicit model id or through IAM's router. They never become IAM and cannot rewrite identity or the protected constitution.
4. **Local primary wins when reachable.** If the approved local model is available, it serves the shared path even when hosted keys are configured. Hosted providers then act as fallback or specialists.
5. **A released model becomes the served model.** A fine-tuned version that passes benchmark reproducibility, provenance and signed Creator approval is activated as the serving model; signed rollback restores what was serving before it.
6. **Private memories stay in permission-controlled memory systems**, never in model weights or fine-tuning datasets without consent.

## 3. Model roles

| Role | Current alias/id | Where | Authority |
|------|------------------|-------|-----------|
| Shared primary | `local-qwen-3b` → `qwen2.5:3b` | Local Ollama, opt-in via `OLLAMA_ENABLED` | Default for all IAM chat and reasoning; owner reopened OD-46 on 27 Nov 2026 |
| Secondary local model | `local-qwen-3b` → `qwen2.5:3b` | Local Ollama | Approved alternative, not the default |
| Fallback / general specialist | `qwen3.5-9b` | Hosted DashScope (LiteLLM) | Explicit sub-agent or fallback when local unavailable |
| Further hosted specialists | NVIDIA NIM, Gemini (gated) | Hosted, replaceable | Optional, explicit id only |
| Gateway | LiteLLM + IAM Intelligence Orchestrator | Local | One interface; failover, spend control, answer comparison |

`iam_sdk_default_model` remains a gateway routing alias for hosted fallback; it is **not** IAM's primary model and is not an identity.

## 4. Resolution rules

Implemented in `backend/app/services/model_inference.py`:

- With no explicit `model`, resolve the active serving model from `backend/app/services/serving_model.py`.
- If the active model is a local alias and the local tag is reachable, route to Ollama using the concrete tag (`iam_primary_local_tag`).
- Otherwise, if a hosted key is configured, route through LiteLLM. A local primary that is unavailable falls back to `iam_sdk_default_model`; the response records the reason.
- With an explicit `model`, an id that matches the local alias/tag routes locally; any other id routes through LiteLLM as a specialist.
- If neither path is available, return an explicit offline status — never fabricated reasoning.
- Chat requests are assembled with IAM context: verified `KnowledgeItem` records are injected as labelled reference data, and private memories only when local, explicitly requested and operator-enabled. Hosted providers receive no injected context by default (`iam_context_share_with_hosted=false`).
- With `delegate=true`, an optional hosted specialist runs the task only with an active signed Creator authorization for `model.delegate`. IAM reviews the specialist answer with its own primary model, stores only accepted findings as unverified knowledge with provenance, and passes them back as labelled reference context. Private memory is never shared with a delegate, and a missing authorization, malformed review or rejection stores nothing.
- Inference timeouts are configurable and default to 300 seconds for both chat and streaming. A cache-cold local 3B on the 4 vCPU core can take minutes to load and emit first tokens; a genuine timeout is still reported as 504 rather than a fabricated answer.

Every chat response and SSE `start` event reports `model`, `mode` and `primary`, so callers can verify which model actually answered.

## 5. Self-improvement → live inference bridge

`backend/app/services/serving_model.py` holds the active serving model in the model-release artifact store:

| Event | Serving state |
|-------|---------------|
| No override | `settings.iam_primary_model` (source `config`) |
| Signed promotion via `ModelReleaseService.promote` | `activate(model, version)` — remembers previous model/version (source `release`) |
| Signed rollback via `ModelReleaseService.rollback` | `rollback()` — restores the previous model (source `rollback`) |

Promotion gates are unchanged and remain mandatory: reproducible benchmark evidence, dataset provenance (`dataset_sha256`, `licence`, `consent_recorded`, `poisoning_scan_ref`), measured improvement over baseline, and an active signed Creator authorization for `development.model_release`. Capability assessment, reflection, dataset preparation and SFT/QLoRA submission remain in the OD-40/OD-41 services and `POST /api/v1/development/research-runs`.

## 6. API contract

### `GET /api/v1/models/primary`

Returns the single shared primary and its resolution state:

```json
{
  "primary": "local-qwen-3b",
  "source": "config | release | rollback",
  "version": null,
  "resolved_model": "qwen2.5:3b",
  "mode": "ollama | hosted | offline",
  "available": true,
  "reason": "IAM primary local model is reachable",
  "local_alias": "local-qwen-3b",
  "local_tag": "qwen2.5:3b",
  "delegates": ["qwen3.5-9b"]
}
```

### Chat

`POST /api/v1/models/chat` and `POST /api/v1/models/chat/stream` keep `model` optional. Omitting it selects the shared primary. SSE `start` is now `{request_id, model, mode, primary}`.

### Readiness

`GET /api/v1/models/readiness` additionally reports `primary`. No provider key is ever exposed.

## 7. Governance preserved

- Changing the primary model remains a protected-core change under OD-11/OD-19; promotion requires signed Creator authorization.
- Paid API usage still requires explicit owner authorization; OD-04 zero standing budget is unchanged.
- External models cannot rewrite identity, constitution, memory or governance.
- Fine-tuning is controlled, evaluated, versioned and reversible.
- Model replacement does not lose IAM continuity.

## 8. Decision resolved — local model variant (OD-46)

OD-38 (25 November 2026) had removed `qwen2.5-coder:3b` from the local set and kept only `qwen2.5:3b`. On 26 November 2026 the owner reopened that choice to **Qwen2.5-Coder 3B**; on **27 November 2026 the owner reopened it again to Qwen2.5-3B** (`qwen2.5:3b`, alias `local-qwen-3b`), with `qwen2.5-coder:3b` retained as an optional secondary local model. Recorded as OD-46 in `IAM_OWNER_DECISIONS.md`.

Evidence relied on: `tests/model_competition/RESULTS.md` — weighted score 4.10 for `local-qwen-coder-3b` versus 3.83 for `local-qwen-3b` and 2.87 for `local-qwen3.5-4b` (`think=false`), with measured cold/warm latency and RAM profiles on the 4 vCPU / 8 GB target. The previous primary remains available for rollback.

Configuration applied after the 27 Nov 2026 reopening: `IAM_PRIMARY_MODEL=local-qwen-3b`, `IAM_PRIMARY_LOCAL_TAG=qwen2.5:3b`, the `local-qwen-3b` alias in `infra/litellm/config.yaml`, and `OLLAMA_ENABLED=true`. The coder alias remains an optional secondary, not the default. Local inference remains opt-in by design; if it is disabled or the tag is not pulled, the hosted fallback serves requests and reports that fact.

## 9. Implementation references

- `backend/app/core/config.py` — `iam_primary_model`, `iam_primary_local_tag`, `adaptive_delegate_model`, inference timeouts
- `backend/app/services/serving_model.py` — active serving model, activation, rollback
- `backend/app/services/model_inference.py` — resolution, local/hosted routing, SSE metadata
- `backend/app/services/iam_context.py` — context assembly from existing memory/knowledge systems with privacy gating
- `backend/app/services/delegation.py` — authorized sub-agent delegation, independent IAM review and provenance storage
- `backend/app/api/routes/models.py` — `GET /primary`, `GET /readiness`, chat endpoints
- `backend/app/services/ai_research/release_gate.py` — promotion and rollback hooks
- `frontend/components/iam/interface.tsx`, `frontend/lib/api.ts` — no client-side model pinning
- `docker-compose.yml`, `.env.example` — primary model environment variables
- `backend/tests/test_serving_model.py` — evidence tests
- `IAM_OPENAPI.json` — contract for `/api/v1/models/primary`
