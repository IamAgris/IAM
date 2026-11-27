# IAM — Documentation Inventory & Conflict Report

**Version:** 1.0 · 28 November 2026
**Repository:** `D:\AI\project-aura` · branch `testing` · HEAD `4025c5c`
**Classification:** Reference — **audit artefact**. Not authoritative. Amends no owner decision, specification, source file, configuration or index.
**Method:** Read-only inspection of every tracked and untracked Markdown file; direct reads of the authority documents; `git status`; `audit_architecture.py`; a full Markdown-link/path-reference scan; targeted source/evidence checks.
**Purpose:** First deliverable of the controlled documentation consolidation — an accurate inventory and conflict report **before** any document is rewritten.

---

## 0. Scope and working-tree caveat

| Measure | Value |
|---|---|
| Markdown files in scope | **125** (123 tracked + 2 untracked) |
| Working-tree entries | **92** modified/untracked |
| Markdown files changed in working tree | **7** — 5 modified, 2 untracked (listed in §3.12) |
| Branch | `testing`, tracking `origin/testing`, HEAD `4025c5c` |
| Files changed by this report | **1 new file only** (this report) |

**Working-tree rule:** all existing edits are user work. This report does not overwrite, restage, reformat, normalize line endings or delete any file. Several authority claims below are based on *uncommitted* verification notes; they are recorded as claims with their location, not promoted to verified fact.

Untracked notes: `tools/rkie/notes/llm-asm-benchmark-extension-plan.md`, `tools/rkie/notes/llm-asm-inference-research-2026-11-27.md`.

---

## 1. Executive summary

The repository already has a workable authority structure (`ARCHITECTURE_INDEX.md` → `IAM_FINAL_CONSOLIDATION.md` + `IAM_OWNER_DECISIONS.md` → `canonical/IAM_DOC_01…04` → numbered specs). The problem is not a missing master document. It is **authority drift**:

1. **Four different decision counts** are presented as current: 41, 49, 52 and 53 (plus a fifth, "51", inside the register itself).
2. **OD-56 has two owners**: Financial Intelligence Amendment A (locked) and Paid Hosted Model Access (proposed).
3. **The primary model has two truths**: `qwen2.5:3b` / `local-qwen-3b` is locked by OD-46, but two confirmed/frozen specifications still say the Coder model is primary.
4. **Completion is asserted and denied in the same authority document**: `IAM_FINAL_CONSOLIDATION.md` declares all five acceptance levels passed and, in its final line, says Levels 2–5 remain.
5. **A superseded document is still the declared parent of ~25 specifications** (`IAM_MASTER_ARCHITECTURE.md`), and the README still presents superseded drafts as working specifications.
6. **"Verified" is used for three different things**: independent tests, a successful API/status response, and a database row. The dated audit record `IAM_ARCHITECTURE_COMPLETION_AUDIT.md` documents concrete cases where status strings and caller-supplied values were treated as evidence; the working tree has since evolved in places, so each claim must be re-checked against current source before reuse.
7. **Numbers describing the repository are stale everywhere**: paths/schemas, migration counts, ORM tables, route modules, document counts and test totals each have 4–10 mutually incompatible values.
8. **Proposals are written in the language of frozen capability** in at least three places (IICS addendum, Web3 doc, paid-model doc), blurring PROPOSED and APPROVED.

No historical decision should be deleted to fix this. The fix is to make authority explicit, restate unique requirements once, and convert duplicated explanations into references.

---

## 2. Documentation authority — as it actually stands

### 2.1 Intended authority (declared)

| Tier | Document(s) | Declared status |
|---|---|---|
| Entry point | `ARCHITECTURE_INDEX.md` | AUTHORITATIVE; do not rewrite source-of-truth tables without owner confirmation |
| Priority 1 | `IAM_FINAL_CONSOLIDATION.md` | Master gap analysis, systems, completion levels, roadmap |
| Priority 1 | `IAM_OWNER_DECISIONS.md` | Locked OD-xx register |
| Priority 2 | `canonical/IAM_DOC_01…04` | Frozen supplied documents |
| Priority 2 | Numbered Docs 05–36 + technical specs | Frozen/confirmed specifications |
| Priority 3 | `sdk/`, tooling, notes | Implementation/reference material |

### 2.2 Actual authority problems

- `ARCHITECTURE_INDEX.md:13` says **52 locked decisions**; `:55` says "the register now holds 52 decisions". The register header (`IAM_OWNER_DECISIONS.md:3`, `:287`) says **53** (OD-01…OD-52 + OD-56). `IAM_FINAL_CONSOLIDATION.md:42`, `README.md:5` and `IAM_IMPLEMENTATION_TECHNOLOGY_ADDENDUM.md:60,102` say **41**. `IAM_ARCHITECTURE_COMPLETION_AUDIT.md:19,211` says **49**. `IAM_OWNER_DECISIONS.md:111` says **"ALL FIFTY-ONE DECISIONS LOCKED"**.
- `ARCHITECTURE_INDEX.md:61` says `MASTER_SPECIFICATION.md` is superseded by `IAM_FINAL_CONSOLIDATION.md` **+ `IAM_MASTER_ARCHITECTURE.md`**, while `:62` says `IAM_MASTER_ARCHITECTURE.md` is itself superseded by canonical Doc 01 + the consolidation. This is a circular/contradictory supersession chain.
- `AGENTS.md:22–25` and `ARCHITECTURE_INDEX.md:57–66` correctly mark seven documents as history, but **~25 other documents still declare `IAM_MASTER_ARCHITECTURE.md` as their `Parent:`**, and `README.md:219–225` still lists superseded drafts as derived working specifications.
- `IAM_ARCHITECTURE_AUDIT_REPORT.md` is a point-in-time audit at **26/32 decisions** whose verdict ("the frozen architecture claim is now TRUE", `:12,71`) is still written in the present tense. It is evidence, not authority.
- `IAM_ARCHITECTURE_COMPLETION_AUDIT.md:8–11` correctly disclaims authority; it is the most accurate *implementation-status* document in the tree, but it is not classified or linked as such in the index.

### 2.3 Orphan documents (substantive, not in the index authority table)

`IAM_AI_COMMUNICATION_COLLABORATION.md`, `IAM_DIGITAL_IDENTITY_UNIVERSAL_WEB_INTERACTION.md`, `IAM_ARTEX_INTEGRATION_SPEC.md`, `IAM_BROWSER_AND_GEO_BACKEND.md`, `IAM_API_AUTH_SPEC.md`, `IAM_CREATOR_APPROVAL_SPEC.md`, `IAM_CREATOR_SIGNER_SETUP.md`, `IAM_SKILL_FORGE_SPEC.md`, `IAM_SKILL_RUNTIME_SPEC.md`, `IAM_FRONTEND_IMPLEMENTATION.md`, `IAM_CI_AND_WORKERS.md`, `IAM_DEPLOYMENT_CONFIG.md`, `IAM_PRIVACY_AND_SECRETS.md`, `IAM_FREE_SANDBOXES.md`, `IAM_MEDIA_AND_RESEARCH.md`, `IAM_DATABASE_INTEGRATION_REPORT.md`, `IAM_EXTERNAL_MODULES_REVIEW.md`, `MODEL_PROVIDER_SETUP.md`.

Their presence is legitimate; their **authority parent is undeclared**. They must be classified and linked, not deleted.

---

## 3. Full documentation inventory (125 documents)

Classification vocabulary: **A** Authoritative · **S** Specification · **P** Implementation plan · **IS** Implementation status · **H** Historical · **O** Operational · **R** Reference · **D** Duplicate.
Lifecycle vocabulary: PROPOSED · APPROVED · SPECIFIED · IN DEVELOPMENT · IMPLEMENTED · VERIFIED · PRODUCTION · SUPERSEDED · HISTORICAL.
"Parent" is the parent declared in the document or the index — not an inference from content.

### 3.1 Authority and navigation

| Document | Cls | Lifecycle | Parent | Purpose / issue |
|---|---|---|---|---|
| `ARCHITECTURE_INDEX.md` | A | PRODUCTION | — | Single entry point, authority table, superseded list, repo map. Says 52 decisions (C01). |
| `AGENTS.md` | R | PRODUCTION | index | Agent search/investigation/verification contract; explicitly not an architecture spec. |
| `IAM_FINAL_CONSOLIDATION.md` | A | PRODUCTION | — | Master gap analysis, coverage matrix, L1–L5 framework, roadmap, verification log. Internally contradictory (C06, C10, C26); working-tree modified. |
| `IAM_OWNER_DECISIONS.md` | A | PRODUCTION | — | OD-01…OD-52 + OD-56 register and change control. Three different counts (C01); broken reference (C16). |
| `README.md` | O | PRODUCTION | — | Project overview, status claims, links. Stale counts and architecture list (C09, C14). |

### 3.2 Canonical frozen documents

