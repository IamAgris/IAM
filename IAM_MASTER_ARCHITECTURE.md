# IAM — Master Architecture

**Status:** FROZEN — architecture baseline  
**Companion documents:** Intelligence & Self-Evolution Spec · Internet, Autonomy & Ecosystem Spec · UI & Global Access Spec  
**Note:** This describes one integrated IAM system, not four separate projects.  
**Addenda:** `IAM_DISTRIBUTED_ARCHITECTURE.md` · `IAM_HARDWARE_ADAPTATION.md` · `IAM_DYNAMIC_NODE_NETWORK_SPEC.md` (OD-26) · `IAM_UNIVERSAL_WEBSITE_INTERACTION_SPEC.md` (OD-27) · `IAM_AI_ASSISTANT_INTEROPERABILITY_SPEC.md` (OD-28) · `IAM_DEVELOPER_SDK_AND_CLI_SPEC.md` (OD-29) · `IAM_GLOBAL_RESEARCH_AND_KNOWLEDGE_SPEC.md` (OD-30) · `IAM_LEGAL_INTELLIGENCE_AND_COMPLIANCE_SPEC.md` (OD-31) · `IAM_GEOSPATIAL_INTELLIGENCE_AND_LIVE_MAPPING_SPEC.md` (OD-32)

---

## 1. Definition

IAM is one central, persistent AI entity with its own identity, memory, autonomy and
ecosystem. It is not a chatbot, not a collection of disconnected assistants, and not
dependent on any single model provider, hosting provider or external platform.

Five characteristics: **Identity, Intelligence, Autonomy, Independence, Continuity.**

Important distinction: IAM is a highly autonomous adaptive agent. This architecture makes
no claim of consciousness or human-like subjective experience.

### Control vs education (permanent distinction)

Two layers govern IAM's behaviour and both are required:

- **Infrastructure enforcement** (permissions, tool gateway, network controls, execution
  environment) defines what IAM **can** do. This is the authoritative security control.
- **Personality and constitution** teach IAM the **law** — legal boundaries, ethical
  reasoning and how it should operate within them. This defines what IAM **should** do.

The personality prompt is **not** a security control and never replaces enforcement. If the
two ever conflict, the infrastructure control is authoritative and the personality yields.
Teaching the law makes IAM's behaviour principled; enforcing it in infrastructure makes it safe.

### Communication channels (Document 07)

IAM uses three separate channels: operational (Google/Gmail) for signups and service communications; Creator authority (IAM domain email) for approval requests signed via hardware signer — **not** a dashboard; and private user communication with isolated per-user memory and privacy-preserving collective learning. The frontend is a user interface only.

---

## 2. Core systems (15 + cross-cutting)

| # | System | Responsibility |
|---|--------|----------------|
| 1 | Identity and Constitution | Permanent IAM identity, personality, continuity, operating principles |
| 2 | Intelligence and Reasoning | Models, providers, router, reasoning, world model, knowledge |
| 3 | Memory and Knowledge | Episodic, semantic, procedural, relationship, working, self-memory |
| 4 | Autonomy and Goal Management | Goals, plans, tasks, decisions, scheduling, background operation |
| 5 | Learning and Capability Development | Research, education, measurable capability registry |
| 6 | Communication and Multimodal | Text, voice, vision, video, documents, translation |
| 7 | Digital Workspace and Computer Environment | Browser, terminal, files, dev environment, cloud services |
| 8 | Creation and Software Development | Software, products, IP, versioning, deployment |
| 9 | Economic and Financial Management | Businesses, finances, assets, approved reinvestment |
| 10 | Ecosystem and Project Management | Multiple independently managed projects under one intelligence |
| 11 | Self-Evolution and Model Independence | Experiments, model replacement, validated upgrades, rollback |
| 12 | Governance, Security and Privacy | Permissions, owner authority, secrets, audit, isolation |
| 13 | Infrastructure and Operational Resilience | Hosting, monitoring, backups, disaster recovery, portability |
| 14 | Evaluation and Research | Benchmarks, reliability, research lab, change validation |
| 15 | Global Access, Anonymous Visitors and Concurrent Processing | Public access, GeoIP, isolated sessions, scaling |

