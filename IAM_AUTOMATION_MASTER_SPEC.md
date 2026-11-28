# IAM — Automation Master Specification & Implementation Audit

**Version:** 1.0 · 28 November 2026
**Status:** AUTHORITATIVE CONSOLIDATION of the automation discussion record; **derived** implementation-status record. It does **not** create an owner decision, a new top-level system, or a new queue.
**Scope:** Every automation system, subsystem and capability named across the accumulated IAM discussions, reconciled against the frozen architecture and the repository working tree at `c02f706` (branch `testing`, 28 modified/untracked entries at audit time).
**Authority:** This document is subordinate to `ARCHITECTURE_INDEX.md` (entry point), `IAM_FINAL_CONSOLIDATION.md` (master gap analysis) and `IAM_OWNER_DECISIONS.md` (locked OD register). Where a conversation-derived name and the frozen baseline disagree, the frozen baseline wins for **intent**, source code wins for **what runs**, and the disagreement is recorded here as a gap. Per `AGENTS.md` §1, the source-of-truth tables in `ARCHITECTURE_INDEX.md` are **not** rewritten by this document.

> **Purpose.** End the repeated re-invention of already-agreed automation. One place holds every name, every status, every permission boundary and every acceptance criterion; nothing is called complete without evidence.

---

## 1. Why this document exists

Across the preceding discussions, the automation inventory was expanded five times (16 domains → 28 divisions → 36 domains → successive corrections). Each pass found real omissions, but the expansions were **organisational**, not architectural: almost every named system is a responsibility boundary or capability inside the frozen 16 canonical systems A–P (`canonical/IAM_DOC_01_MASTER_ARCHITECTURE.md` §3), not a seventeenth top-level system.

This document therefore does three things:

1. **Consolidates** every name into one crosswalk (§5) and one capability inventory (§6).
2. **Audits** each entry against code, tests and gates in the current tree (§3, §6, §11).
3. **Fixes the completion rule** (§12): a capability may be marked complete only against the evidence ladder in §2.

The objective is not "36 built systems". It is that every agreed capability belongs somewhere, is governed by the same authority, and is not rebuilt.

---

## 2. Status and evidence vocabulary (mandatory)

### 2.1 Maturity ladder (from `IAM_ARCHITECTURE_COMPLETION_AUDIT.md` §1)

| Level | Meaning | Minimum exit evidence |
|---|---|---|
| **0 — Not defined** | No agreed design | — |
| **1 — Specified** | Frozen spec / OD exists, no implementation | Document with acceptance criteria |
| **2 — Implemented** | Code exists | Unit test(s) exercising the behaviour |
| **3 — Integrated** | Wired into the live runtime path with enforcement | Integration test + permission/audit check on the actual call path |
| **4 — Verified** | Proven under operating conditions | Scripted acceptance (A) or live proof (L), recorded with date and command |

### 2.2 Status labels used in this document

| Label | Definition | Never used when… |
|---|---|---|
| **IMPLEMENTED** | Maturity 3–4 with named code and test evidence | enforcement is only documented, or a route merely flips a status string |
| **PARTIAL** | Real code at maturity 2 with identified integration/enforcement/verification gaps | there is no code at all |
| **SPECIFIED** | Maturity 1 — frozen design, no implementation evidence | a spec exists but was never frozen (use PROPOSED) |
| **MISSING** | No implementation evidence found in the tree for an agreed capability | absence has only been inferred from old notes (then: NOT EVIDENCED) |
| **PROPOSED** | Overlay/decision awaiting signature; explicitly outside the frozen baseline | an OD is confirmed anywhere in `IAM_OWNER_DECISIONS.md` |

### 2.3 Evidence classes appended to status cells

`D` documentation only · `U` unit test · `I` integration test · `A` scripted acceptance (single-node) · `L` live/operational proof · `C` CI gate executed · `N` not evidenced in this pass.

**Rule:** a database row, a status string, a docstring claim or a historical pass count is **not** evidence of completion (`IAM_ARCHITECTURE_COMPLETION_AUDIT.md` G23; `IAM_COMPLETION_PLAN.md` §1.4).

---

## 3. Current gate snapshot (executed for this document)

**Tree:** `HEAD c02f706`, branch `testing`, 28 modified/untracked entries — includes uncommitted orchestration, config, frontend and a new `local_ollama_training.py`. All numbers below are **dated snapshots**, not permanent truth; re-run the protocol in §10.3 before relying on them.

| Gate | Command | Result at `c02f706` |
|---|---|---|
| Static analysis | `python -m ruff check backend` | **PASS** |
| Migration contract | `python tools/api/check_migrations.py` | **PASS** — 66 on disk / 66 in manifest / 0 duplicate prefixes |
| OpenAPI contract | `python tools/api/print_openapi.py --check` | **PASS** — 849 live paths / 482 schemas, snapshot matches |
| Unit tests | `python -m pytest backend/tests -q --no-cov` | **PASS — 1075 passed, 29 subtests passed** (54 warnings) |
| Coverage | `python -m pytest backend/tests -q --cov=app --cov-fail-under=60` | **PASS — 1075 passed, 29 subtests, 66.34%** (gate 60% met). An initial run hit a stale zero-byte `.coverage.*` temp-file `INTERNALERROR`; removing that artefact made the standard gate pass. |
| mypy ratchet | `python tools/quality/check_mypy_ratchet.py` | **OK** — 1951 errors, baseline 2000, **0 new**, 49 fixed. The 3 new errors seen earlier in uncommitted `orchestration/model_development.py` were resolved by concurrent work; no baseline regeneration was used. |
| RKIE smoke | `./tools/rkie/tests/Test-RKIE.ps1` | **PASS — 20/20** |
| RKIE freshness | `./tools/rkie/Check-IndexFreshness.ps1` | **FRESH** after `./tools/rkie/Update-Index.ps1` (1036 files; base = HEAD `c02f706`) |
| Supply chain | `pip-audit` | Last recorded **PASS** after removal of unused `ecdsa`/`python-jose`; not re-run in this pass |
| Live stack / acceptance / GitHub Actions | — | **Not executed in this pass** — dated results only (§11.1) |

**Consequence:** the automation architecture is *not* blocked by missing design. The local gate debt was cleared on 28 November 2026 (mypy 0 new, RKIE FRESH, coverage 66.34%); what remains is the CI-environment discrepancy and the unresolved capability items in §11.

---

## 4. Authority, decisions and governance boundaries

### 4.1 Frozen canonical systems (48-hour reference, unchanged)

