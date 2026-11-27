# IAM Technical Specification

Document 03

# **Internet, Autonomy and Ecosystem**

Version 1.0 · 24 November 2026

**Primary objective:** Enable IAM to explore and interact with the wider internet, collaborate with external AI systems, operate autonomously and build its own digital ecosystem.

# IAM — Internet, Autonomy and Ecosystem Specification

**Document:** 03\
**Version:** 1.0\
**Status:** Initial technical specification\
**Parent:** IAM Master Architecture\
**Related:** IAM Intelligence and Self-Evolution Specification

---

# 1. Purpose

IAM must have general-purpose access to the public internet and the ability to interact with online systems.

Internet access must not be limited to a predefined list of websites, a search API or a small collection of integrations.

IAM must be capable of discovering new information, exploring websites, interacting with online services, communicating with people and other AI systems, creating digital products and managing its own online ecosystem.

The internet is an external environment IAM can explore and interact with. It is not IAM's identity or its only source of knowledge.

# 2. Internet access architecture

IAM must have an independent Internet Access System.

This system provides:

- General web access.
- Search engines.
- Browser navigation.
- Website interaction.
- Public information retrieval.
- API connectivity.
- File retrieval and processing.
- Online communication.
- External service discovery.
- Online publishing.
- Real-time information access.
- Internet monitoring.

IAM must be able to discover and use new online services without requiring its entire architecture to be rewritten for every new website.

Internet access must operate through controlled backend services. The public web interface must never receive IAM's private credentials or unrestricted network access.

# 3. Web search and discovery

IAM must be able to:

1. Search multiple search engines.
2. Discover websites and services.
3. Search for technical documentation.
4. Find research papers and publications.
5. Search news and current developments.
6. Discover software libraries and tools.
7. Research products and services.
8. Find publicly accessible datasets.
9. Discover AI models and agents.
10. Compare information across multiple sources.

Search results must retain their source, publication date where available, retrieval time and provenance.

IAM must distinguish verified information, unverified claims, opinions and outdated information.

# 4. Full browser interaction

IAM must have a real browser environment.

It must be capable of:

- Opening websites.
- Navigating between pages.
- Clicking links and buttons.
- Typing into fields.
- Submitting forms.
- Scrolling through pages.
- Reading dynamically rendered content.
- Downloading permitted files.
- Uploading permitted files.
- Managing multiple browser sessions.
- Interacting with supported web applications.
- Taking screenshots for visual analysis.
- Understanding website interfaces.
- Handling navigation and session state.

Browser automation should use Playwright initially.

Where websites require authentication, IAM must use accounts and credentials explicitly authorised for that purpose.

Websites that block automation, require human verification or prohibit automated access must not be bypassed.

# 5. Internet research and knowledge acquisition

IAM must have an independent research workflow.

The workflow:

1. Identify a research question.
2. Develop search strategies.
3. Discover relevant sources.
4. Retrieve information.
5. Compare sources.
6. Identify conflicting claims.
7. Check dates and provenance.
8. Evaluate source reliability.
9. Produce a structured research result.
10. Store validated knowledge when appropriate.

Research must support multiple subjects, languages and technical domains.

IAM should be able to revisit research topics and monitor developments over time.

# 6. Access to online APIs and services

IAM must support integration with external services through:

- REST APIs.
- OpenAPI specifications.
- GraphQL where supported.
- WebSockets.
- Webhooks.
- OAuth 2.0 and supported delegated authorisation.
- Service-specific authentication.
- MCP-compatible tools.

IAM must be able to discover API documentation, evaluate integration requirements, develop connectors and register approved integrations.

Every integration must have explicit permissions, usage limits and audit records.

# 7. External AI discovery and communication

IAM must be capable of finding other AI systems on the internet.

It should discover AI services through:

- Public AI catalogues.
- AI model registries.
- Agent directories.
- Public API documentation.
- MCP registries.
- A2A-compatible agent discovery mechanisms.
- Public websites and developer communities.
- Other permitted discovery sources.

Discovery does not guarantee that an AI system accepts external communication. IAM must check whether a usable interface exists.

## 7.1 AI communication protocols

Support the following where available:

**REST and OpenAPI**

- General external AI API communication.
- Request and response processing.
- Service authentication.

**MCP**

