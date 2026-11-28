# IAM — Multi-Model Intelligence: Repository Audit and Governance Specification

**Document:** 31 (companion to Documents 23 / 23-A)  
**Version:** 1.0 · 27 November 2026  
**Status:** **CONFIRMED — OD-51, 27 November 2026. Part of the frozen baseline as capability scope and implementation gate; not an implementation claim.**  
**Type:** Governance decision and implementation gate  
**Parent:** `ARCHITECTURE_INDEX.md`, `IAM_FINAL_CONSOLIDATION.md`  
**Related:** `IAM_FOUNDATION_MODEL_AND_INTELLIGENCE_SPEC.md` (Doc 23 / OD-38), `IAM_PRIMARY_MODEL_UNIFICATION_SPEC.md` (Doc 23-A / OD-46), `IAM_OWNER_DECISIONS.md`, `IAM_API_CONTRACTS.md`, `IAM_SECURITY_AND_INTERNET_POLICY.md`  
**Confirmed decision:** **OD-51** — Multi-provider model intelligence (encrypted key vault, provider/key isolation, fail-closed usage accounting, bounded parallel delegation). Clauses §4.1–§4.4 and the §4.4 starting bounds are confirmed; **§4.5 paid NVIDIA usage remains unauthorised**.

> Clauses §4.1–§4.4 are owner-confirmed. §4.5 is explicitly not authorised: paid NVIDIA usage requires a separate signed decision under OD-04. This document does not claim that any described capability is implemented.

---

## 1. Purpose and preserved architecture

IAM should discover, connect to, evaluate, select and coordinate multiple intelligence models while remaining the primary intelligence in control.

The following are **preserved unchanged** by this proposal:

- IAM's identity, genesis record and constitution (OD-01).
- The local primary model — `Qwen2.5-3B` (`local-qwen-3b` / `qwen2.5:3b`) under OD-46, reopened by the owner 27 Nov 2026 — and the rule that it wins when reachable. `qwen2.5-coder:3b` is an optional secondary.
- LiteLLM as the single shared gateway.
- The single-sphere frontend (`/` only); no new page or dashboard.
- No API credentials in browser JavaScript, browser storage or any API response.
- No standing paid budget; OD-04's zero-standing-budget and signed-approval rule remains in force.
- No automatic model promotion; signed release gate and rollback remain mandatory.
- No hosted model access to private IAM memory; hosted context sharing stays off by default.
- Existing systems and system count; this extends systems 2, 5, 11 and 14, and creates no new top-level system.

Hosted models — including NVIDIA NIM — remain **subordinate specialists**, never IAM itself.

---

## 2. Repository audit (point-in-time)

The working tree is dirty and was being edited concurrently during this audit. Findings reflect what was actually read; they must be re-verified before implementation.

### 2.1 What already exists

| Area | Evidence |
|------|----------|
| Shared primary resolution | `backend/app/services/model_inference.py` (`resolve()`, `_route()`, `InferenceService.chat()/stream()`); `backend/app/services/serving_model.py` (`current()`, `activate()`, `rollback()`) |
| Provider gateway | `infra/litellm/config.yaml` — model aliases, `max_budget: 0`, retries, tagging, detailed usage |
| Catalog router | `backend/app/services/intel_router_service.py` (`initialize_providers()`, `discover_nvidia_models()`, `select_model()`), `backend/app/api/routes/modelrouter.py`, `backend/app/models/modelrouter.py` |
| NVIDIA discovery | `discover_nvidia_models()` queries `{nvidia_base_url}/models` with a bearer key and persists `DiscoveredModel` |
| Signed paid-use gate | `backend/app/services/model_policy.py` (`PAID_ACTION`, `require_authorization()`), `CreatorApprovalService` |
| Encryption facility | `backend/app/services/crypto_service.py` — AES-GCM, `enc:v1:`; used for website credentials, MFA secrets and conversation content |
| Single specialist delegation | `backend/app/services/delegation.py` — specialist call, independent primary review, accepted findings stored as unverified with provenance |
| Resource admission | `backend/app/services/irwm.py`, adaptive selector in `backend/app/services/adaptive_model_selector.py` |
| Usage/cost tables | `ProviderUsage` and `RequestUsage` ORM models and migration SQL exist |
| Attribution | `iam_inference` in chat results; SSE `start` reports `model`, `mode`, `primary`, `delegation`; routing history in `RoutingDecision` |
| Sphere control surface | `frontend/components/iam/interface.tsx` in-screen options panel; readiness polled every 30 s |
| Tests | `test_serving_model.py`, `test_model_policy.py`, `test_delegation.py`, `test_adaptive_model_selector.py`, `test_irwm_inference_gate.py`, `test_crypto_service.py`, `test_model_independence.py` |