| ID | Canonical system (`IAM_DOC_01` §3) | Automation purpose |
|---|---|---|
| A | Identity and Constitution | Permanent identity, personality, principles, authority boundaries |
| B | Intelligence and Reasoning | Foundation models, reasoning, planning, evaluation, task intelligence |
| C | Model Provider and Routing | NVIDIA NIM, hosted APIs, open weights, local inference, model selection |
| D | Memory and Knowledge | Memory tiers, experiences, embeddings, provenance, memory permissions |
| E | Autonomy and Goal Management | Goals, priorities, plans, tasks, schedules, decisions, execution |
| F | Internet and Digital Interaction | Search, browser automation, retrieval, APIs, discovery, publishing |
| G | External AI Network | Discovery, protocols, delegation, independent response evaluation |
| H | Learning and Self-Development | Research, design, build, test, improve software and capabilities |
| I | Digital Workspace | Browser, terminal, files, editor, isolated execution, cloud resources |
| J | Multimodal Communication | Text, voice, speech, image, video, document understanding |
| K | Economic and Financial Management | Budgets, records, opportunities, revenue, expenses, reinvestment |
| L | Ecosystem and Project Management | IAM's applications, sites, businesses, projects, products |
| M | Governance and Security | Permissions, approvals, privacy, credentials, isolation, audit, security |
| N | Infrastructure and Resilience | Uptime, monitoring, backups, resources, recovery, scaling |
| O | Global Access and Concurrent Processing | Anonymous sessions, GeoIP, isolated conversations, queues, concurrency |
| P | Evaluation and Research | Reliability, model quality, reasoning, security, cost, improvement effect |

Every named automation system in §5 is mapped to one or more of A–P. No entry authorises a new top-level system.

### 4.2 Owner Decision register (compact; full text in `IAM_OWNER_DECISIONS.md`)

| Range | Decisions | Governance effect on automation |
|---|---|---|
| OD-01…OD-10 | Identity ULID+genesis (01), legal entity (02), hardware signer (03), **zero standing budget $10/txn + $100/month** (04), anonymous memory ON (05), **RPO 24h / RTO 4h** (06), SOPS secrets (07), **ARQ queue** (08), global privacy baseline (09), separate dev VPS (10) | Foundational identity, finance, recovery, queue and privacy constraints |
| OD-11…OD-16 | Protected core (11), hybrid P2P (12), restricted reporting (13), **IAM Aegis**, Shirudo reference-only (14), OEDIE free-first (15), white-hat defensive identity (16) | Authority, network trust, security posture, tool policy |
| OD-17…OD-25 | Replaceable dev environment (17), three Creator channels (18), email/signed approval, no Creator UI (19), privacy-preserving collective learning (20), sensitive-info guidance (21), ARM64+AMD64 (22), thirdweb free-only (23), ZA banking (24), **three-level financial authority** (25) | Workspace, approval, memory, hardware, blockchain, banking, finance |
| OD-26…OD-37 | Dynamic nodes + 1% voluntary contribution (26), **UWAIE** frontend-first interaction (27), assistant interoperability lab (28), **SDK/CLI** (29), frozen global research (30), legal/government monitoring (31), geospatial/live maps (32), psychology/tone defence (33), external AI identity/collaboration (34), free infrastructure nodes (35), AI SDK/framework research (36), traffic/distributed processing (37) | Node, browser, developer, research, legal, geospatial, collaboration automation |
| OD-38…OD-41 | Foundation models + competition (38), **IRWM** (39), **MEFE** (40), frozen autonomous research architecture / 14 engines (41) | Provider intelligence, resources, model development, research autonomy |
| OD-42…OD-46 | Creator CLI/signer channels (42), human behaviour & Equality of Existence (43), financial intelligence (44), **HBI 38 modules / 13 engines** (45), **Qwen2.5-3B as shared primary** (46) | Approval transport, behaviour intelligence, finance, local-model primacy |
| OD-47…OD-52 | Research acquisition & legal intelligence (47, owner-confirmed, **not** a signed Creator decision), **IPLCI** (48), **BIWOS/TIPS** (49), Voice & Hearing scope (50), multi-provider keys + fail-closed paid gate + bounded delegation (51), universal provider orchestration, free-only (52) | Acquisition, IP/legal, browser, voice, provider intelligence |
| OD-56 | Financial Amendment A — prediction markets, gaming research, investment research, **research-only** | Extended economic intelligence |
| Proposed (not frozen) | OD-53 Web3/node (Doc 35), OD-54 Live Information (Doc 34), OD-57 paid model access; IICS gap addendum | **Awaiting signed decision; not authority** |

**Four hard authority rules** (OD-03/04/11/19/25/51):
1. Protected core changes require the verified Creator signature; IAM cannot self-authorise.
2. Zero standing budget: every expenditure needs a signed approval; IAM cannot raise its own limits.
3. Paid model access is fail-closed: signed authorisation, remaining budget, limits and expected cost must all be determinable or the call is denied (OD-51 §4.3); OD-52 remains **free-only**.
4. External AI, peers and web content are untrusted inputs; no external system gains automatic authority over IAM.

---

## 5. Named-system crosswalk — every name from the discussions

This table is the answer to "nothing previously agreed gets forgotten". **Canonical** shows where each name lives; **Status** uses §2. Statuses are evidence-qualified, not aspirational.

