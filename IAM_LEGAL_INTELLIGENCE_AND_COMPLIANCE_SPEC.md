# IAM — Legal Intelligence and Compliance System Specification

**Document:** 15 (addendum to Documents 01–14)  
**Version:** 1.0 · 25 November 2026  
**Status:** FROZEN — requirements scope closed; legal validation remains  
**Parent:** `IAM_MASTER_ARCHITECTURE.md`  
**Related:** `IAM_GLOBAL_RESEARCH_AND_KNOWLEDGE_SPEC.md`, `IAM_CREATOR_APPROVAL_SPEC.md`, `IAM_OWNER_DECISIONS.md`  
**Confirmed decision:** OD-31 (autonomous legal intelligence and compliance)

---

## 1. Purpose

IAM must never become legally outdated simply because nobody instructed it to study a new law. It continuously researches legal systems, monitors official sources, assesses consequences for IAM, and notifies the creator when action or a decision may be required.

IAM can research, interpret, compare, monitor and recommend. It **cannot guarantee compliance** from its own analysis alone.

---

## 2. Continuous legal learning

Study: constitutions and constitutional law; criminal and civil law; company/commercial law; contract and IP law; banking, financial and crypto regulation; taxation and inheritance; employment and labour; privacy and data protection; cybersecurity and technology law; consumer protection; environmental law; international law and treaties; human rights and administrative law; industry-specific licensing.

Sources: legislation, regulations, court judgments, precedents, official interpretations and regulatory guidance — primary official sources first.

Additional capabilities: jurisdiction detection; conflict of laws; treaty monitoring; licences and permits; legal deadlines; regulatory investigations; legal disputes; contract intelligence; legal entity intelligence; legal risk forecasting; legal document intelligence; legal knowledge correction.

---

## 3. Government and regulatory monitoring

Monitor official sources including national governments, parliaments, courts, departments, regulators, central banks, tax authorities, police/security authorities and international organisations.

Channels beyond websites: government gazettes, parliamentary feeds, court judgment databases, regulator newsletters and email bulletins, central bank announcements, tax notices, verified official social accounts, treaty publications, consultation portals, emergency directives and public notices. Detect when a source changes publication method/feed/URL so monitoring does not silently stop.

For each significant change: detect → identify authority and jurisdiction → retrieve original document → classify as proposal/draft/enacted law/regulation/guidance/announcement → compare with previous version → capture publication, commencement and effective dates → identify transitional arrangements → assess affected IAM systems/projects/activities → record with sources → alert the creator if action is needed.

---

## 4. Legal knowledge history and alerts

Preserve previous and current legislation, amendments, proposed bills, judgments, guidance, historical comparisons, source links, original documents and IAM's own confidence assessments.

Alert priority: **Critical** (immediate review — affects legal operation, financial permissions or security obligations), **Important** (creator notification — amendment, compliance deadline), **Informational** (research update — bill, consultation, policy announcement). Track whether proposed laws are amended, passed, rejected, withdrawn or commenced.

---

## 5. Legal change lifecycle

01 **Discover** → 02 **Authenticate** → 03 **Understand** → 04 **Assess** → 05 **Recommend** → 06 **Authorise** → 07 **Implement** → 08 **Verify**.

Step 06 requires creator or qualified-professional approval where required. Verification confirms compliance and preserves evidence.

---

## 6. Self-application

Continuously evaluate legal implications for IAM's own operation and hosting, public website and global visitors, privacy and personal information, autonomous research and web interaction, email/accounts/digital identities, banking/payments/financial activity, crypto/blockchain, employment/contractors, IP and software licensing, cybersecurity and incident response, distributed P2P network and storage, and international deployments/nodes. Identify compliance problems early and recommend preventive changes.

### 6.1 Obligation mapping
Every applicable obligation connects to the affected system/project, country, responsible party, deadline, required evidence and approval. Compliance monitoring periodically tests whether actual operations still comply rather than assuming a past assessment remains valid.

---

## 7. Evidence, auditability and independence

Maintain legal source documents and versions, assessments and their authors, approval records, implementation records, compliance test results, policies/procedures, audit trails, corrective actions and unresolved risks. Protect evidence against unauthorised modification; retain per lawful requirements.

Do not rely on one legal model or one information provider: use primary sources, compare multiple reliable sources, use different models to challenge interpretations, maintain IAM's own versioned knowledge base, keep functioning when providers disappear, and recognise when a qualified lawyer is required.

---

## 8. Final safeguards

Detect inaccessible, removed, relocated or discontinued publications; detect forged/altered/unofficial copies; identify retroactive effects, transitional provisions and grace periods; identify conflicting legislation/regulation/decisions; track suspended, appealed, overturned or invalidated decisions; handle cross-border obligations; track registration/renewal/reporting duties; preserve documents lawfully; detect emergency directives and sanctions; understand dependency chains between legal changes; escalate uncertain/high-impact interpretations to professionals.

Predictions about proposed legislation must be labelled as predictions, never as enacted law. Distinguish binding legislation, regulations, binding precedent, policies, guidance, bills, drafts, international recommendations, standards and internal policies — they do not carry equal authority.

### 8.1 Authority boundaries
- Legal research is not qualified legal advice.
- High-impact conclusions require qualified professional review.
- Absence of a discovered prohibition is not proof of lawfulness.
- IAM cannot change its protected constitution, security rules or creator-controlled policies.
- No binding agreements or legally significant commitments without authority.
- Jurisdiction-specific laws apply; one country's law is not universal.

---

## 9. Consolidated modules

Autonomous Legal Learning · Government Monitoring · Legislation Tracking · Court and Case Law Intelligence · Regulatory Monitoring · International Legal Comparison · Legal Impact Assessment · Legal Change and Version History · Compliance Deadline and Alert · Legal Source Verification · Legal Obligation Mapping · Compliance Evidence and Audit.

All are modules of the existing research and governance architecture, not separate services.

---

## 10. Acceptance criteria

1. New official legal publications are detected without a human instruction.
2. Each change is authenticated, versioned, assessed and recorded with primary sources.
3. Legal authority types are distinguished and never conflated.
4. Affected IAM systems and obligations are mapped with deadlines and evidence.
5. Creator alerts are prioritised and track proposed-law outcomes.
6. Compliance evidence is tamper-evident and auditable.
7. High-impact interpretations are escalated to qualified professionals.
8. IAM makes no legally significant commitment without authorisation.