| Document | Cls | Lifecycle | Parent | Purpose / issue |
|---|---|---|---|---|
| `canonical/IAM_DOC_01_MASTER_ARCHITECTURE.md` | S | SPECIFIED | self | Overall systems A–P, infrastructure, database domains. Conflicts with 15-system master draft (C05). |
| `canonical/IAM_DOC_02_INTELLIGENCE_EVOLUTION.md` | S | SPECIFIED | Master doc | Models, NVIDIA, reasoning, learning, self-development. |
| `canonical/IAM_DOC_03_INTERNET_AUTONOMY_ECOSYSTEM.md` | S | SPECIFIED | Master doc | Internet, external AI, autonomy, business; §7 extended by Doc 18. |
| `canonical/IAM_DOC_04_UI_GLOBAL_ACCESS.md` | S | SPECIFIED | Master doc | Supplied HTML interface, anonymous visitors, GeoIP, concurrency. |

### 3.3 Numbered/confirmed specifications (Docs 05–32 and technical specs)

| Document | Cls | Lifecycle | Parent | Purpose / issue |
|---|---|---|---|---|
| `IAM_DISTRIBUTED_ARCHITECTURE.md` (05) | S | SPECIFIED | superseded master | Creator authority, hybrid P2P, restricted reporting, Aegis, OEDIE. |
| `IAM_WHITEHAT_AND_WORKSPACE.md` (06) | S | SPECIFIED | superseded master | White-hat identity, offensive restrictions, dev environment. |
| `IAM_COMMUNICATION_ARCHITECTURE.md` (07) | S | SPECIFIED | superseded master | Three channels, email approval, private comms. |
| `IAM_HARDWARE_ADAPTATION.md` (08) | S | SPECIFIED | Doc 01 / OD-22 | ARM64/x86-64 AIHAE; multi-arch build unverified. |
| `IAM_BLOCKCHAIN_AND_BANKING.md` (09) | S | SPECIFIED | superseded master | thirdweb free-only, SA banking. |
| `IAM_DYNAMIC_NODE_NETWORK_SPEC.md` (10) | S | SPECIFIED | superseded master | Dynamic nodes, voluntary 1% contribution (OD-26). |
| `IAM_UNIVERSAL_WEBSITE_INTERACTION_SPEC.md` (11) | S | SPECIFIED | superseded master | UWAIE frontend-first interaction (OD-27). |
| `IAM_AI_ASSISTANT_INTEROPERABILITY_SPEC.md` (12) | S | SPECIFIED | superseded master | Internal assistant/voice technology learning (OD-28). |
| `IAM_DEVELOPER_SDK_AND_CLI_SPEC.md` (13) | S | SPECIFIED | superseded master | SDK/CLI/protocol (OD-29); package-name drift (C19). |
| `IAM_GLOBAL_RESEARCH_AND_KNOWLEDGE_SPEC.md` (14) | S | SPECIFIED | superseded master | Frozen research scope (OD-30). |
| `IAM_LEGAL_INTELLIGENCE_AND_COMPLIANCE_SPEC.md` (15) | S | SPECIFIED | superseded master | Legal monitoring and obligations (OD-31); legal validation open. |
| `IAM_GEOSPATIAL_INTELLIGENCE_AND_LIVE_MAPPING_SPEC.md` (16) | S | SPECIFIED | superseded master | Maps/geospatial (OD-32); provider verification deferred. |
| `IAM_HUMAN_PSYCHOLOGY_TONE_AND_INFLUENCE_SPEC.md` (17) | S | SPECIFIED | superseded master | Defensive influence intelligence (OD-33). |
| `IAM_EXTERNAL_AI_IDENTITY_AND_LEARNING_SPEC.md` (18) | S | SPECIFIED | superseded master | External AI identity/interview/learning (OD-34); extends Doc 03 §7. |
| `IAM_FREE_INFRASTRUCTURE_NODE_DISCOVERY_AND_LIFECYCLE_SPEC.md` (19) | S | SPECIFIED | superseded master | Free node lifecycle (OD-35). |
| `IAM_AI_SDK_AND_FRAMEWORK_RESEARCH_SPEC.md` (20) | S | SPECIFIED | superseded master | SDK/framework research + registry (OD-36). |
| `IAM_INFRASTRUCTURE_TRAFFIC_AND_DISTRIBUTED_PROCESSING_SPEC.md` (21) | S | SPECIFIED | superseded master | Traffic/queues/workloads (OD-37); OD-08 ARQ unchanged. |
| `IAM_FREE_SANDBOX_API_ADAPTER_SPEC.md` (22) | S | SPECIFIED | superseded master | Free platform adapters; default-disabled implementation. |
| `IAM_FOUNDATION_MODEL_AND_INTELLIGENCE_SPEC.md` (23) | S | SPECIFIED | consolidation / Doc 02 | Model set, router, competition (OD-38); §§1/3 superseded by 23-A. |
| `IAM_PRIMARY_MODEL_UNIFICATION_SPEC.md` (23-A) | S | SPECIFIED | Doc 23 / OD-38 | Shared primary (OD-46); reopened to Qwen2.5-3B on 27 Nov. |
| `IAM_RESOURCE_AND_WORKLOAD_MANAGER_SPEC.md` | S | SPECIFIED | OD-39 | IRWM residency and ceilings; not on inference path (C23). |
| `IAM_MODEL_EVOLUTION_AND_FINE_TUNING_SPEC.md` | S | SPECIFIED | OD-40 / OD-41 | MEFE datasets, SFT/QLoRA, registry, rollback. |
| `IAM_INDEPENDENT_AI_RESEARCH_DEVELOPMENT_AND_EVOLUTION_ARCHITECTURE.md` | S | SPECIFIED | OD-41 | 14 engines, five pillars; explicitly requirements only. |
| `IAM_HUMAN_BEHAVIOUR_EQUALITY_AND_RESPONSIBILITY_SPEC.md` (24) | S | SPECIFIED | superseded master | Equality of Existence, behaviour, responsibility (OD-43). |
| `IAM_FINANCIAL_INTELLIGENCE_AND_ECONOMIC_INDEPENDENCE_SPEC.md` (25) | S | SPECIFIED | superseded master | Finance + Amendment A (OD-44, OD-56); research-only. |
| `IAM_HUMAN_BEHAVIOUR_INTELLIGENCE_SPEC.md` (26) | S | SPECIFIED | superseded master / consolidation | HBI 38 modules, 13 engines (OD-45); 15-system wording (C05); implementation claim conflict (C12). |
| `IAM_RESEARCH_ACQUISITION_AND_LEGAL_INTELLIGENCE_SPEC.md` (27) | S | SPECIFIED | Doc 26 / Doc 14 | Acquisition channels/pipelines; five vs twelve conflict (C13); OD-45-style vs OD-47 (C15). |
| `IAM_IP_AND_LEGAL_INTELLIGENCE_MASTER_SPEC.md` (28) | S | SPECIFIED | consolidation / superseded master | IPLCI governance (OD-48); 15-system wording (C05); legal validation open. |
| `IAM_BROWSER_INTELLIGENCE_MASTER_SPEC.md` (29) | S | SPECIFIED | consolidation / superseded master | BIWOS/TIPS (OD-49); design only, not implementation. |
| `IAM_VOICE_AND_HEARING_SYSTEM_SPEC.md` (30) | S | SPECIFIED | index / consolidation | 60 capabilities, 12 components (OD-50); scope only. |
| `IAM_MULTI_MODEL_INTELLIGENCE_GOVERNANCE_SPEC.md` (31) | S | SPECIFIED | index / consolidation | Provider vault, isolation, fail-closed accounting (OD-51); not an implementation claim. |
| `IAM_UNIVERSAL_MODEL_PROVIDER_ORCHESTRATION_SPEC.md` (32) | S | SPECIFIED | index / consolidation | Discovery, registry, delegation (OD-52); stale primary model (C04). |
| `IAM_DATABASE_DESIGN.md` | S | SPECIFIED | superseded gap analysis | ERD/table design; "provisional pending OD-01…10" stale; 119-table snapshot. |
| `IAM_API_CONTRACTS.md` | S | SPECIFIED | superseded gap analysis | Endpoint/SSE contracts; "provisional" stale. |
| `IAM_SECURITY_AND_INTERNET_POLICY.md` | S | SPECIFIED | superseded gap analysis | Security/internet policy; "provisional" stale. |
| `IAM_COMPATIBILITY_MATRIX.md` | R | IN DEVELOPMENT | Doc 08 / OD-22 | ARM64/x86-64 verification matrix; unverified rows. |
| `IAM_OPEN_SPECS_RESOLVED.md` | S | SPECIFIED | consolidation | Resolved open areas A–G; some defaults still provisional. |
| `IAM_IMPLEMENTATION_TECHNOLOGY_ADDENDUM.md` | S | SPECIFIED | index / consolidation / register | Python+Rust+TypeScript allocation; 41-decision wording (C01). |

### 3.4 Implementation plans and proposals