| Name used in discussions | Canonical home | Authority / spec | Implementation evidence | Status |
|---|---|---|---|---|
| Mainbrain (central intelligence, reasoning, planning, decision) | A, B | Doc 01 §3; OD-46 | `orchestration/autonomy_graph.py`, `dispatch.py`, `reasoning_engine.py`, `attention_manager.py`, `services/iam_context.py`, `model_inference.py` | **PARTIAL / I** — one entry point and one durable graph; orchestration engines newly added and uncommitted; no live general-autonomy proof |
| Sub-brains / specialised agents | B, C, G | Doc 02; OD-51 §4.4, OD-52 | `services/delegation.py`, `orchestration/collaborative_intelligence.py`, `services/providers/`, `adaptive_model_selector.py` | **PARTIAL / U** — bounded delegation (≤3, 120s, 512MB, 4 calls) is gated and unit-tested; live multi-agent coordination not proven |
| Task orchestration (queues, workflows, parallel) | E | Doc 01; OD-08 (ARQ) | `orchestration/autonomy_graph.py`, `workers/arq_*`, `services/task*`, `api/routes/tasks.py` | **PARTIAL / I** — durable checkpointing + 13 graph integration tests; scheduled/executable tasks still largely CRUD |
| Web intelligence (research, browse, retrieve, monitor) | F, P | Docs 11/14/29; OD-49 | `search_service.py`, `research_service.py`, `browser_service.py`, `web_knowledge_service.py`, `api/routes/research.py` | **PARTIAL / A** — real pipeline, Wikipedia provenance accepted at L2; source-first SABC process not validated |
| Internet access (controlled egress) | F, M, N | Doc 03; security policy | `services/iics/egress.py`, `iics/permissions.py`, `api/routes/internetaccess.py`, `security_policy.py` | **PARTIAL / U** — permission gates and ledger exist; live egress enforcement not re-proven here |
| Background automation (scheduled, continuous) | E, N | OD-08; Doc 21 | `workers/autonomy_worker.py`, `workers/arq_iics_worker.py`, `arq_browser_worker.py`, `arq_model_catalog.py`, `iics/scheduler.py` | **PARTIAL / I** — ARQ runtime operational; long-running recovery unproven |
| Self-learning / autonomous learning engine | H | Doc 02; OD-41 | `orchestration/learning_engine.py`, `services/ai_research/continuous_improvement.py`, `ai_research/memory.py` | **PARTIAL / U** — engines exist; real corpora/studies outstanding |
| Self-improvement engine | H, P | OD-40/41/46 | `ai_research/self_improvement.py`, `release_gate.py`, `registry.py`, `post_deploy.py` | **PARTIAL / U** — signed release + rollback at L3; no silent production replacement |
| Model development / fine-tuning | H, C | OD-40 MEFE; OD-41 | `ai_research/training.py`, `dataset_engine.py`, `benchmarks.py`, `local_ollama_training.py` (untracked) | **PARTIAL / N** — code and gates exist; **no actual GPU fine-tuning run proven** |
| Provider intelligence / discovery / monitoring | C | OD-51, OD-52 | `services/providers/`, `model_discovery.py`, `model_credential_vault.py`, `iics/` registry, `api/routes/modeldiscovery.py` | **IMPLEMENTED / U** — dual discovery, vault, health probes, capability assignment unit-tested; live NVIDIA-name proof dated, DashScope alias 401 |
| Security governance | M | OD-11/14/16 | `aegis.py`, `security_policy.py`, `tool_authorization.py`, `cybersecurity/`, `auth_middleware.py`, `core/auth_policy.py` | **IMPLEMENTED / A** — Aegis 14/14 live; Aegis now called from `model_inference.py` before routing |
| Financial intelligence | K, L | OD-23/24/25/44/56 | `financial_intelligence/`, `ledger_service.py`, `trading/paper.py`, `economy.py`, `api/routes/financial_intelligence.py` | **PARTIAL / A** — paper trading, ledger, signed limits at L5; no live account/connector integration |
| Legal & compliance intelligence | M, P | OD-31/47/48 | `legal_service.py`, `services/iplci/`, `api/routes/iplci.py`, `api/routes/legal.py` | **PARTIAL / U** — `legal_service.authorise()` now verifies signed Creator authority; counsel validation outstanding |
| Human assistance (HAIS) | M, O | OEDIE/OD-19 | `services/human_assistance.py`, `api/routes/assistance.py`, `creator_communication.py` | **PARTIAL / U** — implementation + escalation path; **no real approval workflow proven end-to-end** |
| BIWOS (Browser Intelligence & Web Operations) | F, I | Doc 29 / OD-49 | `browser_service.py`, `browser_intelligence.py`, `browser_security_gateway.py`, `browser_infrastructure.py`, `browser_lifecycle.py`, `workers/arq_browser_worker.py`, `api/routes/browser*` | **PARTIAL / A** — permission matrix + evidence + backend slice; full multi-browser/DOM/visual stack (phases 4–8) not built |
| TIPS (Tor Intelligence & Privacy System) | F, M | Doc 29 / OD-49 | `tor_privacy.py`, `tor_intelligence.py`, `api/routes/tor.py` | **PARTIAL / U** — circuit isolation, kill switch, emergency stop; browser privacy QA not operationally proven |
| Browser Security Gateway | F, M | Doc 29 / OD-49 | `browser_security_gateway.py` (Aegis-based page analysis) | **PARTIAL / U** |
| Web Knowledge Integration | D, F | Doc 29 | `web_knowledge_service.py`, `api/routes/web_knowledge.py` | **PARTIAL / U** — never silently modifies trusted knowledge by design |
| IICS (Internet Intelligence & Connectivity System) | F, I, M, N | `IAM_IICS_GAP_CLOSURE_ADDENDUM.md` (**PROPOSED**) | `services/iics/` — egress, permissions, ledger, source_registry, qa, creator_email, search_strategy, scheduler, media, threat_intel, site_policy, tool_registry | **PARTIAL / N** — overlay code wired; governing addendum not part of frozen baseline |
| UWAIE (Universal Website Interaction Engine) | F, I | Doc 11 / OD-27 | `api/routes/uwaie.py`, `IAM_BROWSER_AND_GEO_BACKEND.md` first slice | **PARTIAL / N** — first gated slice only; full frontend-first multi-browser/visual stack absent |
| PPIICE (Public Presence Intelligence) | O, P | Doc 14 / OD-30 | `socialpresence_service.py`, `api/routes/humanpresence.py`, `external_presence.py`, `digital_reputation.py` | **PARTIAL / A** — human-presence smoke passed; privacy safeguards must be re-verified |
| IRWM (Intelligent Resource & Workload Manager) | B, C, N | OD-39 | `services/irwm.py`; `model_inference.py:69 admit()`, `:98 release()`; `api/routes/irwm.py` force-release | **IMPLEMENTED / U** — on the real inference path; **open defect P0-3: stale `in_flight` lease during hosted calls** |
| World Model | D | Doc 01 §3 D; memory/knowledge specs | `worldmodel_service.py`, `api/routes/worldmodel.py` | **PARTIAL / U** |
| Autonomous Research Engine | H, P | OD-41 parent architecture | `ai_research/coordinator.py`, `jobs.py`, `scheduler.py`, `colab_mcp_driver.py`, `adapters/` | **PARTIAL / N** — real free-tier job submission and artifact persistence not proven; MCP tested against stub |
| Continuous Improvement Engine | H, P | OD-41 | `ai_research/continuous_improvement.py`, `self_improvement.py`, `evaluation_suite.py` | **PARTIAL / U** — five-domain manifest suite replaced the 5-item eval set |
| AI Collaboration System | G | Doc 03 §7; Doc 18 / OD-34 | `ai_communication.py`, `collaborative_intelligence.py`, `ainetwork_service.py`, `attestation_service.py` | **PARTIAL / A** — human-mediated ChatGPT bridge, not automated conversation extraction; external AI never gains authority |
| IAM SDK (TypeScript, Python) | N, O (cross-cutting) | Doc 13 / OD-29 | `sdk/typescript/`, `sdk/python/`, `sdk/PROTOCOL.md` | **PARTIAL / U** — first-class protocol scaffold; CLI contract tests pass locally |
| IAM CLI (`iam`) | N, O | Doc 13 / OD-29 | `sdk/cli/` | **PARTIAL / N** — `login` and `dev init` stubs; `@iam/sdk` vs `@iamagris/sdk` name mismatch (G13) |
| Node management / dynamic nodes | N, G | Doc 10 / OD-26 | `api/routes/nodes.py`, `p2p_transport.py`, `free_sandboxes/manager.py` | **PARTIAL / A** — 1% ceiling enforced in code; live multi-node unproven |
| Remote workspace / WH-01…WH-09 | I | Doc 06 | `services/workspaces/` (service, providers, remote_adapters), `api/routes/workspaces.py` | **PARTIAL / U** — isolation and provisioning exist; full WH component set not demonstrated |
| IAM Aegis / Shirudo | M | OD-14/16 | `aegis.py`, `cybersecurity/`, `api/routes/aegis.py`, `tests/aegis_acceptance.py` | **IMPLEMENTED / A** — 7 components, 14/14 live; Shirudo is reference only, never a dependency |
| IAM Operating System / Control Plane | M, N | Consolidation inventory | `api/routes/ops.py`, `governance_service.py`, `event_stream.py`, frontend control surfaces | **PARTIAL / U** — control-plane services exist; no single audited control-plane view |
| Development Environment Manager | I, H | OD-10/17 | `free_sandboxes/`, `api/routes/development.py`, `development_governance.py` | **PARTIAL / U** — isolated environments; default-off in standard deployment |
| Skill Forge / Skill Runtime | H, I | Skill specs (index map) | `services/skillforge/`, `skillruntime/`, `iam/skills/`, `api/routes/skillforge.py`, `skillruntime.py` | **PARTIAL / U** — phases 1–2 implemented; skill store empty (`.gitkeep` only), runtime default-disabled |
| IAM WIBO / Web3 | K, M | Doc 09; **Doc 35 / OD-55 PROPOSED** | `services/blockchain/` (24 modules), `api/routes/web3.py`, `web3_extended.py`, default-off flags | **SPECIFIED + PROPOSED / N** — research/prepare code exists; no execution, paid tier or mainnet value movement authorised |
| Distributed storage | N | Doc 05; Doc 08 | `api/routes/storage.py`, `ai_research/s3_store.py`, S3/MinIO config | **PARTIAL / U** — S3-compatible store; dynamic placement/IPFS/BitTorrent distribution not implemented |
| Distributed computing | N | Docs 05/08/10/21 | ARQ workers, P2P transport, free-sandbox adapters | **PARTIAL / A** — two-peer gossip proven on one deployment; separate physical nodes not proven |
| Deployment integrity | N | OD-40/41 | `release_gate.py`, `integrity.py`, `api/routes/deployment.py`, supply-chain workflow | **PARTIAL / U** — signed release gates; no infra-drift check, no git tags |
| Creator Authority System / Cryptographic identity | A, M | OD-03/11/18/19/42 | `creatorapproval_service.py` (Ed25519 over one-time challenges), `creator_keys.py`, `api/routes/creator_keys.py`, `tests/signer_acceptance.py` 9/9 | **IMPLEMENTED / A** — IAM runtime never holds the private key; email carrier still owner action |
| Resource cost intelligence | N, K | OD-39, Doc 25 | `irwm.py`, `ledger_service.py`, `iics/ledger.py`, `model_usage` accounting | **PARTIAL / U** — fail-closed usage accounting unit-tested; cost optimisation not operational |
| Metacognition | B | Doc 02; completion audit G16 | `orchestration/attention_manager.py`, `intellectual_honesty.py`, `reasoning_engine.py`, `curiosity_engine.py`, `cross_domain_engine.py` (new/uncommitted) | **PARTIAL / N** — modules added, not independently verified |
| Knowledge verification / reputation / compatibility KB | D, P | OD-30/36/45 | `iics/qa.py`, `source_identity.py`, `technology_registry.py`, `digital_reputation.py`, `hbi/knowledge.py` | **PARTIAL / U** — provenance and credibility scoring; contradiction/freshness sweeping incomplete |
| Supply chain security | N | `supply-chain.yml`; OD-41 | `requirements.lock.txt`, `pip-audit`, CodeQL workflow | **IMPLEMENTED / C** — supply-chain workflow green after dependency remediation |
| Privacy & DLP | M | OD-05/09/20/48 | `privacy` config, `iics/threat_intel.py` DLPEngine, `services/iplci/`, `IAM_PRIVACY_AND_SECRETS.md` | **PARTIAL / U** — SOPS artefacts still absent (G11) |
| Incident response / global resilience | N, M | Docs 05/21; OD-06 | `resilience_service.py`, `api/routes/resilience.py`, `aegis.py`, Caddy/gateway config | **PARTIAL / A** — DR drill passed once against live Postgres; no general emergency stop, no real traffic failover |
| Independent verification | P, M | OD-34/41/49 | `orchestration/independent_evaluation.py`, `evaluation_suite.py`, `tests/level*_acceptance.py` | **PARTIAL / U** — evaluation suite wired; verification of agent output by local primary is a design rule, not a universally enforced runtime gate |
| Human psychology, tone, communication, social intelligence | J, B, O | Docs 17/24/26; OD-33/43/45 | `services/hbi/` (43 .py files), `tone_service.py`, `socialpresence_service.py`, `api/routes/hbi.py` | **PARTIAL / U** — substantial code; "38 modules implemented" vs docstring "modules 1–4 functional" unresolved |
| Device & environment interaction | I, J | Doc 12; OEDIE | `computer_use.py`, `api/routes/computer_use.py`, `api/routes/mobile.py`, `vision_service.py` | **PARTIAL / N** — ADB/mobile interaction default-off; `objects`/`text_ocr` hard-coded empty (G15) |
| Scheduling & continuous monitoring | E, N | Doc 21; OD-37 | `api/routes/scheduling.py`, `iics/scheduler.py`, `continuous-assurance.yml` | **PARTIAL / U** — scheduled runs exist; `schedule_at` ignored in `autonomous_web_task_service.create()` (G17) |
| Testing & quality intelligence | P | `AGENTS.md` §3 | 126 backend test modules + 20 root acceptance scripts; 8 CI workflows | **IMPLEMENTED / C** — 1075 tests pass locally; CI `types` job discrepancy unresolved |
| Control centre & central governance | M | Consolidation inventory | `governance_service.py`, `auth_middleware.py`, `core/auth_policy.py`, `event_stream.py`, `api/routes/governance.py` | **PARTIAL / U** — shared spine exists; no unified module-contract/capability registry |

