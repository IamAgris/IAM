# IAM Architecture — Document Index (AUTHORITATIVE)

**Version:** 1.2 · 27 November 2026  
**Purpose:** Resolve duplicate/superseded documents. This is the single entry point to the frozen IAM architecture.

---

## Source of truth

| Priority | Document | Status |
|----------|----------|--------|
| **1** | `IAM_FINAL_CONSOLIDATION.md` | **AUTHORITATIVE** — master gap analysis, all systems, completion levels, roadmap |
| **1** | `IAM_OWNER_DECISIONS.md` | **AUTHORITATIVE** — 52 locked decisions (OD-01…OD-52; OD-47 owner-confirmed 27 Nov 2026, not a signed Creator decision) |
| 2 | `canonical/IAM_DOC_01…04` | Frozen supplied documents 01–04 |
| 2 | `IAM_DISTRIBUTED_ARCHITECTURE.md` | Document 05 |
| 2 | `IAM_WHITEHAT_AND_WORKSPACE.md` | Document 06 |
| 2 | `IAM_COMMUNICATION_ARCHITECTURE.md` | Document 07 |
| 2 | `IAM_HARDWARE_ADAPTATION.md` | Document 08 |
| 2 | `IAM_BLOCKCHAIN_AND_BANKING.md` | Document 09 |
| 2 | `IAM_DYNAMIC_NODE_NETWORK_SPEC.md` | Document 10 (dynamic nodes, OD-26) |
| 2 | `IAM_UNIVERSAL_WEBSITE_INTERACTION_SPEC.md` | Document 11 (frontend-first interaction with any website, OD-27) |
| 2 | `IAM_AI_ASSISTANT_INTEROPERABILITY_SPEC.md` | Document 12 (internal assistant/voice technology learning, OD-28) |
| 2 | `IAM_DEVELOPER_SDK_AND_CLI_SPEC.md` | Document 13 (official SDK/CLI + protocol, OD-29) |
| 2 | `IAM_GLOBAL_RESEARCH_AND_KNOWLEDGE_SPEC.md` | Document 14 (global research scope frozen, OD-30) |
| 2 | `IAM_LEGAL_INTELLIGENCE_AND_COMPLIANCE_SPEC.md` | Document 15 (legal/government monitoring, OD-31) |
| 2 | `IAM_GEOSPATIAL_INTELLIGENCE_AND_LIVE_MAPPING_SPEC.md` | Document 16 (maps/geospatial, OD-32) |
| 2 | `IAM_FREE_SANDBOX_API_ADAPTER_SPEC.md` | Document 22 (OEDIE free platform adapters; extends OD-15/OD-35) |
| 2 | `IAM_HUMAN_PSYCHOLOGY_TONE_AND_INFLUENCE_SPEC.md` | Document 17 (human psychology, tone and influence intelligence — defensive; OD-33) |
| 2 | `IAM_EXTERNAL_AI_IDENTITY_AND_LEARNING_SPEC.md` | Document 18 (external AI identity, interview, collaborative learning and external skill packages — extends Doc 03 §7; OD-34) |
| 2 | `IAM_FREE_INFRASTRUCTURE_NODE_DISCOVERY_AND_LIFECYCLE_SPEC.md` | Document 19 (free cloud/platform nodes — extends OEDIE and Doc 10; OD-35) |
| 2 | `IAM_AI_SDK_AND_FRAMEWORK_RESEARCH_SPEC.md` | Document 20 (AI SDK/framework/model research + Technology Capability Registry; OD-36) |
| 2 | `IAM_INFRASTRUCTURE_TRAFFIC_AND_DISTRIBUTED_PROCESSING_SPEC.md` | Document 21 (traffic, queues and distributed processing — extends system 13 / Doc 10; OD-37) |
| 2 | `IAM_FOUNDATION_MODEL_AND_INTELLIGENCE_SPEC.md` | Document 23 (locked initial foundation model, router, model competition and model development — extends Doc 02 / systems 2, 5, 11, 14; OD-38) |
| 2 | `IAM_PRIMARY_MODEL_UNIFICATION_SPEC.md` | Document 23-A — shared primary model for frontend and backend, hosted models as sub-agents, self-improvement → live inference bridge (amends OD-38 §1/§3 on local-model selection; OD-46, confirmed 26 November 2026) |
| 2 | `IAM_RESOURCE_AND_WORKLOAD_MANAGER_SPEC.md` | Intelligent Resource and Workload Manager (RAM/CPU control, model residency, node delegation — systems 2, 13, OD-37; OD-39) |
| 2 | `IAM_MODEL_EVOLUTION_AND_FINE_TUNING_SPEC.md` | Model Evolution and Fine-Tuning Engine — MEFE (datasets, SFT/QLoRA, evaluation, registry — systems 5, 11, 14; OD-40) |
| 2 | `IAM_INDEPENDENT_AI_RESEARCH_DEVELOPMENT_AND_EVOLUTION_ARCHITECTURE.md` | Parent architecture for autonomous model research/development/deployment — 14 engines + distributed free-compute research (OD-41; requirements frozen) |
| 2 | `IAM_AI_RESEARCH_IMPLEMENTATION_PLAN.md` | Implementation sequence, dependencies, priorities and acceptance tests for OD-41 |
| 2 | `IAM_IMPLEMENTATION_TECHNOLOGY_ADDENDUM.md` | Cross-cutting Python + Rust + TypeScript implementation allocation; not a new decision and does not reopen OD-01…OD-41 |
| 2 | `IAM_HUMAN_BEHAVIOUR_EQUALITY_AND_RESPONSIBILITY_SPEC.md` | Document 24 (human behaviour, Equality of Existence, power and responsibility — extends Docs 17/14; OD-43) |
| 2 | `IAM_FINANCIAL_INTELLIGENCE_AND_ECONOMIC_INDEPENDENCE_SPEC.md` | Document 25 (income, crypto, trading, payments; Amendment A adds prediction markets, gaming intelligence, investments and provider ecosystem — extends Doc 09 / OD-23/24/25; OD-44, OD-56) |
| 2 | `IAM_IP_AND_LEGAL_INTELLIGENCE_MASTER_SPEC.md` | Document 28 — **IP & Legal Intelligence (IPLCI)** (20 capability areas, 7 enforcement engines, mandatory legal gateway, fail-closed ownership posture, tamper-evident audit; extends Docs 14/15; **OD-48 CONFIRMED 27 November 2026**). Part of the frozen baseline; governance layer inside existing systems, not a new top-level system, not legal advice. |
| 2 | `IAM_RESEARCH_ACQUISITION_AND_LEGAL_INTELLIGENCE_SPEC.md` | Document 27 (Research Acquisition & Legal Intelligence: twelve acquisition channels, three separated pipelines, expanded manifest, independent training approval, A–E classification, research partnerships, legal-context registry — **OD-45-style owner confirmation 27 Nov 2026**). Part of the frozen baseline; not a signed Creator decision and no new top-level system. |
| 2 | `IAM_HUMAN_BEHAVIOUR_INTELLIGENCE_SPEC.md` | Document 26 — **HBI Master Specification v2.0** (38 modules in six divisions, 13 technical engines, eight advanced capabilities, expanded evolution/developmental/cultural/civilisational/crisis/leadership/trust/collective/resilience scope, historical chronology, full schemas/APIs/governance/testing — extends Docs 17/24/14; **OD-45 CONFIRMED 26 November 2026**). Part of the frozen baseline; does not change any earlier decision or system count. |
| 2 | `IAM_VOICE_AND_HEARING_SYSTEM_SPEC.md` | Document 30 — **Voice & Hearing System** (60 capabilities in seven review categories, 12-component architecture) — **CONFIRMED** under **OD-50** (27 November 2026) as capability scope only. Companion to Doc 04 and Doc 12 (OD-28); no implementation claim, no new top-level system, and no change to the system count or any earlier decision. |
| 2 | `IAM_BROWSER_INTELLIGENCE_MASTER_SPEC.md` | Document 29 — **Browser Intelligence & Web Operations Master Specification** (BIWOS + TIPS + Browser Security Gateway + Web Knowledge Integration as four logical components, not four deployments; browser API, permission matrix, Tor/onion privacy, adversarial QA, eight implementation phases — extends Docs 11/14/15; **OD-49 CONFIRMED 27 November 2026**). Part of the frozen baseline; architecture frozen at design level, **not** an implementation claim. |
| 2 | `IAM_BROWSER_PHASE1_IMPLEMENTATION_PLAN.md` | Document 29a — **Phase 1 implementation plan** for Doc 29 (evidence baseline, seven work packages, ARQ task queue, task/evidence/attribution contract, opt-in live smoke test, exit checklist). Planning document only; no implementation or migration is claimed. |
| 2 | `IAM_MULTI_MODEL_INTELLIGENCE_GOVERNANCE_SPEC.md` | Document 31 — **Multi-Model Intelligence** (repository audit + governance gate: encrypted backend provider-key vault, provider/key isolation, fail-closed usage accounting, bounded parallel delegation) — **CONFIRMED** under **OD-51** (27 November 2026) for clauses §4.1–§4.4 and the starting bounds; §4.5 paid NVIDIA usage explicitly **not authorised**. Companion to Docs 23/23-A; no new top-level system, no implementation claim, no change to identity/primary model/LiteLLM/single-sphere frontend. |
| 2 | `IAM_UNIVERSAL_MODEL_PROVIDER_ORCHESTRATION_SPEC.md` | Document 32 — **Universal Model Provider & Intelligence Orchestration System** — **CONFIRMED** under **OD-52** (27 November 2026): dual discovery, live registry, one-key runtime registration, availability monitoring, capability-based sub-agent assignment and bounded parallel delegation. Free models only; paid endpoints not authorised. No new top-level system or frontend route; no change to identity, primary model, LiteLLM gateway or protected core. |
| 3 | `sdk/` | SDK scaffolds: TypeScript, Python, CLI, shared protocol |
| 2 | `IAM_OPEN_SPECS_RESOLVED.md` | Resolved specs A–G |
| 2 | `IAM_COMPATIBILITY_MATRIX.md` | ARM64/x86-64 component matrix (OD-22) |
| 2 | `IAM_DATABASE_DESIGN.md`, `IAM_API_CONTRACTS.md`, `IAM_SECURITY_AND_INTERNET_POLICY.md` | Technical specifications |

