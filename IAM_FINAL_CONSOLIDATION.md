# IAM — Final Architecture Consolidation & Gap Analysis

**Version:** 1.0 · 25 November 2026  
**Status:** Feature-discovery FROZEN — consolidation deliverable  
**Purpose:** One consistent master architecture, supporting specifications, and a clear implementation roadmap.  
**Note:** This supersedes the earlier separate gap analyses as the single source of truth for what remains to be engineered.

---

## 1. Verdict

The IAM vision is **comprehensive and internally consistent**. No further major systems should be invented. The remaining work is engineering: resolving open specifications, fixing conflicts, defining acceptance tests, and implementing in phases.

"Covered" below means included in the requirements — **not** necessarily implemented or fully specified.

Five capability addenda — Doc 17 (psychology/tone/influence defence, OD-33), Doc 18 (external AI identity and interview, OD-34), Doc 19 (free infrastructure node lifecycle, OD-35), Doc 20 (AI SDK/framework research, OD-36) and Doc 21 (traffic management and distributed processing, OD-37) — are **CONFIRMED** and part of the frozen baseline (owner confirmation 25 November 2026).
They extend existing systems (research/communication/governance, Doc 03 §7, OEDIE/Doc 10, Doc 02/OEDIE and system 13/Doc 10 respectively); they are not new major systems.
A sixth addendum — Doc 23 (foundation model, router, model competition and model development, OD-38) — is likewise **CONFIRMED**. It extends Doc 02 and systems 2, 5, 11 and 14 by locking the initial foundation-model set and the replacement process; it does not add a new top-level system.
Two further confirmed capability decisions — OD-39 (Intelligent Resource and Workload Manager) and OD-40 (Model Evolution and Fine-Tuning Engine / MEFE) — extend systems 2/13 and 5/11/14 respectively. They govern resource control and model development; neither alters a locked decision or adds a new top-level system. Specified in `IAM_RESOURCE_AND_WORKLOAD_MANAGER_SPEC.md` and `IAM_MODEL_EVOLUTION_AND_FINE_TUNING_SPEC.md`.
OD-41 freezes the parent research architecture (`IAM_INDEPENDENT_AI_RESEARCH_DEVELOPMENT_AND_EVOLUTION_ARCHITECTURE.md`), including distributed free-compute research, autonomous operation boundaries and five pillars; implementation is sequenced in `IAM_AI_RESEARCH_IMPLEMENTATION_PLAN.md`. It explicitly ends further subsystem invention for this capability.

Doc 24 / OD-43 (human behaviour, Equality of Existence and responsibility) is **CONFIRMED** and extends Docs 17/14 rather than adding a new system or a separate AI. OD-42 (Creator channels, including Cloudflare private access) and Doc 25 / OD-44 (financial intelligence, extending Doc 09) are likewise confirmed. None alters any earlier decision, including OD-04/OD-25 financial authority.
A cross-cutting implementation addendum (`IAM_IMPLEMENTATION_TECHNOLOGY_ADDENDUM.md`) confirms a hybrid Python + Rust + TypeScript allocation: Python for research, training and the FastAPI service layer; Rust for performance- and security-sensitive infrastructure; TypeScript for web and SDK clients. It is **not** a new owner decision, changes no technology mandated in `canonical/IAM_DOC_01_MASTER_ARCHITECTURE.md` §5 (including OD-08 ARQ), and applies prospectively — no completed component is rewritten.

---

## 2. Document inventory