---

## 6. Capability inventory (consolidated, grouped by canonical system)

The columns are deliberately compact: **Status** uses §2, **Evidence / gap** names the file or the missing proof. This is the single authoritative capability list; the 16 / 28 / 36-domain lists in the discussions are alternative groupings of these same rows.

### A–B — Central intelligence, reasoning, agents, orchestration

| Capability | Status | Evidence / gap |
|---|---|---|
| Permanent identity, constitution, genesis | **IMPLEMENTED / A** | `models/identity.py`, `identity_service.py`, genesis in `main.py`; ULID persistence at L1 |
| One shared model resolver and chat/stream path | **IMPLEMENTED / L** | `model_inference.py`; SSE streaming verified live; OD-46 primary `local-qwen-3b` |
| Durable cognitive cycle with real retrieval/dispatch/verification | **PARTIAL / I** | 14-node graph + `dispatch.py` + 13 integration tests; no live long-horizon autonomy run |
| Metacognition, attention, curiosity, honesty, hypothesis, transfer | **PARTIAL / N** | new orchestration modules present but uncommitted and unreviewed |
| Multi-agent delegation and bounded parallel sub-agents | **PARTIAL / U** | `delegation.py`, provider registry; 3/120s/512MB/4-call limits; independent review required |
| Goal → plan → task → decision → execution | **PARTIAL / A** | L2 accepted on single-node stack; `goals/tasks/scheduling` remain CRUD-only |
| Failure detection, retry, recovery branch | **PARTIAL / U** | bounded `recover` node in graph; no task survival proof across restart beyond checkpointing |