**Note:** Documents 17–21 and 23, the OD-39/OD-40 specifications, the OD-41 parent architecture and implementation plan, and OD-33–OD-41 are **CONFIRMED** and part of the frozen baseline (owner confirmation 25 November 2026). They extend existing systems and do not alter any prior decision, including OD-08 (ARQ queue runtime). OD-38 locks the foundation-model set; OD-39 governs resources; OD-40 governs model development; OD-41 freezes autonomous distributed research requirements and implementation sequence. `IAM_IMPLEMENTATION_TECHNOLOGY_ADDENDUM.md` governs implementation language only — it does not change any decision or any mandated technology (Next.js/TypeScript, Python/FastAPI, ARQ). OD-42 (Creator channels), OD-43 (human behaviour and equality) and OD-44 (financial intelligence) are **CONFIRMED**; Docs 24–25 are part of the frozen baseline and do not alter any earlier decision, including OD-04/OD-25 financial authority. Document 26 (`IAM_HUMAN_BEHAVIOUR_INTELLIGENCE_SPEC.md`) is **CONFIRMED** under OD-45 (26 November 2026) and part of the frozen baseline; it establishes 38 modules in six divisions + 13 technical engines inside existing systems, does not create a sixteenth top-level system, and does not change any earlier decision. It supersedes its own v1.0 draft. Document 23-A (`IAM_PRIMARY_MODEL_UNIFICATION_SPEC.md`, OD-46) is **CONFIRMED** and part of the frozen baseline; it supersedes only OD-38 §1/§3 on local-model selection. Owner-directed reopening 27 Nov 2026: **Qwen2.5-3B (`local-qwen-3b`) is the shared primary**; the 26 Nov Qwen2.5-Coder 3B choice is superseded and the coder remains an optional secondary. All other OD-38 provisions remain authoritative. Document 29 (`IAM_BROWSER_INTELLIGENCE_MASTER_SPEC.md`) is **CONFIRMED** under OD-49 (27 November 2026) and part of the frozen baseline; it establishes BIWOS and TIPS as core browser capabilities organised into four logical components inside existing systems, does not create a new top-level system, and is **not** an implementation claim. OD-48 is **CONFIRMED** (27 November 2026) and part of the frozen baseline; proposed OD-47 is **CONFIRMED** by explicit owner instruction (27 November 2026) and part of the frozen baseline; this is owner confirmation, not a signed Creator decision, and it authorises no OD-03 protected-core action. Document 30 (`IAM_VOICE_AND_HEARING_SYSTEM_SPEC.md`) is **CONFIRMED** under OD-50 (27 November 2026) and part of the frozen baseline; it freezes the Voice & Hearing System capability scope (60 capabilities, 12 components) without creating a new top-level system and is **not** an implementation claim. Document 31 (`IAM_MULTI_MODEL_INTELLIGENCE_GOVERNANCE_SPEC.md`) is **CONFIRMED** under OD-51 (27 November 2026) for clauses §4.1–§4.4 and the parallel-delegation starting bounds; §4.5 paid NVIDIA usage is **not authorised**. It creates no new top-level system. Document 32 (`IAM_UNIVERSAL_MODEL_PROVIDER_ORCHESTRATION_SPEC.md`) is **CONFIRMED** under OD-52 (27 November 2026) for the free-model provider architecture; paid endpoints are explicitly not authorised. The register now holds 52 decisions.