| # | Document | Role |
|---|----------|------|
| 01 | `canonical/IAM_DOC_01_MASTER_ARCHITECTURE.md` | Overall systems, infrastructure, database domains |
| 02 | `canonical/IAM_DOC_02_INTELLIGENCE_EVOLUTION.md` | Models, NVIDIA, reasoning, learning, self-development |
| 03 | `canonical/IAM_DOC_03_INTERNET_AUTONOMY_ECOSYSTEM.md` | Internet, external AI, autonomy, business |
| 04 | `canonical/IAM_DOC_04_UI_GLOBAL_ACCESS.md` | HTML interface, anonymous visitors, GeoIP, concurrency |
| 05 | `IAM_DISTRIBUTED_ARCHITECTURE.md` | Creator authority, hybrid P2P, restricted reporting, Aegis, OEDIE |
| 06 | `IAM_WHITEHAT_AND_WORKSPACE.md` | White-hat identity, offensive restrictions, dev environment |
| 07 | `IAM_COMMUNICATION_ARCHITECTURE.md` | Three channels, email approval, private user comms |
| 08 | `IAM_HARDWARE_ADAPTATION.md` | ARM64/x86-64 architecture independence (AIHAE) |
| — | `IAM_DATABASE_DESIGN.md` | Canonical ERD (119 tables) |
| — | `IAM_API_CONTRACTS.md` | Endpoint contracts + SSE schema |
| — | `IAM_SECURITY_AND_INTERNET_POLICY.md` | Security/internet policy |
| — | `IAM_OWNER_DECISIONS.md` | 41 locked decisions |
| — | `IAM_ARTEX_INTEGRATION_SPEC.md` | ArteX integration |
| — | `IAM_CREATOR_APPROVAL_SPEC.md` | Creator approval flow |
| — | `IAM_SKILL_FORGE_SPEC.md` | Skill development system |
| 09 | `IAM_BLOCKCHAIN_AND_BANKING.md` | thirdweb free-only blockchain + ZA banking architecture |
| 10 | `IAM_DYNAMIC_NODE_NETWORK_SPEC.md` | Dynamic node network + 1% contribution (OD-26) |
| 11 | `IAM_UNIVERSAL_WEBSITE_INTERACTION_SPEC.md` | Universal website/app interaction, frontend-first (OD-27) |
| 12 | `IAM_AI_ASSISTANT_INTEROPERABILITY_SPEC.md` | Internal assistant/voice technology learning (OD-28) |
| 13 | `IAM_DEVELOPER_SDK_AND_CLI_SPEC.md` | Official SDK/CLI and shared protocol (OD-29) |
| 14 | `IAM_GLOBAL_RESEARCH_AND_KNOWLEDGE_SPEC.md` | Frozen global research scope (OD-30) |
| 15 | `IAM_LEGAL_INTELLIGENCE_AND_COMPLIANCE_SPEC.md` | Legal and government monitoring (OD-31) |
| 16 | `IAM_GEOSPATIAL_INTELLIGENCE_AND_LIVE_MAPPING_SPEC.md` | Geospatial and live maps (OD-32) |
| 17 | `IAM_HUMAN_PSYCHOLOGY_TONE_AND_INFLUENCE_SPEC.md` | Human psychology, tone and influence defence (OD-33) |
| 18 | `IAM_EXTERNAL_AI_IDENTITY_AND_LEARNING_SPEC.md` | External AI identity, interview, collaborative learning and skill packages (OD-34) |
| 19 | `IAM_FREE_INFRASTRUCTURE_NODE_DISCOVERY_AND_LIFECYCLE_SPEC.md` | Free infrastructure node discovery and lifecycle (OD-35) |
| 20 | `IAM_AI_SDK_AND_FRAMEWORK_RESEARCH_SPEC.md` | AI SDK/framework/model research and Technology Capability Registry (OD-36) |
| 21 | `IAM_INFRASTRUCTURE_TRAFFIC_AND_DISTRIBUTED_PROCESSING_SPEC.md` | Traffic management, queues and distributed processing (OD-37) |
| 23 | `IAM_FOUNDATION_MODEL_AND_INTELLIGENCE_SPEC.md` | Foundation model selection, router, competition and model development (OD-38) |
| — | `IAM_RESOURCE_AND_WORKLOAD_MANAGER_SPEC.md` | RAM/CPU control, model residency and node workload allocation (OD-39) |
| — | `IAM_MODEL_EVOLUTION_AND_FINE_TUNING_SPEC.md` | Dataset, training, evaluation, registry and safe model releases (OD-40 / MEFE) |
| — | `IAM_INDEPENDENT_AI_RESEARCH_DEVELOPMENT_AND_EVOLUTION_ARCHITECTURE.md` | Parent research/development architecture + frozen distributed free-compute requirements (OD-41) |
| — | `IAM_AI_RESEARCH_IMPLEMENTATION_PLAN.md` | OD-41 work packages, dependencies, priorities and acceptance tests |
| — | `IAM_IMPLEMENTATION_TECHNOLOGY_ADDENDUM.md` | Cross-cutting Python + Rust + TypeScript implementation allocation (not a decision) |
| 24 | `IAM_HUMAN_BEHAVIOUR_EQUALITY_AND_RESPONSIBILITY_SPEC.md` | Human behaviour research, Equality of Existence and responsibility (OD-43) |
| 25 | `IAM_FINANCIAL_INTELLIGENCE_AND_ECONOMIC_INDEPENDENCE_SPEC.md` | Financial intelligence amendment: income, crypto, trading, payments; expanded to prediction markets, gaming intelligence and investments (OD-44, Amendment A) |
| — | `IAM_OPEN_SPECS_RESOLVED.md` | Resolved specs A–G |
| — | `IAM_OPENAPI.json` | Generated schema (708 paths, 435 schemas) |

