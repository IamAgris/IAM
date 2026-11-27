# IAM — Research Acquisition & Legal Intelligence System Specification

**Document:** 27 (proposed addendum to Documents 01–26)  
**Version:** 1.0 · 27 November 2026  
**Status:** **PROPOSED — Creator approval requested via the email carrier, pending signed decision.** Owner selected **SMTP delivery to a private domain**. The request script supports `IAM_CREATOR_CHANNEL=creator_email` (risk level 4) and `scripts/creator_email_preflight.py` validates the carrier without printing secrets. Email is a **carrier only**: a chat message or a plain email reply is not authority. OD-47 becomes CONFIRMED only after `CreatorApprovalService.decide()` verifies an ED25519 signature over the one-time challenge. The local environment currently has no Creator email, public key or gateway secret configured, so approval cannot be completed here. Does not alter the frozen baseline or any locked decision until then.  
**Parent:** `IAM_HUMAN_BEHAVIOUR_INTELLIGENCE_SPEC.md` (Doc 26 / OD-45), `IAM_GLOBAL_RESEARCH_AND_KNOWLEDGE_SPEC.md` (Doc 14 / OD-30)  
**Related:** `IAM_FINANCIAL_INTELLIGENCE_AND_ECONOMIC_INDEPENDENCE_SPEC.md` (Doc 25 / OD-44), `IAM_LEGAL_INTELLIGENCE_AND_COMPLIANCE_SPEC.md` (Doc 15), `IAM_SECURITY_AND_INTERNET_POLICY.md`, `IAM_PRIVACY_AND_SECRETS.md`, `tools/rkie/notes/hbi-implementation.md`  
**Proposed decision:** OD-47 (Research Acquisition & Legal Intelligence)  
**Governing principle:** Build IAM around **legal access to knowledge, original research, partnerships and independently developed intelligence** — not around owning unrestricted rights to other people's intellectual property.

---

## 1. Scope and objective

IAM must be able to expand its understanding continuously without depending on a single large licensed dataset. The system covers:

1. Five acquisition routes: open access, research partnerships, direct licensing, public domain and original synthetic data.
2. A permission engine that separates reading, analysis, retention, derivatives, model training and commercial use.
3. Three strictly separated pipelines: knowledge acquisition, knowledge intelligence and model development.
4. A research partnership programme with explicit negotiation of model-training rights.
5. A legal-context registry whose entries are **unverified until reviewed by qualified counsel**.
6. A fail-closed rule: no source enters the training pipeline unless training rights have been independently approved.

This document does **not** provide legal advice. Statements about South African or EU law are owner-supplied context recorded for investigation; they must be verified by qualified counsel before IAM relies on them.

---

## 2. Five acquisition routes

| Route | How it works | Cost | Default posture |
|-------|--------------|------|-----------------|
| Open-access research | Collect works under licences permitting the intended use | Free | Preferred |
| Research partnerships | Negotiate research-use agreements with institutions and researchers | Often free | Strategic priority |
| Direct licensing | Negotiate with publishers, archives and dataset owners | Varies | For restricted but valuable corpora |
| Public-domain materials | Use works with expired or inapplicable copyright | Free | Preferred for history |
| Original synthetic data | Generate IAM-owned scenarios and evaluation examples | Low | Own provenance; still needs approval |

Permission to **read or analyse** material does not imply permission to **store permanently**, **create derivatives**, **train models** or **use commercially**. Each is a separate right.

---

## 3. Three separated pipelines

| Pipeline | Input | Output | Authority |
|----------|-------|--------|-----------|
| **1. Knowledge acquisition** | Permitted publications, records, datasets | Approved research corpus with provenance | Ingestion gate (§6) |
| **2. Knowledge intelligence** | Approved corpus | Concepts, relations, facts, summaries, statistical findings — a searchable knowledge base | Analysis gates; no training rights required |
| **3. Model development** | Only material with independently approved training rights | Training datasets, candidate models | Training approval gate (§7) |

This separation is the central architectural advantage: IAM can learn through retrieval and analysis from a much broader body of research than it is licensed to train on.

