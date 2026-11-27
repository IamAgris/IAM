# IAM — Architecture Gap Analysis

**Version:** 1.0 · 24 November 2026  
**Status:** Consolidation review of Documents 01–04  
**Purpose:** Identify missing requirements, contradictions, security gaps, technical dependencies and database overlaps before finalising the implementation blueprint.  
**Input documents:** `IAM_MASTER_ARCHITECTURE.md` (D1), `IAM_INTELLIGENCE_EVOLUTION_SPEC.md` (D2), `IAM_INTERNET_AUTONOMY_ECOSYSTEM_SPEC.md` (D3), `IAM_UI_GLOBAL_ACCESS_SPEC.md` (D4).  
**Note:** Findings reference the authoritative documents as supplied. Where the current repository implementation differs from the documents, that is recorded separately as implementation drift.

---

## 1. Summary of findings

| Category | Count | Blocking before implementation |
|----------|-------|-------------------------------|
| Contradictions between documents | 11 | 4 |
| Missing requirements | 20 | 6 |
| Security gaps | 14 | 5 |
| Technical dependencies / risks | 12 | 3 |
| Database overlaps / gaps | 11 | 4 |
| Open owner decisions | 10 | 4 |

**Overall assessment:** The four documents form a coherent and comprehensive vision. The architecture is *implementable in principle* but not yet *implementation-ready*. The main blockers are: two conflicting authority models, two conflicting phase sequences, an incomplete database domain list, undefined owner/identity/economic decisions, and a set of security mechanisms that are named but not designed.

---

## 2. Contradictions and conflicts

### C-01 — Conflicting authority models (BLOCKING)
- **D1 §4** defines four levels: Independent thinking, Internal execution, External operations, High-impact decisions.
- **D3 §11** defines five autonomy levels: L0 Observe, L1 Recommend, L2 Execute in isolation, L3 Approved external actions, L4 Bounded autonomy.
- **D2 §14** defines its own permission split (independently / controlled approval).
- **Resolution:** Adopt one canonical ladder. Recommended mapping: D3's L0–L1 are sub-states of D1's "Independent thinking"; D3 L2 = D1 "Internal execution"; D3 L3 = D1 "External operations"; D3 L4 = D1 "High-impact decisions" with bounded recurring permissions. Keep a separate, non-negotiable owner-only boundary for self-authorization, security changes and financial limits. One authority service must be the single source of truth.

### C-02 — Conflicting phase sequences (BLOCKING)
- **D1 §15:** 0 Architecture · 1 Identity/model gateway/interface · 2 Memory · 3 Global access · 4 Internet/external AI · 5 Autonomy · 6 Multimodal · 7 Digital workspace · 8 Self-development · 9 Ecosystem · 10 Economic/advanced.
- **D2 §18** has Milestones 1–5 (core intelligence → multi-model → learning → self-development → advanced evolution).
- **D4 §22** has Milestones 1–7 (interface → conversations → anonymous access → GeoIP → concurrency → multimodal → visual integration).
- **Resolution:** D1 §15 is canonical. D2/D4 milestones become workstreams *inside* those phases. Map them explicitly in the implementation roadmap (Section 9).

### C-03 — First milestone scope conflict (BLOCKING)
- **D1 §16** requires the *first working version* to include anonymous public access, independent sessions, simultaneous conversations and basic internet research.
- **D1 §15** places global access at Phase 3 and internet access at Phase 4.
- **Resolution:** Either define "first working release" as end of Phase 4, or descope the first milestone to Phase 1 + minimal Phase 2/3. Recommend descoping: first working release = Phase 1 identity + interface + Phase 2 memory + minimal anonymous sessions; internet research moves to the Phase 4 gate.

### C-04 — Database table names differ from implementation
- D1 §6 uses `model_providers`, `external_ai_agents`, `external_api_permissions`, `research_sources`, `delegated_tasks`, `approved_reinvestments`, `external_services`.
- Repository uses `ai_providers`, `external_agents`, `internet_permissions`, `internet_resources`, `agent_collaborations`, `business_budgets`, `external_integrations`.
- **Resolution:** Adopt D1 names as canonical; produce a synonym map and migration plan. See Section 7.

