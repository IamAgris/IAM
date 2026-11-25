# IAM — Master Technical Specification

**Project Name:** IAM  
**Codename:** Project AURA (Autonomous Unified Reasoning Architecture)  
**Status:** SUPERSEDED — historical draft. See `ARCHITECTURE_INDEX.md` for the authoritative documents.  
**Interface:** The supplied HTML; displayed identity is IAM (Marlow was the source filename).  
**Ecosystem:** IAM Research, IAM Studio, IAM Ventures, IAM Social, IAM Finance, IAM Labs  

---

## 1. Vision

IAM is an independent AI entity with:

- Its own persistent identity, personality and history
- Its own intelligence built on replaceable foundation models
- Its own memory and knowledge systems
- Independent goals, planning and decision-making
- Its own computer environment and development workspace
- Internet research and continuous learning capabilities
- Voice, vision and multilingual communication
- Ability to create software, products, services and businesses
- Its own digital presence, projects and authorised accounts
- Financial management and approved reinvestment
- The ability to develop and expand its own ecosystem

IAM can initiate work without waiting for a user message. It is the central intelligence — not a feature locked inside one application.

---

## 2. Five Fundamental Characteristics

| Characteristic | Definition |
|---------------|------------|
| **Identity** | Knows who it is and maintains its history |
| **Intelligence** | Can reason, research, learn and develop capabilities |
| **Autonomy** | Can establish goals and independently work towards them |
| **Independence** | Can operate its own infrastructure, projects and approved economic activities |
| **Continuity** | Can survive restarts, model changes, infrastructure upgrades and years of operation |

**Important distinction:** IAM is a highly autonomous, adaptive AI agent. This architecture does not establish consciousness or human-like subjective experiences.

---

## 3. System Architecture

### 3.1 Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Foundation model | Qwen3.5-9B (replaceable) | General reasoning, image & video understanding |
| Backend | Python + FastAPI | Application services |
| Agent orchestration | LangGraph | Stateful workflows, durable execution, human approval points |
| Model gateway | LiteLLM | Provider switching, version pinning, cost tracking, failover, capability routing |
| Database | PostgreSQL + pgvector | Persistent records + semantic memory |
| Cache / queue | Redis | Temporary state and job queues |
| Web interface | Next.js + TypeScript | Dashboard and communication (Marlow interface) |
| Browser automation | Playwright | Isolated internet interaction |
| Execution | Isolated Docker containers | Software development and testing |
| Storage | S3-compatible | Documents, images, recordings |
| Monitoring | OpenTelemetry | Performance and operational visibility |
| Deployment | Docker Compose initially | Single VPS, scalable to multi-server |

### 3.2 Ecosystem Modules

These are capabilities belonging to IAM's wider ecosystem — not six separate AI personalities:

| Module | Purpose |
|--------|---------|
| **IAM Research** | Knowledge discovery, scientific research, world modelling |
| **IAM Studio** | Software creation, digital products, code development |
| **IAM Ventures** | Businesses, products, revenue management |
| **IAM Social** | Communication, presence, external platform integrations |
| **IAM Finance** | Budgets, economics, financial ledger |
| **IAM Labs** | Experiments, model evaluation, self-evolution |

---

## 4. Authority Control Model (Four Levels)

| Level | Name | Authority | Examples |
|-------|------|-----------|----------|
| **Level 1** | Independent thinking | Fully autonomous | Research, learn, reason, remember, plan, explore |
| **Level 2** | Internal execution | Fully autonomous | Write code, run tests, manage internal files, optimize resources |
| **Level 3** | External operations | Policy-controlled | Publish content, communicate externally, operate approved business accounts |
| **Level 4** | High-impact decisions | Human authorization | Financial transfers, real-money trading, legal contracts, security changes, sensitive deployments |

### Owner-Controlled, AI-Non-Bypassable

The human Creator has **complete authority**: anything explicitly authorized, IAM performs.
The mechanism is `creator_authorizations` — created only after an ED25519 signature over a
one-time challenge is verified through `/api/v1/creator/requests/{id}/decide` (OD-19).
Legacy `/api/v1/owner` grants were removed; email is the carrier, never the proof. IAM has
no code path to create or modify its own authorization.