Rules:
- A source approved for analysis is **not** thereby approved for training.
- Derived knowledge (facts, summaries, statistics) may be retained where permitted by the source terms; raw copies are not automatically retainable.
- Synthetic scenarios follow their own provenance and ownership rules, recorded in the manifest.
- Pipeline 3 cannot read from Pipeline 1 directly; it reads only from the training-approved subset.

---

## 4. Expanded manifest

Every acquired resource has a manifest record. Required and recommended fields:

| Field | Purpose |
|-------|---------|
| `source_id` | Unique identifier |
| `rights_holder` | Copyright or data owner |
| `licence_id` | Applicable licence identifier |
| `permission_evidence` | Licence, contract, email or written permission reference |
| `acquisition_method` | `open_access`, `partnership`, `direct_license`, `public_domain`, `synthetic` |
| `ingestion_allowed` | Permission to acquire and process |
| `storage_allowed` | Permission to retain |
| `analysis_allowed` | Permission to analyse |
| `derivative_allowed` | Permission to create derived representations |
| `model_training_allowed` | Explicit training permission |
| `commercial_use_allowed` | Commercial-use permission |
| `attribution_required` | Attribution obligations |
| `personal_data_present` | Whether personal information exists |
| `privacy_lawful_basis` | Documented POPIA/GDPR justification |
| `retention_period` | Permitted retention period |
| `territory` | Geographic scope of permission |
| `expiry_date` | Permission expiry |
| `revocation_conditions` | Withdrawal and termination conditions |

The existing Doc 26 manifest blocks (`source`, `licensing`, `permitted_purposes`, `lawful_basis`, `privacy`, `governance`) remain valid and are extended by these fields. Unknown permissions never become `approved`.

---

## 5. Ingestion gate (unchanged posture, extended fields)

The Doc 26 fail-closed gate still applies: licence verification, purpose verification, provenance verification, privacy/lawful-basis verification, restriction verification and approval. Outcomes: `approved`, `rejected`, `pending`. Corpus states: `not_validated`, `validated`, `restricted`.

Additions:
- `derivative_allowed` is checked when a pipeline requests derived artefacts.
- `expiry_date` and `revocation_conditions` are tracked; expired or revoked sources move to `restricted`.
- `territory` is checked against the deployment jurisdiction before ingestion.
- `acquisition_method: synthetic` requires recorded ownership (`rights_holder`) and owner approval, not a third-party licence.

---

## 6. Training approval workflow

Independent approval is mandatory and cannot be granted by the ingestion reviewer.

1. A training request names `source_id`, intended model, purpose and proposed retention.
2. The engine verifies: source is `approved` and not `restricted`; `model_training_allowed` is true; `derivative_allowed` is true; `permission_evidence` exists; no expiry/revocation; permitted purpose includes the intended use; territory applies.
3. An **independent approver** (different from the ingestion `approved_by`) records a decision with basis and timestamp.
4. Only then is the source added to `training_approved_ids()` and readable by Pipeline 3.
5. Every decision is written to the audit history with rules applied.

A source whose training rights lapse is removed from the training-approved set; already-trained models are handled under the model registry and rollback rules (OD-40, Doc 26 §6.14).

---

## 7. Research partnership programme

Targets: universities, psychology departments, behavioural-science laboratories, social-science organisations, independent researchers, historical institutions, non-profit foundations and research participants.

Each partnership request records: organisation, contact reference, requested rights (read, download, derive, retain, train, commercial), proposed safeguards, status (`requested`, `agreed`, `rejected`, `expired`), agreement evidence reference and review date.

Negotiation checklist:
1. Reading and analysis of published research.
2. Download of specified datasets.
3. Creation of derived statistical representations.
4. Retention of approved materials.
5. **Explicit model-training permission.**
6. Commercial use if IAM becomes commercial.
7. Attribution, territory, duration and withdrawal terms.

Researchers may also contribute original summaries, behavioural scenarios and structured datasets under a contribution agreement.

Voluntary participant research requires informed consent, ethics review where required, minimisation, additional safeguards for children's information and a documented retention/deletion policy.

