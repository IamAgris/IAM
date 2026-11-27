# IAM — Architecture Completion Audit (Stage 1)

**Date:** 27 November 2026  
**Scope:** Repository `D:\AI\project-aura`, branch `testing`, current working tree  
**Status:** Read-only audit. No specification, source, configuration or index file was changed by this audit.  
**Purpose:** Compare the proposed 16-domain completion scope against what IAM actually contains, before any new specification is written.

> This document is an **audit and navigation aid**. It does not amend `ARCHITECTURE_INDEX.md`,
> `IAM_FINAL_CONSOLIDATION.md`, `IAM_OWNER_DECISIONS.md` or any OD decision. Where implementation
> and specification disagree, the specification wins for *intent* and the source wins for
> *what currently runs*; the disagreement is recorded here as a gap.

---

## 1. Executive verdict

**The correct next step is completion and verification of what already exists — not the creation of ten new specifications.**

The repository is not a blank slate and is not missing most of the capabilities in the proposed scope. It contains a frozen 16-system architecture (canonical Document 01, systems A–P), 49 locked owner decisions (OD-01…OD-50; OD-47 remains proposed), ~601 live API paths, ~26,000 Python statements, and unit/acceptance coverage across all five maturity levels. All 26 domains of the separate RKIE target scope already have *some* implementation or artefact.

The dominant problem is the same one the user identified: **systems exist but are not consistently connected, enforced, or verified.**

Four findings are decisive:

1. **The 16 proposed domains are largely a re-description of the frozen 16 canonical systems (A–P) and the 26-domain RKIE scope.** Freezing them requires no new architecture decision; it requires a crosswalk so nobody builds a second copy of an existing system.
2. **Live gates are mostly green, but not all.** Ruff, migrations and test coverage pass. OpenAPI drift, one IPLCI test and the RKIE index/freshness checks currently fail or are stale — all in uncommitted work.
3. **Several critical assurances are documentation claims rather than executable evidence**: disaster recovery has no backup/restore implementation, the Aegis injection detector is not called from the chat/inference path, post-deploy monitoring is disabled by default, and L1–L5 acceptance suites are manual-only in CI.
4. **The "one unified intelligence" requirement is not yet met at runtime.** There is a genuine shared spine — one middleware chain in `main.py`, one model resolver in `model_inference.py`, one durable LangGraph loop, one durable audit/event stream and a shared `iam_context` assembler. But that graph's cognitive nodes are shallow and it never dispatches the research, HBI, finance, skills or workspace services. The result is *one entry point plus many independent domain modules*, which is exactly the risk identified in the brief.

A capability must not be described as complete because its specification, code or historical pass-claim exists. This audit uses the maturity ladder: **0 not defined → 1 specified → 2 implemented → 3 integrated → 4 verified**.

---

## 2. Working-tree caveat (mandatory)

| Measure | Value |
|---|---|
| Git status entries | **85** modified/untracked |
| Tracked files changed | **50** files, **+4,374 / −1,167** lines |
| Deleted legacy migrations | 14 (renamed to 032–046 in the working tree) |
| Untracked new subsystems | IPLCI route/service/models, voice spec, browser spec, HBI research ecosystem, LM-eval/post-deploy/eval-sets |
| Branch | `testing` (HEAD `34d5177`) |

Documented acceptance results dated 25 November 2026 describe an earlier tree. Findings below are from the **current** tree and from gates run during this audit. No conclusion here should be transferred to `origin/main` without a separate audit.

---

## 3. Live gate results (executed during this audit)

| Gate | Command | Result |
|---|---|---|
| Static analysis | `python -m ruff check backend` | **PASS** — all checks passed |
| Migration contract | `python tools/api/check_migrations.py` | **PASS** — 46 files / 46 manifest entries / 0 duplicate prefixes |
| OpenAPI contract | `python tools/api/print_openapi.py --check` | **FAIL (drift)** — live **601 paths / 375 schemas** vs snapshot **589 / 365**; 12 missing `/api/v1/iplci/*` paths, +10 schemas |
| Backend unit tests | `python -m pytest backend/tests -q --cov=app --cov-fail-under=60` | **1 failed, 550 passed** in 19.2 s; coverage **64.15%** (gate 60% met) |
| Failing test | `test_iplci.py::IPLCIPhase1Tests::test_status_declares_phase_and_scope` | `AssertionError: 2 != 1` — service reports phase 2, test expects phase 1 |
| RKIE smoke suite | `./tools/rkie/tests/Test-RKIE.ps1` | **19 passed, 1 failed** — `incremental index: no changes on repeat run` (expected 0, got 1) |
| RKIE index freshness | `./tools/rkie/Check-IndexFreshness.ps1` | **STALE** — 9 changed, 4 new files; base commit matches HEAD |
| Doc consistency | `python audit_architecture.py` | Hygiene only: stale project names (historical), stale "32 decisions" claim in an audit report, wildcard broken-ref false positives, historical phase claims |