## Superseded documents (historical — do not use as source of truth)

These were early derived drafts. They are retained for history but **superseded** by the documents above:

- `MASTER_SPECIFICATION.md` → superseded by `IAM_FINAL_CONSOLIDATION.md` + `IAM_MASTER_ARCHITECTURE.md`
- `IAM_MASTER_ARCHITECTURE.md` → superseded by `canonical/IAM_DOC_01` + `IAM_FINAL_CONSOLIDATION.md`
- `IAM_INTELLIGENCE_EVOLUTION_SPEC.md` → superseded by `canonical/IAM_DOC_02`
- `IAM_INTERNET_AUTONOMY_ECOSYSTEM_SPEC.md` → superseded by `canonical/IAM_DOC_03`
- `IAM_UI_GLOBAL_ACCESS_SPEC.md` → superseded by `canonical/IAM_DOC_04`
- `IAM_ARCHITECTURE_GAP_ANALYSIS.md`, `IAM_DISTRIBUTED_GAP_ANALYSIS.md` → superseded by `IAM_FINAL_CONSOLIDATION.md`

## Naming note

"AURA" is the engineering codename only. The system's permanent identity is **IAM — Intellectual Artificial Mainbrain**. "Marlow" refers only to the supplied HTML file name; the visual interface is IAM's.