### 2.2 Verified gaps

1. **Single NVIDIA credential.** `settings.nvidia_api_key` is one value; no provider-level/key-level isolation, health tracking, rotation, or encrypted per-key storage.
2. **Router and inference are disconnected.** Chat calls `InferenceService.resolve()`, not `IntelligenceRouter.select_model()`. Fallback is a returned dict only; no cross-provider retry; signed `FallbackConfig` rows are not consumed.
3. **Usage tables have no writer.** `usage` returned by LiteLLM is discarded. No token/cost accounting, no spend enforcement tied to a request.
4. **No parallel subagents.** `delegation.py` performs one specialist call; the only LangGraph graph is a single-agent autonomy loop.
5. **Hardcoded sphere choice.** The hosted option sends a literal model id (`nvidia-nemotron-3.5-lightning`); no dynamic model list, task→model assignment or delegated-task status.

Additional audit notes: NVIDIA free-tier detection is a model-name heuristic (`_is_free_endpoint()`), not catalogue pricing; `DiscoveredModel.cost_input_per_1m`/`cost_output_per_1m` columns exist but are unused; `GET /api/v1/models/router/*` handlers have little test coverage.

---

## 3. Frozen decisions touched by the request

| Decision | Relevance | Effect requested |
|----------|-----------|------------------|
| OD-04 | Zero standing budget; every expenditure needs signed owner approval | **No change.** Add enforcement and accounting only; paid NVIDIA usage is **not** authorised here. |
| OD-07 | SOPS-encrypted files + Docker secrets | **No change.** Request an extension for encrypted, backend-held provider keys; no browser-side secrets. |
| OD-11 | Protected core; creator authorisation for core architecture/security changes | **No change to primary model or identity.** Key-vault and paid-use changes require explicit owner approval under this rule. |
| OD-19 | Signed email approvals; frontend is user-only, no Creator UI | **No change.** Provider key administration must stay outside the browser. |
| OD-36 | Replaceable, free-first tooling | **No change.** Provider-independent design; NVIDIA remains one provider behind LiteLLM. |
| OD-38 / OD-46 | Local primary wins; hosted models subordinate | **No change.** No model promotion or primary replacement is requested. |

---

## 4. Proposed owner decision — OD-51 (multi-provider model intelligence)

The following clauses require explicit owner confirmation. None takes effect by this document alone.

### 4.1 Encrypted provider-key vault (backend only)

- A backend store for multiple credentials per provider, with alias, provider, key fingerprint (never the plaintext), `secret_ciphertext` encrypted through `CryptoService`, scope (`free` / `paid` / `specialist`), enabled/disabled state, health state, last-used timestamp and per-key limits.
- Bootstrap from existing `<FIELD>_FILE` Docker secrets; no key may be returned by any API or rendered in the sphere.
- Administration through operator-only backend interfaces and CLI, consistent with OD-19 (no Creator UI in the frontend).
- **Decision requested:** authorise this encrypted store and confirm it does not alter OD-07's secret policy.

### 4.2 Provider-level and key-level isolation

- A failing or disabled key must not be able to take down another authorised key or provider.
- Failover selects another *authorised* key only; it must never bypass spending limits, signed approval, provider `free_only` policy, or privacy gates.
- Each key carries independent health, rate-limit and spend state; keys are never pooled into one unlimited credential.
- **Decision requested:** confirm isolation rules and per-key/per-provider limit policy.

### 4.3 Fail-closed usage accounting

- Before any paid request, IAM must be able to determine: signed authorisation for that action, remaining budget, applicable per-key/per-model limits and expected cost.
- If any of those cannot be determined reliably, the request must **not** be made; this is a fail-closed denial with a recorded reason, not a default-allow.
- Token and cost data from provider responses must be persisted to the existing `ProviderUsage`/`RequestUsage` tables with model, provider, key fingerprint and attribution.
- **Decision requested:** confirm fail-closed behaviour and the cost/authorisation data required before a paid call. Paid NVIDIA usage remains separately unauthorised.

### 4.4 Bounded parallel delegation

- Parallel specialist work must be bounded by: maximum concurrent agents, per-agent execution timeout, per-agent memory limit, maximum delegated calls per request, and IRWM/RAM admission.
- Every delegated result remains subject to independent review by the local primary; only accepted findings may be stored, as unverified knowledge with provenance.
- No delegation may access private IAM memory, replace IAM's decision, or bypass signed `model.delegate` approval.
- **Decision requested:** set the numeric bounds. Proposed starting values (not locked, owner to confirm or replace):