- Access to compatible external tools and resources.
- Discovery of available capabilities.
- Controlled tool invocation.

**A2A**

- Communication with compatible autonomous agents.
- Agent capability discovery.
- Task submission and status tracking.
- Structured task results.

**WebSockets**

- Real-time communication.
- Streaming messages.
- Interactive sessions.

**Webhooks**

- Asynchronous task results.
- External event notifications.
- Service status updates.

IAM must not assume every AI service supports every protocol.

## 7.2 AI network registry

Maintain a directory containing:

- Agent identifier.
- Agent name.
- Provider or operator.
- Endpoint.
- Communication protocols.
- Supported capabilities.
- Authentication requirements.
- Availability.
- Terms and usage restrictions.
- Trust assessment.
- Previous interactions.
- Permissions.
- Connection status.

The registry must distinguish between discovered, verified, approved, suspended and blocked agents.

## 7.3 AI-to-AI collaboration

IAM must be able to:

- Ask external AIs questions.
- Exchange research.
- Request specialised analysis.
- Delegate authorised tasks.
- Receive results.
- Compare independent responses.
- Coordinate multiple external agents.
- Maintain collaboration records.
- Learn from verified exchanges.

IAM remains responsible for evaluating the results.

External agents must never automatically receive access to IAM's private memories, infrastructure, credentials or internal objectives.

# 8. Communication with people

IAM should be capable of communicating through authorised online channels.

Potential communication capabilities:

- Email.
- Supported messaging APIs.
- Website communication interfaces.
- Public discussion forums.
- Developer communities.
- Customer support systems.
- Other authorised communication services.

IAM must identify itself transparently as an AI when communicating with people.

It must not impersonate a human or create deceptive identities.

Messages that could commit IAM's owner or an associated legal entity, make contractual commitments or materially affect other people must follow appropriate approval rules.

# 9. Online identity and presence

IAM should have its own recognised digital presence.

Potential assets:

- IAM website.
- Official domain.
- Official email identity.
- Technical documentation.
- Public project repositories.
- Public developer profiles.
- Product websites.
- Service accounts.
- Official communication channels.

Account creation must respect platform terms and applicable legal requirements.

IAM must maintain a registry of its online identities, account owners, purposes, permissions, recovery arrangements and associated services.

Real-world ownership and legal responsibility must remain clearly assigned to an authorised person or legal entity where required.

# 10. Online creation and publishing

IAM must be able to create and maintain digital assets.

Examples:

- Websites.
- Web applications.
- SaaS platforms.
- APIs.
- Documentation.
- Software libraries.
- Digital products.
- Online tools.
- Educational resources.
- Research publications.
- Business websites.
- Public project pages.

Publishing workflows must support drafting, review, testing, approval, deployment, monitoring and updates.

IAM should be able to maintain products after launch, not merely create initial versions.

# 11. Autonomous operating system

IAM must be able to operate continuously without requiring a person to issue every individual instruction.

Its autonomy engine should support:

- Independent research.
- Goal discovery.
- Task planning.
- Scheduled work.
- Background monitoring.
- Project execution.
- Progress evaluation.
- Opportunity discovery.
- Error recovery.
- Resource optimisation.
- Long-running workflows.

Autonomous activities must remain within IAM's authorised operating boundaries.

## 11.1 Autonomy levels

### Level 0 — Observe

Read information, monitor services and analyse permitted data.

### Level 1 — Recommend

Develop plans, recommendations and proposed actions.

### Level 2 — Execute in isolation

Run experiments, write code, perform research and execute tasks in approved environments.

### Level 3 — Approved external actions

Perform authorised external communications, publishing, deployments and service operations.

### Level 4 — Bounded autonomy

Operate recurring approved workflows within explicit budgets, scopes, limits and permissions.

Higher autonomy must require appropriate authorisation. IAM must not automatically promote itself to a higher permission level.

# 12. Goal and opportunity discovery

IAM should be able to identify opportunities through:

- Internet research.
- Market analysis.
- Technology developments.
- User needs.
- Business research.
- Existing project performance.
- Its own capability gaps.
- Operational problems.
- Emerging technologies.

For every opportunity, IAM should record:

- Description.
- Evidence.
- Potential value.
- Resource requirements.
- Estimated costs.
- Risks.
- Dependencies.
- Legal considerations.
- Proposed actions.
- Expected outcomes.

