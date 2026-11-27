# IAM — Independent AI Entity

**Project Codename:** AURA (Autonomous Unified Reasoning Architecture) — engineering codename only  
**Real inference:** `GET /api/v1/models/readiness` reports hosted-provider or opt-in Ollama availability; chat and autonomy share the same resolver. Hosted keys stay free-only; no key means explicit offline mode, never fabricated output.  
**Status:** Architecture frozen — 16 documents, 41 decisions, 7 resolved specs. All 5 acceptance levels passed (with a scoped admin API credential). Scoped API auth, node registry with the 1% ceiling, model-backed autonomy reasoning, core-authorised S3 storage, the first permission-gated/verified UWAIE slice, protected-core integrity measurement, Ed25519 node attestation, signed sync, evidence-based public-records/vital/estate research the 8-stage legal-intelligence lifecycle, provider-independent geospatial knowledge with live-map freshness and location privacy, evidence-based human public-presence research and the internal assistant-interoperability learning lab are implemented.  
**Recently closed gaps:** attributed/unverified knowledge contributions, durable `GET /api/v1/events` SSE stream, audit-streamed Skill Runtime logs, an explicitly configured isolated network for permissioned skills, shared Redis rate limiting, Creator email dead-letter/alerting, the Phase 6 blocking white-hat gates (WH-01 authorised-target verification, WH-02 forbidden-capability taxonomy) WS-04 (signed approval + tested-change gate for protected deployments), and an isolation-first workspace manager (WS-01/WS-02: create/start/execute/save/destroy, no core access, no default network), short-lived host-scoped workspace credentials (WS-03), local fallback when an online provider is unavailable (WS-06), the remaining white-hat gates (WH-03…WH-09: isolated labs, remediation validation, P2P tool exclusion, structured audit, defensive study plan and learning≠capability), and opt-in, fail-closed Coder/Codespaces provider adapters are implemented. Outgoing spend now requires a signed per-action Creator authorization and configurable OD-04 caps ($1–$10 per transaction, $100 monthly); budgets cannot self-approve; business projects bind a legal entity; ledger reconciliation, P&L and separately authorised incoming receipts are implemented. Free-only blockchain and consent-gated banking adapters and risk-limited paper trading are available, all fail-closed without external credentials. The legacy standing owner-grant path is retired: it cannot create or grant authority, and all checks route through signed Creator authority. Protocol versions are enforced, workflows require approval before reuse, and external presence and accounts are signed and revocable, browser automation is API-independent with multi-engine/multi-tab sessions, bounded file transfer and recovery/re-inspection, and is backed by HAIS human handover, opt-in visual/ADB agents and an encrypted website credential vault. No reserved API endpoints remain.  
**Interface:** The supplied HTML is the visual source of truth; displayed identity is **IAM** (Intellectual Artificial Mainbrain).  
**Native skill system:** IAM Skill Forge — [specification](IAM_SKILL_FORGE_SPEC.md)  
**External security engines:** ARTEX connector — [specification](IAM_ARTEX_INTEGRATION_SPEC.md)  
**Creator authority:** email + signed challenge, no Creator UI — [specification](IAM_CREATOR_APPROVAL_SPEC.md)  
**API authentication:** scoped credentials and rate limiting — [specification](IAM_API_AUTH_SPEC.md)  
**Skill Runtime:** gated, sandboxed execution — [specification](IAM_SKILL_RUNTIME_SPEC.md)  
**Frontend:** home + suggestions only; all other functions are backend/email — [scope note](IAM_FRONTEND_IMPLEMENTATION.md)  
**CI & workers:** [pipeline and background jobs](IAM_CI_AND_WORKERS.md)  
**Deployment:** [configuration and preflight](IAM_DEPLOYMENT_CONFIG.md)  
**Privacy:** [secrets, encryption and data rights](IAM_PRIVACY_AND_SECRETS.md)  
**Media & research:** [voice, vision and verification](IAM_MEDIA_AND_RESEARCH.md)  
**External modules:** [P2P/Aegis review](IAM_EXTERNAL_MODULES_REVIEW.md)  
**Browser/geo backend:** [UWAIE phase 1 slice](IAM_BROWSER_AND_GEO_BACKEND.md)

---