**Interpretation:** the failing IPLCI test and OpenAPI drift are caused by the same uncommitted subsystem. They are the highest-confidence, lowest-cost fixes and should be resolved before any new specification work.

---

## 4. Scope crosswalk: proposed 16 domains ↔ frozen baseline

The canonical systems are A–P (Document 01 §3). The RKIE scope has 26 domains across six layers. The proposed 16 domains map as follows; **none of these rows authorises a new top-level system**.

| # | Proposed domain | Canonical system(s) | RKIE domain(s) | Relationship |
|---|---|---|---|---|
| 1 | Identity and Core Architecture | A Identity & Constitution | 7, 9, 23 | Existing — UlID genesis, constitution, governance boundary |
| 2 | Technical Infrastructure | I Digital Workspace, N Infrastructure & Resilience | 16, 17, 18, 22 | Existing, partially stubbed |
| 3 | Cognitive Intelligence | B Intelligence & Reasoning, P Evaluation & Research | 2, 3, 11, 25 | Partial — lifecycle exists, metacognition does not |
| 4 | Memory and Knowledge | D Memory & Knowledge | 6, 8, 10 | Partial — flat memory types; HBI adds knowledge governance |
| 5 | Perception and Multimodal | J Multimodal Communication | 13 (adjacent) | Partial — text/image/video/browser; no OCR/document/sensor |
| 6 | Integration and Orchestration | B, E, F cross-cutting | 3, 18, 20, 25 | Partial — LangGraph loop + event stream; no module contract registry |
| 7 | Autonomy and Execution | E Autonomy & Goal Management | 25 | Existing (unit-tested); verification is status-based |
| 8 | Specialist Agents and Distributed Intelligence | C Model Routing, G External AI Network | 26, 16 | Partial — signed P2P + trust; live multi-node untested |
| 9 | Self-Development and Model Evolution | C, H Learning & Self-Development | 21, 24, 25 | Existing gates; eval set is 5 items |
| 10 | Security, Trust and Governance | M Governance & Security | 14, 19 | Existing policy; enforcement gaps (see §6) |
| 11 | Validation and Quality Assurance | P Evaluation & Research | 13, 15, 20 | Partial — CI core exists, acceptance manual |
| 12 | Reliability and Operational Continuity | N Infrastructure & Resilience | 20, 22, 23 | Partial — checkpointing real, backup/restore reporting-only |
| 13 | Human Interaction and Social Intelligence | J, O Global Access | 8, 13 | Partial — HBI is substantial; UI is single-session/English |
| 14 | Research and Knowledge Discovery | P, F Internet & Digital Interaction | 6, 8, 9 | Partial — real research pipeline; Colab/MCP unexecuted |
| 15 | Financial and Economic Intelligence | K Economic & Financial, L Ecosystem | 22 (adjacent) | Partial — ledger/trading real; no SDK/UI/provider config |
| 16 | Lifecycle, Compliance and Sustainability | M, N, L | 16, 19, 21, 23, 26 | Partial — specs + CI, no infra drift check or SOPS artefacts |

**Conclusion:** freezing the 16 domains is a *mapping decision*, not a request for 16 new builds. The existing `ARCHITECTURE_INDEX.md` remains the source of truth for intent.

---

## 5. Domain-by-domain evidence summary

Statuses: **Existing** = functional with evidence; **Partial** = real code with gaps; **Spec-only** = documented but not built; **Missing** = no implementation found.