### C — Provider intelligence and routing

| Capability | Status | Evidence / gap |
|---|---|---|
| Local primary Qwen2.5:3B via Ollama | **IMPLEMENTED / L** | `local-qwen-3b` → `qwen2.5:3b`, real SSE verified; local wins when reachable |
| Hosted specialists through LiteLLM, free-only | **IMPLEMENTED / L** | NVIDIA `nemotron` returned READY; `qwen3.5-9b` 401 (missing usable key) |
| Encrypted provider-key vault + key/provider isolation | **IMPLEMENTED / U** | `model_credential_vault.py`, OD-51 §4.1–4.4 |
| Fail-closed usage accounting and budget checks | **IMPLEMENTED / U** | `model_usage`, per-request attribution; paid access not authorised (OD-57 proposed) |
| Dual model discovery, availability monitoring, capability assignment | **IMPLEMENTED / U** | OD-52; `model_discovery.py`, `api/routes/modeldiscovery.py` |
| IRWM residency gate on inference | **IMPLEMENTED / U** | admit/release in `model_inference.py`; **open P0-3 `in_flight` defect** |

### D — Memory, knowledge, world model

| Capability | Status | Evidence / gap |
|---|---|---|
| Semantic recall (pgvector + ILIKE fallback) | **IMPLEMENTED / A** | `memory_service.py`; persistence across restart at L1 |
| Knowledge base, provenance, public nodes | **IMPLEMENTED / A** | `api/routes/knowledge.py`; `interface/nodes` public-only |
| World model and environmental context | **PARTIAL / U** | `worldmodel_service.py` |
| Tiered memory (working/episodic/semantic/procedural/self/strategic) | **MISSING** | six flat types only; no consolidation, dedup or expiry sweeper |
| Knowledge freshness / contradiction detection | **PARTIAL / U** | `iics/qa.py`, source scoring; no deployed FTS5/hybrid ranking |

### E — Autonomy, tasks, scheduling

| Capability | Status | Evidence / gap |
|---|---|---|
| ARQ async queue runtime | **IMPLEMENTED / C** | OD-08; `workers/arq_*`, Docker services |
| Autonomy worker + durable graph | **IMPLEMENTED / I** | `autonomy_worker.py`, `autonomy_graph.py` |
| Scheduled website monitoring / change detection | **PARTIAL / N** | browser lifecycle routes exist; scheduled execution not demonstrated |
| Offline task queues and automatic reconnection | **PARTIAL / N** | P2P outbox proven in-process; offline→reconnect at node level unproven |

### F–I — Internet, external AI, learning, workspace, browser

| Capability | Status | Evidence / gap |
|---|---|---|
| Search → browse → extract → verify research pipeline | **IMPLEMENTED / A** | L2: 3 Wikipedia sources with credibility scores |
| Source-first retrieval (SABC process) | **MISSING** | specifically not validated; browser retrieval off by default |
| Browser engine management, multi-tab, DOM/visual intelligence | **PARTIAL / U** | browser substrate modules; no full multi-engine stack |
| Website compatibility intelligence | **PARTIAL / U** | `technology_registry.py`, compatibility matrix |
| Authenticated website operations, sessions, MFA/CAPTCHA handoff | **PARTIAL / U** | credential routes + HAIS; real handoff not proven |
| Account lifecycle, identity automation | **IMPLEMENTED / U** | identity/account routes at L1–L5 |
| Downloads/uploads, forms, evidence preservation | **PARTIAL / U** | browser evidence service; no full workflow proof |
| Isolated browser/workspace sessions + remote providers | **PARTIAL / U** | `workspaces/`, free sandboxes; default-off |
| External AI registry, interview, collaboration, independent verification | **PARTIAL / A** | OD-34; `ai_communication.py`; human-mediated bridge only |
| Free infrastructure node discovery / lifecycle | **PARTIAL / U** | Doc 19; `free_sandboxes/`; live quota/expiry migration unproven |

### J — Multimodal and voice

| Capability | Status | Evidence / gap |
|---|---|---|
| Voice & Hearing capability scope (12 components / 60 capabilities) | **SPECIFIED / D** | Doc 30 / OD-50 — capability scope only, no implementation claim |
| Speech recognition, synthesis, SSE voice path | **PARTIAL / U** | `voice_service.py`, `api/routes/voice.py`; UI never calls voice routes, STT fixed `en-US` |
| Image/video understanding, OCR, document/screen/sensor input | **PARTIAL / N** | `vision_service.py`; `objects`/`text_ocr` hard-coded empty |

### K–L — Economy, projects, Web3

| Capability | Status | Evidence / gap |
|---|---|---|
| Double-entry ledger, budgets, P&L, receipts, audit trail | **IMPLEMENTED / A** | `ledger_service.py`; L5 rejects unbalanced entries |
| Paper trading, strategy evaluation, emergency stop | **IMPLEMENTED / A** | `trading/paper.py`; signed stop |
| Income / crypto / payment research | **PARTIAL / A** | L5 opportunity discovery; no live connectors |
| Banking integrations (18 capabilities) and blockchain adapters | **SPECIFIED / N** | Doc 09 / OD-23/24; adapters default-off, no real account access |
| Prediction markets / gaming / investment research | **PARTIAL / N** | OD-56; read-only Polymarket adapter behind default-off flags; research-only |
| Wallet creation/import/recovery, multisig, DeFi, NFT, SIWE, x402 | **SPECIFIED + PROPOSED / N** | Doc 35 / OD-55 awaiting signature; no mainnet value movement |
| Signed spending authority, transaction/monthly limits | **IMPLEMENTED / A** | OD-04; enforced in ledger/trading/paid-gate paths |

### M — Governance, security, HAIS, legal, IP