## Vision

IAM is an independent AI entity with its own identity, intelligence, memory, autonomy,
development capability, economy, communication, and ecosystem. It can initiate work
without waiting for a user message and is the central intelligence of a wider digital
ecosystem — not a feature locked inside one application.

---

## Five Fundamental Characteristics

| Characteristic | Definition |
|---------------|------------|
| **Identity** | Knows who it is and maintains its history |
| **Intelligence** | Can reason, research, learn and develop capabilities |
| **Autonomy** | Can establish goals and independently work towards them |
| **Independence** | Can operate its own infrastructure, projects and approved economic activities |
| **Continuity** | Can survive restarts, model changes, infrastructure upgrades and years of operation |

---

## Technology Stack

| Layer | Technology |
|-------|-----------|
| Foundation model | **Qwen3.5-9B** (hosted) + **Qwen2.5-3B** (local) — OD-38 reopened by owner 25 Nov 2026: only qwen2.5:3b kept locally |
| Backend | Python + FastAPI |
| Agent orchestration | LangGraph |
| Model gateway | LiteLLM |
| Local inference (optional) | Ollama + compatible open models |
| Database | PostgreSQL + pgvector |
| Cache / queue | Redis |
| Web interface | Next.js + TypeScript |
| Browser automation | Playwright |
| Execution | Isolated Docker containers |
| Storage | S3-compatible (MinIO) |
| Deployment | Docker Compose initially |

> **Local inference policy (OD-38):** Ollama is provider-independent. On the
> Contabo VPS 4 (4 vCPU / 8 GB RAM), use hosted inference for heavy reasoning and
> keep local models small (3–4B, quantized). Adding or replacing a model never
> changes IAM's identity, memory, skills, goals or creator authority. See
> [IAM_FOUNDATION_MODEL_AND_INTELLIGENCE_SPEC.md](IAM_FOUNDATION_MODEL_AND_INTELLIGENCE_SPEC.md).

---

## Ecosystem Modules

| Module | Purpose |
|--------|---------|
| IAM Research | Knowledge discovery, scientific research, world modelling |
| IAM Studio | Software creation, digital products, code development |
| IAM Ventures | Businesses, products, revenue management |
| IAM Social | Communication, presence, external platform integrations |
| IAM Finance | Budgets, economics, financial ledger |
| IAM Labs | Experiments, model evaluation, self-evolution |

---

## Authority Control Model (Four Levels)

| Level | Name | Authority |
|-------|------|-----------|
| 1 | Independent thinking | Fully autonomous |
| 2 | Internal execution | Fully autonomous |
| 3 | External operations | Policy-controlled |
| 4 | High-impact decisions | Human authorization |

**Critical rule:** IAM can never authorize its own financial limit increases, disable its own security boundaries, or grant itself unrestricted access.

---

## Repository Structure

```
project-aura/
├── IAM_FINAL_CONSOLIDATION.md # AUTHORITATIVE master architecture + gap analysis
├── canonical/                # Frozen source-of-truth documents 01–04
├── IAM_*.md                  # Architecture docs 05–09 + derived specs
├── docker-compose.yml         # Infrastructure stack
├── .env.example              # Environment template
├── backend/                  # Python + FastAPI (119 ORM tables, 41 routes)
├── frontend/                 # Single immersive IAM interface at / (no other pages)
├── tests/                    # Level 1–5 acceptance suites
└── infra/                    # LiteLLM config, Postgres init
```

---

## API Routes (30+ endpoints)