| Bound | Proposed starting value |
|-------|-------------------------|
| Maximum concurrent agents | 3 |
| Per-agent timeout | 120 s |
| Per-agent memory ceiling | 512 MB |
| Maximum delegated calls per request | 4 |
| Failure policy | Fail closed; no partial result presented as verified |

### 4.5 Explicitly not authorised by this document

- Any paid NVIDIA request or removal of the free-only default.
- Any change to the primary model, identity, constitution or protected core.
- Any provider key in the frontend, in logs, or in an API response.
- Any automatic model promotion or silent change to a frozen OD decision.

---

## 5. Implementation sequence (gated)

| Stage | Gate | Scope |
|-------|------|-------|
| 0 — Governance | Owner signs OD-51 clauses | This document; no implementation before confirmation |
| 1–3 — First slice | OD-51 §4.1–4.3 confirmed | Encrypted key vault; router/inference unification with key isolation and fallback; fail-closed usage/cost accounting; tests |
| 4 — Parallel delegation | OD-51 §4.4 bounds confirmed | Bounded fan-out orchestrator with primary-model synthesis; tests |
| 5 — Sphere extension | Stages 1–4 verified | Extend the existing in-screen panel only; dynamic models, provider health, active/previous model, Manual/Auto/Hybrid, delegated-task status; no new route |

### Acceptance criteria for the first slice

1. Two NVIDIA keys can be registered, health-checked and independently disabled without exposing either credential.
2. A failing key falls back only to another authorised key, and never crosses a spending or approval gate.
3. Paid requests are denied when authorisation, remaining budget or cost data is unavailable; the denial is recorded.
4. Each inference request produces attribution and usage rows with model, provider, redacted key fingerprint and tokens/cost.
5. The local primary still answers by default; hosted specialists require an explicit, authorised route.
6. Existing tests plus new tests for vault isolation, fail-closed accounting and fallback pass.

---

## 6. Implementation prohibitions

Implementation must not silently:

- change any locked OD decision, the system count, identity, or the primary model;
- enable paid usage without a signed owner approval for that expenditure;
- introduce a browser-side credential, a second frontend route, or a Creator UI in the frontend;
- share private memory with a hosted provider;
- promote a model automatically or bypass signed release/rollback gates;
- present an unverified delegated result as IAM's own verified knowledge.

---

## 7. Decision record

Owner confirmation was recorded on 27 November 2026 as OD-51 in `IAM_OWNER_DECISIONS.md`. Clauses §4.1–§4.4 and the proposed §4.4 starting bounds were confirmed. §4.5 was explicitly not authorised.

| Clause | Decision |
|--------|----------|
| §4.1 Encrypted backend provider-key vault | ✅ **CONFIRMED** |
| §4.2 Provider and key isolation | ✅ **CONFIRMED** |
| §4.3 Fail-closed usage accounting | ✅ **CONFIRMED** |
| §4.4 Parallel delegation bounds | ✅ **CONFIRMED** — starting values: 3 agents, 120 s, 512 MB, 4 delegated calls |
| §4.5 Paid NVIDIA usage | ❌ **NOT AUTHORISED** — separate signed decision required under OD-04 |

Implementation remains gated by §5: stages 1–3 may proceed; parallel delegation (stage 4) and the sphere extension (stage 5) follow only after verification of the earlier stages.

### Implementation status (27 November 2026)

All five stages are implemented. Stages 1–3: `ModelProviderKey` (migration 052), `ModelCredentialVault`, `ModelUsageService`, OD-51 key/usage integration in `InferenceService.chat()/stream()`, operator-only routes under `/api/v1/models/credentials`, and tests. Stage 4: `delegation_orchestrator.py` with the confirmed bounds (3 concurrent agents, 120 s timeout, 512 MB per-agent ceiling, 4 calls per request), per-task sessions, per-task timeout, independent primary verification inherited from `delegation.run`, fail-closed rejection/timeout handling, and `delegation_tasks` on the chat request. Only IAM-accepted, unverified findings are returned as labelled context; no private memory is passed to specialists.

Stage 5: the existing in-screen options panel now shows active/previous model, Manual/Auto/Hybrid mode, a free-model-only manual selector (filtered on `is_free`), read-only provider key health, and delegated-task status. No new route, no browser credential, no key management action in the frontend; automatic and hybrid modes leave model choice to IAM.

**Paid NVIDIA usage remains unauthorised** — §4.5 is untouched, and the sphere offers only free-discovered models. Provider-side API keys remain in the LiteLLM gateway configuration (`NVIDIA_API_KEY` plus `NVIDIA_API_KEY_1…4` deployments behind the same free model aliases); the encrypted vault holds per-connection gateway credentials used for key-level isolation and requires signed `model.provider_key_manage` authorization to register.