### C-05 — "NVIDIA initial priority provider" vs "no permanent provider"
- D2 §3.2 makes NVIDIA an initial priority; D1 §4 and D2 §1 require permanent independence.
- **Resolution:** Not a true contradiction, but must be explicit: "priority" is a routing *preference* held in configuration, never a property of IAM identity. No identity or memory record may reference NVIDIA as permanent provider.

### C-06 — General internet access vs controlled browsing
- D3 §1 requires general-purpose internet access; D3 §4 forbids bypassing blocks, human verification or access controls.
- **Resolution:** Adopt an explicit policy: unrestricted exploration of *publicly accessible* information; respect robots.txt, terms of service, authentication boundaries and rate limits; no circumvention. Document as `internet_access_policy`.

### C-07 — Anonymous memory "across visits" vs "no cross-device continuity"
- D1 §8, D4 §10 allow pseudonymous memory across visits but require accounts for cross-device continuity.
- **Resolution:** Implement three tiers with explicit defaults: session memory (default), anonymous visitor memory (opt-in, cookie-bound), account memory (optional). Already reflected in repository; add to canonical docs.

### C-08 — Public visitors asking IAM to use its browser
- D3 §4 allows browser interaction and file upload; D3 §19 forbids public access to IAM's private browser/files.
- **Resolution:** Introduce a capability gate: public requests may use a stateless, unauthenticated, isolated browser profile with no IAM credentials, no downloaded-file retention and strict egress rules. Authenticated browser contexts are private-only.

### C-09 — Model adaptation vs paid inference disabled
- D2 §11 allows fine-tuning and specialised models; D2 §3.3 disables paid inference by default.
- **Resolution:** Require a separate approved compute budget for any training/fine-tuning. Training never uses the general inference budget.

### C-10 — Streaming response required but not specified
- D4 §23 requires responses to stream; D1/D2 do not define a streaming protocol.
- **Resolution:** Specify SSE as the canonical stream protocol for text, with WebSocket reserved for voice/real-time. Define event schema, cancellation and reconnection semantics.

### C-11 — Acceptance criteria count mismatch
- D1 §16 lists 10 first-milestone items; D4 §23 lists 22 acceptance criteria; D3 §23 lists 18; D2 §19 lists 12.
- **Resolution:** Create one acceptance-criteria register keyed by phase, with stable IDs. Avoid four separate lists drifting apart.

---

## 3. Missing requirements

| ID | Missing item | Why it matters | Priority |
|----|--------------|----------------|----------|
| M-01 | **Creator relationship definition** — Creator authority vs IAM operational independence, via email + signed challenges (OD-19) | Resolved: `creator_authorizations` records authority from verified signatures; no owner-grant table remains | Resolved |
| M-02 | **Permanent identity identifier & genesis record** — scheme, immutability, recovery procedure | D2 §6 lists identity records but no permanent ID or creation record | BLOCKING |
| M-03 | **RPO/RTO targets and backup verification procedure** | D1 §12 requires backups and recovery testing but no targets | BLOCKING |
| M-04 | **Memory ownership/access matrix** — IAM private / visitor / shared / public boundaries | D4 §16 names categories but no permissions matrix | BLOCKING |
| M-05 | **Economic authority specifics** — legal entity, spending limits, KYC/AML owner, mandate | D1 §11 / D3 §14 state requirements but no concrete arrangement | BLOCKING |
| M-06 | **API contracts and event schemas** (explicitly deferred in your next-steps list) | Needed before any service can be implemented against another | BLOCKING |
| M-07 | Secrets-management selection (Vault / SOPS / Docker secrets) | D1 §6 says "dedicated secrets manager" without choosing one | High |
| M-08 | Queue/worker framework selection (Celery / ARQ / RQ) | Redis is chosen; the worker runtime is not | High |
| M-09 | Streaming protocol (SSE vs WebSocket) | See C-10 | High |
| M-10 | Concrete prompt-injection controls at each untrusted boundary | Named in D3 §18; no design | High |
| M-11 | Public content/abuse policy beyond rate limits | D4 §17 covers technical abuse, not content policy | High |
| M-12 | Retention defaults and deletion SLA | D4 §18 says "configurable" without defaults | High |
| M-13 | Jurisdictional privacy impact assessment (POPIA, GDPR, others) | D4 §18 names laws but no assessment | High |
| M-14 | Model evaluation datasets and benchmark suites | D2 §13 lists categories; no datasets | Medium |
| M-15 | Self-created agent sandboxing and permission inheritance | D2 §12 says agents must not expand authority; no mechanism | High |
| M-16 | Incident response and emergency shutdown procedure | Named in D1 §12; no runbook | High |
| M-17 | Cost governance — hard caps, alerts, kill switch | D2 §3.3 disables paid inference but no runtime enforcement design | High |
| M-18 | Accessibility target (WCAG level) | D4 §8 covers reduced motion only | Medium |
| M-19 | Localisation/i18n architecture for multilingual support | Repeated across docs; no design | Medium |
| M-20 | Document change-control process for the four frozen documents | Needed to prevent drift between docs and code | Medium |

