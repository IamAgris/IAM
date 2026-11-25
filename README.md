# IAM — Independent AI Entity

**Project Codename:** AURA (Autonomous Unified Reasoning Architecture) — engineering codename only  
**Status:** Architecture frozen — 16 documents, 32 decisions, 7 resolved specs. All 5 acceptance levels passed.  
**Interface:** The supplied HTML is the visual source of truth; displayed identity is **IAM** (Intellectual Artificial Mainbrain).  
**Native skill system:** IAM Skill Forge — [specification](IAM_SKILL_FORGE_SPEC.md)  
**External security engines:** ARTEX connector — [specification](IAM_ARTEX_INTEGRATION_SPEC.md)  
**Creator authority:** email + signed challenge, no Creator UI — [specification](IAM_CREATOR_APPROVAL_SPEC.md)

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
| Foundation model | Qwen3.5-9B (replaceable) |
| Backend | Python + FastAPI |
| Agent orchestration | LangGraph |
| Model gateway | LiteLLM |
| Database | PostgreSQL + pgvector |
| Cache / queue | Redis |
| Web interface | Next.js + TypeScript |
| Browser automation | Playwright |
| Execution | Isolated Docker containers |
| Storage | S3-compatible (MinIO) |
| Deployment | Docker Compose initially |

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
├── frontend/                 # Next.js + TypeScript (24 pages)
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
| External AI Network | `/api/v1/network/` |
| Internet Access | `/api/v1/internet/` |

---

## Frontend Pages

`/`, `/conversations`, `/identity`, `/memory`, `/research`, `/voice`, `/vision`,
`/development`, `/autonomy`, `/learning`, `/businesses`, `/finances`, `/resources`,
`/security`, `/external-presence`, `/external-presence/vibecircle`, `/life`, `/world`,
`/resilience`, `/capabilities`, `/governance`, `/reflection`

---

## Getting Started

```bash
# 1. Copy environment file
cp .env.example .env
# Edit .env with your secure values (DASHSCOPE_API_KEY, APP_SECRET_KEY, etc.)

# 2. Start infrastructure
docker compose up -d

# 3. Initialize database
docker exec -i aura-postgres psql -U aura -d aura_db < backend\app\db\migrations\001_initial_schema.sql

# 4. Open the UI
# http://localhost:3000
```

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
- **`IAM_FINAL_CONSOLIDATION.md`** — master gap analysis: all systems, conflicts, completion levels, roadmap
- `IAM_OPEN_SPECS_RESOLVED.md` — resolved engineering specs A–G (creator keys, memory boundaries, P2P, hardware, scaling, finance, operations)
- `IAM_DATABASE_DESIGN.md` — canonical ERD and migration strategy
- `IAM_DATABASE_INTEGRATION_REPORT.md` — live Postgres verification, fixes and remaining migration issues
- `IAM_API_CONTRACTS.md` — endpoint contracts and SSE streaming schema
- `IAM_SECURITY_AND_INTERNET_POLICY.md` — security and internet access policy
- `IAM_OWNER_DECISIONS.md` — 32 owner decisions (ALL LOCKED)
- `IAM_OPENAPI.json` — generated OpenAPI schema (113 paths, 103 schemas)
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
| 6 | Computer environment and software development (specified) |
| 7 | Self-improvement and model independence (specified) |
| 8 | Businesses, financial systems and economic independence (specified) |
| 9 | Digital presence and ecosystem integrations ✅ |
| 10 | Advanced research, world modelling and continued evolution (specified) |