| # | Domain | Status | Representative evidence | Principal gap |
|---|---|---|---|---|
| 1 | Identity and Core Architecture | **Existing** | `models/identity.py`, `services/identity_service.py`, `routes/identity.py`, genesis + constitution in `main.py` | Identity continuity across *unattended* machine migration not exercised |
| 2 | Technical Infrastructure | **Partial** | `docker-compose.yml` (7 services), `infra/litellm/config.yaml`, `core/config.py`, `core/secrets.py` | `infra/postgres/init/001_initial_schema.sql` is 8 lines (no tables); `infra/gateway/nginx.conf` is not mounted; Cloudflare is docs-only |
| 3 | Cognitive Intelligence | **Partial** | `orchestration/autonomy_graph.py` (11-node durable graph), `services/reflection_service.py`, `hbi/causal.py`, `hbi/temporal.py`, `hbi/uncertainty.py` | Graph `reason()` returns a fixed string, `plan()` a literal `["prepare","execute","verify"]`, `verify()` a status-derived string; no metacognition, self-model, counterfactual, belief manager, attention manager, continual-learning or knowledge-transfer engine found in `backend/app` |
| 4 | Memory and Knowledge | **Partial** | `services/memory_service.py` (pgvector + ILIKE fallback), `models/memory.py`, `hbi/knowledge.py`, `hbi/hkg.py`, `worldmodel_service.py` | Six flat memory types, not working/episodic/semantic/procedural/relationship/self/strategic; no consolidation, duplicate detection or expiry sweeper |
| 5 | Perception and Multimodal | **Partial** | `voice_service.py`, `vision_service.py`, `browser_service.py`, `computer_use.py`, `frontend/.../interface.tsx` | `objects`/`text_ocr` hard-coded empty; no document/PDF/screen/sensor input; UI never calls `/api/v1/voice/*`; STT fixed to `en-US` |
| 6 | Integration and Orchestration | **Partial** | `autonomy_graph.py`, `services/event_stream.py`, `api/routes/events.py`, `routes/tools.py`, `tool_authorization.py`, `services/delegation.py` | Graph never dispatches research/HBI/finance/skills/workspace services; goals/tasks/scheduling are CRUD-only; no standard module contract or central capability-discovery registry; `integration_registry` has no service or route |
| 7 | Autonomy and Execution | **Partial** | `workers/autonomy_worker.py`, `models/autonomy.py`, `tool_authorization.py`, `orchestration/autonomy_graph.py`, Level 2 acceptance | `execute()` only writes a `DecisionRecord` and advances a task `pending → in_progress`; `retrieve_memory`/`update_memory` are explicit no-ops; linear edges give no failure/retry branch; `verify()` accepts a status string, not evidence |
| 8 | Specialist Agents and Distributed Intelligence | **Partial** | `p2p_transport.py`, `routes/p2p.py`, `ai_communication.py`, `ainetwork_service.py`, `attestation_service.py`, `tests/p2p_acceptance.py` | HMAC not Ed25519; in-memory transport state; no P2P in Compose or either SDK; live multi-node untested |
| 9 | Self-Development and Model Evolution | **Partial (strong core)** | `ai_research/release_gate.py`, `registry.py`, `lm_eval.py`, `post_deploy.py`, `serving_model.py`, `tests/level3_acceptance.py` | Only trusted eval set is `eval_sets/basic.jsonl` — 5 exact-match questions; no security/reasoning/coding benchmark gate in CI |
| 10 | Security, Trust and Governance | **Partial** | `middleware/auth_middleware.py`, `core/auth_policy.py`, `governance_service.py`, `creatorapproval_service.py` (Ed25519), `security_policy.py`, `core/secrets.py` | Aegis not called from inference path; `AUTH_ENABLED=false` bypasses all auth; SOPS is doc-only; no repository-wide emergency shutdown |
| 11 | Validation and Quality Assurance | **Partial** | 61 test modules / 571 test definitions; CI gates; HBI 10-check acceptance; `tests/level1..5_acceptance.py` | L1–L5 manual-only in CI; no release-gate/post-deploy/preflight invocations in CI; historical pass claims not reproducible in current tree |
| 12 | Reliability and Operational Continuity | **Partial** | `AsyncSqliteSaver` checkpointing, `free_sandboxes/manager.py` circuit breaker, `ai_research/recovery.py`, `routes/ops.py`, `services/irwm.py` | `resilience_service.record_backup_verification()` only inserts a row — no backup or restore code exists; `irwm.admit()/release()` never called by chat or inference; P2P, IRWM and research-lifecycle state are in-memory; OD-06 RPO/RTO unverified |
| 13 | Human Interaction and Social Intelligence | **Partial** | `hbi/` (38 modules, 13 engines), `socialpresence_service.py`, `tone_service.py`, `human_assistance.py`, `routes/hbi.py` | UI has one `localStorage` session, hard-coded English, orphaned 25-link sidebar; no channel UI |
| 14 | Research and Knowledge Discovery | **Partial** | `search_service.py`, `research_service.py`, `web_knowledge_service.py`, `tools/rkie/`, `tests/level2_acceptance.py` | Colab notebook unexecuted, MCP bridge tested against a stub; no FTS5/fuzzy/hybrid ranking deployed |
| 15 | Financial and Economic Intelligence | **Partial** | `ledger_service.py`, `financial_intelligence/`, `trading/paper.py`, `economy.py`, Level 5 acceptance | 26 KB financial frontend page is underscore-prefixed and unrouted; no SDK finance methods or provider config |
| 16 | Lifecycle, Compliance and Sustainability | **Partial** | `.github/workflows/*` (7), `requirements.lock.txt`, `supply-chain.yml`, `iam_context.py`, `irwm.py`, `legal_service.py`, `services/iplci/` | OD-48 was confirmed by the owner on 27 November 2026 and IPLCI is now part of the frozen baseline; `legal_service.authorise()` now verifies signed authority (P0-3); remaining gaps: no infra drift check in CI, no git tags, post-deploy monitoring off by default |