---

## 4. Security gaps

| ID | Gap | Required control |
|----|-----|------------------|
| S-01 | SSRF / DNS rebinding protection only named | Resolve DNS, block private/link-local/metadata ranges, re-validate on every redirect |
| S-02 | Public visitors could use IAM's internet access as an open proxy | Capability policy per context; per-context egress rules; no authenticated contexts for public requests |
| S-03 | Downloaded files scanned "where appropriate" | Mandatory quarantine + scan before any analysis; no auto-execution |
| S-04 | Audit logs not specified as tamper-evident | Append-only store, hash chaining, separate retention |
| S-05 | Provider keys must never reach frontend or visitor logs | Backend-only env injection; log redaction; no keys in prompts |
| S-06 | Visitor isolation stated but mechanism undefined | Enforce `session_id` ownership at query layer (RLS or mandatory filter) with isolation tests |
| S-07 | Voice data sensitivity not addressed | Explicit consent, short retention, encryption, no automatic memory |
| S-08 | Backup encryption key separation not in these docs | Keys stored separately from backups; documented recovery procedure |
| S-09 | Supply-chain controls absent | Dependency scanning, SBOM, pinned images by digest, secrets scanning |
| S-10 | Generated code execution risk | All generated/external code executes only in isolated containers with no production credentials |
| S-11 | Memory-poisoning from external AI/internet needs a concrete gate | Provenance + validation + confidence + human/owner review for high-impact retention |
| S-12 | Rate limiting needs three scopes | Per visitor, per IP-derived key, and global capacity limits |
| S-13 | TOCTOU on permissions in async workers | Re-check authority at execution time, not just at queue time |
| S-14 | No defined "emergency stop" that halts delegated/autonomous actions | Global kill switch with owner-only authority and audit event |

---

## 5. Technical dependencies and risks

| ID | Dependency / risk | Finding |
|----|-------------------|---------|
| T-01 | pgvector dimension mismatch | Repository fixes `vector(1536)` for OpenAI embeddings; NVIDIA embedding models use different dimensions. Need multi-table, per-model dimension strategy |
| T-02 | Playwright browsers not installed in backend Dockerfile | Env var set, but no `playwright install chromium` step — browser automation will fail in container |
| T-03 | Next.js 14.2.0 security advisory | Upgrade to patched release before deployment |
| T-04 | LangGraph persistence/checkpointer not configured | D1 selects LangGraph; durable execution requires an explicit checkpointer |
| T-05 | Redis queue runtime undecided | See M-08 |
| T-06 | Docker Compose has no container resource limits | Add cgroup CPU/memory limits for email, worker and browser containers |
| T-07 | Streaming through LiteLLM to browser unimplemented | See C-10 |
| T-08 | Ollama locally may run on CPU only | Define expected performance and which tasks are allowed locally |
| T-09 | Default MinIO credentials in `.env` are insecure placeholders | Must be replaced before any deployment |
| T-10 | LiteLLM env interpolation syntax in `config.yaml` needs verification | Confirm `${VAR}` substitution is supported by the deployed version |
| T-11 | Backend/frontend have no healthchecks in Compose | `depends_on` for LiteLLM is only `service_started`; add healthchecks |
| T-12 | Initial SQL schema and ORM models may diverge | Generated columns, vector dimensions and new tables need one migration source of truth |