---

## Repository map (navigation supplement — not an architecture decision)

**Status:** Agent navigation aid, appended 27 November 2026. It does not add,
amend or reinterpret any owner decision. The source-of-truth tables above remain
authoritative. Generated details live in `tools/rkie/index/file-index.json`.

### Top-level layout

| Path | Contents | Search first with |
|------|----------|-------------------|
| `canonical/` | Frozen source documents 01–04 | `-Mode docs` |
| Root `IAM_*.md`, `MASTER_SPECIFICATION.md` | 61 specification / analysis documents; see authority table above | `-Mode docs` |
| `backend/app/api/routes/` | ~75 FastAPI route modules (API surface) | `-Mode api` |
| `backend/app/services/` | ~90 service modules, incl. `ai_research/`, `hbi/`, `skillforge/`, `skillruntime/`, `workspaces/` | `-Mode content -Scope backend` |
| `backend/app/models/` | SQLAlchemy ORM models | `-Mode db` |
| `backend/app/db/migrations/` | 001–031 SQL + Alembic `0001_initial.py` | `-Mode db` |
| `backend/app/core/` | Config, database, auth policy, rate limit, secrets | `-Mode content -Scope backend/app/core` |
| `backend/app/orchestration/`, `backend/app/workers/` | LangGraph autonomy loop, ARQ workers | `-Mode content -Scope backend` |
| `backend/tests/`, `tests/` | Unit, integration and Level 1–5 acceptance suites | `-Mode tests` |
| `frontend/` | Next.js/TypeScript UI; has its own generated `AGENTS.md` | `-Mode content -Scope frontend` |
| `sdk/` | TypeScript, Python, CLI scaffolds + `PROTOCOL.md` | `-Mode content -Scope sdk` |
| `infra/` | LiteLLM config, Postgres init, gateway, CI/branch helpers | `-Mode content -Scope infra` |
| `iam/skills/` | On-disk skill package store (runtime-managed) | `-Mode files -Scope iam` |
| `research/` | Colab notebook + MCP notes | `-Mode files -Scope research` |
| `scripts/` | Docker build, model key, Creator signer helpers | `-Mode files -Scope scripts` |
| `tools/rkie/` | Local search toolkit and generated file index | `-Mode files -Scope tools` |