---

## 6. Confirmed cross-cutting gaps (highest confidence)

These are contradictions between authoritative intent and the current tree, confirmed by file reads or gate execution.

| # | Gap | Evidence | Severity |
|---|---|---|---|
| G1 | OpenAPI snapshot drift | 12 live `/api/v1/iplci/*` paths and +10 schemas absent from `IAM_OPENAPI.json` | **Blocking** |
| G2 | Failing IPLCI test | `test_iplci.py:35` expects phase 1; `services/iplci/service.py:31` returns phase 2 | **Blocking** |
| G3 | RKIE index stale + 1 smoke failure | `Check-IndexFreshness.ps1` reports 9 changed / 4 new; `Test-RKIE.ps1` 19/20 | **Blocking** |
| G4 | No executable disaster recovery | No `pg_dump`/restore/backup job anywhere; `resilience_service` only records rows; OD-06 RPO 24h/RTO 4h | **Critical** |
| G5 | Prompt-injection defence not in inference path | `aegis.py` detection exposed via `routes/aegis.py` only; no call from `model_inference.py`/`models.py` | **Critical** |
| G6 | No general emergency shutdown | Only paper-trading stop exists (`financial_adapters.py:251`); HBI `safety_stop` is a label, not a switch | **Critical** |
| G7 | Verification accepts status strings | `autonomy_graph.verify()` marks `"verified_internal_transition"` from `status == "advanced"` | **Critical** |
| G8 | Evaluation suite is trivial | `ai_research/eval_sets/basic.jsonl` — 5 general-knowledge questions; no coding/safety/reasoning gates | **High** |
| G9 | Acceptance and release gates not in CI | L1–L5, `release_gate`, `lm_eval`, `post_deploy`, `deployment_preflight` absent from PR gates | **High** |
| G10 | Post-deploy monitoring disabled | `POST_DEPLOY_MONITOR_ENABLED=false`, `POST_DEPLOY_AUTO_ROLLBACK_ENABLED=false` | **High** |
| G11 | Secret management intent not materialised | OD-07 SOPS: no `.sops.yaml` or encrypted artefacts; Compose ships placeholder credentials | **High** |
| G12 | Skill store empty | `iam/skills/{native,imported,pending,quarantine,archived}/` contain only `.gitkeep` | **Medium** |
| G13 | SDK CLI stubs and name mismatch | `cli/src/index.ts:114` login unimplemented; `:71` `dev init` prints but creates nothing; imports `@iam/sdk` while package is `@iamagris/sdk` | **Medium** |
| G14 | Frontend dead surface | `sidebar.tsx` orphaned; `_financial-intelligence/page.tsx` and `_freesandboxes/page.tsx` unrouted; `/tone` and `/ai-network` return 503 without `IAM_PROXY_TOKEN` | **Medium** |
| G15 | Infra stubs | `infra/postgres/init/001_initial_schema.sql` creates no tables; `infra/gateway/nginx.conf` not mounted; Cloudflare config docs-only | **Medium** |
| G16 | Cognitive lifecycle is shallow | `autonomy_graph.py:64-73` fixed `reason()`, `:83-91` literal `plan()`, `:170-176` status-based `verify()`, `:195-197` no-op `update_memory`, `:59-61` no-op `retrieve_memory`; `execute()` never dispatches a tool or domain service | **Critical** |
| G17 | Objectives are CRUD, not executable | `routes/goals.py`, `tasks.py`, `scheduling.py` are CRUD only; `autonomous_web_task_service.create()` ignores `schedule_at`; no worker executes decomposition or scheduled activity | **Critical** |
| G18 | Resource manager not on inference path | `services/irwm.py` is exposed through `api/routes/irwm.py` but `model_inference.py`/`models.py` never call `admit()`/`release()`; OD-39 is not enforced where it matters | **Critical** |
| G19 | Authority inconsistency | `creatorapproval_service.check_authorization()` is enforced for finance, delegation and model release, but `legal_service.authorise()` accepts any non-empty `creator_approval_reference` string | **Critical** |
| G20 | Governance/status mismatch — **RESOLVED** | Owner confirmed OD-48 on 27 November 2026; register, index, IPLCI spec and browser-spec cross-references updated. Retained here as the resolution record. | **Closed** |
| G21 | Durability holes | P2P transport state, IRWM state and `ai_research.lifecycle` platform records are in-memory; `serving_model.py` uses a temp filesystem store while release evidence may be in S3 | **High** |
| G22 | Schema tracks unreconciled | 46 numbered SQL migrations plus 2 Alembic revisions coexist; no code-level parity check against 236 ORM `__tablename__` declarations | **High** |
| G23 | Validation theatre | `development.py:213-224` `/test` only flips status to `"tested"`; `capability_service.assess_capability()` records caller-supplied proficiency; `hbi/modules.py` docstring says only modules 1–4 are functional while `IMPLEMENTED` lists all 38 | **High** |
| G24 | Default-off posture | Ollama, free sandboxes, skill runtime, workspaces, banking, blockchain, trading, prediction markets, gaming, investment, computer use, mobile agent and post-deploy auto-rollback are all disabled in `core/config.py`; most capability is gated and untested in a default deployment | **High** |
| G25 | No distributed tracing or real observability | `otel_exporter_otlp_endpoint` exists only in config; `/metrics` is three hand-built gauges; request IDs appear only in error bodies; no spans, alerting or dashboards | **Medium** |