| Document | Cls | Lifecycle | Parent | Purpose / issue |
|---|---|---|---|---|
| `IAM_AI_RESEARCH_IMPLEMENTATION_PLAN.md` | P | IN DEVELOPMENT | OD-41 architecture | Work packages, acceptance tests; "Phase 1 COMPLETE" claim. |
| `IAM_BROWSER_PHASE1_IMPLEMENTATION_PLAN.md` | P | IN DEVELOPMENT | Doc 29 / OD-49 | Seven work packages, ARQ contract; WP-01–03 records, phases 4–8 open. |
| `IAM_WEB3_AND_NODE_INTEGRATION_PLAN.md` | P | PROPOSED | index / consolidation / Docs 09,25 | Web3/Umbrel plan; OD-55 unsigned. |
| `IAM_IICS_GAP_CLOSURE_ADDENDUM.md` | P | PROPOSED | consolidation | Nine gap closures; says OD-47/52 proposed and Coder primary (C04, C07); §7 claims implementation. |
| `IAM_LIVE_INFORMATION_AND_WEB_INTELLIGENCE_SPEC.md` (34) | S | PROPOSED | consolidation / Doc 29 | Live information policy; OD-54 unsigned; working-tree note modified. |
| `IAM_WEB3_AND_UMBREL_NODE_INTEGRATION_SPEC.md` (35) | S | PROPOSED | index / consolidation | Node adapters; OD-55 unsigned; code behind default-off flags. |
| `IAM_PAID_MODEL_ACCESS_DECISION.md` (36) | P | PROPOSED | index / register | Paid access request; **OD-56 collision** (C02). |
| `IAM_OD54_SIGNOFF_SHEET.md` | P | PROPOSED | Doc 34 | Unsigned sign-off sheet; OD-53 assignment drift (C03). |
| `IAM_OD55_SIGNOFF_SHEET.md` | P | PROPOSED | Doc 35 + plan | Unsigned sign-off sheet; explicitly no authority. |
| `IAM_WEB3_ACTIVATION_RUNBOOK.md` | O | PROPOSED | Doc 35 + sheet | Operator procedure; prerequisite decision absent. |

### 3.5 Implementation status, audits and operational notes

| Document | Cls | Lifecycle | Parent | Purpose / issue |
|---|---|---|---|---|
| `IAM_ARCHITECTURE_AUDIT_REPORT.md` | IS | HISTORICAL | index | Point-in-time audit at 26/32 decisions; present-tense "frozen TRUE" (C14). |
| `IAM_ARCHITECTURE_COMPLETION_AUDIT.md` | IS | IN DEVELOPMENT | index (non-amending) | Most accurate gap record; G1–G25; working-tree modified; OD-47 stale (C07). |
| `IAM_ARCHITECTURE_GAP_ANALYSIS.md` | H | SUPERSEDED | — | Original Doc 01–04 gap analysis; retained history. |
| `IAM_DISTRIBUTED_GAP_ANALYSIS.md` | H | SUPERSEDED | gap analysis / Doc 05 | Distributed gap analysis; retained history. |
| `IAM_MASTER_ARCHITECTURE.md` | H | SUPERSEDED | — | Early 15-system baseline (C05); still cited as parent ~25 times. |
| `IAM_INTELLIGENCE_EVOLUTION_SPEC.md` | H | SUPERSEDED | master draft | Early companion; superseded by canonical Doc 02. |
| `IAM_INTERNET_AUTONOMY_ECOSYSTEM_SPEC.md` | H | SUPERSEDED | master draft | Early companion; superseded by canonical Doc 03. |
| `IAM_UI_GLOBAL_ACCESS_SPEC.md` | H | SUPERSEDED | master draft | Early companion; superseded by canonical Doc 04. |
| `MASTER_SPECIFICATION.md` | H | SUPERSEDED | — | Earliest master specification; header correctly labelled. |
| `IAM_EXTERNAL_MODULES_REVIEW.md` | IS | VERIFIED | index | P2P/Aegis/OEDIE review; 442-path snapshot stale. |
| `IAM_DATABASE_INTEGRATION_REPORT.md` | IS | VERIFIED | database design | Throwaway-DB integration run; reads password from `.env` (no value in doc). |
| `IAM_MEDIA_AND_RESEARCH.md` | IS | VERIFIED | API contracts / Doc 12 | Voice/vision/research notes; not in index. |
| `IAM_ARTEX_INTEGRATION_SPEC.md` | S | IMPLEMENTED | consolidation inventory | Default-disabled connector; not in index. |
| `IAM_API_AUTH_SPEC.md` | S | IMPLEMENTED | OD-19 | "Implemented and verified against live PostgreSQL" (C11). |
| `IAM_CREATOR_APPROVAL_SPEC.md` | S | IMPLEMENTED | OD-18/19 | Email + Ed25519 flow; no Creator UI. |
| `IAM_CREATOR_SIGNER_SETUP.md` | O | PRODUCTION | OD-18/19 | Local signer setup; private key must not be committed. |
| `IAM_SKILL_FORGE_SPEC.md` | S | IMPLEMENTED | index map | Phases 1–2 core implemented; later phases scaffolded. |
| `IAM_SKILL_RUNTIME_SPEC.md` | S | IMPLEMENTED | index map | Implemented, disabled by default; "verified against live PostgreSQL" (C11). |
| `IAM_BROWSER_AND_GEO_BACKEND.md` | IS | IMPLEMENTED | Docs 29/16 | Backend-only first slice; frontend conflict (C09). |
| `IAM_FRONTEND_IMPLEMENTATION.md` | O | SPECIFIED | index map | "Home + suggestions" two-page claim (C09). |
| `IAM_FREE_SANDBOXES.md` | O | PRODUCTION | Docs 19/22 | Free dev/test platform guide. |
| `IAM_CI_AND_WORKERS.md` | R | PRODUCTION | AGENTS §3 | CI/worker guide; migrations 001–009 stale. |
| `IAM_DEPLOYMENT_CONFIG.md` | O | PRODUCTION | OD-07 | Docker secrets and preflight. |
| `IAM_PRIVACY_AND_SECRETS.md` | O | PRODUCTION | OD-05/07/09 | Secrets and data-rights behaviour. |
| `IAM_IPLCI_LEGAL_VALIDATION_RUNBOOK.md` | O | IN DEVELOPMENT | OD-48 / Doc 28 | Engineering→counsel handoff; no self-verification. |
| `IAM_AI_COMMUNICATION_COLLABORATION.md` | S | SPECIFIED | self-declared Phase 10 | 11-module AI communication architecture; orphaned from index. |
| `IAM_DIGITAL_IDENTITY_UNIVERSAL_WEB_INTERACTION.md` | S | SPECIFIED | self-declared Phase 10 | 20-module identity/web interaction; orphaned, implementation claims. |
| `MODEL_PROVIDER_SETUP.md` | O | PRODUCTION | OD-38/46/52 | Provider key configuration; working-tree modified. |

### 3.6 SDK, research, infra, frontend, tests and tooling

| Document | Cls | Lifecycle | Parent | Purpose / issue |
|---|---|---|---|---|
| `sdk/PROTOCOL.md` | S | SPECIFIED | Doc 13 / OD-29 | Versioned protocol, auth, IPLCI headers. |
| `sdk/typescript/README.md` | R | PRODUCTION | Doc 13 / protocol | `@iamagris/sdk` usage; name drift (C19). |
| `sdk/python/README.md` | R | PRODUCTION | Doc 13 / protocol | `iam-sdk` usage. |
| `sdk/cli/README.md` | R | PRODUCTION | Doc 13 / protocol | CLI usage; stubs flagged by audit G13. |
| `iam/skills/README.md` | R | PRODUCTION | Skill Forge spec | On-disk skill store layout. |
| `research/colab/README.md` | O | IN DEVELOPMENT | OD-41 plan | Free-GPU experiment; model name predates OD-46 reopening (C04). |
| `research/mcp/README.md` | O | IN DEVELOPMENT | OD-41 | MCP setup for free GPU platforms. |
| `infra/cloudflare/README.md` | O | PRODUCTION | OD-03/19/42 | Tunnel + Access transport only, never authority. |
| `frontend/AGENTS.md` | R | PRODUCTION | generated | Next.js generated rules; takes precedence for frontend work. |
| `.github/SECURITY.md` | R | PRODUCTION | — | Supported versions and vulnerability reporting. |
| `tests/creator_cli_e2e.md` | IS | VERIFIED | OD-42 | Signed-decision E2E evidence; temporary key deleted. |
| `tests/model_competition/RESULTS.md` | IS | VERIFIED | OD-38/46 | Benchmark report; explicitly not a deployment decision, yet cited as OD-46 evidence. |
| `tests/real_inference_smoke.md` | IS | VERIFIED | OD-46 | Real local inference smoke; 82.1 s latency. |
| `tools/api/README.md` | R | PRODUCTION | AGENTS §3 | OpenAPI tooling; still reports "DRIFT" (C17). |
| `tools/quality/README.md` | R | PRODUCTION | AGENTS §3 | mypy ratchet tooling; baseline snapshot. |
| `tools/quality/SELF_HOSTED_RUNNER.md` | O | PRODUCTION | workflows | Self-hosted runner setup. |
| `tools/rkie/README.md` | R | PRODUCTION | AGENTS | Repository Intelligence toolkit. |
| `tools/rkie/RKIE_CAPABILITY_AUDIT.md` | IS | IN DEVELOPMENT | index local-search | 26-domain scope audit; §18 stale; working-tree modified. |

### 3.7 Dated investigation notes (all: IS/R, historical context, re-verify before reuse)