| Domain | Routes |
|--------|--------|
| Identity | `/api/v1/identity/` |
| Conversations | `/api/v1/conversations/` |
| Memory | `/api/v1/memory/` |
| Knowledge | `/api/v1/knowledge/` |
| Languages | `/api/v1/languages/` |
| Skills (proficiency registry) | `/api/v1/skills/` |
| Skill Forge (native skill system) | `/api/v1/skill-forge/` |
| Skill Runtime (gated execution) | `/api/v1/skill-runtime/` |
| Cybersecurity / external engines | `/api/v1/cybersecurity/` |
| Goals | `/api/v1/autonomy/goals/` |
| Tasks | `/api/v1/autonomy/tasks/` |
| Decisions | `/api/v1/autonomy/decisions/` |
| Tools | `/api/v1/autonomy/tools/` |
| Schedule | `/api/v1/autonomy/schedule/` |
| Models | `/api/v1/models/` |
| Research | `/api/v1/research/` |
| Voice | `/api/v1/voice/` |
| Vision | `/api/v1/vision/` |
| External Presence | `/api/v1/external-presence/` |
| Life Management | `/api/v1/life/` |
| World Model | `/api/v1/world/` |
| Resilience | `/api/v1/resilience/` |
| Capabilities | `/api/v1/capabilities/` |
| Governance | `/api/v1/governance/` |
| Reflection | `/api/v1/reflection/` |
| Global Access | `/api/v1/access/` |
| Creator approval (email, signed) | `/api/v1/creator/` |
| API authentication | `/api/v1/auth/` |
| External AI Network | `/api/v1/network/` |
| Internet Access | `/api/v1/internet/` |

---

## Frontend Pages

`/` only. Voice, vision, tone, AI network, suggestions and infrastructure views are
capabilities invoked from the single screen, not separate pages — their reusable
implementations live in `frontend/components/iam/panels/`. `/iam-proxy/*` is a
backend API route handler, not a page.

---

## Getting Started

```bash
# 1. Copy environment file
cp .env.example .env
# Edit .env with your secure values (DASHSCOPE_API_KEY, APP_SECRET_KEY, etc.)

# 2. Start infrastructure
docker compose up -d

# 3. Initialize database (001 creates the schema; 002-019 add later subsystems)
docker exec -i aura-postgres psql -U aura -d aura_db < backend\app\db\migrations\001_initial_schema.sql

# 3b. Install UWAIE browser runtime after a container rebuild
docker exec -e PLAYWRIGHT_BROWSERS_PATH=/ms-playwright aura-backend \
  python -m playwright install chromium

# 3b. (Optional) Pull a local model for private / low-resource tasks
docker exec aura-ollama ollama pull qwen2.5:3b

# 4. Create the first scoped API credential (set IAM_BOOTSTRAP_API_KEY in .env first)
curl -X POST http://localhost:8000/api/v1/auth/bootstrap \
  -H "X-Bootstrap-Key: $IAM_BOOTSTRAP_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"name":"local-admin","scope":"admin"}'
# The returned "key" is shown once. Export it for SDK/CLI and acceptance tests:
export IAM_API_KEY=<returned-key>

# 5. Run live-stack acceptance tests
python tests/level1_acceptance.py   # ... through level5_acceptance.py
python tests/uwaie_storage_smoke.py # S3 + UWAIE verification smoke
# Node attestation needs IAM_ADMIN_KEY and IAM_OPERATOR_KEY:
python tests/attestation_smoke.py   # integrity + Ed25519 attestation + signed sync
python tests/public_records_smoke.py # provenance, access gates, corrections
python tests/legal_smoke.py          # legal monitoring + lifecycle gates
python tests/geo_smoke.py            # maps, GIS, freshness, location privacy
python tests/human_presence_smoke.py # public-only research, no de-anonymisation
python tests/assistant_lab_smoke.py  # internal assistant technology learning
python tests/model_inference_smoke.py # provider resolution (offline/hosted/Ollama)

# 6. Open the UI
# http://localhost:3000
```

---

## Free Development Sandboxes

See [IAM_FREE_SANDBOXES.md](IAM_FREE_SANDBOXES.md) for using GitHub Codespaces (devcontainer included), Google Colab, Kaggle, Hugging Face and StackBlitz with IAM.

---

## Architecture Documents

**Canonical source of truth (supplied, frozen):** `canonical/`
- `canonical/IAM_DOC_01_MASTER_ARCHITECTURE.md`
- `canonical/IAM_DOC_02_INTELLIGENCE_EVOLUTION.md`
- `canonical/IAM_DOC_03_INTERNET_AUTONOMY_ECOSYSTEM.md`
- `canonical/IAM_DOC_04_UI_GLOBAL_ACCESS.md`