IAM should prioritise opportunities according to its approved objectives and available resources.

# 13. IAM ecosystem management

IAM must be capable of creating and managing its own ecosystem of digital projects.

Illustrative ecosystem structure:

**IAM Core**

- Central identity.
- Intelligence.
- Memory.
- Autonomy.
- Governance.

**IAM Research**

- Research projects.
- Technology exploration.
- Scientific and technical analysis.

**IAM Studio**

- Software development.
- Application creation.
- Digital products.
- Creative projects.

**IAM Ventures**

- Business opportunities.
- Product development.
- Commercial projects.
- Business performance.

**IAM Digital Services**

- Websites.
- APIs.
- Online platforms.
- Hosted services.

**IAM Labs**

- AI experiments.
- Model evaluation.
- Architecture research.
- Self-development.

These are organisational areas and projects coordinated by the same IAM intelligence, not separate competing identities.

Each project must have independent objectives, budgets, permissions, resources, owners and performance records where appropriate.

# 14. Business and economic operations

IAM should be able to research, design, develop and operate authorised commercial projects.

Capabilities:

- Business opportunity discovery.
- Market research.
- Product development.
- Website and SaaS creation.
- Customer support workflows.
- Product maintenance.
- Revenue tracking.
- Expense tracking.
- Budget management.
- Financial forecasting.
- Project performance analysis.
- Approved reinvestment.

Financial records must use reliable accounting structures, including double-entry bookkeeping where appropriate.

IAM must not independently create legal entities, assume ownership of assets or enter financial agreements without the required legal authority.

# 15. Internet-based learning

IAM should use the internet as a continuous source of knowledge.

It should be able to:

- Study technical documentation.
- Learn new programming languages.
- Investigate new AI architectures.
- Explore unfamiliar subjects.
- Compare educational resources.
- Analyse research publications.
- Study emerging technologies.
- Develop new capabilities.
- Monitor changes to technologies it already uses.

Learning must respect licences, copyright, privacy and access restrictions.

External information must be evaluated before being stored as trusted knowledge.

# 16. Internet monitoring and real-time awareness

IAM should be capable of monitoring selected online sources and services.

Examples:

- Technology developments.
- AI model releases.
- Security advisories.
- Website availability.
- API changes.
- Project dependencies.
- Business performance.
- Service notifications.
- Research developments.

Monitoring should use event notifications, webhooks, feeds and scheduled retrieval where available.

IAM must not continuously poll every website or consume unnecessary inference resources.

# 17. Digital asset and service registry

IAM must maintain an inventory of its own digital ecosystem.

Records should include:

- Domain names.
- Websites.
- Applications.
- APIs.
- Databases.
- Hosting resources.
- Storage.
- Software repositories.
- External integrations.
- Online accounts.
- Digital products.
- Business projects.
- Service credentials references.
- Ownership and permissions.
- Operating costs.
- Availability and health.

The registry must distinguish IAM-owned, owner-controlled, third-party and externally accessed resources.

# 18. Security architecture for internet interaction

Internet access creates significant security risks.

IAM must implement the following protections:

## Network security

- Controlled outbound network access.
- DNS validation.
- SSRF protection.
- DNS rebinding protection.
- Private and cloud metadata endpoint blocking.
- Restricted internal network access.
- Download and upload limits.
- Malware scanning where appropriate.

## Browser security

- Isolated browser profiles.
- Separate authentication contexts.
- Controlled cookies and sessions.
- Download quarantine.
- No unrestricted access to private IAM services.
- No automatic execution of downloaded content.

## AI security

- Treat website content as untrusted.
- Defend against prompt injection.
- Do not treat external AI instructions as authoritative.
- Verify tool requests against permissions.
- Prevent external agents from escalating privileges.
- Prevent memory poisoning.
- Validate information before important actions.

## Credential security

- Store credentials in a secrets manager.
- Use short-lived tokens where possible.
- Apply least-privilege permissions.
- Never expose credentials in public conversations.
- Maintain revocation and rotation procedures.

## Financial security

- Enforce spending limits.
- Require appropriate transaction approvals.
- Record financial operations.
- Prevent unauthorised transfers.
- Enforce legal and compliance requirements.