| Note | Lifecycle | Parent / issue |
|---|---|---|
| `tools/rkie/notes/README.md` | PRODUCTION | Note conventions; notes are untrusted context. |
| `tools/rkie/notes/2026-11-27-p2p-aegis-http.md` | VERIFIED | Docs 05/06; dated snapshot. |
| `tools/rkie/notes/caddy_edge_and_load_test.md` | IMPLEMENTED | Doc 21 / OD-37. |
| `tools/rkie/notes/chat-context-assembly.md` | VERIFIED | consolidation / Doc 26; commit-based snapshot. |
| `tools/rkie/notes/financial-intelligence-amendment-a.md` | IMPLEMENTED | Doc 25 / OD-56. |
| `tools/rkie/notes/free_node_lifecycle.md` | IMPLEMENTED | Doc 19 / OD-35. |
| `tools/rkie/notes/frontend_internal_views.md` | IMPLEMENTED | Doc 04; conflicts with C09. |
| `tools/rkie/notes/hbi-implementation.md` | IMPLEMENTED | Doc 26 / OD-45. |
| `tools/rkie/notes/integration-db-local.md` | PRODUCTION | Database design. |
| `tools/rkie/notes/iplci-legal-validation-outstanding.md` | IN DEVELOPMENT | Doc 28 / OD-48; working-tree modified. |
| `tools/rkie/notes/live-information-policy-doc34.md` | PROPOSED | Doc 29 / OD-49; working-tree modified. |
| `tools/rkie/notes/llm-asm-benchmark-extension-plan.md` | HISTORICAL | **Untracked**; OD-38/41; test-only plan. |
| `tools/rkie/notes/llm-asm-inference-research-2026-11-27.md` | HISTORICAL | **Untracked**; external research, HEAD moved. |
| `tools/rkie/notes/multiarch_build.md` | IN DEVELOPMENT | Doc 08 / OD-22; criterion 4 unverified. |
| `tools/rkie/notes/mypy-ratchet-fixes.md` | VERIFIED | AGENTS §3 gates. |
| `tools/rkie/notes/od46_reopened_qwen25_3b.md` | VERIFIED | OD-46; explains stale coder references. |
| `tools/rkie/notes/p2p_address_and_identity.md` | PRODUCTION | Docs 05/10. |
| `tools/rkie/notes/real_inference_smoke.md` | VERIFIED | Near-duplicate pointer to `tests/real_inference_smoke.md`. |
| `tools/rkie/notes/repo-gate-drift-2026-11-27.md` | VERIFIED | Contains both drift and resolution numbers. |
| `tools/rkie/notes/technology_capability_registry.md` | IMPLEMENTED | Doc 20 / OD-36. |
| `tools/rkie/notes/verification-2026-11-27.md` | VERIFIED | Corrects stale §18 and OpenAPI drift claims. |
| `tools/rkie/notes/web3-doc35-implementation.md` | PROPOSED | Doc 35 / OD-55; cached OD-50 references stale. |

### 3.8 Working-tree-modified Markdown (preserve; do not normalize)

`IAM_ARCHITECTURE_COMPLETION_AUDIT.md`, `IAM_FINAL_CONSOLIDATION.md`, `MODEL_PROVIDER_SETUP.md`, `tools/rkie/RKIE_CAPABILITY_AUDIT.md`, `tools/rkie/notes/live-information-policy-doc34.md` (modified); the two untracked notes listed in §0.

---

## 4. Conflict register

Severity: **HIGH** = changes what is approved/implemented; **MEDIUM** = misleads navigation or status; **LOW** = hygiene.