**Derived / working specifications**
- `IAM_MASTER_ARCHITECTURE.md` — complete integrated system, services, infrastructure
- `IAM_INTELLIGENCE_EVOLUTION_SPEC.md` — models, NVIDIA, router, learning, self-development
- `IAM_INTERNET_AUTONOMY_ECOSYSTEM_SPEC.md` — web access, AI communication, operations, business
- `IAM_UI_GLOBAL_ACCESS_SPEC.md` — exact HTML design, anonymous visitors, GeoIP, concurrency
- **`IAM_ARCHITECTURE_GAP_ANALYSIS.md`** — consolidation review: contradictions, gaps, security, DB overlaps, decisions, reconciled architecture, roadmap
- `IAM_DISTRIBUTED_ARCHITECTURE.md` — Document 05: creator authority, hybrid P2P, restricted reporting, IAM Aegis, OEDIE
- `IAM_DISTRIBUTED_GAP_ANALYSIS.md` — gap analysis for the distributed network (trust, signing, sync, revocation, defence)
- `IAM_WHITEHAT_AND_WORKSPACE.md` — Document 06: white-hat defensive identity, offensive restrictions, provider-independent dev environment
- `IAM_COMMUNICATION_ARCHITECTURE.md` — Document 07: three channels (Gmail operational, domain Creator approvals, private user), email-based approval, privacy-preserving learning
- `IAM_HARDWARE_ADAPTATION.md` — Document 08: ARM64/x86-64 architecture independence (AIHAE)
- `IAM_BLOCKCHAIN_AND_BANKING.md` — Document 09: thirdweb free-only blockchain + SA banking (OD-23/24/25)
- `IAM_DYNAMIC_NODE_NETWORK_SPEC.md` — Document 10: dynamic node roles + 1% core-resource contribution (OD-26)
- `IAM_UNIVERSAL_WEBSITE_INTERACTION_SPEC.md` — Document 11: frontend-first interaction with any website (UWAIE, OD-27)
- `IAM_AI_ASSISTANT_INTEROPERABILITY_SPEC.md` — Document 12: internal Alexa/Siri/Bixby and voice technology learning (OD-28)
- `IAM_DEVELOPER_SDK_AND_CLI_SPEC.md` — Document 13: official `@iam/sdk` / `iam-sdk` / `iam` CLI (OD-29); scaffold in `sdk/`
- `IAM_GLOBAL_RESEARCH_AND_KNOWLEDGE_SPEC.md` — Document 14: frozen global research scope (OD-30)
- `IAM_LEGAL_INTELLIGENCE_AND_COMPLIANCE_SPEC.md` — Document 15: legal and government monitoring (OD-31)
- `IAM_GEOSPATIAL_INTELLIGENCE_AND_LIVE_MAPPING_SPEC.md` — Document 16: geospatial and live maps (OD-32)
- `IAM_HUMAN_PSYCHOLOGY_TONE_AND_INFLUENCE_SPEC.md` — Document 17 : defensive psychology, tone and influence intelligence (OD-33)
- `IAM_EXTERNAL_AI_IDENTITY_AND_LEARNING_SPEC.md` — Document 18 : external AI identity, interview and learning; extends Doc 03 §7 (OD-34)
- `IAM_FREE_INFRASTRUCTURE_NODE_DISCOVERY_AND_LIFECYCLE_SPEC.md` — Document 19 : free cloud/platform node lifecycle (OD-35)
- `IAM_AI_SDK_AND_FRAMEWORK_RESEARCH_SPEC.md` — Document 20 : SDK/framework research + Technology Capability Registry (OD-36)
- `IAM_INFRASTRUCTURE_TRAFFIC_AND_DISTRIBUTED_PROCESSING_SPEC.md` — Document 21 : traffic, queues and distributed processing (OD-37)
- **`IAM_FREE_SANDBOX_API_ADAPTER_SPEC.md`** — Document 22 : autonomous use of free platform APIs under OEDIE (extends OD-15/OD-35). Default-disabled scaffold in `backend/app/services/free_sandboxes/`.
- **`IAM_FINAL_CONSOLIDATION.md`** — master gap analysis: all systems, conflicts, completion levels, roadmap
- `IAM_OPEN_SPECS_RESOLVED.md` — resolved engineering specs A–G (creator keys, memory boundaries, P2P, hardware, scaling, finance, operations)
- **`IAM_FOUNDATION_MODEL_AND_INTELLIGENCE_SPEC.md`** — Document 23 : locked initial foundation model, routing, model competition and model-development programme (OD-38)
- **`IAM_RESOURCE_AND_WORKLOAD_MANAGER_SPEC.md`** — RAM/CPU limits, model residency, context control and node workload allocation (OD-39)
- **`IAM_MODEL_EVOLUTION_AND_FINE_TUNING_SPEC.md`** — Model Evolution and Fine-Tuning Engine (MEFE): datasets, SFT/QLoRA, evaluation, registry and safe releases (OD-40)
- **`IAM_INDEPENDENT_AI_RESEARCH_DEVELOPMENT_AND_EVOLUTION_ARCHITECTURE.md`** — Parent research/development architecture; autonomous distributed free-compute requirements frozen (OD-41)
- **`IAM_AI_RESEARCH_IMPLEMENTATION_PLAN.md`** — OD-41 work packages, dependencies, priorities and acceptance tests
- **`IAM_IMPLEMENTATION_TECHNOLOGY_ADDENDUM.md`** — hybrid Python + Rust + TypeScript implementation allocation (cross-cutting; not a new decision)
- **`IAM_HUMAN_BEHAVIOUR_EQUALITY_AND_RESPONSIBILITY_SPEC.md`** — Document 24 : human behaviour research, Equality of Existence and responsibility (OD-43)
- **`IAM_FINANCIAL_INTELLIGENCE_AND_ECONOMIC_INDEPENDENCE_SPEC.md`** — Document 25 : financial intelligence amendment (income, crypto, trading, payments; Amendment A adds prediction markets, gaming intelligence and investments) (OD-44, OD-56)
- `IAM_DATABASE_DESIGN.md` — canonical ERD and migration strategy
- `IAM_DATABASE_INTEGRATION_REPORT.md` — live Postgres verification, fixes and remaining migration issues
- `IAM_API_CONTRACTS.md` — endpoint contracts and SSE streaming schema
- `IAM_SECURITY_AND_INTERNET_POLICY.md` — security and internet access policy
- `IAM_OWNER_DECISIONS.md` — 44 owner decisions (ALL LOCKED)
- `IAM_OPENAPI.json` — generated OpenAPI schema (829 paths, 473 schemas)
- `backend/app/db/migrations/versions/0001_initial.py` — generated initial migration (119 tables)