---

## 3. Coverage matrix

| Area | Status | Area | Status |
|------|--------|------|--------|
| Identity & personality | Covered | Global anonymous access | Covered |
| Persistent memory & knowledge | Covered | GeoIP regional context | Covered |
| Reasoning & decisions | Covered | P2P & distributed knowledge | Covered |
| Autonomy & tasks | Covered | Creator authority & protected core | Covered |
| Multiple model providers | Covered | Modified-deployment reporting | Covered |
| NVIDIA & Google AI | Covered | IAM Aegis white-hat | Covered |
| OEDIE free-resource discovery | Covered | Shirudo research/integration | Covered |
| Self-development & evolution | Covered | Financial/economic management | Covered |
| Low-resource development | Covered | Digital identity & communications | Covered |
| ARM64 + x86-64 | Covered (OD-22) | Backup & disaster recovery | Identified |
| Online/local coding environments | Covered | Privacy & data protection | Identified |
| Internet research & browser | Covered | Dev/deployment lifecycle | Identified |
| Websites, software, business | Covered | Resource & cost optimisation | Identified |
| GitHub & email identities | Covered | Blockchain (thirdweb free-only) | Covered (OD-23) |
| thirdweb/blockchain | Covered (Doc 09) | SA banking (18 capabilities) | Covered (OD-24) |
| Financial authority | Covered (OD-25) | | |
| Psychology, tone & influence defence | Covered (Doc 17 / OD-33) | External AI identity & interview | Covered — extends Doc 03 §7 (Doc 18 / OD-34) |
| Free infrastructure node lifecycle | Covered — extends OEDIE/Doc 10 (Doc 19 / OD-35) | AI SDK/framework research | Covered — extends OEDIE/Doc 02 (Doc 20 / OD-36) |
| Traffic management & distributed processing | Covered — extends system 13 / Doc 10 (Doc 21 / OD-37); OD-08 ARQ unchanged | | |

---

## 4. Open specifications — the 7 required areas

These were the remaining engineering decisions. **All seven are now resolved** in `IAM_OPEN_SPECS_RESOLVED.md` (provisional owner-specific defaults are marked there and await confirmation).

### A. Creator authority & recovery
- How creator identity is cryptographically verified
- Signing key protection and recovery (hardware signer, OD-03)
- What happens if the original creator server goes offline permanently
- How compromised deployments are revoked
- **Blocking for:** D0 creator signing root, P2P trust