| ID | Sev | Location | Claim A | Claim B | Recommended resolution (no change made) |
|---|---|---|---|---|---|
| C01 | HIGH | `ARCHITECTURE_INDEX.md:13,55`; `IAM_OWNER_DECISIONS.md:3,111,287`; `IAM_FINAL_CONSOLIDATION.md:42`; `README.md:5,257`; `IAM_IMPLEMENTATION_TECHNOLOGY_ADDENDUM.md:60,102`; `IAM_ARCHITECTURE_COMPLETION_AUDIT.md:19,211`; `tools/rkie/RKIE_CAPABILITY_AUDIT.md:71`; `IAM_ARCHITECTURE_AUDIT_REPORT.md:4,21,31,46` | 52 / 53 / 41 / 49 / 51 / 44 / 46 / 26 / 32 locked decisions | — | Register enumerates exactly **53** definitions (OD-01…OD-52 + OD-56; OD-53/54/55 only proposed). Owner confirms 53, then update all occurrences in one batch. |
| C02 | HIGH | `IAM_OWNER_DECISIONS.md:275–281`; `ARCHITECTURE_INDEX.md:41,171`; `IAM_PAID_MODEL_ACCESS_DECISION.md:8,52` | OD-56 = Financial Intelligence Amendment A, **confirmed** | OD-56 = Paid hosted-model access, **proposed** | Keep OD-56 for Amendment A; renumber the paid proposal to next free ID (OD-57) and update index row. |
| C03 | HIGH | `ARCHITECTURE_INDEX.md:169`; `IAM_OD54_SIGNOFF_SHEET.md:6`; `IAM_OWNER_DECISIONS.md:281`; `IAM_FINANCIAL_INTELLIGENCE_AND_ECONOMIC_INDEPENDENCE_SPEC.md:3–8` | OD-53/Doc 33 = Financial Amendment A | OD-53 = Web3 proposal; Amendment A = OD-56 / Doc 25 | Delete the Doc 33/OD-33 assignment; record an identifier-history note; update the sign-off sheet. |
| C04 | HIGH | `IAM_OWNER_DECISIONS.md:83,108,123,204`; `ARCHITECTURE_INDEX.md:34,55`; `IAM_UNIVERSAL_MODEL_PROVIDER_ORCHESTRATION_SPEC.md:18`; `IAM_IICS_GAP_CLOSURE_ADDENDUM.md:17`; `IAM_LIVE_INFORMATION_AND_WEB_INTELLIGENCE_SPEC.md:37,146,150`; `IAM_OD54_SIGNOFF_SHEET.md:29`; `IAM_MULTI_MODEL_INTELLIGENCE_GOVERNANCE_SPEC.md:22`; `IAM_INDEPENDENT_AI_RESEARCH_DEVELOPMENT_AND_EVOLUTION_ARCHITECTURE.md:79,126,143,164`; `IAM_AI_RESEARCH_IMPLEMENTATION_PLAN.md:84`; `IAM_HUMAN_BEHAVIOUR_EQUALITY_AND_RESPONSIBILITY_SPEC.md:461`; `research/colab/README.md:4` | Qwen2.5-3B `local-qwen-3b` is the shared primary (OD-46, 27 Nov) | Qwen2.5-Coder 3B remains local shared primary, and OD-46 details still say "Locked: Coder" | Replace stale primary-model sentences with "OD-46: local primary is `qwen2.5:3b`; coder is optional secondary; the 26 Nov choice is superseded". |
| C05 | HIGH | `canonical/IAM_DOC_01:50–113` (systems A–P); `IAM_MASTER_ARCHITECTURE.md:40–61` (15 systems); `IAM_HUMAN_BEHAVIOUR_INTELLIGENCE_SPEC.md:40,681,689`; `IAM_IP_AND_LEGAL_INTELLIGENCE_MASTER_SPEC.md:31,572`; `IAM_LIVE_INFORMATION_AND_WEB_INTELLIGENCE_SPEC.md:10` | 16 canonical systems A–P | "existing 15 systems", "fifteenth/sixteenth top-level system" | Decide canonical count = 16 (A–P); correct to "not a seventeenth top-level system"; label the 15-system doc HISTORICAL. |
| C06 | HIGH | `IAM_FINAL_CONSOLIDATION.md:250` vs `:265`; `README.md:5` vs `:261`; `IAM_ARCHITECTURE_COMPLETION_AUDIT.md:28,100–145,191` | "ALL FIVE ACCEPTANCE LEVELS PASSED" / "All 5 acceptance levels passed … are implemented" | "What remains: Levels 2–5 acceptance tests"; README "Pre-implementation phase complete. Ready for Phase 0/1 build."; audit says shallow cognitive nodes, status-based verification, manual-only CI | Reclassify L1–L5 claims as **dated single-node test runs, not production verification**; rewrite the README status as one coherent snapshot; separate "tests executed" from "behaviour demonstrated". |
| C07 | HIGH | `IAM_ARCHITECTURE_COMPLETION_AUDIT.md:19,211`; `tools/rkie/notes/repo-gate-drift-2026-11-27.md:16`; `tools/rkie/notes/hbi-implementation.md`; `IAM_IICS_GAP_CLOSURE_ADDENDUM.md:14,29,94,243–244`; `IAM_BROWSER_INTELLIGENCE_MASTER_SPEC.md:5,64,788` vs `:794`; `IAM_IP_AND_LEGAL_INTELLIGENCE_MASTER_SPEC.md:5,40,49,577`; `IAM_RESEARCH_ACQUISITION_AND_LEGAL_INTELLIGENCE_SPEC.md:5,8,253`; `IAM_LIVE_INFORMATION_AND_WEB_INTELLIGENCE_SPEC.md`; `IAM_OWNER_DECISIONS.md:109,113,117,229` | OD-47, OD-48 and OD-52 "remain proposed/pending" | OD-47 owner-confirmed 27 Nov (not signed Creator); OD-48 and OD-52 confirmed 27 Nov; Doc 27 is internally inconsistent | Standardise on "OD-47 owner-confirmed 27 Nov, not a signed Creator decision"; update all stale cross-references; keep owner register as authority. |
| C08 | MEDIUM | completion audit `:54,:203,:252,:297,:328,:344,:362`; browser plan `:349,:407,:427,:446,:462`; IPLCI spec `:619`; notes | Test totals 626/705/805/921/935/992/1002/1013/1021/1027; OpenAPI 589/601/665/678/696/775/801/836/846/848; migrations 46/47/54/56/58/64/66 | — | Treat each as a dated snapshot; add "as of <head>" to each; do not restate in authority docs without re-run. |
| C09 | MEDIUM | `README.md:5,104,105`; `IAM_FINAL_CONSOLIDATION.md:240`; `IAM_FRONTEND_IMPLEMENTATION.md`; `tools/rkie/notes/frontend_internal_views.md`; working tree | 16 documents / 41 decisions / 119 tables / 41 routes / "home + suggestions only" / "one route `/` only" | 76 root `IAM_*.md`; 289 `__tablename__` declarations; 94 route modules; four routable pages added; `suggestions/page.tsx` deleted in working tree | Recount from source, then update README and frontend scope note once. |
| C10 | MEDIUM | `IAM_FINAL_CONSOLIDATION.md:230` vs `:234` | MapLibre GL JS v6 real tiles replace offline grid | "no Leaflet/MapLibre/GeoJSON in repo"; offline vector basemap added | Keep the later implementation state; mark the earlier paragraph SUPERSEDED with a date. |
| C11 | HIGH | `IAM_API_AUTH_SPEC.md:3`; `IAM_SKILL_RUNTIME_SPEC.md:3`; `IAM_ARCHITECTURE_COMPLETION_AUDIT.md:145` (G23) | "Implemented and verified against live PostgreSQL" | `/test` only flips status; `assess_capability()` records caller-supplied proficiency; "verified" means a row/status | Define evidence threshold before allowing VERIFIED; downgrade these headers to IMPLEMENTED unless a linked test exists. |
| C12 | HIGH | `IAM_HUMAN_BEHAVIOUR_INTELLIGENCE_SPEC.md`; `backend/app/services/hbi/modules.py:3,54–56`; completion audit G23 | 38 modules listed as IMPLEMENTED | Module docstring: "Modules 1–4 are functional in this increment" | Reconcile the authoritative module-status table with source; list per-module status. |
| C13 | MEDIUM | `IAM_RESEARCH_ACQUISITION_AND_LEGAL_INTELLIGENCE_SPEC.md` §§1–2 vs §13 | Five acquisition routes | Twelve acquisition channels (OD-47 wording) | Adopt twelve as frozen value; keep five as historical grouping. |
| C14 | MEDIUM | `IAM_ARCHITECTURE_AUDIT_REPORT.md:4,12,31,46,71` | "26 decisions", "32 decisions", "frozen claim TRUE" | Register now 53 | Mark document HISTORICAL with a visible banner; link from index superseded section. |
| C15 | MEDIUM | `IAM_RESEARCH_ACQUISITION_AND_LEGAL_INTELLIGENCE_SPEC.md` status header; `IAM_OWNER_DECISIONS.md:109` | "OD-45-style owner confirmation" for Doc 27 | OD-47 is the recorded decision for Doc 27 | Replace ambiguous "OD-45-style" with "owner confirmation recorded as OD-47, not a signed Creator decision". |
| C16 | MEDIUM | `IAM_OWNER_DECISIONS.md:281`; `audit_architecture.py` output | References `IAM_OD53_SIGNOFF_SHEET.md` | File does not exist | Remove reference or create the sheet after owner decision; no file was created by this report. |
| C17 | LOW | `tools/api/README.md`; `tools/rkie/notes/verification-2026-11-27.md` | "Current state: DRIFT" | Snapshot regenerated, check OK (801/461 at the time; 848/482 now) | Refresh operational note; keep dated snapshots in notes only. |
| C18 | MEDIUM | index authority table; §2.3 list | 18 substantive documents have no declared authority parent | Index claims to be the single entry point | Add a "derived implementation specifications" tier with parent links. |
| C19 | LOW | `IAM_DEVELOPER_SDK_AND_CLI_SPEC.md`; `README.md:233`; `sdk/typescript/README.md`; completion audit G13 | Package `@iam/sdk` / `iam-sdk` | Published scope `@iamagris/sdk`, CLI `@iamagris/cli` | Record canonical package names in Doc 13; fix imports/stubs separately (source change out of scope). |
| C20 | HIGH | `IAM_FINAL_CONSOLIDATION.md:242`; completion audit G5 | "IAM Aegis implemented & verified" | Injection detector not called from chat/inference path | Restate as "Aegis service implemented; not integrated into inference path". |
| C21 | MEDIUM | `IAM_FINAL_CONSOLIDATION.md:244`; `README.md:5` | P2P signed envelopes (HMAC) | Ed25519 node attestation | Distinguish transport HMAC from creator/node Ed25519 attestation in one table. |
| C22 | HIGH | `IAM_OWNER_DECISIONS.md:18`; `IAM_DEPLOYMENT_CONFIG.md`; completion audit G11 | OD-07 SOPS + Docker secrets locked | No `.sops.yaml` or encrypted artefacts; Compose ships placeholder credentials | Mark SOPS as SPECIFIED / IN DEVELOPMENT, not implemented. |
| C23 | HIGH | `IAM_FINAL_CONSOLIDATION.md:228`; `IAM_RESOURCE_AND_WORKLOAD_MANAGER_SPEC.md`; completion audit G18 | IRWM fix "verified", 11 tests pass | `irwm.admit()/release()` never called by chat or inference | Separate unit correctness from enforcement on the live path. |
| C24 | HIGH | `IAM_FINAL_CONSOLIDATION.md:179` (L1 backup restores); `IAM_SECURITY_AND_INTERNET_POLICY.md`; completion audit G4 | Backup/restore listed as L1 exit test; OD-06 RPO 24h/RTO 4h | No `pg_dump`/restore job; `resilience_service` only inserts a row | Move backup/restore to REMAINING WORK; do not claim RPO/RTO met. |
| C25 | LOW | `ARCHITECTURE_INDEX.md:85` | "61 specification / analysis documents" | 76 root `IAM_*.md` files | Recount and avoid hard numbers in navigation tables (use "root `IAM_*.md`"). |
| C26 | MEDIUM | `IAM_FINAL_CONSOLIDATION.md:68` vs `:226`; `IAM_OPENAPI.json` | 829/473 and 846/481 paths/schemas | Snapshot currently 848/482 | Remove counts from authority prose; point to generated artefact. |
| C27 | LOW | `IAM_DATABASE_DESIGN.md:3`; `IAM_API_CONTRACTS.md:3`; `IAM_SECURITY_AND_INTERNET_POLICY.md:3` | "Provisional — pending owner decisions OD-01…OD-10" | OD-01…OD-10 locked since 24 Nov | Update header status to SPECIFIED under locked decisions. |
| C28 | LOW | `IAM_CI_AND_WORKERS.md`; `audit_architecture.py` | "migrations 001–009" | 66 numbered SQL files in working tree | Refresh operational doc. |
| C29 | LOW | `IAM_EXTERNAL_MODULES_REVIEW.md` | 442 OpenAPI paths as review evidence | Current snapshot 848 | Label as dated review snapshot. |
| C30 | LOW | `tools/rkie/notes/real_inference_smoke.md` vs `tests/real_inference_smoke.md` | Two near-duplicate evidence summaries | — | Keep test as evidence owner; replace note with a pointer only. |
| C31 | HIGH | `IAM_ARCHITECTURE_COMPLETION_AUDIT.md:364` (working-tree addition) | Local gates "all success" | Quality-gates `types` job FAILS on CI with HBI strict-typing errors; unresolved environment discrepancy | Record as "local green / CI unresolved" rather than "all gates green". |
| C32 | LOW | `README.md:1`; `AGENTS.md:7–8`; `ARCHITECTURE_INDEX.md:70`; `IAM_SKILL_FORGE_SPEC.md:170`; `IAM_UI_GLOBAL_ACCESS_SPEC.md:9–10,68`; `canonical/IAM_DOC_04:25,663,721` | README title "IAM — Independent AI Entity"; Skill Forge "User-facing Marlow view of the Forge lifecycle" | Permanent identity is **IAM — Intellectual Artificial Mainbrain**; Marlow is only the supplied HTML filename | Use the canonical expansion in the README title and replace "Marlow view" with "IAM UI view"; leave canonical docs verbatim. |
| C33 | MEDIUM | `ARCHITECTURE_INDEX.md:85–101`; `tools/rkie/RKIE_CAPABILITY_AUDIT.md:33,42,64,71,82,92` | Index: migrations 001–031, ~75 routes, ≈422 Python files, 61 documents, ~90 services; RKIE audit: 41 migrations, 46 decisions, 47 test modules, 76 routes, 536 paths | Current tree: 66 SQL files (001–069), 94 route modules, 625 backend / 695 repo Python files, 76 root `IAM_*.md`, 104 direct / 294 recursive services, 848 OpenAPI paths | Define counting rules in the index, remove hard numbers from prose, and mark the RKIE audit as a dated snapshot with a pointer to current gate state. |
| C34 | MEDIUM | `IAM_UNIVERSAL_MODEL_PROVIDER_ORCHESTRATION_SPEC.md:9,153`; `IAM_MULTI_MODEL_INTELLIGENCE_GOVERNANCE_SPEC.md:179`; `IAM_IP_AND_LEGAL_INTELLIGENCE_MASTER_SPEC.md:586`; `IAM_HUMAN_BEHAVIOUR_INTELLIGENCE_SPEC.md:754,758,760` | "All phases A–H implemented", "All five stages implemented", "Phases P1–P6 implemented", "HBI DEPLOYMENT READY" | No test IDs in those claims; HBI line 760 says real corpora and production activation remain; audit lines 54/123–124 record prior drift/failure | Add "as of <head>" plus linked gate evidence, or downgrade to IMPLEMENTED/IN DEVELOPMENT. |
| C35 | MEDIUM | `IAM_FINAL_CONSOLIDATION.md:244,246,248` vs `:257`; `IAM_ARCHITECTURE_COMPLETION_AUDIT.md:28,264` | "P2P / LangGraph / SSE implemented & verified" | "live P2P transport … remain specified/operational dependencies"; two-peer gossip was on one deployment, not two physical nodes | Qualify as "code + single-node test", not live multi-node or production. |