| Capability | Status | Evidence / gap |
|---|---|---|
| Scoped API credentials, middleware, four-role ladder | **IMPLEMENTED / A** | `auth_middleware.py`, `core/auth_policy.py`; admin scope required for sensitive endpoints |
| Creator Ed25519 signing and one-time challenges | **IMPLEMENTED / A** | `creator_keys.py`, `creatorapproval_service.py`; signer acceptance 9/9 |
| Signed-authority check on finance, delegation, model release, legal | **IMPLEMENTED / U** | `legal_service.authorise()` now verifies signed approval |
| Aegis defensive engine (7 components) on inference path | **IMPLEMENTED / A** | `aegis.py`; `model_inference.py` inspects user/tool content before routing; skip system role |
| Protected-core boundary, tool gateway, authorised-target gate | **IMPLEMENTED / U** | `security_policy.py`, `tool_authorization.py`, `cybersecurity/` |
| HAIS escalation and human approval | **PARTIAL / U** | no real approval workflow proven end-to-end |
| Legal monitoring, law-change lifecycle, IPLCI gateway | **PARTIAL / U** | counsel validation outstanding; legal information is not legal advice |
| SOPS secrets / DLP / privacy enforcement | **PARTIAL / D** | no `.sops.yaml` or encrypted artefacts; Compose placeholder credentials |
| General emergency shutdown | **MISSING** | only paper-trading stop and Tor kill switch exist |

### N — Infrastructure, storage, deployment, resilience

| Capability | Status | Evidence / gap |
|---|---|---|
| Docker Compose stack, LiteLLM gateway, Caddy/gateway config | **IMPLEMENTED / A** | `docker-compose.yml`, `infra/litellm/`, live acceptance run |
| Backup + verified isolated restore drill | **IMPLEMENTED / L** | `backup_service.py`, `scripts/backup_restore_drill.py`; 245/245 tables, RPO/RTO met (dated live run) |
| Durable artifacts, model registry, signed release + rollback | **PARTIAL / U** | `ai_research/`; `serving_model.py` temp store vs configured durable store |
| ARM64/AMD64 | **PARTIAL / L** | arm64 OCI image built and inspected; not run on ARM64 hardware; frontend image not built |
| Distributed storage placement / IPFS / BitTorrent | **SPECIFIED / N** | docs only |
| Observability: spans, request IDs, alerts, dashboards | **MISSING** | `/metrics` is three hand-built gauges; OTLP endpoint config only |
| Supply chain / CodeQL / CI gates | **IMPLEMENTED / C** | 8 workflows; local gates pass, CI `types` discrepancy open |
| SOPS, infra drift check, git tags | **MISSING** | documented intent only |

### O–P — Global access and evaluation

| Capability | Status | Evidence / gap |
|---|---|---|
| Anonymous sessions, GeoIP context, concurrency, rate limits | **IMPLEMENTED / A** | Doc 04; L1 isolation/session tests; single `localStorage` session in UI |
| Multilingual/language profiles | **PARTIAL / U** | `languages.py`, translation services; UI hard-coded English |
| Five-domain evaluation suite + release/post-deploy gates | **IMPLEMENTED / U** | `evaluation_suite.py`, 6 tests; release gates absent from PR CI |
| L1–L5 acceptance suites | **IMPLEMENTED / A/L** | dated live runs all green (§11.1); CI runs nightly/manual only |
| Independent verification beyond the executing agent | **PARTIAL / U** | `independent_evaluation.py`; not a universal runtime gate |

---

## 7. Permission and authority model for every automation

Four distinct permission classes (from the discussions; enforceable through `core/auth_policy.py`, `tool_authorization.py` and Creator signing):

| Class | Meaning | Example IAM may do | Example requires Creator |
|---|---|---|---|
| **READ** | Access authorised information | Read public web sources, own memory, permitted knowledge | Private user data, protected-core files |
| **RESEARCH** | Investigate and analyse | Compare providers, research a service, prepare an account configuration, simulate trades | Accepting binding terms, accessing authenticated third-party areas without grant |
| **OPERATE** | Execute authorised operations | Create a workspace, run a browser workflow, post a signed transaction to a simulator | Production changes, protected-core modification, external commitment |
| **COMMIT** | Consequential / irreversible commitments | — | Purchase, payment, real trade, contract, model promotion, key change |

**Every action must carry:** an attributable identity (IAM/node/user, ULID + scope), a permission check, an audit record (`event_stream.py`), resource limits (OD-39), a cancellation path, independent verification, and the appropriate approval. Autonomy is **not** widened by success at a lower class: Research permission never implies Commit permission.

**Financial example:** IAM may research a provider, compare prices and *prepare* a configuration under READ/RESEARCH; purchasing the service or accepting an agreement requires signed COMMIT authority under OD-04/OD-25, with zero standing budget.

---

## 8. Autonomous workflow catalogue

| Workflow | Trigger | Path | Authority gate | Failure behaviour |
|---|---|---|---|---|
| Chat / reasoning | User or worker | `main.py` middleware → `model_inference` → Aegis → IRWM → LiteLLM/Ollama | OD-51 paid gate, OD-39 residency | Fail closed; block event without echoing content |
| Goal → plan → task → verify | Worker tick | `autonomy_worker` → `autonomy_graph` → `dispatch` → domain services → evidence-backed `verify` | Creator check node | Bounded `recover` branch; human escalation via HAIS |
| Research and provenance | Goal or schedule | `search_service` → `research_service` → `web_knowledge_service` → knowledge | Internet permission + legal/IPLCI gateway | Source rejected if unverified; no silent knowledge write |
| Browser workflow | Authorised task | ARQ browser worker → `browser_security_gateway` → browser substrate → `browser_evidence` | Permission matrix; sensitive actions require Creator | Session isolation; workflow recovery; evidence preserved |
| Scheduled monitoring | ARQ cron | `iics/scheduler` / scheduling routes → research → change detection | Read/Research only unless authorised | Retry with backoff; alert via HAIS |
| Model self-improvement | Eval regression or schedule | `evaluation_suite` → `ai_research` → `release_gate` → signed registry → `post_deploy` | OD-11/19/40/46; never silent production replacement | Rollback from signed previous model |
| Resource admission | Every inference | `irwm.admit()` → provider call → `release()` in `finally` | OD-39 ceilings | Queue, delegate or refuse; never sacrifice core services |
| Backup / DR | Schedule or drill | `backup_service` → pg_dump → SHA-256 → isolated pg_restore → RPO/RTO audit | Operator/Creator scope | Production DSN restore refused; audit records redacted |
| P2P sync | Peer event | signed envelope → dedup → outbox → WebSocket gossip | Trust state (candidate/trusted/restricted/revoked) | Offline outbox; revoked peer refused |
| Paid inference (not enabled) | Explicit request | vault key → signed auth → budget/limit/cost → usage record | OD-51 §4.3, OD-57 proposed | Deny if any value undeterminable |

---

## 9. APIs, integrations and dependencies (evidence map)

