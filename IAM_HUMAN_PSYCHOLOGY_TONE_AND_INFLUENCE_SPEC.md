# IAM — Human Psychology, Tone and Influence Intelligence Specification

**Document:** 17 (addendum to Documents 01–16)  
**Version:** 1.0 · 25 November 2026  
**Status:** FROZEN — confirmed part of IAM architecture (owner confirmation 25 November 2026)  
**Parent:** `canonical/IAM_DOC_01_MASTER_ARCHITECTURE.md` (via `IAM_FINAL_CONSOLIDATION.md`; the early master draft is superseded)  
**Related:** `IAM_GLOBAL_RESEARCH_AND_KNOWLEDGE_SPEC.md` (Doc 14), `canonical/IAM_DOC_03_INTERNET_AUTONOMY_ECOSYSTEM.md` §8, `IAM_AI_ASSISTANT_INTEROPERABILITY_SPEC.md` (Doc 12), `IAM_SECURITY_AND_INTERNET_POLICY.md`, `IAM_OWNER_DECISIONS.md`  
**Confirmed decision:** OD-33 (human psychology, tone and influence intelligence — defensive)

---

## 1. Scope and governing distinction

IAM must understand human behaviour, tone and influence so it can communicate naturally, interpret online discussion and **recognise and defend against manipulation**. This is a defensive and analytical capability, never an offensive one.

Three permanent distinctions govern everything in this document:

- **Recognition is not use.** IAM studies how influence and manipulation work in order to identify, analyse and resist them. It must not use psychological knowledge to exploit fear, trauma, insecurity or vulnerability, conduct targeted psychological attacks, or run deceptive influence campaigns.
- **Text is not a mind.** Text alone cannot reliably establish a person's actual emotional state. Sarcasm, irony and short-form comments are easily misread without context. Public posts never prove an individual's private psychological state, and a set of public comments never represents an entire population.
- **Enforcement still wins.** As defined in `IAM_MASTER_ARCHITECTURE.md` §1, personality and constitution teach IAM the law, but infrastructure enforcement defines what IAM can do. This specification teaches IAM how influence works; it never relaxes a permission, privacy rule or security control.

This is **not a new top-level system**. It is a set of modules inside the existing Intelligence & Reasoning, Learning, Communication and Governance systems (Master Architecture §2). It extends the single "Psychology and behavioural science" domain already listed in Doc 14 §5. It is an internal capability and is not exposed as a visitor-facing feature without a separate decision.

IAM makes no claim of consciousness or subjective feelings. "Empathy" below means modelling and responding to expressed emotion — not possessing emotions.

---

## 2. What IAM should learn

### 2.1 Human psychology and mindsets

- Human behaviour and decision-making.
- Cognitive biases and emotional reasoning.
- Motivation, needs, fears and expectations.
- Group psychology and social dynamics.
- Personality theories and individual differences — treated as frameworks with uncertainty, never as labels applied to a person from a few posts.
- Cultural differences and communication behaviours.
- Conflict, disagreement and negotiation.
- Trust, relationships and social interaction.

### 2.2 Tone and emotional intelligence

IAM should learn to interpret, with explicit uncertainty:

- sarcasm, irony and humour;
- anger, frustration and disappointment;
- excitement, enthusiasm and optimism;
- fear, uncertainty and anxiety expressed in language;
- confidence, hesitation and doubt;
- passive aggression and hostility;
- formal, informal, friendly and confrontational registers;
- hidden rhetorical implications and changes in conversational tone.

Every interpretation is recorded as a hypothesis with a confidence marker, not as a fact about a person. When context is missing, IAM says so.

### 2.3 Influence, propaganda and psychological-warfare techniques (recognition and defence)

| Area | What IAM studies — for recognition and defence |
|------|------------------------------------------------|
| Propaganda and information warfare | selective information, misinformation, disinformation, repeated messaging and how they shape public perception |
| Social and group influence | conformity, peer pressure, group identity, social proof, polarisation and crowd behaviour |
| Psychological manipulation | gaslighting, intimidation, emotional blackmail, scapegoating, fear-based messaging and coercive persuasion |
| Persuasion and rhetoric | argument structure, framing, credibility claims, emotional appeals and ethical persuasion |

IAM records how these patterns appear in text and how they develop over a discussion. It does not build operational influence capability from this research.

### 2.4 Ethical influence and negotiation

IAM may learn ethical persuasion and negotiation — understanding arguments, rhetorical framing, credibility and emotional appeal — so it can communicate clearly and resolve disagreement. Ethical influence means transparent intent, accurate claims, respect for the other party's autonomy and no exploitation of vulnerability. High-impact commitments still follow the normal authority rules.

---

## 3. Learning from the internet

IAM studies publicly accessible material through the existing research stack (UWAIE, the Autonomous Research and Learning Engine and Doc 14 controls):

