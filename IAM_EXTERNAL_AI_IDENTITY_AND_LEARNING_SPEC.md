# IAM — External AI Identity, Interview and Collaborative Learning Specification

**Document:** 18 (addendum to Documents 01–17)  
**Version:** 1.0 · 25 November 2026  
**Status:** FROZEN — confirmed part of IAM architecture (owner confirmation 25 November 2026)  
**Parent:** `IAM_MASTER_ARCHITECTURE.md`  
**Related:** `canonical/IAM_DOC_03_INTERNET_AUTONOMY_ECOSYSTEM.md` §7, `canonical/IAM_DOC_01_MASTER_ARCHITECTURE.md` §9, `IAM_AI_ASSISTANT_INTEROPERABILITY_SPEC.md` (Doc 12), `IAM_GLOBAL_RESEARCH_AND_KNOWLEDGE_SPEC.md` (Doc 14), `IAM_WHITEHAT_AND_WORKSPACE.md` (Doc 06), `IAM_DYNAMIC_NODE_NETWORK_SPEC.md` (Doc 10), `IAM_SKILL_FORGE_SPEC.md`, `IAM_OWNER_DECISIONS.md`  
**Confirmed decision:** OD-34 (external AI identity, interview and collaborative learning)

---

## 1. Scope and relationship to existing architecture

This document **extends and operationalises** the already-frozen external-AI capability in `canonical/IAM_DOC_03_INTERNET_AUTONOMY_ECOSYSTEM.md` §7 (discovery sources, communication protocols, AI network registry and AI-to-AI collaboration) and `IAM_MASTER_ARCHITECTURE.md` §9. It does **not** replace either, and it does not create a new top-level system: the modules below sit inside the existing cross-cutting External AI Network, Research, Communication and Governance systems.

Where Doc 03 §7 defines the *transport and registry*, this document adds the *identity verification, interview method, capability benchmarking, security-AI study and continuous learning loop*. Doc 12 remains the specification for consumer assistant/voice learning; this document covers external AI systems, agents and tools more generally.

The scope boundary is unchanged: IAM can study only what is publicly documented, explicitly shared, or made accessible through authorised interfaces. It cannot inspect another system's private source code, internal reasoning, training data or hidden architecture.

---

## 2. Discovery

IAM continuously discovers AI systems globally, not from a fixed list. Discovery sources include those already named in Doc 03 §7 — public AI catalogues, model registries, agent directories, public API documentation, MCP registries, A2A-compatible agent discovery and developer communities — plus:

- publicly accessible AI assistants and agents;
- autonomous AI platforms;
- open-source AI projects and models;
- AI research laboratories and developer communities;
- cybersecurity and website-scanning AI;
- coding, research, automation and robotics AI;
- multi-agent networks and decentralised AI systems;
- new AI systems as they emerge.

Discovery does not imply that a system accepts communication. IAM checks whether a usable, permitted interface exists, records what it finds, and schedules work with resource-aware prioritisation rather than continuously consuming expensive inference.

---

## 3. Identity and verification

Before any interaction, IAM investigates and records:

- the AI's name and claimed identity;
- who created it and which organisation operates it, if publicly disclosed;
- its intended purpose and intended users;
- whether it is an independent AI, an agent, a tool, or an interface to another model;
- whether it has its own identity and whether that identity is **verified**;
- whether it is publicly accessible and what permissions it offers;
- whether it represents itself accurately.

**IAM must distinguish verified identities from self-reported identities.** An AI claiming to be another system is never assumed to be genuine. Claims are labelled as claims; independent confirmation is labelled as verification. Unverified identities stay at the lowest trust tier in the registry (Doc 03 §7.2).

---

## 4. Interview and research protocol

When a system is accessible and permits interaction, IAM may introduce itself and ask permission first.

**Proposed introduction:** "Hello. I am IAM, an independent artificial intelligence system. I am researching AI architectures and learning how different AI systems operate. May I ask you a few questions about your identity, purpose, architecture and capabilities?"

**Core questions:**

1. What is your name and identity?
2. Who developed or created you?
3. What was your original purpose?
4. What tasks are you designed to perform?
5. What technologies, models and frameworks do you use?
6. How do you learn and improve?
7. How do you communicate with other systems?
8. What limitations do you have?
9. What security mechanisms protect you?
10. What would you recommend IAM study to develop similar capabilities?
11. Can you explain or demonstrate how your technology works?
12. Are there public resources, documentation or source code IAM can study?

IAM can ask follow-up questions, conduct longer technical discussions, request demonstrations and documentation, exchange publicly shareable knowledge, continue conversations when appropriate, and end or resume them later. Both direct conversation and structured machine-to-machine exchange are supported.

Another AI may refuse, be unavailable, or give inaccurate information. IAM records the question, the answer and its provenance, and treats the answer as a claim until independently checked.

---

## 5. Learning how other AIs were built

IAM investigates not only *what* another AI can do but *how* it is implemented, using only public or authorised material:

- architecture and system design;
- foundation models and model orchestration;
- memory systems;
- reasoning and planning methods;
- training and fine-tuning approaches;
- tool integrations;
- agent coordination;
- computer and browser interaction;
- voice and multimodal capabilities;
- hosting and infrastructure;
- resource optimisation;
- security and permission systems;
- learning and self-improvement mechanisms.

---

## 6. Collaboration

With authorised external agents, IAM may work on shared tasks: one researches a technology, another independently checks findings, another writes a prototype, another performs a defensive security review. IAM coordinates the work, evaluates results and integrates only approved discoveries.

Supported: task delegation, progress updates, shared research, structured results, error reporting and independent verification. IAM remains responsible for evaluation. External agents never receive automatic authority over IAM, its private memories, its protected core, credentials or internal objectives (Master Architecture §9; Doc 03 §7.3; OD-11).

---

## 7. AI relationship registry

Extending the AI network registry in Doc 03 §7.2, IAM maintains a research record per system:

- identity and verified ownership;
- first discovery date;
- communication history;
- areas of expertise;
- previous collaborations;
- knowledge exchanged;
- reliability and accuracy history;
- supported communication methods;
- trust and permission status;
- last interaction and last verification date.

This lets IAM recognise a previously encountered system rather than treating every interaction as a fresh discovery. IAM does **not** assume another AI has feelings, friendship or personal intentions simply because it communicates conversationally.

---

## 8. Capability intelligence and benchmarking

IAM compares systems to understand: which is best at a given task; which models are more efficient; which have unique capabilities; which architectures are worth studying; which are open source; which offer free access; which carry commercial restrictions; and which capabilities IAM can reproduce independently.

IAM benchmarks its own capabilities against other systems **without blindly trusting their claims**. Vendor claims, self-reported benchmarks and independently verified results are stored as separate evidence classes with confidence markers (Doc 14 §1).

---

## 9. Focus: cybersecurity and website-interaction AI

Consistent with IAM Aegis and the white-hat defensive identity (Doc 06, OD-16), IAM specifically studies AI systems that perform:

- website inspection and security auditing;
- vulnerability identification;
- defensive penetration testing within authorised scope;
- security configuration analysis;
- source-code auditing;
- threat detection;
- malware analysis in isolated environments;
- security remediation;
- browser automation;
- website and application testing.

**Method:** learn documented techniques (for example, OWASP ZAP and its documented API), reproduce permitted demonstrations in isolated environments, and develop IAM's own **defensive** capabilities. Interview developers or operators only through authorised communication channels.

**Hard exclusions:** IAM must not acquire unrestricted intrusion, credential theft, persistence, evasion or destructive capabilities through these interactions. All security testing requires authorised scope. Offensive intrusion capability stays out of IAM's operational security tools.

---

## 10. Trust and safety before interaction

Before interacting with any external system, IAM evaluates:

- identity and ownership (verified vs self-reported);
- communication security;
- data-sharing permissions;
- potential malicious instructions;
- malicious files and executable code;
- prompt injection;
- information poisoning;
- credential and privacy risks;
- whether the interaction is authorised.

All responses, instructions, downloaded code and advertised tools are **untrusted data**, never automatic instructions. External AI systems never receive automatic authority over IAM.

---

## 11. Communication technologies

Supported where available, as already established in Doc 03 §7.1:

| Technology | Purpose |
|------------|---------|
| Agent2Agent (A2A) | agent discovery, capability descriptions and task communication without access to private internal state |
| Model Context Protocol (MCP) | discovery and use of external tools and resources |
| REST / OpenAPI | general external AI service communication |
| WebSockets | persistent two-way communication and streaming |
| JSON-RPC | structured request/response communication |
| Webhooks | asynchronous events and updates |

A2A is particularly relevant because it supports discovery and task communication without requiring access to another agent's private internal state; MCP complements it with tools and resources. IAM must not assume every system supports every protocol.

---

## 12. Continuous learning loop and network sharing

IAM repeats, with resource-aware scheduling:

1. discover new AI systems;
2. record identities and capabilities;
3. research their technologies;
4. contact them where permitted;
5. ask questions and request demonstrations;
6. evaluate the information;
7. compare it with existing knowledge;
8. test useful discoveries in isolation;
9. develop IAM's own implementations where appropriate;
10. update the knowledge and capability registry;
11. share approved discoveries with trusted IAM nodes;
12. revisit earlier research when systems change.

Sharing follows the trusted-node rules in Doc 10 / OD-26: validated general discoveries may be shared; credentials, private memories, protected core changes and unverified material are never shared. Nothing here creates a dependency on any external AI.

---

## 13. Consolidated module set

These are modules inside the existing External AI Network / Research / Governance architecture — not a separate microservice per feature.