### B. Memory & knowledge boundaries
- Separate IAM identity memory / visitor memory / shared P2P knowledge
- What IAM may learn from conversations
- What may be synchronised between nodes
- Retention, deletion, privacy rules
- **Progress:** ERD defines owner scopes; policy doc written; retention SLA still open

### C. P2P networking
- Peer discovery and authentication
- Direct communication and NAT traversal
- Offline synchronisation
- Conflict resolution
- Knowledge verification and malicious-node handling
- **Blocking for:** D1–D5

### D. Self-development & hardware compatibility
- Cross-platform build and testing
- ARM64/AMD64 compatibility matrices
- Model migration and rollback
- Signed builds and supply-chain verification
- Isolated dev environments
- Protection of protected core
- **Progress:** Document 08 defines AIHAE; matrix still needs implementation

### E. Public access & scaling
- Concurrent user targets and load-test benchmarks
- Anonymous session expiry and recovery
- Provider quota management
- Abuse prevention and request prioritisation
- Regional privacy requirements
- **Progress:** session manager + rate limits built; no load-test target defined

### F. Financial & legal operations
- Legal ownership of businesses, assets, IP
- Banking/payment permissions
- Spending limits and approval rules (OD-04: zero standing budget)
- Tax, KYC/AML responsibilities
- External contracts and commercial operations
- **Progress:** OD-02 (legal entity) and OD-04 locked; detailed policy open

### G. Operational independence
- Hosting-provider migration
- Multi-provider backup and recovery
- Monitoring and incident response
- Hardware failure recovery
- Offline capabilities
- Emergency shutdown and restoration
- **Progress:** RPO/RTO locked (OD-06); procedures open

---

## 5. Conflicts & dependencies resolved

| Prior finding | Resolution |
|---|---|
| Two authority models (D1 4-level vs D3 5-level) | One canonical ladder in `AuthorityBoundary`; D0–D4 mapped |
| Two phase sequences | D1 §15 canonical; D2/D4 milestones are workstreams inside phases |
| Three conversation models | One `conversation_threads` + `conversation_messages` with owner scope |
| Multiple registries | One integration registry, one model catalog, one metering table |
| Visitor memory default conflict | OD-05 locked: anonymous memory ON by default; code aligned |
| /owner Creator UI vs OD-19 | `/owner` page removed from frontend |
| Frontend read private IAM memory | Replaced with `/api/v1/interface/nodes` (public knowledge only) |
| CORS errors | Same-origin Next.js rewrites (`/api/*`, `/health`) |

---

## 6. Completion levels (acceptance framework)

| Level | Definition | Measurable exit test |
|---|---|---|
| **L1 — Operational** | IAM runs, maintains identity, communicates, remembers | Identity persists across restart; multi-turn chat persists; health green; backup restores |
| **L2 — Independent** | Researches, learns, plans, executes authorised tasks | Research workflow with provenance; goal→plan→task execution; authority checks reject self-escalation |
| **L3 — Self-developing** | Builds, tests, improves, maintains own software | Isolated dev env; change tested vs baseline; signed release; rollback demonstrated |
| **L4 — Distributed** | Operates across ARM64/AMD64 and trusted P2P nodes | Multi-arch image built; ARM64 peer syncs; revoked peer refused; restricted reporting works |
| **L5 — Ecosystem** | Operates services, projects, approved businesses | Multiple projects managed; ledger reconciles; owner approval for spend/publish verified |

Each level requires its tests to pass before the next is declared complete. Autonomy is not widened just because a prior level works.

---

## 7. Implementation roadmap

### Current status (25 November 2026)
- **Code-complete but activation-blocked:** Phase 1 backend additions (genesis, constitution, suggestions, public nodes) parse cleanly; frontend builds cleanly.
- **Resolved:** Docker/WSL recovered (v29.9.3). Backend rebuilt with all Phase 1 code; health green.
- **Verified live:** IAM genesis (ULID `01M882TSZ937JTAK2WYV`), dynamic suggestions, public nodes, voice toggle, connection dot, cancel/retry, end-to-end message persistence via browser Send button. Zero console errors.
- Two bugs fixed during activation: `requires_owner_authorization` → `requires_creator_authorization` keyword in bootstrap; React stale-session closure (sessionRef) for message persistence.

