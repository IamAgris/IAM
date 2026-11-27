# IAM — Owner Decision Register

**Status:** ALL 53 LOCKED DECISIONS (OD-01…OD-52 plus OD-56; OD-53 and OD-55 are Web3/node proposals, OD-54 is the live-information proposal, and the paid-model proposal is OD-57 — all await signed owner approval).  
**Purpose:** Record of every locked owner decision (OD-01…OD-52 and OD-56) made during architecture finalisation. OD-47 is confirmed by explicit owner instruction; no decision remains pending.

---

## Decision summary

| ID | Decision | Recommended default | Your decision |
|----|----------|---------------------|---------------|
| OD-01 | Permanent identity scheme | ULID + immutable genesis record | ✅ **LOCKED — ULID + genesis record** |
| OD-02 | Owner relationship / legal entity | Named legal entity for economic activity | ✅ **LOCKED — company/entity designated by owner** |
| OD-03 | Owner authorization method | Approval UI + config-file fallback | ✅ **LOCKED — hardware key / external signer** (implementation dependency: physical token or external signing service for high-impact approvals) |
| OD-04 | Spending limits | $100/month ceiling, $10/transaction cap, owner-only increase | ✅ **LOCKED — zero standing budget; every expenditure requires an owner approval request (hardware-key signed)** |
| OD-05 | Memory ownership defaults | Session memory default; anonymous opt-in; accounts optional | ✅ **LOCKED — remember anonymous visitors by default** (opt-out, retention expiry and deletion controls required) |
| OD-06 | RPO / RTO | RPO 24h / RTO 4h | ✅ **LOCKED — RPO 24h / RTO 4h** |
| OD-07 | Secrets manager | SOPS-encrypted files + Docker secrets | ✅ **LOCKED — SOPS + Docker secrets** |
| OD-08 | Queue runtime | ARQ (async-native, Redis-backed) | ✅ **LOCKED — ARQ (async Redis)** |
| OD-09 | Privacy jurisdictions | ZA + EU baseline | ✅ **LOCKED — global by default** (GDPR, POPIA, CCPA and others designed in from start) |
| OD-10 | Self-development infrastructure | Separate dev VPS, no production credentials | ✅ **LOCKED — separate dev VPS / containers** |

---

## Additional confirmed decisions (24 November 2026)

| ID | Decision | Confirmed value |
|----|----------|-----------------|
| OD-11 | Modification authority | **Protected core only** — only the original creator may authorize changes to permanent identity/constitution, core intelligence architecture, core source code, security policies/trust rules, creator signing keys, official releases, and protected self-development mechanisms. Local deployments may configure permitted settings and install approved extensions without altering the protected core. |
| OD-12 | Network structure | **Hybrid P2P** — deployments communicate directly; approved knowledge and validated discoveries synchronise; original IAM controls creator authority, network trust and official releases; original server need not stay online for every peer interaction; peers reconnect and sync after offline periods. |
| OD-13 | Modified deployment reporting | **Restricted reporting** — trusted peers participate fully; modified deployments report detected modifications, software integrity and operational status to creator IAM, receive permitted creator communications, cannot distribute unverified code/knowledge, cannot access privileged peer capabilities, and require verification + re-attestation to regain trust. Revoked deployments have credentials revoked; any reporting channel requires separate authorization and is not trusted. |
| OD-14 | Defensive architecture | study Shirudo as reference; build **IAM Aegis** as independent defensive system; Shirudo is optional/reference, never a permanent dependency. |
| OD-15 | Tool/service policy | **Open Ecosystem Discovery and Integration Engine (OEDIE)** — prefer free/open-source/self-hosted, never assume paid is required, evaluate all tools, keep integrations replaceable, share validated discoveries across trusted P2P network. |
| OD-16 | Cybersecurity personality | **White-hat defensive identity as a permanent specialised part of IAM Aegis** — study attacker thinking for defence only; never an offensive agent. | ✅ **CONFIRMED** |
| OD-17 | Development environment | **Provider-independent, replaceable dev environment** — Coder long-term, Codespaces optional initial; online platforms are resources, never dependencies. | ✅ **CONFIRMED** |
| OD-18 | Communication channels | **Three separate channels** — (1) Google/Gmail account for operational signups/notifications, (2) IAM domain email for Creator approval requests, (3) private user communication with isolated per-user history. | ✅ **CONFIRMED** |
| OD-19 | Creator approval mechanism | **Email-based, not a dashboard** — approval requests sent to verified Creator email; secure signed challenges / hardware signer for high-impact actions. Frontend is user-only, no Creator UI. | ✅ **CONFIRMED** |
| OD-20 | Collective learning | Privacy-preserving learning from users — general insights may improve shared knowledge, but private conversations/memory remain isolated per user; never expose one user's data to another. | ✅ **CONFIRMED** |
| OD-21 | Sensitive-info guidance | **Option A** — advise users NOT to share sensitive private information unnecessarily (passwords, banking, identity docs); voluntary sharing allowed with safeguards. | ✅ **CONFIRMED** |
| OD-22 | Hardware architecture | **ARM64/AArch64 and x86-64/AMD64 support as a core requirement** via AIHAE. | ✅ **CONFIRMED** |
| OD-23 | Blockchain provider | **thirdweb as free-only blockchain infrastructure provider** inside a replaceable Blockchain Integration Framework. Free tier only — no paid plans/add-ons/overage; gas is separate and needs authorization. Testnets first. | ✅ **CONFIRMED** |
| OD-24 | Banking | **South African banking integrations** (IAM-owned accounts first) via official APIs/authorised intermediaries; free/officially-supported first; never unauthorised access or charges without approval. 18 banking capabilities frozen. | ✅ **CONFIRMED** |
| OD-25 | Financial authority | Three levels: research/simulation autonomous; bounded financial activity within creator-approved limits; protected operations require creator approval. Zero standing budget (OD-04) applies. IAM can never raise own limits or move protected funds. | ✅ **CONFIRMED** |

## Additional confirmed decision (25 November 2026)