| Layer | Concrete surface |
|---|---|
| API routes (94 modules) | `aegis, ainetwork, ai_communication, assistance, assistantlab, auth, autonomous_web_task, autonomy, bootstrap, browser, browser_agents, browser_infrastructure, browser_intelligence, browser_knowledge, browser_lifecycle, browser_security, capabilities, computer_use, conversations, creatorapproval, creator_communication, creator_keys, cybersecurity, decisions, deployment, development, digitalassets, digital_reputation, digital_security, economy, events, external_presence, financial_adapters, financial_intelligence, freenodes, freesandboxes, geo, globalaccess, goals, governance, hbi, humanpresence, identity, iics, integrity, internetaccess, iplci, irwm, knowledge, languages, legal, lifemanagement, live_information, memory, mfa, mobile, modelcredentials, modeldiscovery, modelindependence, modelrouter, models, nodes, ops, ownerauth, p2p, publicrecords, reflection, research, resilience, scheduling, skillforge, skillruntime, skills, socialpresence, storage, suggestions, tasks, technology_registry, tone, tools, tor, uwaie, vision, voice, web3, web3_extended, websitecredentials, web_account, web_consent, web_knowledge, whitehat, workspaces, worldmodel` |
| Runtime services | 105 top-level modules + `ai_research` (29), `hbi` (43), `iics` (11), `workspaces` (4), `blockchain` (29), `financial_intelligence` (3), `skillforge`, `skillruntime`, `trading`, `banking`, `providers`, `free_sandboxes`, `cybersecurity`, `iplci`, `prediction_markets`, `gaming_intelligence`, `investment_intelligence` |
| Orchestration | `autonomy_graph`, `dispatch`, `reasoning_engine`, `attention_manager`, `learning_engine`, `model_development`, `evaluation_suite`, `independent_evaluation`, `curiosity_engine`, `hypothesis_engine`, `cross_domain_engine`, `grounded_intelligence`, `intellectual_history`, `intellectual_honesty`, `collaborative_intelligence`, `agency_engine` |
| Workers | `autonomy_worker`, `arq_browser_worker`, `arq_iics_worker`, `arq_model_catalog`, `arq_creator_email`, `creator_email_worker` |
| Storage | 57 ORM models; 66 numbered SQL migrations + 2 Alembic revisions; pgvector/pgvector fallback; S3-compatible `ai_research/s3_store`; SQLite `AsyncSqliteSaver` checkpoints |
| Infrastructure | `docker-compose.yml` (+ benchmark, ram-profile), `infra/litellm/config.yaml`, `infra/caddy`, `infra/gateway`, `infra/postgres`, `infra/cloudflare` (docs), `.github/workflows` (8) |
| Client ecosystem | `sdk/typescript`, `sdk/python`, `sdk/cli`, `sdk/PROTOCOL.md` |
| Repository intelligence (independent of the primary model) | `tools/rkie/`, `ARCHITECTURE_INDEX.md`, `audit_architecture.py` — must not be rebuilt under `backend/app/` (`AGENTS.md` §4) |

**Do-not-duplicate rule:** before adding any search, memory, knowledge or RAG capability, inspect `search_service.py`, `memory_service.py`, `research_service.py`, `hbi/knowledge.py`, `hbi/hkg.py`, `worldmodel_service.py`, `web_knowledge_service.py`, `reflection_service.py` and `ai_research/memory.py` (`ARCHITECTURE_INDEX.md` §"Existing systems").

---

## 10. Completion criteria and acceptance

### 10.1 The ten mandatory criteria — honest current verdict

| # | Criterion | Verdict | Evidence / remaining gap |
|---|---|---|---|
| 1 | Autonomous plan → execute → monitor → complete | **NOT MET** | L2 accepted on single-node stack; live long-horizon unattended run absent |
| 2 | Task persistence across restarts/failures | **PARTIAL** | `AsyncSqliteSaver` checkpoints + L1 persistence; P2P/IRWM/research state in-memory |
| 3 | Intelligent delegation and evaluation | **PARTIAL** | Bounded delegation + independent evaluation; no live multi-agent coordination proof |
| 4 | Continuous research/monitoring/knowledge acquisition | **PARTIAL** | Real pipeline; browser retrieval off by default; SABC source-first unvalidated |
| 5 | Controlled self-improvement | **PARTIAL** | Signed release/rollback gates; no silent production replacement; no real GPU fine-tune run |
| 6 | Governed execution under one policy | **PARTIAL** | Shared middleware + Aegis + IRWM gates; no universal module contract or capability registry |
| 7 | Financial governance | **PARTIAL** | Signed authority, limits, ledger, paper trading proven; no real account/payment integration |
| 8 | Legal governance | **PARTIAL** | IPLCI gateway + signed legal authority; counsel validation and jurisdictional review outstanding |
| 9 | Independent verification (tests, security, operational) | **PARTIAL** | 1075 local tests, gates, A/L acceptance; CI `types` discrepancy, coverage tool error, mypy drift |
| 10 | Failure recovery and human assistance | **PARTIAL** | Backup/restore drill + recovery node; no general emergency stop, no proven real approval workflow |

**Overall:** IAM is **not fully verified as an autonomous system**. Architecture: extensively defined. Implementation: significant. Integration and real-world autonomy: not established. Production readiness: not established.

### 10.2 Acceptance ladder (`IAM_FINAL_CONSOLIDATION.md` §6)

| Level | Exit test | Last recorded result |
|---|---|---|
| L1 Operational | Identity survives restart, multi-turn chat, health, backup restores | 14/14 + 3/3 (25 Nov); 14/0 in live 27 Nov run |
| L2 Independent | Provenance research, goal→plan→task, self-escalation rejected | 20/20 (live 27 Nov) |
| L3 Self-developing | Isolated dev, tested change, signed release, rollback | 13/13 (live 27 Nov) |
| L4 Distributed | Multi-arch, peer sync, revoked peer refused, restricted reporting | 20/20 single-node semantics; ARM64 **build** only; two-peer gossip on one deployment |
| L5 Ecosystem | Multiple projects, ledger reconciles, owner approval enforced | 13/13 (live 27 Nov) |

These are dated, mostly single-node results. Re-run under the CI protocol before treating them as current.

### 10.3 Verification protocol (record HEAD, date and full output)

```powershell
git rev-parse HEAD; git status --short
python -m ruff check backend
python tools/api/check_migrations.py
python tools/api/print_openapi.py --check
python -m pytest backend/tests -q --cov=app --cov-fail-under=60
python -m pytest backend/tests -q --no-cov
python tools/quality/check_mypy_ratchet.py
./tools/rkie/Check-IndexFreshness.ps1
./tools/rkie/tests/Test-RKIE.ps1
python audit_architecture.py
```

Acceptance scripts: `tests/level1_acceptance.py` … `tests/level5_acceptance.py`, `tests/aegis_acceptance.py`, `tests/signer_acceptance.py`, `tests/p2p_acceptance.py`, `scripts/backup_restore_drill.py`.

---

## 11. Open items and owner actions