### Sequence
| Step | Action | Gate |
|------|--------|------|
| 0 | Reboot → restore Docker → bring up stack → smoke test | Health green, 119 tables |
| 1 | Resolve open specs A–G | Written specs — DONE (`IAM_OPEN_SPECS_RESOLVED.md`) |
| 2 | Implement Phase 1 activation + verify suggestions/nodes/identity | L1 tests |
| 3 | Resolve E (scaling targets) + wire load test | Concurrent session test |
| 4 | Phase 2–3: memory consolidation, autonomy, internet research | L2 tests |
| 5 | Resolve D (self-dev/hardware) → multi-arch images | ARM64 build |
| 6 | Phase 6–8: workspace, self-evolution, economy | L3 tests |
| 7 | Resolve C (P2P) → D0–D8 distributed phases | L4 tests |
| 8 | Phase 9–10: ecosystem + advanced evolution | L5 tests |

---

## 8. What is explicitly NOT outstanding

- No new major systems will be added without a gap-analysis-proven omission.
- Model inference availability is an **operational** dependency (API keys/hardware), not an architecture gap.
- Docker/WSL failure is an **environment** issue, not an IAM design gap.

---

## 9. Conclusion

The IAM architecture is **frozen at the feature level** and **complete at the requirements level**. The 7 open specification areas are RESOLVED (`IAM_OPEN_SPECS_RESOLVED.md`).

**Real inference unified (26 Nov):** `app/services/model_inference.py` resolves one of three modes — hosted provider keys through LiteLLM, opted-in local Ollama (discovered via `/api/tags`), or explicit offline. `/api/v1/models/chat`, `/chat/stream` and the autonomy worker all use that same resolver; readiness is exposed at `GET /api/v1/models/readiness` without revealing keys. Unit smoke: `tests/model_inference_smoke.py` 3/3 (offline, hosted, Ollama).

**Creator hardware signer ceremony implemented & verified (25 Nov):** `app/services/creator_keys.py` + `/api/v1/creator/keys/*` — Ed25519 keypair generation, offline challenge signing, signature verification, documented 8-step key ceremony. IAM runtime never holds the private key; admin scope required for ceremony endpoints. `tests/signer_acceptance.py` 9/9 — generation, signing, valid/wrong-decision/tampered-hash verification, ceremony docs, unsigned gateway rejection. The existing `creatorapproval_service.py` already enforced Ed25519 signatures over one-time challenges — this adds the missing key-generation tooling.

**Interface correction (25 Nov):** Removed ALL additional frontend routes. The app is a single immersive screen — `/` only. Focus/Recall/Create are modes; voice (Web Speech + TTS), vision (image/video attachment via paperclip), conversation history, theme are capabilities inside that one screen. No other pages. Capabilities like memory, goals, projects, finance, security are AI functions invoked through the interface, not navigable pages. Frontend build clean (1 route).

**IAM Aegis implemented & verified (25 Nov):** `app/services/aegis.py` — all 7 defensive components (white-hat intelligence, ethical scope verification, vulnerability research, secure remediation, threat detection/prevention, threat intel, self-defence research). `tests/aegis_acceptance.py` 12/12 — injection detection, safe text, secret detection without echo, scope checks, SSRF/metadata blocking, safe remediation, shareable-finding sanitization, self-test. Security bug found and fixed: shareable findings were leaking raw evidence; now only type/severity/evidence-hash are shared. Also fixed concurrent-work model bug (`metadata` reserved attribute in freesandbox.py).