**Positive finding:** no literal secrets, private keys or API-key values were found in any Markdown file. `IAM_DATABASE_INTEGRATION_REPORT.md:9` reads `POSTGRES_PASSWORD` from `.env` at run time but does not print it. No secret values are reproduced in this report.

---

## 5. Broken links and references

Full structural link audit of all 126 Markdown files in scope (125 original + this report). Read-only; the temporary verification script was created outside the repository and deleted.

### 5.1 Markdown links

| Check | Result |
|---|---|
| Explicit `[text](target)` links | 25 checked; **0 broken** |
| Images `![](target)` | 0 present |
| Anchors | 0 bad; 3 targets are external URLs |

**The link problem is not broken Markdown syntax.** It is backticked file references, authority references and stale paths.

### 5.2 Backticked path-like tokens

2,113 tokens checked; **49 unresolved**. They split into four groups:

| Group | Examples | Treatment |
|---|---|---|
| Notation / placeholders (not real paths) | `canonical/IAM_DOC_01…04` (`AGENTS.md:20`, index `:14`), `IAM_DOC_0X.md` (`IAM_ARCHITECTURE_AUDIT_REPORT.md:23`), `tests/level1..5_acceptance.py` (completion audit `:108`), `canonical/IAM_DOC_01:50–113` (this report `:255`) | Convert to prose or a real list in Batch 1; not link defects |
| Genuinely missing files | `IAM_OD53_SIGNOFF_SHEET.md` (`IAM_OWNER_DECISIONS.md:281`); `BRANCHING_POLICY.md` (RKIE audit `:102`); `backend/mypy-baseline.json` (quality README `:14`, RKIE audit `:42`, note `repo-gate-drift…:14` — only versioned `mypy-baseline-3.15.json` exists) | **Fix** — C16 plus new refs in C33 |
| Planned assets described as present | `SKILL.md` (Skill Forge `:43`, Doc 18 `:268`); `eval_sets/basic.jsonl` (completion audit `:106`, note `chat-context-assembly.md:119` — current tree has only `eval_sets/held_out/*.jsonl`); planned source paths in Doc 29a `:120,149,168`, Doc 32 `:132,134`, Doc 35 `:484`, Doc 26 `:730,758,812,830,848`, Doc 25 `:407`, Doc 08 `:96`, Doc 28 `:625`; `scripts/export_weights.py` in the untracked llm.asm note | Label as planned/absent, or add the files deliberately; do not silently create them |
| External documentation paths | `06-fetching-data.md`, `02-guides/data-security.md`, `02-guides/caching-without-cache-components.md` (`IAM_FRONTEND_IMPLEMENTATION.md:38–39`) | Format as external URLs, not repo paths |

### 5.3 Superseded documents cited as current sources

77 references to the seven documents in `ARCHITECTURE_INDEX.md:57–66`. **28** are correctly meta/historical citations (`AGENTS.md:22–25`, index `:61–66,85`, this report). **49 across 27 other files** cite them as parents or working specifications:

- `README.md:219–225` — superseded drafts listed as "Derived / working specifications" (C14).
- `IAM_HUMAN_BEHAVIOUR_INTELLIGENCE_SPEC.md:7` and ~24 other numbered specs — `Parent: IAM_MASTER_ARCHITECTURE.md`.
- `IAM_AI_SDK_AND_FRAMEWORK_RESEARCH_SPEC.md:6–7`, `IAM_INFRASTRUCTURE_TRAFFIC_AND_DISTRIBUTED_PROCESSING_SPEC.md:6–7`, `IAM_HUMAN_PSYCHOLOGY_TONE_AND_INFLUENCE_SPEC.md:6,20`, `IAM_EXTERNAL_AI_IDENTITY_AND_LEARNING_SPEC.md:6,14`, `IAM_UNIVERSAL_WEBSITE_INTERACTION_SPEC.md:6–7`.
- `IAM_API_CONTRACTS.md:5`, `IAM_DATABASE_DESIGN.md:5`, `IAM_SECURITY_AND_INTERNET_POLICY.md:5` — parent is the superseded gap analysis.
- `IAM_ARCHITECTURE_AUDIT_REPORT.md:20,65` — superseded masters presented as current baseline.
- `ARCHITECTURE_INDEX.md:61–62` — circular supersession chain (§2.2).

This is the single largest authority defect: it is not that documents are missing, but that **superseded documents are still structurally wired in as parents**.

### 5.4 References to deleted frontend files

| Source | Referenced path | Current state |
|---|---|---|
| `IAM_ARCHITECTURE_COMPLETION_AUDIT.md:136` | `_financial-intelligence/page.tsx`, `_freesandboxes/page.tsx` | deleted |
| `IAM_FRONTEND_IMPLEMENTATION.md:10` | `frontend/app/suggestions/page.tsx` | deleted |
| `IAM_IICS_GAP_CLOSURE_ADDENDUM.md:283` | `frontend/components/iam/panels/iics-control-panel.tsx` | deleted |
| `tools/rkie/notes/financial-intelligence-amendment-a.md:28` | `frontend/app/financial-intelligence/page.tsx` | deleted |
| `tools/rkie/notes/frontend_internal_views.md:12` | `app/{tone,ai-network,freesandboxes,financial-intelligence}` | only empty `_*` directories remain |
| `IAM_DOCUMENTATION_INVENTORY_AND_CONFLICT_REPORT.md:259` | `suggestions/page.tsx` | deleted (quoted here as evidence, not as a live link) |

Current `frontend/app` directories: `conversations`, `iam-proxy`, `_ai-network`, `_financial-intelligence`, `_freesandboxes`, `_iics`, `_tone`. No `page.tsx` under the `_*` directories.

### 5.5 Sensitive-file references

42 path-only references; **no secret values were read or reported**:

- `.env` (26) — e.g. `IAM_FINAL_CONSOLIDATION.md:232`, `MODEL_PROVIDER_SETUP.md:9,29,33,78,86`, `IAM_OWNER_DECISIONS.md:186`, `IAM_FREE_SANDBOXES.md:7,44,50`.
- `.env.example` (11), `frontend/.env.local` (2), `frontend/.env.example` (1).
- `~/.config/iam/creator_ed25519.pem` (2) — `IAM_CREATOR_SIGNER_SETUP.md:13`, `tools/rkie/notes/chat-context-assembly.md:242`.

Combined with §4's positive secret-value check, the documentation currently passes the no-exposure gate on content, but operational docs should keep referring to paths only.

---

## 6. Intended intelligence vs implementation reality

This is the core anti-aspiration table requested for every major intelligence system. Status vocabulary here is deliberately conservative: **SPECIFIED** ≠ implemented; **IMPLEMENTED** ≠ verified; **VERIFIED** requires an executable test or reproducible demonstration, not a status string or database row.