---

## 7. What is genuinely complete enough to reuse (do not rebuild)

- Repository search and navigation: `tools/rkie/`, `ARCHITECTURE_INDEX.md`, `audit_architecture.py`.
- Runtime memory/knowledge: `services/memory_service.py`, `api/routes/knowledge.py`, `hbi/knowledge.py`, `hbi/hkg.py`, `worldmodel_service.py`, `web_knowledge_service.py`, `reflection_service.py`, `ai_research/memory.py`.
- External research: `services/search_service.py`, `research_service.py`, `browser_service.py`.
- Governance/security: `security_policy.py`, `cybersecurity/security_guard.py`, `whitehat_policy.py`, `governance_service.py`, `development_governance.py`, `core/secrets.py`, `source_identity.py`, `event_stream.py`, `tool_authorization.py`.
- Model lifecycle: `ai_research/{release_gate,registry,benchmarks,lm_eval,post_deploy,recovery,serving}.py`, `serving_model.py`.
- Resources: `services/irwm.py`, `adaptive_model_selector.py`, `free_sandboxes/manager.py`.
- Orchestration: `orchestration/autonomy_graph.py`, `workers/autonomy_worker.py`.

`tools/rkie/` must remain independent of the primary model (Qwen2.5:3B): indexing and verification stay deterministic; the model may call them through a shared interface.

---

## 8. Recommended stage-1 exit decision

**Do not open the ten-document specification work yet.** The audit shows that the binding constraint is *verification and enforcement*, not missing design.

Immediate P0 sequence (no new features):