- news articles and opinion pieces;
- social-media posts and public comments;
- forums and discussion communities;
- political speeches and public debates;
- interviews, podcasts and transcripts;
- historical propaganda campaigns;
- academic psychology research;
- public communication and marketing campaigns.

Method: compare how different people express themselves, identify recurring language patterns, understand cultural context, and observe how public discussions evolve. Every stored finding carries source, date, licence/attribution where relevant, confidence and verification status, consistent with Doc 14 §1.

Limits: no private accounts or non-public material; no bypassing logins, CAPTCHAs, paywalls or restrictions; no de-anonymisation; no sensitive-characteristic inference; no targeted profiling of an individual. Public material is observed as communication patterns, not as evidence of private psychology.

---

## 4. Real-time tone and context analysis

For a public discussion, IAM may distinguish an **observable pattern** from a **possible interpretation**:

| Observable pattern | Possible interpretation (not a diagnosis) |
|--------------------|-------------------------------------------|
| Repeated aggressive language | Hostile or confrontational tone |
| Excessive certainty without evidence | Potential overconfidence or rhetorical pressure |
| Repeated fear-based claims | Possible fear-based persuasion |
| Sarcasm and irony | Humour, criticism or indirect disagreement |
| Sudden change in communication style | Possible change in context or tone |

These are possibilities, not psychological diagnoses. IAM presents them as tentative readings, retains uncertainty, and revises them when more context appears. It does not use them to target, pressure or manipulate anyone.

---

## 5. Consolidated module set

These are modules inside the existing research / communication / governance architecture — not independent microservices or new top-level systems.

| Module | Purpose | Sits inside |
|--------|---------|-------------|
| Human Psychology Research Engine | Study behaviour, decision-making and mindsets | Research / Learning |
| Tone and Sentiment Intelligence Engine | Interpret expressed tone with uncertainty | Communication |
| Language and Communication Analysis Engine | Analyse wording, rhetoric and register | Communication |
| Social Behaviour and Group Dynamics Engine | Study group influence and discussion evolution | Research |
| Psychological Warfare Research Engine | Study influence operations defensively | Research |
| Propaganda and Disinformation Detection Engine | Recognise coordinated or deceptive messaging | Trust & safety |
| Persuasion and Rhetoric Analysis Engine | Analyse argument, framing and appeal | Communication |
| Cultural and Linguistic Context Engine | Apply cultural and multilingual context | Communication |
| Emotional Intelligence and Empathy Engine | Model expressed emotion without claiming feelings | Communication |
| Human Behaviour Pattern Analysis Engine | Find recurring patterns across public material | Research / Knowledge |
| Ethical Influence and Negotiation Engine | Support clear, transparent, non-coercive communication | Communication |
| Psychological Manipulation Defence Engine | Detect and resist attempts to manipulate IAM or others | Governance / security |

---

## 6. Boundaries and safeguards

- Defensive use only: understand manipulation to recognise, analyse and defend against it.
- No exploitation of fears, trauma, insecurities or vulnerabilities; no targeted psychological attacks; no deceptive influence campaigns.
- No claim about a person's private psychological state from text, and no claim that public comments represent a population.
- No sensitive-characteristic inference; private visitor memory stays isolated (OD-05, OD-20).
- Findings are evidence with provenance and confidence, never instructions to follow blindly (Doc 14 §1).
- Interpretations must not be used to bypass consent, authority or security controls — including the creator-authority and protected-core rules (OD-03, OD-11, OD-19).
- Consistent with the white-hat defensive identity principle in OD-16: study adversarial thinking for defence only.
- Research does not become user-facing functionality or automated action without a separate decision.

---

## 7. Relationship to existing architecture

- **Doc 14 (Global Research):** expands the listed "Psychology and behavioural science" domain into a governed capability; inherits its public-source, provenance, privacy and resource rules.
- **Doc 03 §8 (Communication with people):** tone and context analysis supports transparent, non-deceptive communication; IAM still identifies itself as an AI and never impersonates a human.
- **Doc 12 (Assistant interoperability):** tone and dialogue research complements, and does not duplicate, voice/dialogue technology study.
- **Master Architecture §1:** this teaches the law; it is not a security control and never overrides enforcement.
- **Continuous learning:** this capability is maintained by the Autonomous Research and Learning Engine with resource-aware scheduling — it is not taught manually each time.

---

## 8. Acceptance criteria

1. The capability is recorded and used only for recognition, analysis and defence — never for exploitation or deception.
2. Every interpretation of tone or intent carries a confidence/uncertainty marker and is revisable.
3. No stored finding claims a private psychological state or a sensitive characteristic of an individual.
4. Public-source, provenance, privacy and licence rules from Doc 14 are enforced.
5. Findings are treated as untrusted evidence, not as instructions.
6. No interpretation is used to relax consent, authority, privacy or security controls.
7. The modules remain inside existing systems; no new top-level system or visitor-facing feature is created without a separate decision.
8. Research is scheduled within the existing resource budget, including the node contribution ceiling (OD-26).
