# IAM Architecture — Document Index (AUTHORITATIVE)

**Version:** 1.0 · 25 November 2026  
**Purpose:** Resolve duplicate/superseded documents. This is the single entry point to the frozen IAM architecture.

---

## Source of truth

| Priority | Document | Status |
|----------|----------|--------|
| **1** | `IAM_FINAL_CONSOLIDATION.md` | **AUTHORITATIVE** — master gap analysis, all systems, completion levels, roadmap |
| **1** | `IAM_OWNER_DECISIONS.md` | **AUTHORITATIVE** — 32 locked decisions |
| 2 | `canonical/IAM_DOC_01…04` | Frozen supplied documents 01–04 |
| 2 | `IAM_DISTRIBUTED_ARCHITECTURE.md` | Document 05 |
| 2 | `IAM_WHITEHAT_AND_WORKSPACE.md` | Document 06 |
| 2 | `IAM_COMMUNICATION_ARCHITECTURE.md` | Document 07 |
| 2 | `IAM_HARDWARE_ADAPTATION.md` | Document 08 |
| 2 | `IAM_BLOCKCHAIN_AND_BANKING.md` | Document 09 |
| 2 | `IAM_DYNAMIC_NODE_NETWORK_SPEC.md` | Document 10 (dynamic nodes, OD-26) |
| 2 | `IAM_UNIVERSAL_WEBSITE_INTERACTION_SPEC.md` | Document 11 (frontend-first interaction with any website, OD-27) |
| 2 | `IAM_AI_ASSISTANT_INTEROPERABILITY_SPEC.md` | Document 12 (internal assistant/voice technology learning, OD-28) |
| 2 | `IAM_DEVELOPER_SDK_AND_CLI_SPEC.md` | Document 13 (official SDK/CLI + protocol, OD-29) |
| 2 | `IAM_GLOBAL_RESEARCH_AND_KNOWLEDGE_SPEC.md` | Document 14 (global research scope frozen, OD-30) |
| 2 | `IAM_LEGAL_INTELLIGENCE_AND_COMPLIANCE_SPEC.md` | Document 15 (legal/government monitoring, OD-31) |
| 2 | `IAM_GEOSPATIAL_INTELLIGENCE_AND_LIVE_MAPPING_SPEC.md` | Document 16 (maps/geospatial, OD-32) |
| 2 | `IAM_HUMAN_PSYCHOLOGY_TONE_AND_INFLUENCE_SPEC.md` | Document 17 (human psychology, tone and influence intelligence — defensive; OD-33) |
| 2 | `IAM_EXTERNAL_AI_IDENTITY_AND_LEARNING_SPEC.md` | Document 18 (external AI identity, interview, collaborative learning and external skill packages — extends Doc 03 §7; OD-34) |
| 2 | `IAM_FREE_INFRASTRUCTURE_NODE_DISCOVERY_AND_LIFECYCLE_SPEC.md` | Document 19 (free cloud/platform nodes — extends OEDIE and Doc 10; OD-35) |
| 2 | `IAM_AI_SDK_AND_FRAMEWORK_RESEARCH_SPEC.md` | Document 20 (AI SDK/framework/model research + Technology Capability Registry; OD-36) |
| 2 | `IAM_INFRASTRUCTURE_TRAFFIC_AND_DISTRIBUTED_PROCESSING_SPEC.md` | Document 21 (traffic, queues and distributed processing — extends system 13 / Doc 10; OD-37) |
| 3 | `sdk/` | SDK scaffolds: TypeScript, Python, CLI, shared protocol |
| 2 | `IAM_OPEN_SPECS_RESOLVED.md` | Resolved specs A–G |
| 2 | `IAM_DATABASE_DESIGN.md`, `IAM_API_CONTRACTS.md`, `IAM_SECURITY_AND_INTERNET_POLICY.md` | Technical specifications |

**Note:** Documents 17–21 and OD-33/OD-37 are **CONFIRMED** and part of the frozen baseline (owner confirmation 25 November 2026). They extend existing systems and do not alter any prior decision, including OD-08 (ARQ queue runtime).

## Superseded documents (historical — do not use as source of truth)

These were early derived drafts. They are retained for history but **superseded** by the documents above:

- `MASTER_SPECIFICATION.md` → superseded by `IAM_FINAL_CONSOLIDATION.md` + `IAM_MASTER_ARCHITECTURE.md`
- `IAM_MASTER_ARCHITECTURE.md` → superseded by `canonical/IAM_DOC_01` + `IAM_FINAL_CONSOLIDATION.md`
- `IAM_INTELLIGENCE_EVOLUTION_SPEC.md` → superseded by `canonical/IAM_DOC_02`
- `IAM_INTERNET_AUTONOMY_ECOSYSTEM_SPEC.md` → superseded by `canonical/IAM_DOC_03`
- `IAM_UI_GLOBAL_ACCESS_SPEC.md` → superseded by `canonical/IAM_DOC_04`
- `IAM_ARCHITECTURE_GAP_ANALYSIS.md`, `IAM_DISTRIBUTED_GAP_ANALYSIS.md` → superseded by `IAM_FINAL_CONSOLIDATION.md`

## Naming note

"AURA" is the engineering codename only. The system's permanent identity is **IAM — Intellectual Artificial Mainbrain**. "Marlow" refers only to the supplied HTML file name; the visual interface is IAM's.