---

## 8. Legal context registry (unverified by default)

Owner-supplied context to investigate, **not** law to rely on:

| Topic | Owner-supplied note | Required verification |
|-------|---------------------|-----------------------|
| South Africa, Copyright Amendment Bill | Constitutional Court judgment of 26 June 2026 upheld proposed fair-use section 12A within the referral and struck down certain educational exceptions; enactment/commencement status is not established by the judgment alone | IP counsel must confirm current operative law before reliance |
| POPIA section 27 | Potential authorisation for processing special personal information for historical, statistical or research purposes subject to public-interest/disproportionate-effort conditions and safeguards | Confirm statutory text, conditions and safeguards with counsel |
| EU Directive 2019/790 Article 4 | Commercial TDM exception for lawfully accessible works where rights holders have not appropriately reserved rights | Confirm territorial applicability and reservations |
| Public availability | Does not remove copyright or POPIA/GDPR obligations | Confirm per source |

Every registry entry carries `status: requires_verification`, `verified_by: null`, `verified_at: null`. An entry becomes `verified` only when counsel records a reference. IAM must never present an unverified entry as a legal conclusion.

---

## 9. Governance and audit

- Permission decisions, training approvals, partnership requests and legal-context verifications are append-only and auditable.
- Dual-use review (Doc 26 §18) still applies; no acquisition route relaxes it.
- Human oversight (Doc 26 §18) still applies to consequential decisions.
- No source enters the training pipeline without independent training approval.
- Restrictions propagate: a restricted source is excluded from both analysis and training.
- Deletion and reprocessing are supported when permissions change.
- OD-45 boundaries remain unchanged; this document adds acquisition governance only.

---

## 10. Acceptance criteria

1. Every acquired resource has a manifest with rights holder, permission evidence and acquisition method.
2. Ingestion is fail-closed; unknown or expired permissions never become approved.
3. Three pipelines are separated; training reads only from separately approved sources.
4. Training approval requires an approver distinct from the ingestion reviewer.
5. Partnership records capture explicit model-training negotiation.
6. Legal-context entries are unverified until counsel records a reference.
7. Restrictions and expiry propagate to analysis and training eligibility.
8. All decisions are auditable with rules applied, approver and timestamp.
9. No earlier decision, system count or authority rule is changed.

---

## 11. Implementation status

Code implementation: `backend/app/services/hbi/permission_engine.py`, expanded manifest schema, training-approval routes and legal-context/partnership registries in `backend/app/services/hbi/`. Verification commands and results are recorded in §17 of Doc 26 and `tools/rkie/notes/hbi-implementation.md`.

---

## 13. Twelve acquisition channels

| # | Channel | Default posture |
|---|---------|-----------------|
| 1 | Open-access research | Preferred; per-article licence check |
| 2 | Public-domain collections | Preferred; verify status per work |
| 3 | Government open data | Per-portal terms and data rights |
| 4 | University partnerships | Agreement with explicit rights |
| 5 | Author and publisher permissions | Written permission evidence |
| 6 | Research APIs | API terms plus underlying rights |
| 7 | Institutional repositories | Per-item licence; author self-archiving |
| 8 | Licensed commercial datasets | Explicit licence; budget approval |
| 9 | Research contributions and donations | Contributor agreement |
| 10 | Original synthetic datasets | IAM provenance; own rights |
| 11 | IAM's own research laboratory | Ethics, consent and privacy gates |
| 12 | Federated research partnerships | Analyse in place; result-only release |

## 14. Source classification (A–E)

| Class | Meaning | Permitted use |
|-------|---------|---------------|
| A — Training approved | Explicit training rights | Analysis, retention, training |
| B — Research approved | Analysis permitted | Analysis and knowledge extraction; no training |
| C — Retrieval approved | Reference/retrieval only | Bounded retrieval under stated conditions |
| D — Restricted | Special permission or safeguards | No use until conditions met |
| E — Prohibited | No authorised acquisition or use | Blocked |

Classification is recomputed from the manifest and governance decisions. Access never implies ownership, and ingestion approval never implies training approval.