Dominant implementation language is Python (≈422 `.py` files); TypeScript/React
is a thin frontend and SDK layer. Deployment is Docker Compose.

### Implementation → authority quick map

| Subsystem | Representative files | Authoritative spec / decision |
|-----------|----------------------|-------------------------------|
| Model routing, selection, inference | `backend/app/api/routes/modelrouter.py`, `backend/app/services/intel_router_service.py`, `model_inference.py`, `serving_model.py`, `infra/litellm/config.yaml` | `IAM_FOUNDATION_MODEL_AND_INTELLIGENCE_SPEC.md`, `IAM_PRIMARY_MODEL_UNIFICATION_SPEC.md` (OD-38, OD-46) |
| Human behaviour intelligence | `backend/app/services/hbi/`, `backend/app/api/routes/hbi.py`, `backend/app/models/hbi.py` | `IAM_HUMAN_BEHAVIOUR_INTELLIGENCE_SPEC.md` (OD-45) |
| Autonomous research / development | `backend/app/services/ai_research/`, `backend/app/api/routes/development.py` | `IAM_INDEPENDENT_AI_RESEARCH_DEVELOPMENT_AND_EVOLUTION_ARCHITECTURE.md`, `IAM_AI_RESEARCH_IMPLEMENTATION_PLAN.md` (OD-41) |
| Skills | `backend/app/services/skillforge/`, `skillruntime/`, `iam/skills/` | `IAM_SKILL_FORGE_SPEC.md`, `IAM_SKILL_RUNTIME_SPEC.md` |
| Workspace / white-hat | `backend/app/services/workspaces/`, `whitehat_labs.py`, `whitehat_policy.py` | `IAM_WHITEHAT_AND_WORKSPACE.md` |
| Finance, ledger, banking, trading | `backend/app/services/financial_intelligence/`, `ledger_service.py`, `models/financial_intelligence.py` | `IAM_FINANCIAL_INTELLIGENCE_AND_ECONOMIC_INDEPENDENCE_SPEC.md` (OD-44) |
| Memory, knowledge, world model | `backend/app/services/memory_service.py`, `worldmodel_service.py`, `reflection_service.py`, `api/routes/knowledge.py` | `IAM_DATABASE_DESIGN.md`, `IAM_FINAL_CONSOLIDATION.md` |
| Auth, Creator authority, MFA | `backend/app/api/middleware/auth_middleware.py`, `core/auth_policy.py`, `routes/ownerauth.py`, `routes/creatorapproval.py` | `IAM_API_AUTH_SPEC.md`, `IAM_CREATOR_APPROVAL_SPEC.md` |
| Frontend | `frontend/app/`, `frontend/components/iam/`, `frontend/lib/api.ts` | `IAM_FRONTEND_IMPLEMENTATION.md`, `canonical/IAM_DOC_04` |
| Voice and media | `backend/app/services/voice_service.py`, `backend/app/api/routes/voice.py` | `IAM_VOICE_AND_HEARING_SYSTEM_SPEC.md`, `IAM_MEDIA_AND_RESEARCH.md`, `IAM_API_CONTRACTS.md`, Doc 12 (OD-28) |
| SDK / protocol | `sdk/typescript/`, `sdk/python/`, `sdk/cli/`, `sdk/PROTOCOL.md` | `IAM_DEVELOPER_SDK_AND_CLI_SPEC.md` (OD-29) |
| IP & Legal Intelligence (IPLCI) | `backend/app/services/iplci/`, `backend/app/models/ip_legal.py`, `api/routes/iplci.py`, `scripts/iplci_activate_policy.py` | `IAM_IP_AND_LEGAL_INTELLIGENCE_MASTER_SPEC.md` (Doc 28, OD-48); engineering→counsel handoff in `IAM_IPLCI_LEGAL_VALIDATION_RUNBOOK.md` and `tools/rkie/notes/iplci-legal-validation-outstanding.md` |