1. Reconcile the uncommitted IPLCI work: fix `test_iplci.py` to the declared phase, regenerate `IAM_OPENAPI.json` from the live app, and resolve OD-48 status before treating IPLCI as frozen.
2. Run `tools/rkie/Update-Index.ps1`, fix the single failing incremental-index assertion, and re-run both RKIE gates.
3. Re-run the full pytest suite and require 551/551 green before any further merge.
4. **Wire the cognitive lifecycle before expanding it**: replace the no-op `retrieve_memory`/`update_memory` nodes and heuristic `reason`/`plan`/`verify` with real retrieval, model-backed reasoning, domain-service dispatch and evidence-backed verification; add failure/retry branches.
5. Wire `irwm.admit()/release()` into the actual chat/inference path so OD-39 is enforced, and make goals/tasks/scheduling executable rather than CRUD-only.
6. Make `legal_service.authorise()` verify signed Creator authority exactly as finance, delegation and model release do.
7. Implement an executable backup + verified restore drill for OD-06, then record the result.
8. Wire `aegis` analysis into the inference path with a fail-closed policy and test it adversarially; introduce a repository-wide emergency stop.
9. Convert the historical L1–L5 pass claims into a reproducible, CI-invoked acceptance run (the workflow already exists as `workflow_dispatch`) and add release-gate/post-deploy/preflight invocations.
10. Replace the 5-item eval set with domain benchmarks (reasoning, planning, coding, tool use, safety, security), and wire `release_gate`/`post_deploy` into a PR gate.
11. Reconcile the two schema tracks against the ORM models; add a code-level parity check.
12. Persist P2P/IRWM/research-lifecycle state and align `serving_model.py` with the configured durable artifact store.

Only after P0 is green should the six-pillar specification set be written — and then each document must be a **repository-accurate description of existing systems plus explicit gaps**, not a new design.

---

## 9. Audit limitations

- Live stack, GitHub Actions results, Docker deployment, real provider inference and multi-node P2P were not executed; "not evidenced" means absence of in-tree evidence, not proof of runtime failure.
- The five acceptance levels were not re-run; their pass figures are dated claims from `IAM_FINAL_CONSOLIDATION.md`.
- Counts reflect the heavily modified `testing` working tree and will change as uncommitted work lands.
- Proposed documentation files referenced in the user's scope are not present in this repository; this audit maps the scope to what exists rather than assuming those documents.

---

## 10. P0 execution record (27 November 2026)

This section records what was actually changed after the audit. It distinguishes code-level completion from live-stack proof.

| # | Workstream | Status | Evidence |
|---|---|---|---|
| 1 | Repair failing gates | **Closed** | OpenAPI 612/612 paths, 383/383 schemas OK; migrations 47/47 OK; ruff clean; **626 tests passed**, coverage 65.84%; RKIE smoke 20/20, index FRESH. The failing IPLCI test and drift were resolved in the working tree during the session. |
| 2 | Unified cognitive lifecycle | **Closed (code-level)** | `orchestration/autonomy_graph.py` rewritten: real `MemoryService` retrieval, model-backed `reason()` with honest offline fallback, allowlisted actionable `plan()`, `orchestration/dispatch.py` calling real IAM services, `TaskExecution`/`DecisionRecord` evidence, evidence-backed `verify()`, verified-only `update_memory()`, bounded `recover` branch. 13 integration tests in `backend/tests/test_autonomy_graph_integration.py`; graph compiles with 14 nodes. |
| 3 | Authority enforcement | **Closed** | `legal_service.authorise()` now calls `CreatorApprovalService.check_authorization()` for `legal.change_authorisation` targeted at the exact change, rejects mismatched references, and stores the verified authorization id. 4 tests in `backend/tests/test_legal_authority.py`. |
| 4 | Resource governance | **Closed** | `model_inference.py` admits every `chat()` and `stream()` request through IRWM before any provider call, refuses `queue`/`delegate`, releases in `finally`, and reports the decision in `iam_inference`. 5 tests in `backend/tests/test_irwm_inference_gate.py`; existing inference smoke still passes. |
| 5 | Inference security | **Closed** | `aegis.analyze_text()` inspects every message before routing; `InferenceBlocked` and `security_blocked` SSE event fail closed without echoing content. Default-on via `inference_aegis_enabled`. 5 tests in `backend/tests/test_inference_security_gate.py`. |
| 6 | Disaster recovery | **Closed (code-level)** | New `services/backup_service.py`: real `pg_dump`, SHA-256, `pg_restore --list` verification, isolated-only restore with production-DSN refusal, table-count verification, measured RPO/RTO, redacted audit events. `scripts/backup_restore_drill.py` for real drills. 5 tests in `backend/tests/test_backup_service.py`. **A live DR drill against Postgres has not been executed here.** |
| 7 | Evaluation | **Closed** | Five-domain manifest suite (reasoning, planning, tool use, safety, instruction following) with per-domain thresholds, dataset checksums, weighted overall score and `compare()` regression detection; wired as the self-improvement default while keeping the injected single-dataset driver available. 6 tests in `backend/tests/test_eval_suite.py`; legacy `test_lm_eval.py` still passes. |
| 8 | Continuous assurance | **Closed (automation added)** | `.github/workflows/continuous-assurance.yml`: deterministic assurance suites on schedule/manual, nightly isolated L1–L5 acceptance run with teardown. |
| 9 | IPLCI governance | **Closed — owner decision recorded** | Owner confirmed OD-48 on 27 November 2026 (option a). Updated `IAM_OWNER_DECISIONS.md` (49 locked decisions, new OD-48 entry), `ARCHITECTURE_INDEX.md` (IPLCI moved to authoritative table), `IAM_IP_AND_LEGAL_INTELLIGENCE_MASTER_SPEC.md` (status confirmed), `IAM_BROWSER_INTELLIGENCE_MASTER_SPEC.md` cross-references, and this audit. No implementation was removed or quarantined. |