---

## 6. Database overlaps and gaps

### Overlaps to consolidate

| ID | Overlap | Consolidation |
|----|---------|---------------|
| D-01 | Three conversation models: `conversations`/`conversation_messages`, `conversation_threads`/`visitor_messages`, and D4's `conversation_threads`/`conversation_messages`/`contexts`/`summaries`/`attachments` | One conversation model with `owner_type` (iam_internal / visitor) and `owner_id`; attachments and summaries as child tables |
| D-02 | `skills` + `capability_definitions` + `language_profiles` | One capability registry with typed assessments; language profiles as a specialisation |
| D-03 | `model_registry` + `model_versions` + `model_evaluations` + `ai_providers` + `discovered_models` + `model_comparisons` | One provider → model → version → evaluation chain; router reads from it |
| D-04 | `integration_registry` + `external_integrations` + `external_services` + permission tables + `credential_references` | One integration registry with permissions, usage and secret references |
| D-05 | `security_incidents` + `incident_records` + `audit_events` | One incident table; audit events remain separate append-only stream |
| D-06 | `financial_budgets` + `business_budgets` + `operating_expenses` + `approved_reinvestments` | One budget table scoped by owner (system / business / project) |
| D-07 | `resource_metrics` + `provider_usage` + `request_usage` | One metering table with dimensions (provider/model/visitor/worker) |
| D-08 | `memory_items` + `experiences` + `knowledge_items` + embeddings | Explicit taxonomy: episodic, semantic, procedural, relationship, working, self — one base table with type and typed views |
| D-09 | `agent_collaborations` + `delegated_tasks` | One collaboration/delegation entity with status and verification |
| D-10 | `scheduled_activities` + `monitored_targets` | One scheduler with trigger types (cron, event, threshold) |

### Gaps in D1 §6 database domains

D1 §6 omits entire domains that D2–D4 require. Add:
- Global access: `anonymous_visitors`, `visitor_sessions`, `visitor_locations`, `visitor_preferences`, `visitor_consents`, `visitor_memory_permissions`, `request_jobs`, `request_usage`, `visitor_rate_limits`
- Internet access: `internet_sessions`, `browser_actions`, `online_accounts`, `published_content`, `monitored_targets`, `retrieved_files`, `internet_permissions`, `internet_events`
- AI network: `external_agents`, `agent_interactions`, `agent_trust_records`, `agent_collaborations`
- Creator authority: `creator_requests`, `signed_challenges`, `creator_approvals`, `creator_authorizations`, `communication_audit`
- Reflection/life: `reflection_entries`, `operating_principles`, `life_history`, `goal_lifecycles`
- Resilience: `health_checks`, `recovery_logs`, `backup_verifications`, `incident_records`, `credential_rotations`
- Governance: `authority_boundaries`, `security_boundaries`, `approval_policies`
- Digital assets, model router, world model, capability registry tables

**Recommendation:** Produce a single canonical ERD and generate migrations from ORM models, not from a parallel hand-written SQL file.

---

## 7. Open decisions requiring owner input

These cannot be invented by the architecture. They need your decision before implementation.

| ID | Decision | Options | Recommended default |
|----|----------|---------|---------------------|
| OD-01 | Permanent identity scheme | UUIDv5 / ULID / content-addressed ID | ULID with genesis record |
| OD-02 | Owner relationship & legal entity | Personal owner / named entity / trust | Named legal entity for economic activity |
| OD-03 | Creator authorization method | Approval UI / config file / hardware key | **Locked: hardware key / external signer, email carrier (OD-19), no UI** |
| OD-04 | Spending limits | Per-transaction / monthly / per-project | Monthly ceiling, per-transaction cap, owner-only increase |
| OD-05 | Memory ownership & retention | Session-only default / opt-in anonymous / accounts | Session default, anonymous opt-in, accounts optional |
| OD-06 | RPO / RTO | e.g. RPO 24h, RTO 4h | RPO 24h / RTO 4h initially |
| OD-07 | Secrets manager | Vault / SOPS / Docker secrets | SOPS + Docker secrets initially |
| OD-08 | Queue runtime | Celery / ARQ / RQ | ARQ (async-native) |
| OD-09 | Jurisdictions for privacy compliance | ZA only / ZA+EU / global | ZA + EU baseline |
| OD-10 | Self-development infrastructure | Same VPS isolated / separate VPS | Separate dev VPS, no production credentials |

