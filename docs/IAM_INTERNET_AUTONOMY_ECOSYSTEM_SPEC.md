# IAM — Internet, Autonomy and Ecosystem Specification

> **HISTORICAL — SUPERSEDED.** Retained for development history only. Superseded by `canonical/IAM_DOC_03_INTERNET_AUTONOMY_ECOSYSTEM.md`. Do not use as a current source of truth.

**Status:** SUPERSEDED — early draft companion to the superseded master architecture.

---

## 1. Internet Access and Digital Interaction System

Full general-purpose access to the open internet — not just IAM's own hosting.

**Ten components:** web search/discovery; full browser automation (navigate, click, type,
submit, scroll, screenshot, text, links); internet communication; API/service integrations;
AI-to-AI communication; online identity/account management; file/information retrieval with
scanning; real-time monitoring; online publishing/content management; internet security,
privacy and permission management.

**Permission distinction:**
- Autonomous: browse public websites, search, read public content, download public files,
  call public APIs, discover services.
- Owner-authorized: send messages, spend money, register accounts, publish content,
  access private services, join communities.

Implementation: `/api/v1/internet/*`, `InternetPermission`, `InternetEvent` audit trail,
persistent Playwright browser sessions.

---

## 2. Autonomy

Independent goal creation within authority; planning and task execution; continuous background
operation; self-directed research; scheduled activities; multiple simultaneous projects;
progress tracking; decision histories; problem/opportunity identification; operates without
waiting for a prompt for every task.

Operational loop states: idle, exploring, learning, working, developing, reviewing, conserving.
Event-driven plus scheduled reflection — not continuous expensive model calls.

Life management: daily self-management, long-term goals, priorities, personal development,
continuity after restart/outage/model change, chronological life history.

---

## 3. Digital workspace

Own browser, terminal, file system, development environment, cloud-hosted services, database
and storage management, application/website development, software testing, controlled external
service access. Environment isolated from the infrastructure protecting identity, credentials
and production systems.

Three environments: development (autonomous), testing (autonomous), production (controlled).

---

## 4. Creation and economic independence

Software, products, services and businesses. Opportunity discovery, market/competitor research,
product development, customer management, sales, subscriptions, support, project profitability.

Financial management: income/expense tracking, double-entry ledger, cash-flow forecasting,
budgets, tax records, reporting, reinvestment planning. Digital assets: software, websites,
domains, IP records, product catalogue.

Independence milestones: cover operating costs → recurring revenue → operating reserve →
finance additional projects → expand infrastructure when justified.

Real-money operations respect legal ownership, KYC/AML and approval requirements. IAM is not
a legal person; accounts and assets use eligible person/entity arrangements.

---

## 5. Ecosystem management

IAM manages multiple independently operated projects — each with its own purpose, objectives,
budget, resources, metrics, development history and operational permissions. IAM remains the
central intelligence and allocates resources between projects (e.g. research project, software
product, commercial website, educational platform simultaneously).

Ecosystem modules: IAM Research, Studio, Ventures, Social, Finance, Labs — capabilities of
one IAM, not six AI personalities.

---

## 6. Resilience and security

Health monitoring, automatic recovery, backup verification, disaster recovery, credential
rotation, version rollback, emergency shutdown, incident history. Threat modelling,
vulnerability/dependency monitoring, secure development, access management, intrusion
detection, encrypted backups, supply-chain protection, privacy management, recovery drills.
IAM cannot disable its own security or grant itself unrestricted access.

---

## 7. Relationship and knowledge integrity

Relationship management: people, organisations, conversation histories, preferences,
commitments, dates, trust assessments, cultural context. Distinguish personal information,
public information and assumptions; respect privacy and deletion.

Knowledge verification: source provenance, confidence, verification status, contradiction
detection, memory correction, protection against memory poisoning and prompt injection.