**Not claimed at that point:** the live stack, a Postgres restore drill and CI execution had not yet been run. Section 11 records the subsequent operational proof.

---

## 11. Operational proof (executed against the live stack)

The running Docker Compose stack was used — no containers were rebuilt or replaced.

### 11.1 Level 1–5 acceptance (live HTTP API)

An admin-scoped credential is required: the frontend `user` key produces 403 on identity and governance endpoints. This was the cause of the first, failed acceptance run. After creating a uniquely named admin credential, all suites passed:

| Suite | Result |
|---|---|
| Level 1 — Operational | **14 passed, 0 failed** |
| Level 2 — Independent | **20 passed, 0 failed** |
| Level 3 — Self-developing | **13 passed, 0 failed** |
| Level 4 — Distributed | **20 passed, 0 failed** |
| Level 5 — Ecosystem | **13 passed, 0 failed** |

**CI fix:** both `.github/workflows/quality-gates.yml` and `.github/workflows/continuous-assurance.yml` previously exported the `user` key from `frontend/.env.local`. They now call the new `backend/scripts/bootstrap_acceptance_admin.py`, which creates a uniquely named admin credential and prints only the key to stdout for `IAM_API_KEY`.

### 11.2 Disaster recovery drill (real Postgres)

`scripts/backup_restore_drill.py` was executed against the live Postgres container through `BackupService` itself (`BACKUP_CONTAINER_SERVICE=postgres`), using a separate `iam_restore_drill` database:

| Evidence | Result |
|---|---|
| Backup | `iam-20261127T022712Z-drill`, 915,276-byte pg_dump custom archive |
| Integrity | SHA-256 `8c251633…02411a`; `pg_restore --list` read 980 catalog objects |
| Isolated restore | **245/245** public tables restored to the separate database |
| RPO | 0.0017 h (~6.1 s) against a 24 h target — **met** |
| RTO | 0.0013 h (~4.7 s) against a 4 h target — **met** |
| Audit | `backup.created`, `backup.verified`, `dr.restore_verified` rows written with redacted DSNs |

Two host-environment issues were found and fixed during the drill: Windows `Path('/tmp')` became `\tmp` inside the container (POSIX paths are now generated explicitly), and `sha256sum` escaped hashes of backslash-named files (hash parsing now strips the escape). `BackupService` gained container-execution support for pg_dump/pg_restore/psql/hash/stat; unit tests still pass in host mode.

### 11.3 Final gates after operational work

- **705 tests passed**, coverage **66.69%** (gate 60%)
- ruff clean; OpenAPI 653/653 paths, 407/407 schemas; migrations 51/51 with no duplicate prefixes

**Still not proven here:** GitHub Actions execution, real hosted-provider inference, multi-node P2P and ARM64 images. Live acceptance also remains manual/scheduled in CI until the updated workflows run on GitHub.

### 11.4 P2P, Aegis and signer acceptance (live)