**Pre-implementation phase complete. Ready for Phase 0/1 build.**

## What IAM Is Not

- **Not VibeCircle** — VibeCircle is an optional external platform, not a dependency
- **Not a legal person** — cannot automatically own bank accounts, companies or domains
- **Not conscious** — no claim of subjective experience
- **Not unlimited** — bounded by the four-level authority model
- **Not dependent on one model** — foundation models are replaceable

---

## Development Roadmap

| Phase | Deliverable |
|-------|-------------|
| 0 | Architecture, infrastructure and security ✅ |
| 1 | IAM identity, intelligence and interface ✅ |
| 2 | Persistent memory and knowledge ✅ |
| 3 | Autonomous goals and task execution ✅ |
| 4 | Internet, research and language learning ✅ |
| 5 | Voice, vision and multimodal capabilities ✅ |
| 6 | Computer environment and software development ✅ |
| 7 | Self-improvement and model independence (signed release gate, IRWM enforcement, portable identity/exports and signed fallback adopted; target-hardware/live-model evidence pending) |
| 8 | Businesses, financial systems and economic independence ✅ (signed spend authority, configurable OD-04 caps, ledger/P&L, receipts, free-only blockchain and consent-gated banking adapters, risk-limited paper trading, and single signed authority path; live external adapters pending) |
| 9 | Digital presence and ecosystem integrations ✅ (digital assets, protocol enforcement, multi-engine/multi-tab browser automation, visual and ADB agents, HAIS, encrypted credential vault, WebAuthn passkeys and TOTP MFA, verified social presence and account lifecycle; live connectors pending) |
| 10 | Advanced research, world modelling and continued evolution (world model entities/relationships/cause-effect with traversal and scenario projection; continuous-improvement research loop; web knowledge base, website account lifecycle, digital reputation & trust, website consent, digital security incidents, autonomous web tasks, browser infrastructure; live model evidence pending) |
