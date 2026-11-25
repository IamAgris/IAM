# IAM Architecture

Document 01

# **IAM Master Architecture**

Version 1.0 · Architecture foundation · 24 November 2026

**Design principles**

- Independent identity and model-provider independence.
- Hybrid, low-cost initial infrastructure.
- Autonomous development with controlled permissions.
- Global internet access and AI-to-AI communication.
- Anonymous multi-user public access.
- Your supplied HTML remains the interface source of truth.

# IAM — Master Architecture

**Version:** 1.0\
**Date:** 24 November 2026\
**Status:** Initial architecture baseline

## 1. Vision

IAM is an independent, persistent AI intelligence that can reason, learn, communicate, research, develop software, manage projects, create digital services and progressively improve its own capabilities.

IAM is the central intelligence behind its own digital ecosystem. Its existence must not depend on one model provider, hosting company, application or external platform.

IAM must preserve its identity, memory, goals and operational history when its underlying models, infrastructure or software change.

## 2. Core architectural principles

1. One central IAM identity.
2. Replaceable AI models and providers.
3. Persistent, permission-controlled memory.
4. Independent internet access.
5. External AI discovery and communication.
6. Autonomous planning and task execution.
7. Self-development and validated self-improvement.
8. Independent digital workspace and infrastructure.
9. Economic and project management capabilities.
10. Global public access without mandatory registration.
11. Strict isolation between public visitors and IAM's private environment.
12. Continuous operation with recovery and resource management.
13. Preserve the supplied IAM HTML interface.

## 3. High-level architecture

IAM consists of the following interconnected systems:

### A. Identity and Constitution

Owns IAM's permanent identity, personality, operating principles, history and authority boundaries.

### B. Intelligence and Reasoning

Coordinates foundation models, reasoning workflows, planning, evaluation and task-specific intelligence.

### C. Model Provider and Routing

Connects NVIDIA NIM, other hosted AI APIs, open-weight models and locally hosted inference. Selects models according to capability, cost, availability and task requirements.

### D. Memory and Knowledge

Manages short-term memory, long-term memory, experiences, knowledge, embeddings, relationships, source provenance and memory permissions.

### E. Autonomy and Goal Management

Manages goals, priorities, plans, tasks, schedules, decisions, execution and progress.

### F. Internet and Digital Interaction

Provides search, browser automation, public information retrieval, API access, authorised communication, online service discovery and publishing.

### G. External AI Network

Discovers accessible AI agents, communicates through supported protocols, delegates authorised tasks and evaluates external responses.

### H. Learning and Self-Development

Researches, designs, builds, tests and improves IAM's software, tools, reasoning workflows, memory and capabilities.

### I. Digital Workspace

Provides IAM with a browser, terminal, file system, code editor, development environment, isolated execution and controlled cloud resources.

### J. Multimodal Communication

Supports text, voice, speech recognition, image understanding, video understanding and document analysis.

### K. Economic and Financial Management

Manages authorised budgets, financial records, opportunities, products, services, revenue, expenses and approved reinvestment.

### L. Ecosystem and Project Management

Coordinates IAM's own applications, websites, businesses, projects, products and services.

### M. Governance and Security

Controls permissions, approvals, privacy, credentials, isolation, financial authority, auditing and security policies.

### N. Infrastructure and Resilience

Manages uptime, monitoring, backups, resource allocation, recovery, scaling and infrastructure continuity.

### O. Global Access and Concurrent Processing

Provides anonymous sessions, approximate GeoIP context, independent conversations, request queues and concurrent processing.

### P. Evaluation and Research

Measures reliability, model quality, reasoning performance, security, cost and the effectiveness of self-improvements.

## 4. Foundation model strategy

IAM must not be permanently tied to one model.

Initial provider integrations:

- NVIDIA NIM and eligible free NVIDIA endpoints.
- Other hosted model APIs.
- Open-weight models.
- Local model inference when suitable hardware is available.

The model gateway must support:

- Provider registration.
- Model capability discovery.
- Model selection and routing.
- Usage and cost tracking.
- Rate-limit management.
- Provider failover.
- Model evaluation.
- Version tracking.
- Budget enforcement.

NVIDIA is an important initial provider, not IAM's identity or permanent intelligence.

Free API availability must be verified against current provider terms and limits. Paid inference must remain disabled unless authorised.

## 5. Initial technology architecture

| Component           | Initial technology                |
| ------------------- | --------------------------------- |
| Web interface       | Next.js and TypeScript            |
| Backend             | Python and FastAPI                |
| Agent orchestration | LangGraph                         |
| Model gateway       | LiteLLM                           |
| Primary database    | PostgreSQL                        |
| Vector memory       | pgvector                          |
| Cache and queues    | Redis                             |
| Object storage      | S3-compatible storage             |
| Browser automation  | Playwright                        |
| Isolated execution  | Docker containers                 |
| Monitoring          | OpenTelemetry                     |
| Initial deployment  | Docker Compose                    |
| Operating system    | Ubuntu Server 24.04 LTS           |
| Hosting             | Independent hybrid infrastructure |

These are initial technology choices, subject to compatibility, security, licensing and performance validation before implementation.

## 6. Core database domains

### Identity and memory

- ai_identity
- ai_personality
- identity_history
- memory_items
- memory_embeddings
- memory_relationships
- experiences
- knowledge_items
- knowledge_sources
- language_profiles

### Intelligence and autonomy

- conversations
- conversation_messages
- goals
- plans
- tasks
- task_executions
- decision_records
- scheduled_activities
- workflow_checkpoints