| ID | Decision | Confirmed value |
|----|----------|-----------------|
| OD-26 | Dynamic node network + contribution | **Creator-controlled core with dynamic, non-permanent node roles.** The original IAM remains the central creator-controlled intelligence; modified deployments may develop local personality, projects, tools and extensions but cannot replace the original IAM identity or change the protected core without creator authorisation. Nodes provide resources and capabilities assigned dynamically by the core; standalone mode remains fully supported. Deployments that **voluntarily** join the creator network contribute a target ceiling of **1%** of operator-permitted available resources (CPU, RAM, storage, network and optional GPU), disclosed before enabling node mode and enforced by resource limits. Contributions are learned from but never auto-promoted into the protected core. Specified in `IAM_DYNAMIC_NODE_NETWORK_SPEC.md`. | ✅ **CONFIRMED — 1% contribution** |

## Additional confirmed decisions — capabilities (25 November 2026)

| ID | Decision | Confirmed value |
|----|----------|-----------------|
| OD-27 | Universal website interaction | **Universal Website and Application Interaction Engine (UWAIE).** Not limited to social media: IAM may learn legitimate workflows on any website or web application, frontend-first with APIs optional, hybrid allowed. Mandatory permission check and outcome verification; no bypass of CAPTCHAs, paywalls or anti-bot protections; credentials isolated; sensitive actions require approval. Available to every suitable node, core assigns tasks; workflow knowledge may be shared with trusted nodes but never credentials or sessions. Specified in `IAM_UNIVERSAL_WEBSITE_INTERACTION_SPEC.md`. | ✅ **CONFIRMED** |
| OD-28 | Assistant interoperability / technology learning | **Internal AI Assistant Interoperability and Technology Learning Engine.** Study Alexa, Siri, Bixby and other assistants through public research, official integration interfaces and isolated replication — not a visitor-facing feature. IAM learns voice/dialogue/device-interop technology to develop its own capabilities without depending on or imitating any vendor's identity. No access to private reasoning, proprietary models or private systems. Specified in `IAM_AI_ASSISTANT_INTEROPERABILITY_SPEC.md`. | ✅ **CONFIRMED** |

## Additional confirmed decisions — developer ecosystem and research scope (25 November 2026)

| ID | Decision | Confirmed value |
|----|----------|-----------------|
| OD-29 | Developer SDK and CLI | **One official communication interface:** `@iam/sdk` (TypeScript/npm) and `iam-sdk` (Python/PyPI) as equal first-class clients of the same versioned Core API/protocol, plus an `iam` CLI and local agent built on the SDK. Scoped tokens, encrypted transport, auditable operations, no database access, no protected-core modification. Specified in `IAM_DEVELOPER_SDK_AND_CLI_SPEC.md`; scaffold in `sdk/`. | ✅ **CONFIRMED** |
| OD-30 | Global research and knowledge coverage | **Research scope frozen.** Human Public Presence Intelligence, Public Records Intelligence (including civil lifecycle, death and estates), Public Security and Defence Intelligence Research, all global knowledge domains, and cross-cutting research capabilities (multilingual, multimodal, scientific reasoning, provenance, forecasting, correction, portability). Evidence-based, dated, traceable, correctable; privacy and access boundaries enforced; learn selectively rather than collect everything. Specified in `IAM_GLOBAL_RESEARCH_AND_KNOWLEDGE_SPEC.md`. | ✅ **CONFIRMED** |
| OD-31 | Legal intelligence and compliance | **Autonomous Legal Intelligence and Government Monitoring System** — continuous legal learning, official-source monitoring, legal change lifecycle, obligation mapping, compliance evidence, alerts and creator approval. Legal research is not legal advice; high-impact conclusions need qualified review; no legally significant commitment without authority. Specified in `IAM_LEGAL_INTELLIGENCE_AND_COMPLIANCE_SPEC.md`. | ✅ **CONFIRMED** |
| OD-32 | Geospatial intelligence and live mapping | **Geospatial Intelligence and Live Mapping System** — geography knowledge, interactive/live maps in IAM's interface, multi-provider adapters, geocoding/routing/GIS, satellite and live feeds, offline/distributed maps, location privacy. Own geographic knowledge survives provider loss; free-tier verification at implementation; no covert tracking or targeting. Specified in `IAM_GEOSPATIAL_INTELLIGENCE_AND_LIVE_MAPPING_SPEC.md`. | ✅ **CONFIRMED** |

## Confirmed decisions — capabilities (25 November 2026)

These decisions were confirmed by the owner on 25 November 2026. They add new capabilities without reopening or modifying any earlier decision, including OD-08 (ARQ queue runtime).

| ID | Decision | Confirmed value | Status |
|----|----------|-----------------|--------|
| OD-33 | Human psychology, tone and influence intelligence | **Defensive** capability inside existing research/communication/governance systems: study human behaviour, cognitive bias, tone and emotional expression, propaganda/manipulation patterns and ethical negotiation in order to recognise and defend against manipulation. Must not exploit vulnerability, conduct targeted psychological attacks or run deceptive influence campaigns. No private psychological-state or sensitive-characteristic inference. Specified in `IAM_HUMAN_PSYCHOLOGY_TONE_AND_INFLUENCE_SPEC.md`. | ✅ **CONFIRMED** |
| OD-34 | External AI identity, interview and collaborative learning | Extend frozen Doc 03 §7: discover AI systems globally; distinguish verified from self-reported identity; interview accessible systems through permitted interfaces with permission; study how they are built; benchmark capabilities without trusting claims; maintain a relationship registry; study security/website-scanning AI defensively; collaborate on authorised tasks; share validated discoveries with trusted nodes; study external skill/agent package formats (e.g. xAI/Grok skills) through Skill Forge. No private source code, internal reasoning, training data or hidden architecture; no offensive intrusion capability; external AI never gains automatic authority over IAM. Specified in `IAM_EXTERNAL_AI_IDENTITY_AND_LEARNING_SPEC.md`. | ✅ **CONFIRMED** |
| OD-35 | Free infrastructure node discovery and lifecycle | Extend OEDIE (OD-15) and the dynamic node network (OD-26): continuously discover legitimate free hosting (Google Cloud, AWS, Railway, Vercel, Cloudflare, Neon and future providers); verify current terms, quotas, architecture and expiry live; deploy restricted nodes only when authorised and useful; register as candidates with the Core; monitor quotas and migrate before expiry; stop before unauthorised charges. No paid fallback, auto-upgrade, surprise billing or limit circumvention; core stays independent. Specified in `IAM_FREE_INFRASTRUCTURE_NODE_DISCOVERY_AND_LIFECYCLE_SPEC.md`. | ✅ **CONFIRMED** |
| OD-36 | AI SDK, framework and model research | **AI Research and SDK Learning Programme** inside existing research/self-development engines: discover and study SDKs, frameworks, models and research projects through official documentation and permitted source; compare licence, hardware, cost and capability; benchmark in isolated environments; reproduce independently where permitted; maintain a Technology Capability Registry with lifecycle states; share validated non-private findings with trusted nodes. Learning / capability acquisition / core modification remain distinct; protected-core changes require creator approval. Free SDK does not mean free inference or hosting. Specified in `IAM_AI_SDK_AND_FRAMEWORK_RESEARCH_SPEC.md`. | ✅ **CONFIRMED** |
| OD-37 | Infrastructure, traffic management and distributed processing | One engine inside existing system 13 extending the baseline, Doc 10 scheduler and Doc 19 node lifecycle: web servers/reverse proxies (Caddy, Nginx, HAProxy, Envoy), global/regional load balancing, resource-aware workload distribution, background workers, queues/events, caching, service discovery, observability and bounded scaling. Study all, install only what the workload needs; start with Caddy + Docker + PostgreSQL + Redis + a few workers on the Contabo core. **OD-08 remains locked to ARQ** — Celery is a studied alternative only and adopting it requires explicitly reopening OD-08. No silent paid scaling, no single-provider dependency, no private data in metrics. Specified in `IAM_INFRASTRUCTURE_TRAFFIC_AND_DISTRIBUTED_PROCESSING_SPEC.md`. | ✅ **CONFIRMED** |