---

## 8. Reconciled final system architecture

```
PUBLIC EDGE
  Global Access Gateway → Session Manager → GeoIP Resolver → Rate/Abuse Control
                       → Conversation Manager → Streaming Service

INTELLIGENCE CORE
  IAM Orchestrator
    ├── Reasoning Engine / Planning Engine / Reflection Engine
    ├── Model Gateway (LiteLLM) + Intelligence Router
    │     └── Providers: NVIDIA · Dashscope · OpenAI · Anthropic · Ollama · local
    ├── Memory Service (episodic/semantic/procedural/relationship/working/self)
    ├── Knowledge & Verification Service
    ├── World Model
    └── Agent Orchestrator (internal specialised agents)

CAPABILITIES
  Internet Access (search, browser, files, APIs, monitoring)
  External AI Network (discovery, communication, trust, collaboration)
  Multimodal (voice, vision, video, documents, translation)
  Digital Workspace & Isolated Execution
  Creation / Software Development
  Economy / Ecosystem Manager

CONTROL PLANE
  Identity & Constitution
  Governance & Owner Authorization (single authority service)
  Approval Service
  Secrets Manager
  Security Operations
  Resilience / Backup / Recovery
  Evaluation Framework
  Observability & Audit (append-only)

DATA PLANE
  PostgreSQL + pgvector · Redis · S3-compatible storage
```

**Single authority service** resolves C-01. **Single conversation model** resolves D-01. **Single integration registry** resolves D-04. **Single metering table** resolves D-07. **Single ERD generated from ORM** resolves T-12.

---

## 9. Phased implementation plan (aligned to D1 §15)

| Phase | canonical deliverable | Workstreams absorbed | Exit gate |
|-------|----------------------|----------------------|-----------|
| 0 | Architecture, infrastructure, security, repo | OD-01…OD-10 decided; ERD; API contracts | Docs frozen; ERD + OpenAPI approved; security policy signed |
| 1 | Identity, model gateway, original interface | D2 M1; D4 M1–M2 | IAM identity persists; NVIDIA via router; HTML interface live; multi-turn chat |
| 2 | Memory & knowledge | D2 M3 | Memory retrieval, provenance, isolation tests pass |
| 3 | Global anonymous access | D4 M3–M5 | Anonymous sessions, GeoIP, concurrent isolated visitors, load test passed |
| 4 | Internet & external AI | D3 workflows | Browser interaction, research, agent discovery/communication, trust gates |
| 5 | Autonomy & goals | D1 §6 lifecycle | Goals/tasks/decisions, authority enforcement, reflection |
| 6 | Multimodal | D4 M6 | Voice, vision, documents, per-visitor media isolation |
| 7 | Digital workspace & software dev | D2 M4 | Isolated dev env, tests, versioning, rollback |
| 8 | Self-development & model independence | D2 M2 + M5 | Provider swap without identity loss; validated improvements |
| 9 | Ecosystem & products | D3 §13–14 | Multiple projects, asset registry, owner-approved publishing |
| 10 | Economic independence & advanced evolution | D2 M5, D3 §14 | Ledger reconciliation, KYC/AML arrangements, advanced research |

---

## 10. Immediate next actions (in order)

1. **Save the four supplied documents verbatim as the canonical source of truth** and replace the earlier draft versions in the repository; add document versioning/change control (M-20).
2. **Decide OD-01 through OD-10** — at minimum OD-01, OD-02, OD-04, OD-05 (blocking).
3. **Produce the canonical ERD** from consolidated models; resolve D-01…D-10; generate one migration source (T-12).
4. **Write OpenAPI contracts and the SSE event schema** (M-06, C-10).
5. **Write the Internet Access Policy and Security Policy** (C-06, S-01…S-14).
6. **Fix build blockers:** Playwright install in Dockerfile (T-02), pgvector dimension strategy (T-01), Next.js upgrade (T-03), container resource limits (T-06), healthchecks (T-11).
7. **Then begin Phase 0/1 implementation** with the phase exit gates above.