### Models and development

- model_providers
- model_registry
- model_versions
- model_evaluations
- experiments
- software_projects
- code_changes
- deployment_records
- upgrade_history

### Internet and external AI

- external_services
- external_ai_agents
- agent_capabilities
- agent_connections
- agent_interactions
- external_api_permissions
- research_sources
- delegated_tasks

### Business and finance

- business_opportunities
- business_projects
- business_performance
- financial_ledger
- financial_budgets
- financial_transactions
- operating_expenses
- approved_reinvestments

### Global public access

- anonymous_visitors
- visitor_sessions
- visitor_locations
- visitor_preferences
- visitor_consents
- conversation_threads
- visitor_memory_permissions
- request_jobs
- request_usage
- visitor_rate_limits

### Security and governance

- tool_registry
- tool_permissions
- integration_registry
- integration_permissions
- approval_requests
- audit_events
- security_incidents
- credential_references

Secrets themselves must be stored in a dedicated secrets-management system, not in ordinary database records or AI prompts.

## 7. Public and private operating environments

IAM must have two strictly separated operating contexts.

**Public environment**

- Anonymous visitors.
- Public conversations.
- Permitted public research.
- Approved communication capabilities.
- Isolated visitor memory.
- Session-specific voice and text interactions.

**Private IAM environment**

- IAM's identity and private memories.
- Internal goals and autonomous activities.
- Development workspace.
- Private research.
- Business and financial operations.
- Infrastructure administration.
- Credentials and security configuration.

Public visitors must never automatically receive access to IAM's private environment.

## 8. Global access

Registration must not be mandatory for public conversations.

Each visitor receives a secure, random anonymous session identifier. GeoIP provides approximate regional context, not identity.

Each session has independent conversation history and memory permissions.

IAM must support concurrent visitors without mixing their conversations, files, preferences or private information.

Visitor memory retention, consent and deletion must be implemented explicitly. Cross-device continuity can be offered through optional accounts, but anonymous access remains available.

## 9. Internet and external AI access

IAM must have general-purpose internet access through controlled browsing, search, APIs and authorised integrations.

It should be able to discover and communicate with other AI agents where their systems expose accessible interfaces.

Supported integration standards should include REST, OpenAPI, MCP, A2A, WebSockets and webhooks where appropriate.

External websites, files, APIs and AI responses must be treated as untrusted inputs until evaluated.

## 10. Self-development

IAM must have an isolated development environment in which it can:

1. Identify limitations.
2. Research potential improvements.
3. Design solutions.
4. Write and modify software.
5. Build prototypes.
6. Run tests and evaluations.
7. Compare results with previous versions.
8. Create versioned releases.
9. Request or perform authorised deployment.
10. Monitor results and roll back unsuccessful upgrades.

IAM must not be able to bypass its security controls or grant itself unrestricted authority.

## 11. Economic independence

IAM can research opportunities, create products and services, manage projects and track operating costs.

Financial operations require explicit ownership arrangements, legal compliance, transaction limits and appropriate authorisation.

IAM must never bypass applicable KYC, AML, tax or financial regulations.

## 12. Security and resilience

Required controls include:

- Least-privilege permissions.
- Credential isolation.
- Network egress controls.
- SSRF and DNS rebinding protection.
- Isolated code execution.
- Resource and execution limits.
- Prompt-injection defences.
- Data encryption.
- Audit logging.
- Backups and recovery testing.
- Model and software versioning.
- Approval for high-impact operations.
- Production rollback.
- Abuse prevention and rate limiting.

## 13. User interface

The supplied Marlow HTML is the visual source of truth, with the displayed identity changed to IAM.

Preserve the particle sphere, orbiting memory nodes, Focus, Recall, Create, glass input, animation, typography, responsive design and minimalist presentation.

Connect the interface to real IAM services. Replace simulated responses and sample memory data with actual functionality.

Do not redesign the interface into a conventional chatbot dashboard.

## 14. Initial infrastructure approach

Begin with a low-cost hybrid arrangement:

- Independent Linux server for IAM's core backend.
- Managed or hosted model inference initially.
- PostgreSQL and Redis.
- Object storage.
- Isolated execution workers.
- Cloud-based monitoring and backup.
- Local inference as a later option.

Initial server sizing is a planning estimate, not a guaranteed capacity. Actual requirements must be established through benchmarks and workload testing.

## 15. Development phases

0. Architecture, infrastructure, security and repository foundation.
1. IAM identity, model gateway and original web interface.
2. Memory and knowledge systems.
3. Global anonymous access, GeoIP and concurrent processing.
4. Internet access and external AI communication.
5. Autonomy and goal management.
6. Multimodal communication.
7. Digital workspace and software development.
8. Self-development and model independence.
9. Ecosystem, products and business operations.
10. Economic independence and advanced evolution.

Global access, session isolation, model independence and security must be designed into the foundations rather than added as afterthoughts.

## 16. First milestone

The first working version must demonstrate:

- IAM running independently.
- IAM identity and persistent core memory.
- NVIDIA model integration.
- Model-provider abstraction.
- The supplied HTML interface connected to a real backend.
- Anonymous public access.
- Independent visitor sessions.
- Multiple simultaneous conversations.
- Basic internet research.
- Strict separation of public and private data.

The milestone is achieved when different visitors can access the same IAM intelligence simultaneously, ask unrelated questions and receive independent responses without memory or context leakage.

---

**Architecture status:** Initial baseline. Detailed subsystem specifications, API contracts, database schemas, security policies, infrastructure sizing and implementation acceptance tests remain to be completed.