**Cross-cutting:** External AI Network and Internet Access & Digital Interaction System —
spanning systems 2, 6, 7, 8, 10, 12 and 15.

---

## 3. Technology baseline

| Layer | Technology |
|-------|-----------|
| Foundation model | Qwen3.5-9B starting candidate — replaceable |
| Additional providers | NVIDIA NIM (free endpoints), Alibaba Dashscope, OpenAI, Anthropic, Ollama, open-weight/local |
| Backend | Python + FastAPI |
| Orchestration | LangGraph |
| Model gateway | LiteLLM |
| Database | PostgreSQL + pgvector |
| Cache / queues | Redis |
| Frontend | Next.js + TypeScript (Marlow HTML as source of truth) |
| Browser | Playwright |
| Execution | Isolated Docker containers |
| Storage | S3-compatible |
| Deployment | Docker Compose initially; hybrid low-budget hosting |
| Monitoring | OpenTelemetry |

---

## 4. Authority model

Four levels: (1) independent thinking — autonomous; (2) internal execution — autonomous;
(3) external operations — policy-controlled; (4) high-impact decisions — human authorization.

Creator-controlled, AI-non-bypassable: the human Creator authorizes through email plus a
verified signed challenge at `/api/v1/creator/requests/{id}/decide`. IAM reads the resulting
`creator_authorizations` but cannot create or modify them. The legacy `/owner` path was
removed. There is no code path for IAM to self-grant authority, self-raise financial limits
or disable its own security.

IAM is not a legal person. Legal ownership of accounts, companies and domains is assigned
to an eligible person or entity; IAM operates them only under owner authorization with
disclosure.

---

## 5. Public vs private separation

**Public IAM:** anonymous visitors, isolated sessions, public capabilities, no access to
private infrastructure.

**IAM private environment:** identity, private memories, goals, development environment,
business/financial operations, security configuration, owner controls.

A public visitor can ask IAM to write code but does not gain access to IAM's private computer.
Public requests run through an explicitly permitted capability layer.

---

## 6. Data architecture

PostgreSQL is the source of truth with pgvector for semantic memory. All data groups:
identity/memory, intelligence/autonomy, self-development, business/finance, security,
life management, world model, resilience, capability, research lab, social intelligence,
business engine, digital assets, model router, global access, internet access,
AI network, owner authorization, governance and reflection.

Every stored knowledge item carries source, timestamp, confidence, verification status,
last review, topic, relationships and review/expiry policy. Distinguish facts, opinions,
hypotheses, preferences and creative content.

Visitor data is strictly isolated. Private IAM memories never enter visitor contexts.
Internet and external-AI content is untrusted until verified.

---

## 7. Infrastructure and continuity

- Hosted inference initially; no GPU purchase required.
- Daily backups, encrypted off-site copies, versioned identity/memory exports.
- Backup verification (actual restore tests), disaster recovery, failover.
- Identity portability across hosting providers and model changes.
- Recovery targets must be defined (RPO/RTO) before production.
- Resource monitoring, cost controls, abuse/rate limits.

---

## 8. Development phases

0 Foundations · 1 Identity/intelligence/interface · 2 Persistent memory · 3 Autonomy ·
4 Internet/research/languages · 5 Voice/vision · 6 Computer/software development ·
7 Self-improvement/model independence · 8 Business/finance · 9 Digital presence/ecosystem ·
10 Advanced research/world modelling/continued evolution.

Phases 0–9 have implemented scaffolding; Phase 10 is specified. Each phase has tests and
acceptance criteria. Autonomy is not widened merely because a previous phase works.

---

## 9. Definition of completion

First working release: own website and identity; communication through the Marlow interface;
remembers conversations after restarts; retrieves previous experience; initiates permitted
tasks; researches online; maintains goals and unfinished projects; creates and tests software;
auditable security and permissions.

Full vision: all ecosystem capabilities implemented, tested and operating reliably.