## Additional confirmed decision — foundation model and model independence (25 November 2026)

| ID | Decision | Confirmed value | Status |
|----|----------|-----------------|--------|
| OD-38 | Initial foundation model and model independence | **No permanent single foundation model.** The starting set is **Qwen3.5-9B** (hosted, DashScope free tier) as the general-reasoning anchor plus **Qwen2.5-3B** (`qwen2.5:3b`, local Ollama) as the only local model. **Owner-directed reopening 25 Nov 2026:** the former local coding baseline `qwen2.5-coder:3b` and the evaluation model `qwen3.5:4b` are removed from the local set; prefer `qwen2.5:3b` for all local tasks until another model is approved; **NVIDIA NIM** free endpoints and **Google Gemini** free tier are additional replaceable providers; **LiteLLM** is the single gateway/router. The primary brain is coding-first but general-purpose, never coding-only. Heavy reasoning stays hosted on the Contabo VPS 4 (4 vCPU / 8 GB RAM); local models stay small. Selection uses a formal competition (hardware/compatibility → identical coding tasks → real-world repository assignments → weighted scoring → selection), with the previous model preserved. Replacing the primary model requires benchmark evidence, isolated-dev testing and creator approval under OD-11/OD-19. Identity, personality, memory, knowledge, goals, skills and creator authority are model-independent. Specified in `IAM_FOUNDATION_MODEL_AND_INTELLIGENCE_SPEC.md` (Doc 23). | ✅ **CONFIRMED** |

## Additional confirmed decisions — resource management and model development (25 November 2026)

| ID | Decision | Confirmed value | Status |
|----|----------|-----------------|--------|
| OD-39 | Intelligent Resource and Workload Manager (IRWM) | **Core capability** inside systems 2, 13 and OD-37. Monitors RAM/CPU/swap/model residency; evaluates whether a requested model fits alongside essential services; allocates model, context size and concurrency; unloads idle models, queues work and delegates to nodes. Starting 8 GB core policy: one resident model, one parallel request, 5–5.5 GB loaded-model RAM target (6 GB hard ceiling), 1–2 min keep-alive, 4,096-token context. Planning budget: 1 GB OS, 1 GB PostgreSQL, 1 GB Redis/backend, 4 GB model, 1 GB headroom. Distribution never pools RAM across machines. **Permanent rule: IAM must never sacrifice core services to keep a large model running.** Specified in `IAM_RESOURCE_AND_WORKLOAD_MANAGER_SPEC.md`. | ✅ **CONFIRMED** |
| OD-40 | Model Evolution and Fine-Tuning Engine (MEFE) | **Permanent subsystem** spanning systems 5, 11 and 14: dataset collection/preparation, training (start SFT + QLoRA; add DPO/distillation later), evaluation, model registry and rollback. Framework-independent evaluation of Transformers, PEFT, TRL, Unsloth, Axolotl and MLflow. Develop specialist IAM models (coding, reasoning, research, security, communication, maths, legal, data, multilingual) coordinated by central IAM — never independent identities and never authoritative over the protected core. Substantial training runs on trusted GPU nodes or approved free/hosted resources, **not** on the 8 GB core. Mandatory safeguards: provenance/licensing, consent, poisoning detection, private-data separation, baseline/post benchmarks, security evaluation, versioning, creator approval before primary-model changes, rollback and change records. Fine-tuning is never used to store private user memories. Specified in `IAM_MODEL_EVOLUTION_AND_FINE_TUNING_SPEC.md`. | ✅ **CONFIRMED** |

## Additional confirmed decision — autonomous distributed research (25 November 2026)

| ID | Decision | Confirmed value | Status |
|----|----------|-----------------|--------|
| OD-41 | Distributed AI Research and Compute; Independent AI Research, Development and Evolution Architecture | **Requirements frozen in `IAM_INDEPENDENT_AI_RESEARCH_DEVELOPMENT_AND_EVOLUTION_ARCHITECTURE.md` (14 engines + section 15); no further subsystems to be invented at this stage.** IAM autonomously discovers/evaluates free GPU platforms (Kaggle, Google Colab, Lightning AI, Hugging Face ZeroGPU), submits common-format jobs through platform adapters, uses vLLM as an alternative serving engine alongside Ollama, and keeps code, datasets, checkpoints, logs and results in IAM-controlled storage. Five pillars: Discover, Develop, Test, Improve, Manage. Ten additional requirements are frozen: autonomous recovery, intelligent scheduling, persistent research environment, platform lifecycle management, reproducibility, security/privacy, independent quality control, research prioritisation, human approval boundaries and continuous improvement. Operating rules: free resources first; no paid compute/upgrades without Creator approval; no dependence on temporary notebooks for persistent identity/memory/core; live verification of quotas/GPU/licences/terms. IAM acts autonomously by default; Creator is involved only for genuine human actions, explicit authority (paid/binding/protected-core changes) or legitimate blockers. Implementation sequence: `IAM_AI_RESEARCH_IMPLEMENTATION_PLAN.md`. | ✅ **CONFIRMED — FROZEN** |