| System | Intended capability | Requirements (authority) | Implementation (current tree) | Evidence | Limitations | Dependencies | Remaining work |
|---|---|---|---|---|---|---|---|
| Identity & constitution | Persistent, model-independent IAM identity | canonical Doc 01 §3.A; OD-01/11 | genesis, constitution, identity service/route | L1 acceptance runs (dated 25 Nov) | Unattended machine migration untested | protected-core enforcement | migration/recovery exercise |
| Model routing & primary brain | One shared local primary, replaceable, hosted specialists subordinate | Docs 23/23-A; OD-38/46/51/52 | `model_inference.py` resolver, LiteLLM, readiness, SSE stream | unit smoke, browser stream observation, competition report | Coder-primary text still in confirmed specs; hosted calls gated | signed Creator auth, stable key vault | reconcile C04; enforce OD-51 on live path |
| Memory & knowledge | Isolated visitor/owner memory, governed knowledge, provenance | canonical Doc 01 §3.D; Doc 26; `IAM_DATABASE_DESIGN.md` | `memory_service.py`, `knowledge.py`, `hbi/knowledge.py`, `hkg.py`, world model | integration DB report; HBI notes | Six flat types, no consolidation/expiry sweeper | DB migrations, privacy policy | implement lifecycle, dedup, expiry |
| Human Behaviour Intelligence | 38 modules, 13 engines, governed, no consequential individual prediction | Doc 26 / OD-45 | HBI package, routes, governance gates | HBI tests; docstring says only modules 1–4 functional | **C12**: status table says all 38 implemented | phase-0 gate | per-module status truth table |
| External research intelligence | Evidence-based, provenance-tracked web/GitHub research | Docs 03/14; OD-30 | `search_service.py`, `research_service.py`, `browser_service.py` | L2 research run (Wikipedia sources) | Colab/MCP unexecuted; no hybrid ranking | provider availability | run free-tier verification, FTS/hybrid retrieval |
| Browser / UWAIE | Frontend-first interaction with any website, permission-gated | Docs 11/29; OD-27/49 | backend adapters, session manager, first gated slice | WP-01–03 gate records | No full multi-browser/visual stack; UI scope contradictory (C09) | browser sandbox, approval gates | reconcile frontend scope; phases 4–8 |
| Voice & hearing | 60 capabilities, 12 components, local-first | Doc 30 / OD-50 | voice service/route, Web Speech/TTS in UI | build + toggle smoke | UI does not call all voice routes; STT fixed `en-US` | audio providers | implement capability surface |
| Financial intelligence | Research/simulation first, signed approval for real activity | Docs 09/25; OD-23/24/25/44/56 | ledger, paper trading, adapters default-off | Level 5 acceptance (dated) | No real adapters, no SDK finance, unrouted page | legal entity, signed policy | implement provider config, UI, legal clearance |
| Distributed / P2P | Signed, zero-trust, store-and-forward peer network | Doc 05 / OD-12/13 | `p2p_transport.py`, routes, signed sync | `p2p_acceptance.py` 9/9 (dated) | HMAC transport, in-memory state, no live multi-node, no Compose P2P | trusted peers, durable store | Ed25519 distinction (C21), persistence, live test |
| IRWM / resources | Model residency and hard ceilings, never sacrifices core services | Doc 39 / OD-39 | `irwm.py`, routes, stale-snapshot fix | 11 IRWM unit tests | **C23**: not called by chat/inference | integration into resolver | wire admit/release, enforce live |
| IP & Legal Intelligence | Fail-closed legal gateway, tamper-evident audit | Doc 28 / OD-48 | IPLCI service, routes, models | 111 IPLCI tests (dated) | Legal validation outstanding; counsel handoff open | qualified counsel | complete runbook, legal review |
| Skills | Forge + sandboxed runtime, gated | Skill Forge/Runtime specs | forge, runtime, on-disk store | integration DB report; runtime tests | Skill store empty; runtime disabled by default | grants, signed packages | populate store, enable deliberately |
| Autonomy graph | Durable, evidence-based goal→plan→execute→verify loop | canonical Doc 01 §3.E; Doc 05; OD-41 | 11-node LangGraph, checkpointing; working tree now has `reasoning_engine.py`, `attention_manager.py`, `evidence_service.py` and broader `autonomy_graph.py` | Level 2 acceptance (dated); current module has structured reasoning/evidence code | The completion audit's G16/G7 (fixed `reason()`, literal `plan()`, status-derived `verify()`) is a **27 Nov snapshot** and is partly overtaken by uncommitted work — re-verify before treating as current | module contract registry, domain dispatch | re-run read of current source, then record actual node behaviour and dispatch coverage |
| Disaster recovery | RPO 24h / RTO 4h, restore demonstrated | OD-06; L1 exit test | `resilience_service` records rows only | none for restore | **C24**: no backup/restore code | backup target, schedule | implement and demonstrate restore |

---

## 7. Proposed status vocabulary and mapping

Current labels are inconsistent: **FROZEN**, **CONFIRMED**, **LOCKED**, **Implemented and verified**, **Provisional**, **Initial architecture baseline**, **PLAN + implementation record**, etc. Proposed one-to-one mapping (to be applied only in the controlled batches):

| Proposed status | Meaning | Current labels to convert |
|---|---|---|
| PROPOSED | Suggested, not approved | Doc 34/35/36, IICS addendum, OD-54/55 sheets, Web3 plan/runbook |
| APPROVED | Creator/owner decision recorded | LOCKED, CONFIRMED (decision-level) |
| SPECIFIED | Requirements/architecture documented | FROZEN, Initial architecture baseline, CONFIRMED (doc-level), Provisional |
| IN DEVELOPMENT | Implementation underway | Implementation plan, PLAN + implementation record, Living document |
| IMPLEMENTED | Code exists, not necessarily verified | "Implemented", default-disabled modules |
| VERIFIED | Behaviour demonstrated by executable test/reproduction | "verified against live PostgreSQL", "tests passed" (only with linked evidence) |
| PRODUCTION | Released and verified in intended environment | currently **no document should claim this**; no released version per `.github/SECURITY.md` |
| SUPERSEDED | Replaced by newer authority | existing SUPERSEDED/HISTORY lists |
| HISTORICAL | Retained for history only | older audits, gap analyses, early drafts |

**Rule to adopt:** a status of VERIFIED requires a named test, benchmark or reproducible demonstration. A successful API response, a created database row, a status string or a checkbox in a Markdown file is not verification.

---

## 8. Documentation quality gates (current state)

| Gate | Check | Current state |
|---|---|---|
| No conflicting owner decisions | OD IDs and counts unique | **FAIL** — C01, C02, C03, C15 |
| No duplicate authoritative specifications | One owner per requirement | **FAIL** — C05, C10, C14, §2.2 |
| No broken internal links | Links and references resolve | **PARTIAL** — 0/25 Markdown links broken; 49/2,113 backticked refs unresolved and 49 superseded-doc citations misused (§5) |
| No outdated model identities/provider decisions | OD-46 primary | **FAIL** — C04 |
| No inaccurate completion claims | VERIFIED backed by evidence | **FAIL** — C06, C11, C12, C20, C22, C23, C24, C31 |
| No undocumented changes to authority | Index matches register | **FAIL** — C01, C14, C18 |
| No contradictory implementation instructions | Plans vs specs vs code | **FAIL** — C07, C09, C13 |
| No obsolete frontend/infra instructions | Current routes and stack | **FAIL** — C09, C28, C29 |
| No secret exposure | Literal key/credential values | **PASS** — §4 positive finding |
| Historical documents retained | Superseded docs preserved | **PASS** — none deleted |

---

## 9. Controlled consolidation sequence (recommended, not executed)

1. **Batch 0 — Authority reconciliation (needs owner confirmation).** Confirm 53 locked decisions; resolve OD-56 collision (C02); confirm OD-47/52 status; confirm 16-system count; confirm OD-46 primary wording; decide which document owns implementation status. Update only `IAM_OWNER_DECISIONS.md` and `ARCHITECTURE_INDEX.md` for these items.
2. **Batch 1 — Index and navigation.** Remove hard-coded counts; replace wildcard references; add the "derived implementation specifications" tier; link the completion audit as implementation-status evidence; add HISTORICAL banners to the seven superseded docs and the 26/32-decision audit report.
3. **Batch 2 — Decision-ID and model-identity sweep.** C03, C04, C15, C16; preserve unique requirement text while replacing duplicated explanations with references.
4. **Batch 3 — Completion-claim correction.** C06, C11, C12, C20, C22, C23, C24, C31. Insert the seven-field intended/implemented/evidence/limitations table from §6 into the relevant specifications, not into a new master spec.
5. **Batch 4 — Duplicate and orphan reconciliation.** Phase 10 specs, near-duplicate notes, stale README architecture list; merge unique requirements into their authoritative parents and leave dated pointers.
6. **Batch 5 — Link and count hygiene.** C08, C17, C25–C29, C33; resolve the 49 unresolved backticked references in §5.2 (without creating planned files by accident), convert notation to prose, fix deleted frontend paths, regenerate generated artefacts, then re-check every internal link.
7. **Batch 6 — Final validation.** Re-run the gate table in §8; confirm no historical document or locked decision was removed; confirm working-tree user edits preserved.

No source code, frontend page, infrastructure file, model identity, primary model or owner decision has been changed by this report.

---

## 10. Decisions required from the owner before Batch 0

1. Decision count: confirm **53 locked** (OD-01…OD-52 + OD-56), with OD-53/54/55 proposed.
2. OD-56: keep Financial Amendment A; assign a new ID to the paid-model proposal.
3. System count: confirm **16 canonical systems A–P** and retire "15 systems" wording.
4. Primary model: confirm the single sentence to use everywhere for OD-46.
5. Implementation status: confirm whether `IAM_ARCHITECTURE_COMPLETION_AUDIT.md` becomes the designated implementation-status document (recommended) or whether a new, short status register is wanted.
6. Frontend scope: confirm the current page set before rewriting `IAM_FRONTEND_IMPLEMENTATION.md`.