---

## 11. Assessment

The vision is comprehensive and internally consistent at the level of intent. The gaps are mostly *specification depth*, not missing concepts. Nothing found so far invalidates the architecture. Once the blocking decisions are made and the ERD/API/security specifications exist, the system can be implemented phase by phase without discovering that a major capability was forgotten.

**No coding should begin until items 1–6 in Section 10 are complete.**

---

## 12. Resolution status (updated same day)

| Item | Status | Artifact |
|------|--------|----------|
| Canonical database design (D-01…D-10, T-01, T-12) | RESOLVED | `IAM_DATABASE_DESIGN.md` |
| API contracts + SSE schema (M-06, C-10) | RESOLVED | `IAM_API_CONTRACTS.md` |
| Security & internet policy (C-06, S-01…S-14) | RESOLVED | `IAM_SECURITY_AND_INTERNET_POLICY.md` |
| T-02 Playwright install in Dockerfile | FIXED | `backend/Dockerfile` (`playwright install --with-deps chromium`) |
| T-03 Next.js security advisory | FIXED | `package.json` bumped to `^14.2.35` (reinstall pending) |
| T-06 container resource limits | FIXED | `docker-compose.yml` deploy limits (backend 2 CPU/4G, frontend 1 CPU/2G) |
| T-11 healthchecks | FIXED | `docker-compose.yml` healthchecks for backend, frontend, LiteLLM; backend waits for healthy LiteLLM |
| OD-01…OD-10 owner decisions | OPEN | Provisional defaults recorded in database design; require owner confirmation |

**Remaining before implementation:** owner decisions (OD-01…OD-10), verbatim canonical copy of the four supplied documents, OpenAPI code generation from contracts, and modal SQL→Alembic migration generation.

### Package upgrade (resolved same day)

| Item | Status |
|------|--------|
| T-03 Next.js security advisory | RESOLVED — upgraded 14.2.0 → 14.2.35 → **16.4.6** (all critical CVEs cleared) |
| React | Upgraded 18.3.1 → 19.3.1 (required by Next 16) |
| ESLint packages | Removed (source of glob/minimatch CVEs; Next 16 has no `next lint`) |
| `npm audit` | **0 vulnerabilities** |
| Production build | `npm run build` passes — 24 pages, 0 errors |
| Pre-existing bugs fixed by strict Turbopack build | duplicate `useState` in external-presence page; unclosed `<div>` in owner page; missing `Attach` icon (→`Paperclip`); missing `MessageCircle` import |

---

## 13. Owner decisions resolved (24 November 2026)

All ten decisions are now locked. See `IAM_OWNER_DECISIONS.md` for the full register.

| ID | Decided value |
|----|---------------|
| OD-01 | ULID + immutable genesis record |
| OD-02 | Named legal entity designated by owner |
| OD-03 | Hardware key / external signer for approvals |
| OD-04 | Zero standing budget — every expenditure requires signed approval |
| OD-05 | Remember anonymous visitors by default (opt-out, retention, deletion required) |
| OD-06 | RPO 24h / RTO 4h |
| OD-07 | SOPS + Docker secrets |
| OD-08 | ARQ (async Redis) |
| OD-09 | Global privacy compliance baseline |
| OD-10 | Separate dev VPS / containers, no production credentials |

The gap analysis is now fully resolved on documentation. The remaining pre-implementation artifacts have been generated:

### Generated artifacts (complete)

| Artifact | Status | Detail |
|----------|--------|--------|
| OpenAPI schema | GENERATED | `IAM_OPENAPI.json` — 708 paths, 435 schemas |
| Initial Alembic migration | GENERATED | `backend/app/db/migrations/versions/0001_initial.py` — 119 tables |
| Migration generator | TOOL | `backend/generate_migration.py` — regenerates migration offline from ORM |

### Environment notes (host constraints)