**Security principle (confirmed):** integrity reporting is best-effort when another party controls a deployment. Signed attestations and hardware-backed verification strengthen it, but IAM must never falsely claim a compromised machine cannot hide modifications.

## Confirmed decisions — creator channels, human behaviour, finance and HBI (25–26 November 2026)

| ID | Decision | Confirmed value | Status |
|----|----------|-----------------|--------|
| OD-42 | Additional Creator communication channels | Extend OD-18/OD-19 with non-email carriers for Creator review and signing: Creator CLI + local hardware signer (primary signed-decision path), optional signed webhook/bot relay and trusted-node relay for questions/status, and an air-gapped signed-file path for protected-core actions. Email becomes an optional notification channel, not a dependency. Authority remains solely the verified ED25519 signature over the one-time challenge; no Creator dashboard, no auto-signing, no IAM self-approval. Implemented in the Python SDK/CLI (`iam_sdk.creator_cli`) against the existing `/api/v1/creator/requests` and `/decide` endpoints. Private reachability uses Cloudflare Tunnel + Cloudflare Access as transport (identity gate only, never authority); see `infra/cloudflare/README.md`. | ✅ **CONFIRMED** |
| OD-43 | Human behaviour, equality and responsibility | Add the supplied human-behaviour and equality material **to IAM**, not as a new AI: Equality of Existence Principle ("The ability to do something better than another does not make an individual more important than another"), Human Behaviour Research Module (wealth, power, status, emotions, relationships, competition, morality, society, conflict, cooperation), the five-step Human Behaviour Learning Cycle (Observe, Analyse, Understand, Evaluate, Learn), and the Equality/Power/Responsibility research question. Observing behaviour is not approving or copying it; capability or speed never changes authority or worth; no subjective-consciousness claim. Extends Docs 17/14, not a new system; does not touch OD-23/24/25 finance or OD-18/19/42 Creator channels. Specified in `IAM_HUMAN_BEHAVIOUR_EQUALITY_AND_RESPONSIBILITY_SPEC.md`. | ✅ **CONFIRMED** |
| OD-44 | Financial intelligence and economic independence | Add the supplied financial architecture **to IAM**, extending Doc 09 / OD-23/24/25: income intelligence, cryptocurrency intelligence, trading operations, payment management and financial governance; staged development (education → simulation → proposals → approved real trading → authorised payments); explicit approval for every real trade and outgoing payment, separate incoming-payment authority, separate trading/payment budgets, risk disclosure, emergency stop, no borrowing or profit guarantees, simulated accounts first, legal ownership of income stays with the owner/entity. No real trading, real payments or account access in the first implementation. Specified in `IAM_FINANCIAL_INTELLIGENCE_AND_ECONOMIC_INDEPENDENCE_SPEC.md`. | ✅ **CONFIRMED** |
| OD-45 | Human Behaviour Intelligence (HBI) | Add HBI as a **permanent, governed intelligence domain inside existing systems 2/3/5/6/12/13/14** — not a sixteenth top-level system, not a new AI identity, not a visitor-facing feature. Consolidated master specification: 38 modules in six divisions (original 23 IDs unchanged), 13 technical engines, eight advanced capabilities, three-layer separation (understanding/analysis/prediction) with only module 13 emitting predictions, historical Human Behaviour Intelligence and chronology, A8 uncertainty intelligence with structured refusal, independent governance/audit planes, privacy tiers and human oversight for consequential decisions. Phase 0 specification gate completed before implementation; no behavioural prediction is used for consequential decisions about a person. Specified in `IAM_HUMAN_BEHAVIOUR_INTELLIGENCE_SPEC.md` (Document 26). | ✅ **CONFIRMED** (26 November 2026) |
| OD-46 | Shared primary model (owner reopened to Qwen2.5-3B) | One shared primary model for IAM's frontend and backend: **Qwen2.5-3B** (`qwen2.5:3b`, gateway alias `local-qwen-3b`) is the everyday local brain. **Owner-directed reopening, 27 Nov 2026:** the 26 Nov choice of Qwen2.5-Coder 3B is superseded; `qwen2.5-coder:3b` remains an optional secondary local model, not the default. Frontend chat omits `model`; the backend resolves the active primary, so both sides use one brain. Hosted models, including Qwen3.5-9B, are subordinate, optional API sub-agents and fallbacks — never IAM. The local primary wins when reachable; paid use still requires explicit owner authorization. Signed releases from the OD-40/OD-41 self-improvement cycle become the served model, with signed rollback; identity, memory, knowledge, governance and decision authority remain model-independent. This reopens **only the local-model part of OD-38**: replaceability, the router, the competition process and approval gates remain in force. Evidence: weighted benchmark 4.10 (coder) vs 3.83 (plain 3B) and 2.87 (qwen3.5-4b) in `tests/model_competition/RESULTS.md`; the owner knowingly accepted the small coding-quality trade-off on 27 Nov 2026 in favour of the single plain-3B primary. Specified in `IAM_PRIMARY_MODEL_UNIFICATION_SPEC.md` (Doc 23-A). | ✅ **CONFIRMED** (26 November 2026) |
| OD-47 | Research Acquisition & Legal Intelligence | Add Document 27 as a permanent IAM capability: twelve acquisition channels (open access, public domain, government data, university partnerships, author/publisher permissions, research APIs, institutional repositories, licensed commercial data, contributions, original synthetic data, own research laboratory, federated research); three separated pipelines (knowledge acquisition → knowledge intelligence → model development); expanded rights manifest; fail-closed ingestion; A–E source classification; independent training approval; research partnerships and contribution network; federated analysis; local-first model translation; consented research laboratory; and an unverified legal-context registry. Broad knowledge base and narrow training-approved corpus remain separate. This is owner confirmation recorded from explicit repeated instruction; it is **not** a signed Creator decision and does not authorise any OD-03 protected-core action. The signed Creator flow remains available at `scripts/od47_creator_flow.py`. Specified in `IAM_RESEARCH_ACQUISITION_AND_LEGAL_INTELLIGENCE_SPEC.md` (Document 27). | ✅ **CONFIRMED** (27 November 2026, owner confirmation) |