This mapping is declarative and editable in
`tools/rkie/config/architecture-links.json`; regenerate the index with
`./tools/rkie/Update-Index.ps1` after editing it.

### Existing systems — do not duplicate

Repository search is **separate** from IAM's runtime systems. Before adding any
search, memory or knowledge code, inspect:

- `backend/app/services/search_service.py` — external web search (Brave, Google, Wikipedia fallback).
- `backend/app/services/memory_service.py` — pgvector semantic recall + ILIKE fallback.
- `backend/app/services/research_service.py` — search/browse/extract/verify pipeline.
- `backend/app/services/hbi/knowledge.py`, `hbi/hkg.py` — governed knowledge and historical knowledge graph.
- `backend/app/services/worldmodel_service.py`, `web_knowledge_service.py`, `reflection_service.py`.
- `backend/app/services/ai_research/memory.py` — failed-experiment memory.

None of these index the repository itself; that gap is what `tools/rkie/` fills.

### Local search toolkit

```powershell
./tools/rkie/Search-IAMRepo.ps1 -Query modelrouter -Mode files
./tools/rkie/Search-IAMRepo.ps1 -Query "OD-46" -Mode docs -Json
./tools/rkie/Search-IAMRepo.ps1 -Query "IntelligenceRouter" -Mode symbols
./tools/rkie/Update-Index.ps1
```

`tools/rkie/README.md` documents all modes, switches, the standard investigation
procedure and security rules. The root `AGENTS.md` is the agent-facing contract.
`tools/rkie/RKIE_CAPABILITY_AUDIT.md` maps the frozen 26-domain RKIE target scope
to evidence in this working tree and lists the prioritised implementation backlog.

### Why local search is required

GitHub code search indexes contents and splits on punctuation, so a file named
`modelrouter.py` containing `model-router` / `model router` is not found by the
token `modelrouter`. GitHub also cannot see uncommitted files. Local filename
and content search address both failures without any external index or service.

### Pending proposals (navigation only — not architecture decisions)

Appended 27 November 2026. These entries provide navigation to proposals that
are **not** part of the frozen baseline. They do not amend, reinterpret or add
to the authority tables or the Owner Decision Register.

| Path | Status |
|------|--------|
| `IAM_IICS_GAP_CLOSURE_ADDENDUM.md` | Proposed overlay: nine IICS gap closures mapped to existing systems. Navigation only; not part of the frozen baseline, no owner decision, no new top-level system or queue. IICS overlay implemented and wired in `backend/app/services/iics/` (egress, permissions, ledger, source registry, QA, Creator email, strategy, scheduler, media, threat intel, site policy, tool registry); §7 records status. |
| `IAM_WEB3_AND_UMBREL_NODE_INTEGRATION_SPEC.md` | Proposed **Document 35 / OD-55** — Web3 (thirdweb, free-only) and three independent self-hosted Bitcoin/Lightning node adapters. **Awaiting signed owner decision — not part of the frozen baseline.** Renumbered: OD-50/Doc 30 = Voice & Hearing, OD-53/Doc 33 = Financial Intelligence Amendment A, OD-54/Doc 34 = Live Information proposal. Plan: `IAM_WEB3_AND_NODE_INTEGRATION_PLAN.md`; sign-off: `IAM_OD55_SIGNOFF_SHEET.md`; activation: `IAM_WEB3_ACTIVATION_RUNBOOK.md`. Research/prepare code exists behind default-off flags; no execution, paid tier or mainnet value movement is authorised by this navigation entry. |
| `IAM_LIVE_INFORMATION_AND_WEB_INTELLIGENCE_SPEC.md` | Proposed **Document 34 / OD-54** — always-on Web Access and Live Information Policy, deterministic triggers, conditional browser escalation, claim labels/corroboration, free-first provider management and bounded research cache/monitoring. **Awaiting signed owner decision — not part of the frozen baseline.** Numbered 34/OD-54 because Doc 32/OD-52 and Doc 33/OD-53 were assigned to other decisions. Addendum to Doc 29/OD-49; sign-off: `IAM_OD54_SIGNOFF_SHEET.md`; request: `scripts/creator_request_od54.py`. Behavioural reference implementation exists; no new top-level system, identity or model is claimed. |