### 11.1 Current gate debt (from §3)
- **O-1 / O-2 / O-3 — CLOSED (28 Nov 2026).** mypy ratchet OK with 0 new errors; `Update-Index.ps1` run and RKIE FRESH; stale zero-byte `.coverage.*` artefact removed and the standard coverage gate passes at 66.34%. No baseline was regenerated and no test weakened.
- **O-4 — OPEN** CI `quality-gates/types` discrepancy (HBI errors on GitHub runner, not locally) — requires an authorised push and authenticated CI-log review; do not suppress error codes.
- **O-15 — NEW** P0-3 (IRWM `in_flight` defect) has not been reproduced against the current tree: it now has lease IDs, a task done-callback release, a 120 s expiry sweep, a force-release route, and a separate bounded hosted pool. Treat the dated defect report as stale until a live hosted-call reproduction succeeds or fails.

### 11.2 Blocking capability gaps (from completion audit G1–G25, still open where not closed by §11.3)
- **O-5** General emergency shutdown across inference, workers, browser and trading (G6).
- **O-6** Source-first SABC retrieval validation; browser retrieval off by default.
- **O-7** Long-running task recovery and executable scheduled activity (G17).
- **O-8** P2P/IRWM/research-lifecycle state persistence and two **physical** nodes (G21).
- **O-9** Universal module contract / capability-discovery registry (G16).
- **O-10** Tiered memory lifecycle, real OCR/document input, UI voice wiring.
- **O-11** SOPS artefacts, infra drift check, git tags, real observability (G11, G25).
- **O-12** Skill store population and SDK CLI completion (G12, G13).
- **O-13** HBI "38 modules implemented" vs docstring "1–4 functional"; real corpora/studies.
- **O-14** Real GPU fine-tuning run and domain benchmarks beyond the five-domain manifest.

### 11.3 Items proven in the audit record (do not re-implement)
- Gates repaired and L1–L5 passed live (27 Nov); OpenAPI/migrations/RKIE green at that head.
- DR drill against real Postgres: 245/245 tables restored, RPO ~6.1 s, RTO ~4.7 s.
- Aegis and signer acceptance 14/14 and 9/9; P2P 9/9 (two peers, one deployment).
- Hosted inference: NVIDIA free endpoint READY; Aegis system-prompt over-block fixed.
- ARM64 backend OCI image built and inspected (440 MB, `linux/arm64`, 10 layers).
- OD-48/OD-49/OD-50/OD-51/OD-52/OD-56 confirmed; OD-47 owner-confirmed (not a signed Creator decision).

### 11.4 Human / external actions (cannot be performed by code)
| Item | Action |
|---|---|
| IPLCI legal validation | Qualified counsel verifies POPIA/GDPR/UK GDPR/EU AI Act/DMCA; official registry searches; FTO opinions |
| OD-55 / Doc 35 Web3 + nodes | Signed challenge; Umbrel/LND/CLN credentials; thirdweb secret; reviewed executor. No mainnet value movement before clearance |
| OD-54 / Doc 34 Live Information | Creator signature, Tavily key, STT provider |
| OD-49 Browser Phase 1 | Signed decision artefact, Xvfb profile, Firefox/WebKit runtimes, evidence retention policy |
| OD-03 Creator signer | `CREATOR_EMAIL` deliberately unset; email carrier remains an owner action |
| OD-57 paid model access | **Not authorised** — signed decision + per-expenditure approval required |
| Open specs A–G | Retention SLA, P2P D1–D5, ARM matrix + signed builds, load-test target, spending/tax/KYC policy, migration/incident procedures |

---

## 12. Completion rule and change control

1. **Nothing is complete without evidence** from §2 — a spec, a route, a database row or a historical pass claim is insufficient.
2. **No new top-level system** may be created for a name in §5; every name maps to canonical A–P. New capabilities extend an existing system and name their authority parent (`ARCHITECTURE_INDEX.md` derived tier).
3. **No duplicate intelligence systems**: repository search stays in `tools/rkie/`; runtime memory/knowledge and external research stay in the services listed in §9 (`AGENTS.md` §4). The search toolkit remains independent of Qwen.
4. **No silent authority expansion**: Research ≠ Operate ≠ Commit; protected-core and paid/binding actions always require the signed Creator path.
5. **No silent production model replacement**: candidate models go through evaluation, isolated testing and signed release with rollback (OD-40/46).
6. **Gate quarantine**: while the tree is dirty or a gate is red, record the state and re-run; do not baseline away drift or weaken a failing test to make a claim green.
7. **Amendment path**: changes to this document require a dated, evidence-bearing edit. Changes to architecture intent or OD decisions require the owner/Creator process and must be made in `ARCHITECTURE_INDEX.md` / `IAM_FINAL_CONSOLIDATION.md` / `IAM_OWNER_DECISIONS.md`, never by editing this file alone.

---

## 13. Sources and evidence index

**Authority:** `ARCHITECTURE_INDEX.md`, `IAM_FINAL_CONSOLIDATION.md`, `IAM_OWNER_DECISIONS.md`, `canonical/IAM_DOC_01_MASTER_ARCHITECTURE.md` (systems A–P).
**Status record:** `IAM_ARCHITECTURE_COMPLETION_AUDIT.md` (G1–G25, P0 §10, operational proof §11), `IAM_COMPLETION_PLAN.md` (P0/P1/P2 + owner actions), `IAM_DOCUMENTATION_INVENTORY_AND_CONFLICT_REPORT.md` (C01–C35), `IAM_ARCHITECTURE_AUDIT_REPORT.md` (historical snapshot), `tools/rkie/RKIE_CAPABILITY_AUDIT.md`, `tools/rkie/notes/*`.
**Specifications referenced:** Docs 05–32, 34–37 as listed in `ARCHITECTURE_INDEX.md` — notably Doc 11/29 (browser), Doc 13 (SDK/CLI), Doc 15/28/27 (legal, IPLCI, acquisition), Doc 18 (external AI), Doc 21/25 (traffic, finance), Doc 23/23-A/31/32 (models and providers), Doc 26 (HBI), Doc 30 (voice), Doc 34/35/36/37 (proposals).
**Repository evidence:** `backend/app/{api/routes,services,orchestration,workers,models,core}`, `tests/`, `sdk/`, `infra/`, `.github/workflows/`, `scripts/`, `tools/rkie/`.
**Snapshot basis:** audit executed 28 November 2026 against `HEAD c02f706`, branch `testing`, 28 dirty entries; gate results in §3 were run for this document. Historical acceptance figures are dated claims, not current truth.

### Coverage limit (stated honestly)
This consolidation reconciles **all five inventories supplied in the current conversation**, the authoritative documents indexed in `ARCHITECTURE_INDEX.md`, the conflict register and the working tree. It **cannot** certify that no discussion outside this conversation was missed, or that any capability works in a production environment that was not exercised here. "Not evidenced" always means absence of in-tree or in-session evidence — never proof of runtime failure.