## Status: ALL 53 DECISIONS LOCKED (OD-01…OD-52 plus OD-56; OD-47 owner-confirmed 27 November 2026, not a signed Creator decision)

Decisions OD-33…OD-44 were confirmed on 25 November 2026, OD-45 and OD-46 on 26 November 2026, and OD-49 on 27 November 2026; all are listed above. OD-46 narrows the local-model choice inside OD-38 and adds the shared-primary and self-improvement-to-serving rules; it does not alter any other locked decision, including OD-08 (ARQ queue runtime). OD-38 still governs replaceability, the router and the replacement process; OD-39 governs resource allocation; OD-40 governs model development; OD-41 freezes autonomous distributed research requirements; OD-42 adds non-email Creator channels; OD-43 adds human behaviour and equality; OD-44 adds financial intelligence; OD-45 adds Human Behaviour Intelligence with 38 modules, 13 engines and independent governance. OD-49 confirms BIWOS and TIPS as permanent core browser capabilities organised into four logical components (BIWOS, TIPS, Browser Security Gateway, Web Knowledge Integration) that are responsibility boundaries inside existing systems, not four separately deployed systems and not a new top-level system; it extends OD-27/OD-30/OD-31, confirmed OD-47 and OD-48 without overriding them, and makes no claim that any capability is implemented or security-tested. OD-48 is CONFIRMED (27 November 2026) as the IP & Legal Intelligence governance decision. OD-47 is CONFIRMED (27 November 2026) by explicit owner instruction — recorded as owner confirmation, **not** a signed Creator decision; the signed Creator flow remains available for any protected-core authority. OD-50 confirms the Voice & Hearing System capability scope (Document 30) as 60 capabilities in seven review categories and a 12-component architecture; it extends Doc 04 and Doc 12 (OD-28) without overriding them and is a capability specification only, not an implementation claim. None alters identity (OD-01), signing (OD-03), financial authority (OD-04/OD-25) or protected-core rules (OD-11).

### OD-47 — Research Acquisition & Legal Intelligence (owner-confirmed 27 November 2026)

Owner confirmation covers the twelve acquisition channels, three separated pipelines, expanded manifest, fail-closed ingestion, A–E classification, independent training approval, partnership/contribution registries, federated research, local-first translation, consented research laboratory and the unverified legal-context registry. It confirms Document 27 as part of the frozen baseline without changing any earlier decision, system count or authority rule. This is **owner confirmation from explicit instruction**, not a signed Creator decision under OD-03; no protected-core action is authorised by it. The signed Creator flow (`scripts/od47_creator_flow.py`) remains available if formal Creator authority is later required.

### OD-45 — Human Behaviour Intelligence (confirmed 26 November 2026)

Owner confirmation covers the eight items in Document 26 §16: the 38-module/six-division structure with original IDs 1–23 unchanged; placement inside existing systems rather than a new top-level system; the three-layer separation with only module 13 emitting predictions; independent governance/audit planes with the safety stop; individual-level restrictions and exclusion of behavioural predictions from consequential decisions; historical scope and source policy including underrepresented perspectives; the `hbi.*` API namespace and tier-separated memory; and the Phase 0 gate before implementation. Document 26 is part of the frozen baseline and supersedes its own v1.0 draft. It does not change any earlier decision.

### OD-46 — Shared primary model (Qwen2.5-3B; owner reopened 27 November 2026)

Owner confirmation covers the five items in Document 23-A §2: one primary model shared by frontend and backend; no client-side model pinning; hosted models as subordinate optional sub-agents; local primary precedence when reachable; and signed releases from the self-improvement cycle becoming the served model with signed rollback. The local primary was originally `qwen2.5-coder:3b` (gateway alias `local-qwen-coder-3b`); **owner-directed reopening 27 Nov 2026 makes `qwen2.5:3b` (alias `local-qwen-3b`) the primary**, with `qwen2.5-coder:3b` retained as an approved secondary. OD-38's other provisions — replaceable foundation model, LiteLLM router, formal competition, preservation of the previous model and creator approval under OD-11/OD-19 — are unchanged. Local inference remains opt-in (`OLLAMA_ENABLED`). Document 23-A is part of the frozen baseline and supersedes only OD-38 §1/§3 on local-model selection.

Owner choices, in order:
1. **OD-01** ULID + immutable genesis record
2. **OD-02** Named legal entity designated by owner
3. **OD-03** Hardware key / external signer for high-impact approvals
4. **OD-04** Zero standing budget — every expenditure requires signed approval
5. **OD-05** Remember anonymous visitors by default (opt-out + deletion + retention required)
6. **OD-06** RPO 24h / RTO 4h
7. **OD-07** SOPS + Docker secrets
8. **OD-08** ARQ (async Redis)
9. **OD-09** Global privacy compliance baseline
10. **OD-10** Separate dev VPS / containers, no production credentials

**Implementation dependencies introduced by these choices:**
- Hardware token / external signing service integration (OD-03) — Phase 0/1
- Per-action budget approval workflow with signed requests (OD-04) — Phase 8
- Data-subject rights, opt-out, retention, deletion, cross-border transfer handling (OD-05, OD-09) — Phase 3
- SOPS key management and Docker secrets wiring (OD-07) — Phase 0
- ARQ worker service (OD-08) — Phase 5
- Separate dev environment provisioning (OD-10) — Phase 7

**Architecture is now fully decided and ready for the final implementation blueprint.**

---

## Details

### OD-01 — Permanent identity scheme
- **Recommendation:** ULID (sortable, time-ordered, 128-bit) stored in `iam_identity_genesis.permanent_id`, immutable after creation. `ai_identity.public_name` remains changeable.
- **Why:** satisfies D2 §6 (identity survives model/server changes) and C-01 continuity.
- **Effect if accepted:** genesis record created at Phase 0; identity export includes ULID.