---

## 11. Batch 0 resolution record (28 November 2026)

Owner-confirmed values applied: **53 locked decisions**; **OD-56 = Financial Intelligence Amendment A** (paid proposal renumbered to **Doc 37 / OD-57**, still proposed); **Qwen2.5-3B / `local-qwen-3b`** as shared primary; `IAM_ARCHITECTURE_COMPLETION_AUDIT.md` as the designated implementation-status document; frontend scope aligned to the working tree. **System count (C05) was left unanswered and is deliberately unchanged.**

| Conflict | Resolution applied | Locations edited |
|---|---|---|
| C01 decision count | Normalised to 53 (OD-01…OD-52 + OD-56); register's "ALL FIFTY-ONE" heading corrected | `ARCHITECTURE_INDEX.md:13,55`; `IAM_FINAL_CONSOLIDATION.md:42`; `README.md:5,257`; `IAM_IMPLEMENTATION_TECHNOLOGY_ADDENDUM.md:60,102`; `IAM_OWNER_DECISIONS.md:3,111`; `IAM_ARCHITECTURE_COMPLETION_AUDIT.md:19,211`; `tools/rkie/RKIE_CAPABILITY_AUDIT.md:71` |
| C02 / C03 identifier collisions | OD-56 kept for Amendment A; paid proposal is OD-57/Doc 37; OD-53/Doc 33 assigned to Web3/node; dangling `IAM_OD53_SIGNOFF_SHEET.md` reference removed | `ARCHITECTURE_INDEX.md:13,169,172`; `IAM_OWNER_DECISIONS.md:3,281`; `IAM_PAID_MODEL_ACCESS_DECISION.md:3,8,52`; `IAM_OD54_SIGNOFF_SHEET.md:6`; `IAM_UNIVERSAL_MODEL_PROVIDER_ORCHESTRATION_SPEC.md:153` |
| C04 primary model | Coder-as-primary statements replaced with OD-46's 27 Nov value; historical benchmark references retained | `IAM_OWNER_DECISIONS.md:123,204`; `IAM_UNIVERSAL_MODEL_PROVIDER_ORCHESTRATION_SPEC.md:18`; `IAM_IICS_GAP_CLOSURE_ADDENDUM.md:17`; `IAM_LIVE_INFORMATION_AND_WEB_INTELLIGENCE_SPEC.md:37,146,150`; `IAM_OD54_SIGNOFF_SHEET.md:29`; `IAM_MULTI_MODEL_INTELLIGENCE_GOVERNANCE_SPEC.md:22`; `IAM_INDEPENDENT_AI_RESEARCH_DEVELOPMENT_AND_EVOLUTION_ARCHITECTURE.md:126,143`; `IAM_HUMAN_BEHAVIOUR_EQUALITY_AND_RESPONSIBILITY_SPEC.md:461`; `research/colab/README.md:4`; `tools/rkie/notes/live-information-policy-doc34.md:82` |
| C07 OD-47/48/52 status | "Proposed/pending" wording replaced with confirmed status; OD-47 explicitly described as owner confirmation, not a signed Creator decision | `IAM_IICS_GAP_CLOSURE_ADDENDUM.md:14,31,94,120,131,232,243–244`; `IAM_BROWSER_INTELLIGENCE_MASTER_SPEC.md:5,7,48,426,521,788,794`; `IAM_IP_AND_LEGAL_INTELLIGENCE_MASTER_SPEC.md:5,7,40,49,577`; `IAM_RESEARCH_ACQUISITION_AND_LEGAL_INTELLIGENCE_SPEC.md:3,5,8`; `IAM_OWNER_DECISIONS.md:241`; two dated notes |
| C13 / C15 Doc 27 wording | "OD-45-style" replaced with OD-47 owner confirmation; Doc 28's inherited requirement row aligned to twelve channels | `IAM_RESEARCH_ACQUISITION_AND_LEGAL_INTELLIGENCE_SPEC.md:3,5,8`; `IAM_IP_AND_LEGAL_INTELLIGENCE_MASTER_SPEC.md:49` |
| C09 / C32 frontend scope | Current routes recorded (`/`, `/suggestions`, `/conversations`, `/conversations/[id]`); underscore panels marked non-routable; README title uses canonical IAM identity; the 25 Nov one-route claim marked historical | `IAM_FRONTEND_IMPLEMENTATION.md:7–20`; `README.md:1,13,105`; `IAM_FINAL_CONSOLIDATION.md:240`; `IAM_BROWSER_AND_GEO_BACKEND.md:3`; `tools/rkie/notes/frontend_internal_views.md:6` |
| C14 status owner | New `1 — status` row added to the index source-of-truth table; README status line points to the audit | `ARCHITECTURE_INDEX.md:14`; `README.md:5,261` |

### Batch 0 validation

- Re-scan for `41 decisions`, `44 owner decisions`, `49 locked`, `52 decisions`, `46-decision`, `OD-53/Doc 33`, and Coder-as-primary claims: **no unresolved instances remain in active documents**. Matches in this report are historical quotations of the audit findings and are labelled as such.
- No source code, test, infrastructure, model identity, primary model or locked decision was changed. No historical document was deleted. The two untracked notes were left in place.
- Working-tree activity was observed during the session (status entries grew from 92 to 115, including frontend route changes). Re-verify the tree immediately before Batch 1; treat concurrent-owner edits as authoritative over this report's snapshots.

### Deferred to later batches

C05 system count (owner did not answer); C06 detailed completion claims beyond the status line; C08 dated gate numbers; C10 map chronology; C11–C12 evidence thresholds and HBI module status; C16 creation of a sign-off sheet (only the dangling reference was removed); C17–C31 counts, stale operational notes, orphan documents and link hygiene.

## 12. Batch 1 resolution record (28 November 2026)

Batch 1 was index and navigation cleanup. No owner decision, source file, frontend page or infrastructure file was changed. System-count wording remains untouched (owner answer still pending).

| Item | Action | Locations |
|---|---|---|
| Derived authority tier | Added an explicit "Derived implementation specifications" tier to the index with 18 entries, each naming its authority parent. These are navigation entries, not new authorities. | `ARCHITECTURE_INDEX.md` after source-of-truth table |
| Circular supersession | `MASTER_SPECIFICATION.md` now points to the consolidation and canonical Docs 01–04, not to a document that is itself superseded. | `ARCHITECTURE_INDEX.md`, superseded list |
| Hard-coded repository counts | Replaced with current counts plus an explicit "at last count / navigation aid only" rule: 77 root `IAM_*.md`, 94 route modules, 105 direct / 295 recursive service modules, 66 SQL files (001–069), 628 backend Python files. | `ARCHITECTURE_INDEX.md`, repository map |
| Canonical document list | Expanded `canonical/IAM_DOC_01…04` into four real paths so the notation is no longer an unresolved reference. | `ARCHITECTURE_INDEX.md:14` |
| Broken canonical reference | `IAM_DOC_02_INTELLIGENCE_EVOLUTION.md` → `canonical/IAM_DOC_02_INTELLIGENCE_EVOLUTION.md`. | `IAM_FOUNDATION_MODEL_AND_INTELLIGENCE_SPEC.md:7` |
| Superseded parents | 22 `Parent:` headers repointed from the superseded master/gap-analysis documents to canonical Doc 01 via the consolidation. Only the explicitly historical `IAM_DISTRIBUTED_GAP_ANALYSIS.md` still names the superseded gap analysis. | 22 numbered specifications |
| Historical banners | Added "HISTORICAL — SUPERSEDED / NOT CURRENT STATUS" banners to `IAM_MASTER_ARCHITECTURE.md`, the three early companions, both gap analyses, `MASTER_SPECIFICATION.md` and `IAM_ARCHITECTURE_AUDIT_REPORT.md` (the last marked as a dated snapshot). No document was deleted. | 8 files |
| README architecture list | Superseded drafts moved under a "Superseded — historical only" heading; current documents remain under "Derived / working specifications". | `README.md` architecture section |

### Batch 1 validation

- Re-scan of `**Parent:**` headers: only one match remains, in a document with a HISTORICAL banner.
- Re-scan of `FROZEN — companion to IAM Master Architecture`: no matches remain.
- Index authority table is unchanged except for the confirmed decision-count row, the new status row and the expanded canonical paths.
- Working-tree activity continued during this batch (status entries grew to 124). All edits were targeted string replacements; concurrent-owner changes were preserved.

### Still deferred

C05 system count (owner answer pending); C06/C11/C12 completion and evidence claims; C08 dated gate numbers; C10 map chronology; C16 sign-off sheet creation; C17 stale operational notes; C25–C31 remaining count/link hygiene; C13's full five-vs-twelve reconciliation beyond the IPLCI inheritance row.

*End of report. Batches 0–1 applied targeted edits only; no document, decision or source file was rewritten wholesale.*