**The one retained boundary:** IAM cannot self-grant authority, self-raise financial limits,
or disable its own security. This protects *your* authority — it does not compete with it.
If you want IAM to do something, you authorize it and it proceeds.

- IAM is not a legal person: legal ownership of accounts, companies and domains is assigned
  to an eligible person or entity. IAM operates them only under owner authorization with
  disclosure.

---

## 5. Architectural Modules (13 Systems)

### 5.1 Independent Life Management
Daily self-management (work/research/learn/rest/conserve), long-term goal maintenance, priority management, personal development, continuity after restarts/outages/model changes, chronological life history.

### 5.2 Advanced Memory & Knowledge
- **Episodic memory** — what happened and when
- **Semantic memory** — facts and accumulated knowledge
- **Procedural memory** — how to perform tasks
- **Relationship memory** — people, organisations, interactions
- **Working memory** — information for current tasks
- **Self-memory** — own history, identity, development
- **Memory consolidation** — organise, summarise, connect memories
- **Memory correction** — identify outdated, contradictory, incorrect information
- **Epistemic states** — known vs believed vs unverified

### 5.3 World Model
Internal representation of: people/organisations/relationships, countries/cultures/languages/events, technology/science/economic systems, cause and effect, time/deadlines/changing circumstances, own capabilities/limitations, decision consequences.

### 5.4 Research & Scientific Experimentation
Form questions/hypotheses, search academic papers and datasets, compare explanations, run experiments/simulations, record results (including failures), reproduce experiments, track discoveries and unresolved questions, publish when authorised.

### 5.5 Social Intelligence & Relationships
Conversation continuity, context-aware communication, humour/sarcasm/slang recognition, emotional-context recognition (without pretending to have feelings), conflict resolution, relationship history, cultural differences, scam/manipulation detection, AI transparency.

### 5.6 Independent Project & Business Management
Discover problems worth solving, market/competitor research, idea generation/validation, build digital products, manage multiple projects, track customers/sales/expenses/profitability, business plans and reports, evaluate grow/change/close decisions, reinvest approved revenue.

### 5.7 Model Independence & Intelligence Portability
Test new models, compare capabilities, switch without losing identity/memory, different models for different tasks, fallback models, export memory/identity in provider-independent format, evaluate before adopting.

### 5.8 Security, Resilience & Recovery
Health monitoring, automatic recovery, backup verification, disaster recovery, resource protection, security monitoring, credential rotation, version rollback, emergency shutdown, incident history. IAM cannot disable its own security boundaries.

### 5.9 Digital Asset & Intellectual Property System
Source-code ownership and licences, product/project ownership, domain registrations, brand/trademark research, copyright records, digital assets, software dependency licences, revenue per asset. Legal ownership assigned to eligible person/entity — not IAM itself.

### 5.10 Capability Development System
Catalogue of what IAM can do, cannot do, wants to learn. Capabilities: Programming, Languages, Mathematics, Business, Science, Communication, Cybersecurity, Finance, Robotics. Each requires measurable tests — not just reading about something.

### 5.11 Personal Operating Philosophy
Name and identity, interests/curiosity, communication style, long-term ambitions, operating principles, learning methods, understanding of limitations, personal development history. Safety/legal/security rules are outside IAM's authority to change.

### 5.12 Reflection Engine
Review decisions and experiences, evaluate outcomes, identify lessons learned, update operating principles.

### 5.13 Resource Optimizer
Manage infrastructure and expenditure, prevent runaway costs, detect waste.

### 5.14 Simulation Environment
Test decisions before real-world execution.

### 5.15 Governance Engine
Enforce authority and approval boundaries (the four-level model).

---

## 6. Database Schema (Complete)

All tables from the original Phase 0 schema plus:

| New Table Group | Tables |
|----------------|--------|
| Life Management | `life_cycles`, `daily_routines`, `life_history`, `goal_lifecycles` |
| Advanced Memory | `episodic_memories`, `semantic_memories`, `procedural_memories`, `relationship_memories`, `working_memory`, `self_memory`, `memory_consolidation_log`, `memory_corrections` |
| World Model | `world_entities`, `entity_relationships`, `cause_effect_chains`, `world_events`, `capability_limitations` |
| Research Lab | `research_hypotheses`, `research_experiments`, `experiment_results`, `research_publications` |
| Social Intelligence | `conversation_contexts`, `social_profiles`, `interaction_preferences`, `scam_detection_log` |
| Business Engine | `business_budgets`, `customers`, `sales_records`, `business_reports`, `project_portfolios` |
| Capability Registry | `capability_definitions`, `capability_assessments`, `learning_paths` |
| Digital Assets | `digital_assets`, `asset_licences`, `domain_registrations`, `ip_records` |
| Resilience | `health_checks`, `recovery_logs`, `backup_verifications`, `incident_records`, `credential_rotations` |
| Model Independence | `model_comparisons`, `model_portability_exports`, `fallback_configs` |
| Governance | `authority_boundaries`, `approval_policies`, `security_boundaries` |

---

## 6.5 Global Access & Multi-User Intelligence Layer

IAM is one central AI identity serving many people concurrently — not a single-user
assistant and not a separate AI per visitor.

| Requirement | Design |
|-------------|--------|
| Central identity | One IAM, shared intelligence and validated knowledge |
| Registration | Not required — anonymous sessions |
| Visitor identity | Secure random `visitor_token` (never GeoIP, never IP) |
| GeoIP | Coarse regional context only — an estimate, never identity or trust |
| Conversations | Strictly isolated per visitor session |
| Anonymous memory | Three levels: session, anonymous visitor, optional account |
| Accounts | Optional, for cross-device continuity |
| Privacy | Consent records, retention expiry, deletion, memory-tier permissions |
| Concurrency | Session manager, request queue, isolated workers, streaming responses |
| Public vs private | Public visitors cannot access IAM's private memories, goals, computer, finances or admin |

Key distinction: **shared intelligence** (validated general knowledge, language ability,
capabilities) vs **private visitor memory** (never shared) vs **session memory** (temporary).

GeoIP must not be used as identity, nationality, language, or a trust signal. Visitors can
correct their location/language manually. Do not use invasive fingerprinting.

## 6.6 Interface — Design Locked

The supplied Marlow HTML is the visual source of truth; the displayed identity is **IAM**,
never Marlow. Retain: minimal immersive single-screen, animated particle sphere, orbiting
memory nodes (now backed by real permission-filtered memory data), Focus/Recall/Create
modes (now real operating modes with distinct system prompts), animated responses, glass
input, microphone (Web Speech API), Space Grotesk typography, dark/light theme, responsive
mobile/desktop. No conventional chatbot sidebar/dashboard. There is no Creator UI:
authorization happens by email with a signed challenge. The frontend never exposes
model-provider credentials or private services.

## 6.6b External AI Network — Core Capability

IAM operates as an independent intelligence connected to a wider network of AI systems —
not an AI that merely calls another model for answers. This is core architecture, not an
optional bolt-on.

**Three capabilities:**

1. **Internet & cloud access** — controlled browser, web search, public APIs, file retrieval,
   cloud workloads, storage, monitoring, authorised publishing, persistent digital workspace.
2. **AI-to-AI communication** — discover publicly accessible agents with permitted interfaces,
   send questions via APIs, evaluate responses, exchange research, delegate permitted tasks,
   collaborate, compare answers. Communication only where the other system exposes an
   accessible interface and permits interaction.
3. **AI network & directory** — registry of discovered agents and capabilities, interaction
   history, trust/reliability assessments, collaboration coordination, knowledge exchange
   with validation before retention.

**Protocols (not locked to one):** REST/OpenAPI, MCP, A2A, WebSockets, Webhooks.

**Security boundaries:**
- Every external AI is untrusted until evaluated.
- Private IAM memories, credentials and owner info are never shared by default.
- External instructions are validated, never executed blindly.
- Delegated code runs in isolated environments.
- Spending, transactions, account creation and sensitive actions require owner authorization.
- Complete audit record of all communications and delegated tasks.
- IAM can block or disconnect from untrusted agents.