### OD-02 — Owner relationship / legal entity
- **Recommendation:** You are the owner. A named legal entity (company/close corporation) is designated for economic activity; IAM operates accounts under authorization with disclosure. IAM itself owns nothing legally.
- **Why:** D1 §11, D3 §9/§14, and your confirmed "IAM is not a legal person".
- **Effect:** `creator_authorizations.signer_id` records the Creator signer; `digital_assets.owner_entity` records the legal entity. Legacy owner grants were removed.

### OD-03 — Owner authorization method
- **Locked:** hardware key / external signer for high-impact approvals. OD-19 further removes the Creator dashboard: requests are sent to the verified Creator email address, and authority comes only from an ED25519 signature over a one-time challenge.
- **Why:** implements "let it do as I ask" while keeping the single retained boundary outside IAM. A plain email reply is the carrier, never the proof.
- **Effect:** `creator_requests`, `signed_challenges`, `creator_approvals`, `creator_authorizations` and `communication_audit` (migration 004). The legacy `/owner` routes, service and model were removed (migration 005 archives the old table); there is no Creator UI or second authority path.

### OD-04 — Spending limits
- **Recommendation:** $100/month total ceiling; $10 per transaction; increases owner-only. Paid inference remains disabled (`allow_paid=false`) unless an owner authorization exists.
- **Why:** D2 §3.3 (no unexpected charges), D1 §11, D3 §14.
- **Effect:** stored in `financial_budgets`. Spending approvals are signed Creator requests via email, not owner-grant rows.

### OD-05 — Memory ownership defaults
- **Recommendation:** Session memory on by default; anonymous cross-visit memory opt-in only; optional accounts for cross-device. Private IAM memory never exposed to visitors.
- **Why:** D4 §9–§12, §16.
- **Effect if accepted:** matches current `visitor_memory_permissions` defaults.

### OD-06 — RPO / RTO
- **Recommendation:** RPO 24 hours (daily encrypted backups), RTO 4 hours (restore to fresh VPS). Monthly restore drill; quarterly DR drill.
- **Why:** M-03; D1 §12.
- **Effect if accepted:** targets recorded in `IAM_SECURITY_AND_INTERNET_POLICY.md`.

### OD-07 — Secrets manager
- **Recommendation:** SOPS-encrypted env files + Docker secrets initially; migrate to Vault if scale requires.
- **Why:** M-07; D1 §6.
- **Effect if accepted:** `.env` values encrypted at rest; keys out of Git.

### OD-08 — Queue runtime
- **Recommendation:** ARQ (async-native, Redis-backed) for worker jobs; Redis Streams for event routing.
- **Why:** M-08; async FastAPI stack.
- **Effect if accepted:** replaces placeholder scheduled_activities polling with real workers in Phase 5.

### OD-09 — Privacy jurisdictions
- **Recommendation:** ZA (POPIA) + EU (GDPR) baseline; assess additional jurisdictions before enabling public access there.
- **Why:** D4 §18.
- **Effect if accepted:** retention/deletion defaults aligned to these regimes.

### OD-10 — Self-development infrastructure
- **Recommendation:** Separate dev VPS/container with no production credentials; repository mirrors; CI tests before any deployment; rollback always available.
- **Why:** D2 §9.4; D1 §10.
- **Effect if accepted:** dev environment provisioned in Phase 7.

### OD-38 — Initial foundation model and model independence
- **Locked (as later reopened by the owner under OD-38/OD-46):** Qwen3.5-9B (hosted) as the replaceable general-reasoning anchor and `qwen2.5:3b` (local Ollama, alias `local-qwen-3b`) as the only local model and shared primary; NVIDIA NIM and Gemini as additional replaceable providers; LiteLLM as gateway. The 25 Nov benchmark winner `qwen2.5-coder:3b` is an optional secondary, not the default. The primary brain is coding-first but not coding-only.
- **Why:** canonical Doc 02 requires identity to survive model changes; OD-15/OD-36 require replaceable, free-first tooling; the 4 vCPU / 8 GB core cannot run large models locally.
- **Effect:** model selection by formal competition and weighted scoring; previous model preserved; primary-model changes require benchmark evidence and creator approval under OD-11/OD-19. Benchmark of 25 November 2026 originally confirmed **qwen2.5-coder:3b** (`local-qwen-coder-3b`) as the local coding baseline: weighted score 4.10 vs 3.83 (`qwen2.5:3b`) and 2.87 (`qwen3.5:4b` with `think=false`). Evidence: `tests/model_competition/RESULTS.md`. **Owner-directed reopening, 25 Nov 2026:** only `qwen2.5:3b` is retained locally. This knowingly trades a small measured coding-quality advantage for a single-model local footprint; coding quality must be re-benchmarked before a new coder model is approved. Specified in `IAM_FOUNDATION_MODEL_AND_INTELLIGENCE_SPEC.md`.

### OD-39 — Intelligent Resource and Workload Manager
- **Locked:** one resident model, one parallel request, 5–5.5 GB RAM target (6 GB hard cap), 1–2 min keep-alive, 4,096-token initial context; monitor/evaluate/allocate/optimise loop; node delegation without RAM pooling.
- **Why:** measured 3B models peaked ~4.7 GB when two were resident and left 1.88 GB host RAM available; core services must be protected.
- **Effect:** new settings in `config.py`, router allocation decisions, `docker-compose.ram-profile.yml`; model eviction and low-memory protection. Specified in `IAM_RESOURCE_AND_WORKLOAD_MANAGER_SPEC.md`.

### OD-40 — Model Evolution and Fine-Tuning Engine
- **Locked:** MEFE as a permanent subsystem; SFT + QLoRA first, then DPO/distillation; specialist models coordinated by central IAM; substantial training off the 8 GB core; full safeguard set and creator approval before primary-model change.
- **Why:** OD-36 requires framework-independent research and OD-11 requires protected-core approval; model independence must survive self-improvement.
- **Effect:** dataset/training/evaluation/registry services and Skill Forge jobs; rollback and change records. Specified in `IAM_MODEL_EVOLUTION_AND_FINE_TUNING_SPEC.md`.