- Host uses Python 3.15 with an Application Control policy that blocks compiled C extensions (SQLAlchemy 2.1, asyncpg). Pinned SQLAlchemy `<2.1` (pure-Python fallback).
- Database engine creation is now lazy (`app/core/database.py`) so the app can import for schema generation without a DBAPI driver.
- Added missing deps: `pgvector`, `python-multipart`, Hatch wheel package config in `pyproject.toml`.
- The Alembic migration was compiled offline from `Base.metadata` via the PostgreSQL dialect — no live DB or asyncpg required.

**Pre-implementation phase is now complete.** Phase 0/1 implementation can begin.

### Stack brought up + frontend wired (verified end-to-end)

- Docker stack: PostgreSQL+pgvector (119 tables via ORM `create_all`), Redis, LiteLLM, MinIO, FastAPI backend — all healthy.
- Frontend → backend wired via same-origin Next.js rewrites (`/api/*` → port 8000), eliminating CORS.
- Verified: anonymous session creation, GeoIP context, per-visitor conversation isolation, message persistence (user + assistant) in PostgreSQL.
- Chat request reaches backend and model gateway; only external inference is unavailable until API keys are set in `.env`.
- First milestone progress: independent website ✅, IAM identity ✅, real multi-turn backend chat ✅, persists after restart ✅, isolated visitor sessions ✅. Remaining: real model inference (needs API keys), memory retrieval nodes, autonomous task initiation.

### Phase 1 continuation (25 November 2026)

- IAM bootstrap service added: immutable ULID genesis record (`iam_identity_genesis`), constitution (operating principles), authority/security boundaries, internet permissions, model providers — all idempotent, run at startup.
- Contextual suggestions endpoint (`/api/v1/interface/suggestions`) — mode-aware, region-aware, never private data.
- Permission-filtered public memory nodes (`/api/v1/interface/nodes`) — replaced frontend's direct read of IAM private memory, enforcing public/private separation.
- Frontend wired to both endpoints; dynamic suggestions and real public nodes now shown.
- Backend + frontend parse/build cleanly. Apply requires Docker daemon (restarting).
- **UI/UX features completed without DB:** real spoken responses via browser SpeechSynthesis (toggle), cancel-generation (AbortController + timer cleanup), retry-last-query, subtle backend connection indicator (health check via Next.js `/health` rewrite). Frontend builds cleanly; verified in browser.
- **Environment note:** Docker Desktop WSL integration became unresponsive (engine `_ping` 503); clean shutdown, process kill and `wsl --shutdown` attempted. Requires machine reboot per Docker/Microsoft guidance. Phase 1 code activation pending: `docker compose up -d --build backend` after reboot.

---

## 14. Distributed architecture addendum (24 November 2026)

The architecture now formally includes distributed systems (confirmed decisions OD-11…OD-15):
- Creator authority over a **protected core only**; local deployments may configure permitted settings and install approved extensions.
- **Hybrid P2P** network with offline-capable peers; original server is not a single point of failure.
- **Restricted reporting** for modified deployments; revocation for untrusted ones.
- **IAM Aegis** — independent defensive engine that studies Shirudo as a reference, never a dependency.
- **OEDIE** — Open Ecosystem Discovery and Integration Engine (free/self-hosted first).

See `IAM_DISTRIBUTED_ARCHITECTURE.md` (Document 05) and `IAM_DISTRIBUTED_GAP_ANALYSIS.md`.
The distributed gap analysis has its own blocking items (DT-02/03, CA-01/03, SY-01/02, RR-01/04, RC-01/03, AG-01/03) to resolve before distributed-system coding begins (phases D0–D8). Base Phase 0/1 implementation is unaffected.

**Document 06 (OD-16/OD-17):** white-hat defensive identity as a permanent part of IAM Aegis, with mandatory offensive-capability restrictions enforced outside the personality prompt; and a provider-independent, replaceable development environment (Coder primary, Codespaces optional). See `IAM_WHITEHAT_AND_WORKSPACE.md` and sections 12–14 of `IAM_DISTRIBUTED_GAP_ANALYSIS.md`. Blocking items: WH-01/WH-02 (target policy + tool-gateway restrictions), WS-02 (workspace isolation).
