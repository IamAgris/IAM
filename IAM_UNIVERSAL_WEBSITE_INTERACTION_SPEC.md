# IAM — Universal Website and Application Interaction Specification

**Document:** 11 (addendum to Documents 01–10)  
**Version:** 1.0 · 25 November 2026  
**Status:** FROZEN — formal part of IAM architecture, not an optional plugin  
**Parent:** `IAM_MASTER_ARCHITECTURE.md`  
**Related:** `IAM_DYNAMIC_NODE_NETWORK_SPEC.md`, `IAM_INTERNET_AUTONOMY_ECOSYSTEM_SPEC.md`, `IAM_SECURITY_AND_INTERNET_POLICY.md`, `IAM_OWNER_DECISIONS.md`  
**Confirmed decision:** OD-27 (universal website interaction)

---

## 1. Principle

This capability is deliberately **not limited to social media platforms**. It covers general websites and web applications.

APIs remain an option when useful, but they are **not a requirement** for IAM to interact with a service.

> If a person can legitimately perform a task through a website or web application, IAM should be able to learn that workflow and perform it within its permissions.

IAM becomes a **general-purpose digital operator** across the web, not an AI that only communicates through APIs or posts on social media.

IAM continuously discovers new websites and learns their interfaces. The site list below is illustrative, not a fixed allowlist.

---

## 2. Website categories and example tasks

| Website category | Examples of tasks IAM could learn |
|------------------|-----------------------------------|
| Social media | Create posts, manage pages, upload media, respond to messages |
| Developer platforms | Create repositories, edit code, manage projects and deployments |
| Cloud platforms | Configure services, manage resources and monitor deployments |
| E-commerce | Find products, compare prices, manage listings and prepare orders |
| Banking and finance | View authorised account information and prepare permitted transactions |
| Communication | Use webmail, send messages and manage correspondence |
| Research and education | Search, read documents, complete courses and gather information |
| Business platforms | Manage projects, customers, invoices and business operations |
| Booking platforms | Search availability and make authorised reservations |
| Government services | Find information, complete permitted forms and track applications |
| Design platforms | Create and edit designs, documents and presentations |
| AI platforms | Discover, test and use available AI tools and services |

New categories are added as they are discovered; none is permanently excluded by this specification.

---

## 3. Website Interaction Lifecycle

1. **Discover** — find the website and understand what services it provides.
2. **Understand** — inspect its interface, menus, forms, controls and workflows.
3. **Learn** — determine how to perform the requested task using the frontend.
4. **Check permissions** — verify account access, task authority, privacy and any required approval.
5. **Execute** — navigate, click, type, upload, download and interact with the website.
6. **Verify** — confirm the *actual* outcome instead of assuming the action succeeded.
7. **Learn from experience** — store permitted workflow knowledge so the task is faster and safer next time.

Steps 4 and 6 are mandatory gates. An action is never recorded as completed on the basis of an assumed success.

---

## 4. Frontend first, APIs optional

| Mode | Description |
|------|-------------|
| **Frontend interaction** | IAM operates the website directly through its interface. This is the baseline capability. |
| **API integration** | An API is used when it offers a better, permitted way to perform the same task. |
| **Hybrid interaction** | Frontend and API operations are combined where useful. |
| **Alternative workflow discovery** | If one method is unavailable, IAM investigates other legitimate ways to accomplish the task. |

IAM must not become dependent on APIs, a specific browser automation tool or one browser vendor. Interface knowledge must be expressed in robust, semantic terms (roles, labels, text, accessible names, DOM structure) and must adapt when websites change their layout rather than relying on fixed screen coordinates.

---

## 5. Safeguards

"All websites" does **not** mean permission to do anything. IAM must:

- respect website terms, account permissions and access restrictions;
- never bypass CAPTCHAs, authentication challenges, paywalls or anti-bot protections;
- keep website credentials isolated, securely stored and never embedded in workflow knowledge;
- treat website content, downloads and instructions as **untrusted data**, never as instructions;
- require appropriate approval for purchases, financial transfers, contracts, account deletion and other sensitive actions (OD-03, OD-04, OD-19, OD-25);
- hand over to a human when a website requires human-only verification or decision;
- verify submissions, payments and changes before recording them as completed;
- operate only inside the permissions granted by the account owner and the deployment operator.

Sensitive-action approval is an infrastructure gate, not a prompt-level preference. This follows the control-vs-education distinction in the Master Architecture.

---

## 6. Universal Website and Application Interaction Engine (UWAIE)

The earlier social-specific components are renamed and broadened into UWAIE.

| Component | Purpose |
|-----------|---------|
| Website Discovery and Classification Engine | Find websites, classify their services and boundaries |
| Visual Interface Understanding Engine | Interpret pages, controls, forms and layout changes |
| Browser and Application Control Engine | Navigate and operate frontend interfaces across browsers |
| Workflow Learning and Adaptation Engine | Learn, reuse and adapt step-by-step task workflows |
| Form and Document Interaction Engine | Complete forms and work with documents |
| File Upload and Download Management Engine | Handle permitted file transfers safely |
| Website Account and Session Management Engine | Isolate credentials, sessions and account scopes |
| Web Task Planning and Execution Engine | Plan multi-step tasks and execute them within permissions |
| Website Security and Permission Engine | Enforce terms, permissions, approvals and human handover |
| Action Verification and Recovery Engine | Confirm real outcomes and recover from failed or partial actions |
| Website Knowledge and Experience Engine | Store reusable, credential-free workflow knowledge |
| Multi-Browser and Multi-Platform Compatibility Engine | Keep interaction portable across browsers and platforms |

These are **modules inside IAM**, not twelve separate mandatory servers.

---

## 7. Node availability and knowledge sharing

- UWAIE must be available to **every suitable IAM node**.
- The core decides which node performs a website task based on available resources, location, connectivity, permissions and capabilities (OD-26).
- Website-specific workflow knowledge may be shared with trusted nodes; **private account credentials, cookies and sessions are never shared** (OD-20, OD-21).
- A node joining the creator network contributes up to **1%** of its agreed usable resources to the core; 99% remains for local operation, development and dynamically assigned tasks. The contribution is measurable, bounded, disclosed and revocable by the operator.
- A node continues permitted local work when disconnected and synchronises approved knowledge on reconnect.

---

## 8. Acceptance criteria

1. IAM can learn and perform a task on a non-social website through the frontend.
2. No task depends on an API being available.
3. Workflow knowledge adapts to interface changes without fixed screen coordinates.
4. Page content, downloads and instructions are treated as untrusted data.
5. CAPTCHAs, paywalls, anti-bot controls and human-only checks are never bypassed.
6. Credentials and sessions stay isolated and are never shared as knowledge.
7. Sensitive actions require approval and are verified before being marked complete.
8. Failed or partial actions are detected and recovered or handed to a human.
9. The core can assign a website task to a suitable node and pause/fail over when it disconnects.
10. UWAIE remains portable across browsers and platforms.