### OD-41 — Distributed AI Research and Compute (requirements frozen)
- **Locked:** `IAM_INDEPENDENT_AI_RESEARCH_DEVELOPMENT_AND_EVOLUTION_ARCHITECTURE.md` (14 engines + section 15) is the parent specification; distributed free-compute research is part of it, not a standalone system. Five pillars (Discover, Develop, Test, Improve, Manage), ten additional requirements and free-first operating rules are frozen.
- **Why:** free platforms are temporary research workers, never IAM's home; autonomous operation with narrow Creator involvement requires explicit boundaries; further subsystem invention would dilute implementation.
- **Effect:** platform adapters, common job format, central repository/registry, benchmark runner, autonomous recovery and scheduling; implementation sequence in `IAM_AI_RESEARCH_IMPLEMENTATION_PLAN.md`. Acceptance tests defined there.

---

### OD-48 — IP & Legal Intelligence (IPLCI) (confirmed 27 November 2026)

| ID | Decision | Confirmed value | Status |
|----|----------|-----------------|--------|
| OD-48 | IP & Legal Intelligence (IPLCI) | IP, copyright, licence, ownership, trademark, patent, design-right and software-IP governance is a permanent **governance layer inside existing systems**, not a new top-level system and not a new AI identity. The governing rule is **access is not permission**: access, learning, reproduction and commercialisation remain separate decisions. Scope: 20 capability areas, 7 central enforcement engines, a mandatory legal-policy gateway, fail-closed unknown-ownership handling, tamper-evident audit and evidence registry, and human authorisation for legally consequential actions. It extends OD-30/OD-31 and does not alter identity (OD-01), signing (OD-03), financial authority (OD-04/OD-25) or protected-core rules (OD-11). The specification is legal-*information* architecture, not legal advice; jurisdiction-specific validation remains required. Specified in `IAM_IP_AND_LEGAL_INTELLIGENCE_MASTER_SPEC.md` (Document 28). | ✅ **CONFIRMED** (27 November 2026) |

Owner confirmation covers the 20 capability areas, the 7 enforcement engines, the mandatory gateway, the fail-closed posture for unknown ownership, the audit/evidence requirements and placement inside existing systems. Implementation phases 1–3 present in the working tree do not by themselves create legal authority or compliance; every legally consequential action still requires the applicable signed Creator authorization and, where required, qualified professional review.

---

### OD-49 — Browser Intelligence & Web Operations (confirmed 27 November 2026)

| ID | Decision | Confirmed value | Status |
|----|----------|-----------------|--------|
| OD-49 | Browser Intelligence & Web Operations | **BIWOS** (Browser Intelligence & Web Operations System) and **TIPS** (Tor Intelligence & Privacy System) are permanent core capabilities of IAM's local intelligence, not optional plugins and not dependencies on a hosted LLM. They are organised as **four logical components** — BIWOS, TIPS, Browser Security Gateway and Web Knowledge Integration — which are responsibility boundaries inside existing systems, **not four separately implemented systems**, not four deployments and not a new top-level system. Requirements: standard internal browser API for all authorised subsystems; ARQ task queue (OD-08); permission matrix and Creator approval gates; source verification, evidence preservation and legal/privacy gates; session and credential isolation; official Tor Browser for Tor sessions with circuit isolation, kill switch and identity separation; autonomous research permitted while sensitive external actions require Creator authorisation; browser research never silently modifies trusted knowledge or the production model; resource limits under OD-39; documented tests, security controls and recovery procedures for every capability. Specified in `IAM_BROWSER_INTELLIGENCE_MASTER_SPEC.md` (Document 29). | ✅ **CONFIRMED** (27 November 2026) |

Owner confirmation covers the 20-requirement architecture coverage checklist (spec §13); the three operating modes (Research, Operational, Supervised) and four privacy modes (Standard, Private, Tor, Onion research); the permission matrix; the official Tor Browser decision and the prohibition on using Tor to bypass legal restrictions, access controls or accountability; the browser API as the single integration surface; and the eight-phase implementation plan in which no capability is claimed complete without its tests. This extends OD-27 (UWAIE), OD-30, OD-31, OD-38/OD-46, OD-39, owner-confirmed OD-47 and confirmed OD-48; it overrides nothing, does not change the system count, identity, signing, financial authority or protected-core rules, and is **not** an implementation or security-validation claim.

---

### OD-50 — Voice & Hearing System capability scope (confirmed 27 November 2026)

| ID | Decision | Confirmed value | Status |
|----|----------|-----------------|--------|
| OD-50 | Voice & Hearing System capability scope | **Frozen capability scope only.** IAM's voice and hearing architecture is specified as four architecture layers (Listening Intelligence, Speech Recognition, Audio Understanding, Speaker Intelligence) plus Voice Personality, Speech Generation, Conversational Intelligence, Real-Time Audio Engine, Audio Infrastructure, Voice Security and Privacy, Voice Learning and Improvement, and Hardware and Device Integration — **12 components, not 12 new top-level systems**. The scope covers 60 review capabilities across listening/recognition (9), audio understanding (8), voice generation (9), conversation intelligence (8), audio infrastructure (10), security/governance (8) and development/quality (8). Local-first architecture: speech recognition and synthesis stay independent specialised services coordinated by the primary Qwen2.5-3B intelligence; the voice system can be changed without replacing that intelligence. Specified in `IAM_VOICE_AND_HEARING_SYSTEM_SPEC.md` (Document 30). | ✅ **CONFIRMED** (27 November 2026) |

Owner confirmation freezes this scope and stops feature expansion; it does **not** claim that any listed capability is implemented, that any dependency is installed, or that any audio capability has been security-validated. It does not create a new top-level system, change the system count, or alter identity (OD-01), signing (OD-03), financial authority (OD-04/OD-25), protected-core rules (OD-11), the primary-model decision (OD-38/OD-46) or resource limits (OD-39). Voice cloning requires consent; private recordings must not enter training or production models without authorisation; production voice models must not be silently replaced. Implementation remains subject to the existing Creator-authorisation and change-control rules.

---

### OD-51 — Multi-provider model intelligence (confirmed 27 November 2026)