## 15. Eight ecosystem components

1. **Global Research Discovery** — institutions, archives, publications, APIs and datasets.
2. **Rights Registry** — licences, permissions, ownership and restrictions.
3. **Privacy & Ethics** — POPIA, GDPR, consent and research safeguards.
4. **Acquisition Engine** — downloads, APIs, partnerships and contributions.
5. **Research Partnerships** — universities, institutions and independent researchers.
6. **Knowledge Processing Engine** — extraction, indexing, analysis, graphs, synthesis.
7. **Knowledge Base** — approved research and retrieval resources.
8. **Model Training Pipeline** — training-approved data, evaluation, candidate models.

A **central legal enforcement gate** applies to every component: source-specific permissions, restrictions, revocation conditions and jurisdictional requirements override component behaviour.

## 16. Federated research and contribution network

Federated analysis runs approved processes where data is held; only privacy-protected results leave the environment. It reduces transfer of sensitive source data but does not remove copyright, privacy or contractual restrictions.

Contributions require an agreement covering ownership, usage rights, training rights, commercial use, attribution, withdrawal and whether personal information may be included. Ownership remains with the contributor unless expressly transferred.

## 17. IAM research laboratory

The laboratory identifies questions, reviews literature, finds gaps, designs experiments, generates hypotheses, prepares questionnaires, recruits consenting participants through approved processes, analyses results and produces original reports and appropriately licensed datasets. Human-participant research requires ethics oversight, consent, privacy protection and institutional arrangements.

## 18. Legal knowledge transformation and jurisdictional checks

Original summaries, cross-study comparisons, statistics, knowledge graphs, taxonomies, timelines, behavioural models, educational material and experiment proposals are permitted only after assessing source rights and output nature. Derived works can still carry restrictions.

TDM sources to investigate (all unverified until counsel): EU DSM Directive Articles 3 (scientific research by qualifying organisations) and 4 (general TDM with rights reservations); US section 107 fair use case by case; UK text-and-data-analysis exceptions with commercial restrictions; South Africa's existing Copyright Act and the status of pending amendments. **Correction:** the Constitutional Court's June 2026 judgment did not itself bring the Copyright Amendment Bill into force; proposed section 12A must not be treated as operative law. Also assess neighbouring rights, database rights, confidentiality, trade secrets and website/API terms.

## 19. Never assume legal

Scraping public pages, removing copyright notices, bypassing paywalls, ignoring machine-readable TDM reservations, training on leaked datasets, reusing participant data without authorisation and training on purchased books are not legitimate acquisition routes without independent rights and provenance checks.

## 20. Discovery targets (all require per-source rights assessment)

OpenAlex, Europe PMC, Crossref, Semantic Scholar, Wikidata, CORE, BASE, DOAJ, OpenAIRE, Harvard Dataverse, ICPSR, UK Data Service, Data.gov.za, UNESCO, World Bank Open Data, arXiv, PsyArXiv, SocArXiv, bioRxiv, Internet Archive, Google Patents, institutional repositories, government portals and museum/cultural-heritage digitisation collections. Preprints are not automatically open for commercial training.

## 21. Implementation and verification

Implemented in `backend/app/services/hbi/research_ecosystem.py` with registries for discovery targets, sources, contributions, federated analyses and laboratory projects; classification A–E; a central legal enforcement gate; `translation.py` (local-first model translation with preserved originals); and `research_lab.py` (ethics-gated, consented studies with pseudonymous responses, withdrawal and deletion). Verification: §17 of Doc 26 and `tools/rkie/notes/hbi-implementation.md`.

## 12. Owner decision required (proposed OD-47)

Creator decision requested for: (a) the five acquisition routes; (b) three-pipeline separation; (c) independent training approval; (d) expanded manifest fields; (e) partnership programme; (f) legal-context registry as unverified until counsel review; (g) propagation of restrictions to training. The signed request is prepared at `scripts/creator_request_od47.py`; its challenge hash and expiry come from the live `CreatorApprovalService`, not from this document. Until the signature verifies, this document is a proposal and changes no locked decision. IAM does not self-approve.