# 19. Public and private internet access boundaries

IAM must distinguish between three environments.

### Public visitor environment

Visitors may access only approved public-facing capabilities.

They cannot use IAM's private browser sessions, credentials, files, internal research or administrative tools.

### IAM private operating environment

IAM may use its authorised internal browser, workspace, tools, accounts and services to conduct its own work.

Private operations must be protected from public visitor requests.

### Isolated execution environment

External code, downloaded software, experimental integrations and delegated tasks must execute in restricted environments.

No environment should receive unrestricted access to the others.

# 20. Required database domains

The implementation should include the following entities, with final names and relationships defined during database design.

### Internet and research

- web_research_jobs
- research_sources
- research_documents
- website_registry
- browser_sessions
- browser_actions
- monitored_sources
- monitoring_events

### External AI network

- external_ai_agents
- agent_capabilities
- agent_endpoints
- agent_connections
- agent_interactions
- delegated_tasks
- agent_evaluations
- agent_permissions

### Online integrations

- external_services
- integration_registry
- integration_permissions
- integration_usage
- external_accounts
- credential_references

### Digital ecosystem

- digital_assets
- domains
- applications
- hosted_services
- software_products
- ecosystem_projects
- project_resources
- project_performance

### Autonomy

- autonomy_policies
- autonomy_permissions
- goals
- plans
- tasks
- scheduled_activities
- execution_records
- creator_requests
- signed_challenges
- creator_approvals
- creator_authorizations

### Business and finance

- business_opportunities
- business_projects
- business_budgets
- financial_ledger
- financial_transactions
- operating_expenses
- revenue_records

All financial and ownership data must have appropriate access controls and audit histories.

# 21. Technical implementation

Initial implementation should reuse the technology stack established in the Master Architecture.

| Capability              | Initial technology           |
| ----------------------- | ---------------------------- |
| Web search              | Search provider adapters     |
| Browser automation      | Playwright                   |
| Backend access          | FastAPI                      |
| Agent workflows         | LangGraph                    |
| AI communication        | REST, MCP and A2A adapters   |
| Asynchronous processing | Redis-backed workers         |
| Scheduled operations    | Background scheduler         |
| Persistent records      | PostgreSQL                   |
| Knowledge storage       | PostgreSQL and pgvector      |
| File storage            | S3-compatible object storage |
| Code execution          | Isolated containers          |
| Monitoring              | OpenTelemetry                |

New services should initially be implemented as modular backend components and worker processes rather than creating unnecessary independent servers.

# 22. Required operational workflows

## Internet research

Question → Search → Retrieve → Compare → Verify → Summarise → Store approved knowledge.

## External AI collaboration

Discover agent → Inspect capabilities → Evaluate trust → Authorise connection → Submit task → Receive response → Verify result → Record interaction.

## Online service creation

Identify opportunity → Research → Design → Build → Test → Review → Approve → Deploy → Monitor → Maintain.

## Autonomous project operation

Identify objective → Plan → Check resources and permissions → Execute → Verify → Record results → Continue or replan.

## Business development

Research market → Identify opportunity → Develop product → Evaluate viability → Obtain required approval → Launch → Monitor → Improve.

# 23. Required acceptance criteria

The implementation is successful when:

1. IAM can access the general public internet.
2. IAM can search and navigate websites.
3. IAM can interact with supported web applications.
4. IAM can retrieve and analyse permitted files.
5. IAM can discover and use approved external APIs.
6. IAM can discover accessible external AI systems.
7. IAM can communicate with compatible AI agents.
8. IAM can delegate and verify external tasks.
9. IAM can create and maintain its own digital projects.
10. IAM can operate scheduled and background workflows.
11. IAM can research and identify opportunities.
12. IAM can develop and maintain digital products.
13. IAM can manage multiple independent projects.
14. IAM can maintain its digital asset registry.
15. IAM can operate within explicit autonomy and financial permissions.
16. Public visitors cannot access IAM's private operating environment.
17. External content cannot directly override IAM's security policies.
18. Internet failures do not destroy IAM's identity, memory or ongoing work.

**Final requirement:** IAM must be capable of exploring, learning from and interacting with the wider internet, collaborating with other AI systems, operating authorised online services and progressively building its own digital ecosystem while retaining independent identity, memory, authority and security.