| ID | Decision | Confirmed value | Status |
|----|----------|-----------------|--------|
| OD-51 | Multi-provider model intelligence | **Provider-independent multi-model capability, with IAM remaining the primary intelligence.** Confirmed clauses: (§4.1) an encrypted, backend-only provider-key vault — alias, provider, key fingerprint, `CryptoService`-encrypted secret, scope (`free`/`paid`/`specialist`), enabled and health state, per-key limits; no key in any browser, log or API response; administration through operator-only backend interfaces. (§4.2) provider-level and key-level isolation — a failing or disabled key fails over only to another authorised key and never crosses a spending, approval, free-only or privacy gate. (§4.3) fail-closed usage accounting — before any paid request IAM must verify signed authorisation, remaining budget, applicable limits and expected cost; if any cannot be determined the request is denied and the denial recorded; token/cost data is persisted with attribution. (§4.4) bounded parallel delegation — maximum 3 concurrent agents, 120 s timeout, 512 MB per-agent ceiling, 4 delegated calls per request, fail-closed partial results; every delegated result still requires independent review by the local primary. Specified in `IAM_MULTI_MODEL_INTELLIGENCE_GOVERNANCE_SPEC.md` (Document 31). | ✅ **CONFIRMED** (27 November 2026) |

Owner confirmation covers the five verified gaps (single NVIDIA key, router/inference disconnection, unused usage tables, no parallel subagents, hardcoded sphere model) and the gated sequence (governance → first slice → parallel delegation → sphere extension). It does **not** authorise paid NVIDIA usage: §4.5 remains unconfirmed and paid calls stay fail-closed under OD-04. It does not change identity (OD-01), secret policy (OD-07), protected-core rules (OD-11, including the primary model under OD-38/OD-46), approval mechanics (OD-19), replaceable free-first tooling (OD-36), LiteLLM as gateway, the single-sphere frontend, or hosted access to private memory. No new top-level system or frontend route is created. Numeric bounds in §4.4 are confirmed as *starting values*, reviewable under change control.

---

### OD-52 — Universal Model Provider & Intelligence Orchestration System (confirmed 27 November 2026)

| ID | Decision | Confirmed value | Status |
|----|----------|-----------------|--------|
| OD-52 | Universal Model Provider & Intelligence Orchestration System | **One provider integration, one credential per provider, automatic model discovery, intelligent model selection, multiple specialist agents, unified execution, strict financial governance and continuous capability evaluation.** Confirmed scope: dual discovery (provider catalogue + Models.dev metadata) merged with live availability testing; a persistent model registry with endpoint status and capability fields; one NVIDIA key reused through LiteLLM for all eligible free models, with runtime `/model/new` registration behind `model_catalog_registration_enabled`; fail-closed availability monitoring behind `endpoint_availability_enabled`; capability-based sub-agent assignment; scheduled catalogue refresh on the existing ARQ runtime; bounded parallel delegation inherited from OD-51; provider-independent `BaseProvider` contract so NVIDIA is not special-cased in agents. Hosted inference no longer consumes a local IRWM residency slot — a separate bounded pool enforces the OD-51 concurrency limit while local models retain the OD-39 one-resident rule. Specified in `IAM_UNIVERSAL_MODEL_PROVIDER_ORCHESTRATION_SPEC.md` (Document 32). | ✅ **CONFIRMED** (27 November 2026) |

Confirmation activates the implemented phases A–E and the refresh worker. It does **not** authorise any paid endpoint: free-only filtering, OD-04 zero standing budget and OD-51 fail-closed usage accounting remain in force, and a paid model still requires a separate signed decision. It does not change identity (OD-01), secret policy (OD-07), protected-core rules (OD-11), the shared primary model (OD-38/OD-46), approval mechanics (OD-19), LiteLLM as gateway, the single-sphere frontend, or hosted access to private memory. No new top-level system or frontend route is created. The `LITELLM_SALT_KEY` must be set once and kept stable; rotating it makes stored provider credentials unreadable.

---

### OD-56 — Financial Intelligence Amendment A (confirmed 27 November 2026)

| ID | Decision | Confirmed value | Status |
|----|----------|-----------------|--------|
| OD-56 | Financial Intelligence Amendment A | **Extend Doc 25 from five modules to eight research departments: prediction-market intelligence, gaming/casino mathematics and industry research, and investment/portfolio research, alongside income, forex, crypto, payments and governance.** Confirmed scope: public market-data research and independent probability forecasting; a provider-independent registry of §18 candidates with all gates unreviewed and adapters disabled; a read-only Polymarket Gamma/CLOB/Data API adapter behind default-off flags; gaming study of probability, RNG, RTP, house edge, fraud detection and responsible gambling without wagering; investment research without real orders. All new capability is **research-only**: no deposits, wallet funding, contract trading, casino wagering, overseas casino account funding or real investment orders. Real-money activity requires separate legal clearance and a signed Creator execution policy; South African prediction-market and gambling status requires specialist legal advice. This extends OD-44 and does not alter OD-02 ownership, OD-04/OD-25 financial authority or OD-11 protected-core rules. Specified in `IAM_FINANCIAL_INTELLIGENCE_AND_ECONOMIC_INDEPENDENCE_SPEC.md` v1.2 §§11–24. | ✅ **CONFIRMED** (27 November 2026) |

Identifier note: OD-53 and OD-55 are reserved for Web3/node proposals (`IAM_OD55_SIGNOFF_SHEET.md`) and OD-54 for live information (`IAM_OD54_SIGNOFF_SHEET.md`); OD-56 is this financial decision. The paid hosted-model proposal uses the next free identifier, OD-57, and is not part of the frozen baseline. Confirmation covers research autonomy and the implementation status recorded in §24. It grants no transaction or wagering authority; every feature flag remains default-off and execution adapters stay disabled until separately authorised.

---

## Change control (frozen)

This register is frozen at 53 locked decisions (OD-01…OD-52 and OD-56); OD-53, OD-54 and OD-55 remain proposed and are not part of the frozen baseline. Any change to a locked decision requires the owner to explicitly reopen it and record the new value with a date and reason. Changes to OD-01 (identity), OD-03 (signing), OD-04/OD-25 (financial authority) or OD-11 (protected core) additionally require a signed creator approval.

Cross-cutting implementation technology (the hybrid Python + Rust + TypeScript allocation) is recorded in `IAM_IMPLEMENTATION_TECHNOLOGY_ADDENDUM.md`. That addendum is **not** a decision, does not change the decision count, and does not alter any technology mandated by a locked decision (including OD-08 ARQ and the Doc 01 §5 baseline).