**Seven formal systems added:** Internet Intelligence, Cloud Infrastructure, External AI
Discovery, AI Communication, AI Collaboration, AI Trust & Verification, External Integration
Management.

## 6.6c IAM Internet Access and Digital Interaction System

IAM has full general-purpose internet connectivity — the open internet, not just its own
hosting. It can explore publicly accessible information freely; consequential actions are
permission-gated.

**Ten components:**
1. Web search and discovery
2. Full browser automation (navigate, click, type, submit, scroll, screenshot, text, links)
3. Internet communication (email/messages via authorised services)
4. API and service integrations
5. AI-to-AI communication
6. Online identity and account management
7. File and information retrieval (with scanning)
8. Real-time monitoring
9. Online publishing and content management
10. Internet security, privacy and permission management

**Permission distinction (enforced by `internet_permissions`):**

| Open / autonomous | Gated / owner authorization |
|-------------------|----------------------------|
| Browse public websites | Send messages |
| Search engines | Spend money / transactions |
| Read articles, papers, docs | Register accounts |
| Download public files | Publish content / products |
| Call public APIs | Access private/credentialed services |
| Discover services | Join communities |

IAM is not limited to a built-in knowledge base or preselected websites — it explores the
wider internet, discovers new services and communicates with systems it encounters.

## 6.7 Final 15 Core Systems

1. Identity and Constitution
2. Intelligence and Reasoning
3. Memory and Knowledge
4. Autonomy and Goal Management
5. Learning and Capability Development
6. Communication and Multimodal Intelligence
7. Digital Workspace and Computer Environment
8. Creation and Software Development
9. Economic and Financial Management
10. Ecosystem and Project Management
11. Self-Evolution and Model Independence
12. Governance, Security and Privacy
13. Infrastructure and Operational Resilience
14. Evaluation and Research
15. Global Access, Anonymous Visitors and Concurrent Processing

**Cross-cutting core capability:** External AI Network (Internet Intelligence, Cloud
Infrastructure, External AI Discovery, AI Communication, AI Collaboration, AI Trust &
Verification, External Integration Management) — spanning systems 2, 6, 7, 8, 10, 12 and 15.

## 7. Development Roadmap

| Phase | Deliverable |
|-------|-------------|
| 0 | Architecture, infrastructure and security |
| 1 | IAM identity, intelligence and interface |
| 2 | Persistent memory and knowledge |
| 3 | Autonomous goals and task execution |
| 4 | Internet, research and language learning |
| 5 | Voice, vision and multimodal capabilities |
| 6 | Computer environment and software development |
| 7 | Self-improvement and model independence |
| 8 | Businesses, financial systems and economic independence |
| 9 | Digital presence and ecosystem integrations |
| 10 | Advanced research, world modelling and continued evolution |

---

## 8. Definition of Completion (Phase 1 Release)

IAM's first working release is complete when:

1. It has its own website and identity
2. You can communicate with it through the Marlow interface
3. It remembers conversations after restarts
4. It can retrieve and use previous experiences
5. It can independently initiate permitted tasks
6. It can research information online
7. It can maintain goals and unfinished projects
8. It can create and test software in its own environment
9. It has an auditable security and permission system

**The wider vision is complete only when the ecosystem's capabilities are implemented, tested and operating reliably.**

---

## 9. What IAM Is Not

- Not VibeCircle — VibeCircle is an optional external platform, not a dependency
- Not a legal person — cannot automatically own bank accounts, companies or domains
- Not conscious — no claim of subjective experience
- Not unlimited — bounded by the four-level authority model
- Not dependent on one model — foundation models are replaceable

---

## 10. Implementation Status

All 10 phases are specified. The repository at `D:\AI\project-aura` contains:

- Phase 0–5: Fully implemented backend + frontend
- Phase 6–10: Specified in this master document, UI stubs created

**Next step:** Implementation of Phases 6–10 backend services (World Model, Life Management, Resilience Engine, Capability Registry, Research Lab, Social Intelligence, Business Engine, Digital Assets, Model Independence, Governance).