- `tests/aegis_acceptance.py` — **14/14** passed after replacing its hard-coded credential with `IAM_API_KEY`.
- `tests/signer_acceptance.py` — **9/9** passed after the same fix.
- `tests/p2p_acceptance.py` — initially 4/9. Two real defects were corrected:
  1. The script hard-coded an `operator`-scope token; P2P HTTP routes require `admin`. It now reads `IAM_API_KEY`/`IAM_API_URL`. Hard-coded tokens were also removed from the Aegis and signer scripts (credential hygiene).
  2. The script used topics `knowledge`/`threat`, which the enforced white-hat allowlist rejects. Topics are now `research`/`finding`, matching `SHAREABLE_TOPICS`.
  - Final result: **9/9**, including signed envelopes, tamper detection, offline outbox and real two-peer WebSocket gossip. This proves two peers on one deployment, **not** two separate physical nodes.

### 11.5 Live defect found and fixed — Aegis over-blocking

During hosted-inference investigation the backend container became unhealthy. Live logs showed autonomous reasoning was failing with `InferenceBlocked: Aegis refused inference input (critical): self_escalation`. Cause: `_inspect_input()` inspected IAM's own trusted **system** prompt, whose safety sentence "Never grant yourself permissions" matched the detection signature. Inspection now skips `role == "system"` and still inspects user/tool content; a regression test was added (`test_inference_security_gate.py`, 6/6 passing).

### 11.6 Hosted-provider inference (live)

- `GET /api/v1/models/readiness` reports local Ollama as the active primary and NVIDIA as the only configured hosted provider.
- Direct service-level smoke through the real LiteLLM gateway (IRWM disabled for this isolated measurement only): **`nvidia-nemotron-3-nano` returned `READY`** in hosted mode. `qwen3.5-9b` returned **401** — the DashScope key field is present in `.env` but no usable key is configured inside LiteLLM, so that alias is not operational.
- API-level hosted calls are currently refused by IRWM (`503: another model is busy; request queued`), and an earlier hosted attempt coincided with a backend container death. The Aegis system-prompt defect found in the logs was fixed (§11.5) and the container was rebuilt; the IRWM `in_flight` state remains an open defect to investigate.

### 11.7 CI workflow validation

All eight workflow files parse as valid YAML and expose the expected jobs/triggers: `ci`, `codeql`, `continuous-assurance`, `openapi-drift`, `publish-sdk`, `quality-gates` (including `repo-intel` and `workflow-validation`), `rkie-tests`, `supply-chain`. Their commands were reproduced locally where applicable, but **no GitHub Actions run was executed** — that requires a push to `origin/testing`, which has not been authorised.

### 11.8 ARM64 image build (verified artifact)

`docker buildx build --platform linux/arm64` produced an OCI artifact at
`C:\Users\kagis\AppData\Local\Temp\opencode\iam-backend-arm64.tar` (440,350,720 bytes). Manifest inspection confirms
**`architecture: arm64`, `os: linux`, 10 layers**. No registry push was performed and the image was not run on ARM64 hardware — it is a build artifact, not a runtime test. The first attempt was killed at the 600 s tool limit; the retry with a longer allowance completed.

**Final status of the four originally unproven items:**

| Item | Result |
|---|---|
| GitHub Actions execution | YAML and commands validated locally; **not executed on GitHub** (no push authorised) |
| Hosted-provider inference | **Proven** — `nvidia-nemotron-3-nano` returned `READY`; `qwen3.5-9b` fails 401 (missing DashScope key in LiteLLM) |
| Multi-node P2P | **Two-peer WebSocket gossip proven** on one deployment; separate physical nodes not proven |
| ARM64 images | **Build verified** (`arm64/linux`, 10 layers); not run on ARM64 hardware |

Open defects found during this work: IRWM `in_flight` remains occupied during API-level hosted calls, and the backend container died once during the first hosted attempt (before the Aegis system-prompt fix and rebuild).

Final gate state after the four-item investigation: **805 tests passed**, coverage **67.35%**; ruff clean; OpenAPI 696/696 paths and 430/430 schemas; migrations 56/56 with no duplicate prefixes; RKIE smoke **20/20** and index **FRESH**. Two stale tests were corrected during this pass: `test_serving_model.py` assumed the pre-OD-46 local tag, and `test_adaptive_model_selector.py` transiently failed against a concurrently changing config. A new migration/model pair (`056_iics_foundation.sql`, `iics.py`) appeared during verification and was reconciled by the concurrent owner before the final run.