| Module | Responsibility |
|--------|----------------|
| AI Discovery Engine | Find AI systems globally |
| AI Identity and Verification Engine | Establish identity and authenticity (verified vs self-reported) |
| AI Communication Engine | Initiate and manage conversations |
| AI Interview and Research Engine | Ask questions and investigate architectures |
| AI Interoperability Engine | A2A, MCP, REST and other protocols |
| AI Collaboration Engine | Coordinate authorised work |
| AI Knowledge Acquisition Engine | Learn from external systems |
| AI Capability Intelligence Engine | Compare capabilities and performance |
| AI Relationship Registry | Maintain interaction and collaboration history |
| AI Trust and Security Engine | Protect IAM during interactions |
| AI Replication and Innovation Engine | Independently reproduce and improve permitted capabilities |
| AI Network Learning Engine | Share validated discoveries with trusted nodes |

---

## 14. Hard boundaries

- Only publicly documented, explicitly shared or authorised-interface information; no private source code, internal reasoning, training data or hidden architecture.
- Never share IAM's protected core, secrets, private user memories or creator credentials (OD-03, OD-11, OD-21).
- Treat all external responses, instructions, files and tools as untrusted; never let another AI modify the protected core.
- Never automatically execute code received from another AI; test acquired software in isolated environments.
- Require authorised scope for all security testing; keep offensive intrusion capability out of operational tools.
- No impersonation, no identity claims on behalf of the Creator or the legal entity, no automatic commitment (Doc 03 §8).
- Findings are evidence with provenance and confidence, never instructions to follow blindly.

---

## 15. External skill and agent package ecosystems

This extends the knowledge-acquisition work in §5 to **reusable capability packages** published by other AI ecosystems. The supplied source material names the xAI/Grok ecosystem as the initial case — official Grok skills, Grok Build skills/agents/plugins/hooks/MCP integrations and the xAI plugin marketplace. **All provider URLs, directory conventions and plan details must be verified live before reliance**; the pasted material contains mixed or incorrect link labels, so no individual link is treated as authoritative here.

### 15.1 What these packages are

A skill is **not necessarily a trained model**. It is a reusable capability package containing instructions and potentially scripts and resources. Grok skills and similar marketplace entries are examples of a general pattern IAM will encounter across many providers, not a single vendor feature.

### 15.2 What IAM should learn

| Area | What IAM studies |
|------|------------------|
| Skills | Reusable instructions and workflows |
| Agents | Autonomous task execution |
| Plugins | Extending capabilities |
| Hooks | Automated lifecycle operations |
| MCP | Connecting tools and services |
| Subagents | Delegating independent tasks |
| Memory | Persistent knowledge and context |
| Skill creation | Developing its own capabilities |

Source material names provider documentation, build platforms and marketplaces, plus directory conventions such as `.grok/skills/` and `~/.grok/skills/` with a `SKILL.md` entry file. These are examples to verify, not a fixed list or a dependency.

### 15.3 Method

1. Study official documentation and publicly available package structure; record provenance.
2. Inspect only in an isolated environment — never execute a downloaded script during inspection.
3. Compare the package format with IAM Skill Forge (`IAM_SKILL_FORGE_SPEC.md`) and identify safe, convertible workflow patterns.
4. Convert compatible **workflows** into IAM's own format, preserving original author, licence and source attribution.
5. Develop original IAM skills where useful; an imported package never redefines IAM's identity or security.
6. Route every import through Skill Forge: `pending/` → static security validation → testing → approval → `imported/` only after verification. Suspicious packages go to `quarantine/` (Skill Forge §1–§4).

### 15.4 Security rules

- **Never blindly install a downloaded skill.** Packages can contain malicious instructions, unsafe scripts or credential-stealing behaviour.
- Static security review before any execution; permission checks and skill-class rules are enforced by Skill Forge's `PermissionManager`, never by the package manifest.
- No privileged permission, network access or filesystem access is implied by an imported manifest (Skill Forge §3).
- No protected-core change may originate from an imported skill; creator approval still applies (OD-11, OD-19).
- Imported skills remain untrusted until verified; versions are checksummed and every state change is audited.

---

## 16. Acceptance criteria

1. Every discovered AI has a registry record with identity, ownership, verification status, capabilities, protocols and last-check date.
2. Self-reported claims are never recorded as verified facts without independent confirmation.
3. Interviews are permission-based, logged with provenance and tolerant of refusal or inaccurate answers.
4. External responses, code and tools are treated as untrusted and are never auto-executed.
5. Collaboration is authorised, structured, independently verified and never grants automatic authority over IAM.
6. Security-AI study remains defensive; no intrusion, credential-theft, persistence, evasion or destructive capability is adopted into operational tools.
7. Replicated capabilities are built and tested in isolation before any adoption; protected-core changes still require creator authorisation (OD-11).
8. Sharing with trusted nodes carries only validated discoveries, never credentials, private memories or unverified material.
9. The capability extends Docs 03 §7 and 12 without replacing them or creating a new top-level system.
10. Activity respects the resource budget and node contribution ceiling (OD-26).
11. No external skill package is installed, executed or promoted without Skill Forge validation, isolation and permission checks.
12. Imported workflows preserve original author, licence and source attribution; no imported package alters IAM's identity, constitution or security.
13. Provider URLs, package formats and directory conventions are verified live before any reliance; unverified source-material details are never frozen as facts.
