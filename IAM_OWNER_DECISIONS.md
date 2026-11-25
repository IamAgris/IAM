# IAM — Owner Decision Register

**Status:** ALL 37 DECISIONS LOCKED (25 November 2026).  
**Purpose:** Record of every owner decision (OD-01…OD-37) made during architecture finalisation. This is now a historical register — no decisions are pending.

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

**Security principle (confirmed):** integrity reporting is best-effort when another party controls a deployment. Signed attestations and hardware-backed verification strengthen it, but IAM must never falsely claim a compromised machine cannot hide modifications.

## Status: ALL THIRTY-SEVEN DECISIONS LOCKED (25 November 2026)

Decisions OD-33…OD-37 were confirmed on 25 November 2026 and are listed above. They add new capabilities without modifying any earlier decision, including OD-08 (ARQ queue runtime).

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

---

## Change control (frozen)

This register is frozen at 37 decisions. Any change to a locked decision requires the owner to explicitly reopen it and record the new value with a date and reason. Changes to OD-01 (identity), OD-03 (signing), OD-04/OD-25 (financial authority) or OD-11 (protected core) additionally require a signed creator approval.