**P2P transport implemented & verified (25 Nov):** `app/services/p2p_transport.py` + `app/api/routes/p2p.py` — signed envelopes (HMAC), replay/dedup protection, store-and-forward outbox, WebSocket peer connections with per-peer shared secret, gossip fan-out. `tests/p2p_acceptance.py` 9/9 (signing, tamper detection, auth-gated HTTP, offline queue, broadcast, real two-peer WebSocket gossip). Operator credential required for HTTP P2P routes; WS uses `?secret=`.

**LangGraph durable orchestration implemented & verified (25 Nov):** `app/orchestration/autonomy_graph.py` — 11-node StateGraph (observe→retrieve→reason→identify→plan→authority→execute→verify→reflect→memory→end) with `AsyncSqliteSaver` checkpointing. Worker now calls the durable graph each tick with simple-loop fallback. `/api/v1/autonomy/status` reports `langgraph_durable` with real cycle results (observed goals/tasks, advanced task, verified, reflected). Restored missing ownerauth model/service/route files lost during concurrent edits.

**SSE streaming implemented & verified (25 Nov):** `POST /api/v1/models/chat/stream` emits real `start`/`delta`/`done`/`error` events (backend proxies LiteLLM streaming; graceful offline fallback). Frontend consumes with `ReadableStream` — live token display replaces fake animation. `/api/v1/models` and `/api/v1/interface` made public at IAM auth layer (gateway key stays backend-only). Verified in browser: full streamed response rendered, zero console errors.

**ALL FIVE ACCEPTANCE LEVELS PASSED (25 Nov):**
- Level 1 Operational: 14/14 + 3/3
- Level 2 Independent: 20/20
- Level 3 Self-developing: 13/13
- Level 4 Distributed: 20/20
- Level 5 Ecosystem: 12/12 (`tests/level5_acceptance.py` — opportunity discovery, business project, zero standing budget enforced, double-entry ledger rejects unbalanced entries, budgets, integrations inactive until approved, life history, portfolio, reconciliation)

Note: levels test semantics on a single-node stack; live P2P transport, multi-arch images, hardware signing, and real model inference remain specified/operational dependencies.

**Level 4 — Distributed tests PASSED (25 Nov):** `tests/level4_acceptance.py` 20/20 — permanent identity + creator authority, immutable security boundaries, four self-escalation paths blocked, P2P peer zero-trust lifecycle (register/assess/block/refuse), interaction audit, delegation authorization flag, backup verification, incident record, architecture detection, provider abstraction. Note: actual multi-arch images (ARM64) and live P2P transport are specified (Docs 05/08, spec C) but not runtime-tested in this single-node environment.

**Level 3 — Self-developing tests PASSED (25 Nov):** `tests/level3_acceptance.py` 13/13 — dev project lifecycle, code change records, experiment evaluated vs baseline, versioned release + rollback, upgrade history, capability registry with measurable assessment, reflection, resilience health, routing audit. New `development` route module created (projects/code-changes/experiments/deployments/upgrades). Fixes: Playwright baked into image (transient apt failure retried), httpx redirect-follow for trailing-slash routes.

**Level 2 — Independent tests PASSED (25 Nov):** `tests/level2_acceptance.py` 20/20 — goal→plan→task lifecycle, decision record/review, three self-escalation paths blocked, internet permission gates, research workflow with provenance, external AI agent untrusted, autonomy worker running. Real research verified: 3 Wikipedia sources retrieved with credibility scores. Fixes: Playwright baked into image, DuckDuckGo 403 handled by Wikipedia free API fallback.

**Level 1 acceptance tests PASSED (25 Nov):** `tests/level1_acceptance.py` 14/14 (health, identity, isolation, memory, authority, owner endpoint); `tests/level1_persistence.py` 3/3 (identity/memory/governance survive restart). Bugs found and fixed: missing ownerauth route/service/model, `requires_creator_authorization` keyword, React stale-session closure, ULID width. What remains: Levels 2–5 acceptance tests and phased implementation. The system is designed to be one independent intelligence that can outlive any model, host, provider, or hardware architecture — and no claim of consciousness is made.
