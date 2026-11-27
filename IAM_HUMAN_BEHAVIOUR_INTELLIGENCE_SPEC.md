# IAM — Human Behaviour Intelligence (HBI) Master Specification

**Document:** 26 — **Master Specification** (proposed addendum to Documents 01–25)  
**Version:** 2.0 · 26 November 2026  
**Status:** **FROZEN — CONFIRMED** part of the IAM architecture under **OD-45** (owner confirmation 26 November 2026). Phase 0 gate (§13) completed before implementation. Supersedes its own v1.0 draft; does not alter any earlier decision.  
**Supersedes:** the v1.0 draft of this same document (all content absorbed here).  
**Parent:** `IAM_MASTER_ARCHITECTURE.md`, `IAM_FINAL_CONSOLIDATION.md`  
**Related:** Doc 14 (`IAM_GLOBAL_RESEARCH_AND_KNOWLEDGE_SPEC.md`), Doc 17 (`IAM_HUMAN_PSYCHOLOGY_TONE_AND_INFLUENCE_SPEC.md`), Doc 24 (`IAM_HUMAN_BEHAVIOUR_EQUALITY_AND_RESPONSIBILITY_SPEC.md`), Doc 23 (OD-38), `IAM_MODEL_EVOLUTION_AND_FINE_TUNING_SPEC.md` (OD-40), `IAM_INDEPENDENT_AI_RESEARCH_DEVELOPMENT_AND_EVOLUTION_ARCHITECTURE.md` (OD-41), `IAM_SECURITY_AND_INTERNET_POLICY.md`, `IAM_PRIVACY_AND_SECRETS.md`, `IAM_API_CONTRACTS.md`, `IAM_OWNER_DECISIONS.md`  
**Confirmed decision:** OD-45 (HBI as a permanent, governed intelligence domain — confirmed 26 November 2026)  
**Scope:** Individual psychology and behaviour; cognition, motivation and decisions; communication and relationships; collective, cultural and societal behaviour; historical human behaviour, evolution and civilisations; prediction, scientific learning and psychological protection.  
**Final module count:** **38 intelligence modules** (original 23 retained with unchanged IDs, plus 15 added) and **13 supporting technical engines** (the 12 requested engines plus the Historical Chronology Engine). Modules and engines are distinct by design: modules produce understanding, analysis and predictions; engines provide shared platform services.

---

## 0. Executive summary and design thesis

HBI is IAM's permanent, scientifically grounded capability for **understanding** human behaviour, **analysing** particular situations, and **anticipating plausible outcomes** across individual, group, societal, cultural and historical scales. One sentence governs it:

> **Understand humanity, do not control humanity. Predict possibilities, never claim certainty. Learn independently, but never outside governance.**

This master specification is deliberately complete before coding begins. It defines:

- **38 modules** in **six divisions**;
- **13 technical engines** that make the intelligence verifiable, temporal, multilingual, causal, simulated, benchmarked and self-correcting;
- **eight advanced capabilities** for independent scientific development;
- a **full data and knowledge model**, including historical event/timeline schemas and a historical knowledge graph;
- **14 implementation specifications** covering schemas, ingestion, licensing, training, APIs, communication, memory, local models, resources, security, privacy, testing and versioning;
- a scientific foundation, prediction methods, evaluation framework, ethical safeguards, roadmap and acceptance gates.

The central structural commitment remains the **three-layer separation**:

| Layer | Question | Permitted output |
|-------|----------|------------------|
| **Understanding** | What does science establish about human behaviour in general? | Traceable, evidence-graded knowledge claims |
| **Analysis** | What might explain *this* situation? | Revisable interpretations and hypotheses with confidence |
| **Prediction** | What could happen next, and how likely is each outcome? | Calibrated probability distributions with uncertainty and alternatives |

Confusing these layers is the primary failure mode of behavioural AI: a theory becomes a label, a label becomes a "fact" about a person, and a "fact" becomes a decision. The architecture makes that confusion structurally difficult.

HBI is implemented **inside the existing 15 systems** (principally 2, 3, 5, 6, 12, 13, 14). It does **not** create a sixteenth top-level system, a new AI identity, or a visitor-facing feature without a further decision.

---

## 1. Scope, status and governing principles

### 1.1 What this adds — and what it does not

- **Adds:** 38 modules, 13 engines, eight advanced capabilities, a persistent historical memory and a complete implementation contract set.
- **Extends:** Docs 14, 17 and 24; inherits their public-source, provenance, privacy and defensive-use rules.
- **Does not:** alter identity (OD-01), signing (OD-03), financial authority (OD-04/OD-25), protected-core rules (OD-11), Creator channels (OD-18/19/42), foundation-model set (OD-38), resource control (OD-39), model-development rules (OD-40) or frozen research scope (OD-41).
- **Does not:** create automated decisions about people, secret psychological profiles, or an operational influence capability.

### 1.2 Permanent governing distinctions

1. **Recognition is not use.** Manipulation, coercion and propaganda are studied to identify, analyse and defend against them — never to exploit vulnerability or conduct influence operations.
2. **Text is not a mind; a group is not a person.** Expressed language yields tentative interpretations, not private psychological facts. Aggregate patterns never license claims about an identifiable individual.
3. **Enforcement still wins.** Governance is an independent plane; no analytical module can relax a permission, privacy rule, consent requirement or security control.
4. **Capability is not worth.** From Doc 24: *"The ability to do something better than another does not make an individual more important than another."*
5. **No consciousness claim.** "Empathy" means modelling and responding to expressed emotion.
6. **Possibility, not destiny.** Every forecast is a distribution over alternatives conditioned on stated evidence and assumptions.
7. **Theory pluralism.** No single school explains behaviour; competing explanations are preserved until evidence discriminates.
8. **History is context, not fate.** Historical precedent informs scenarios; it never guarantees repetition.
9. **Independent learning is bounded learning.** Self-directed research, hypothesis generation and knowledge evolution operate only inside purpose, provenance, privacy and approval gates.

### 1.3 Two population scopes

| Scope | Subject | Data | Default |
|-------|---------|------|---------|
| **Aggregate** | Groups, communities, societies, cohorts, historical populations | Anonymised, aggregated, licensed, public or consented research data | **Permitted** under governance |
| **Individual** | A specific living person | Consented, task-scoped, first-party interaction data only | **Restricted** — explicit purpose, minimisation, human oversight, no sensitive-trait inference |

### 1.4 Core philosophy

Understand rather than control; support autonomy; separate probability from confidence; keep every claim revisable; adopt methods for measured benefit on legitimate outcomes, not for sophistication.

---

## 2. Scientific foundations (advanced)

Every theory record follows: **claim → canonical anchors → mechanism → domain of applicability → known failures → evidence grade → IAM use → IAM prohibition.** Findings are graded by replication status, effect size, sample quality, population coverage, method strength and recency — not by fame.

### 2.1 Neuroscience and predictive processing
Predictive processing/free energy (Friston); predictive coding and precision-weighted attention; interoception and allostasis (Barrett); reward-prediction error and RL (Schultz; Sutton & Barto); memory as reconstruction (Baddeley, Loftus); drift-diffusion models of evidence accumulation. **Guard:** no reverse inference from neural correlates to complex social explanation.

### 2.2 Cognitive psychology
Dual-process theories (Evans; Kahneman) as heuristics, not literal systems; bounded rationality and satisficing (Simon); heuristics and biases (Tversky & Kahneman); prospect theory — reference dependence, loss aversion, diminishing sensitivity, probability weighting; motivated and directional reasoning (Kunda); reconstructive memory. **Guard:** several classic priming/ego-depletion findings failed replication — grade accordingly.

### 2.3 Behavioural economics and decision theory
Expected utility vs prospect theory; hyperbolic discounting and commitment devices (Laibson); mental accounting, endowment effect, status quo/default/framing effects; nudge theory studied **defensively** (dark-pattern recognition); social preferences — fairness, reciprocity, trust, public goods; information cascades and herd behaviour; mechanism and auction design.

### 2.4 Affective science
Russell's valence–arousal circumplex and PAD; appraisal theories (Lazarus, Scherer); constructionist accounts (Barrett); emotion regulation (Gross); broaden-and-build (Fredrickson); affective forecasting and impact bias (Wilson & Gilbert). **Guard:** emotion recognition from text/voice/face is culturally fragile and legally restricted — weak, contestable signal only.

### 2.5 Personality and individual differences
Big Five (Goldberg, Digman) and HEXACO (Ashton); person–situation interaction (`B = f(P, E)`; Mischel); rank-order stability with real change; temperament; self-concept and identity (Erikson); measurement biases and ecological fallacy. **Guard:** no trait inference from a few posts; no trait labels on identifiable people.

### 2.6 Social psychology and network science
Conformity (Asch), obedience (Milgram), normative/informational influence (Deutsch & Gerard), social proof, pluralistic ignorance; Social Identity and self-categorisation (Tajfel & Turner); groupthink (Janis), polarisation (Moscovici & Zavalloni); network models — small-world (Watts & Strogatz), scale-free (Barabási & Albert), homophily, centrality, community detection, complex contagion and thresholds (Granovetter, Watts, Centola); emergent norms in crowds.

### 2.7 Cultural anthropology and cross-cultural psychology
Hofstede, Schwartz values, Inglehart–Welzel — useful heuristics with ecological-fallacy and measurement-invariance critiques; emic/etic perspectives, thick description (Geertz); enculturation, ritual and cultural change; WEIRD-sample bias (Henrich, Heine & Norenzayan). **Guard:** never apply culture-level averages to a person.

### 2.8 Developmental, life-span and evolutionary foundations
Piaget, Vygotsky, Erikson, Kohlberg (with critique), Baltes' selection–optimisation–compensation; attachment (Bowlby, Ainsworth); behavioural genetics — heritability as a *population* statistic, G×E (Caspi & Moffitt), gene–environment correlation; **human evolution and palaeoanthropology** — hominin behavioural evolution, tools, fire, language, sociality, migration out of Africa, admixture, archaeological inference limits. **Guard:** no essentialism or hierarchy claims from genetics or prehistory.

### 2.9 Communication science and linguistics
Speech acts (Austin, Searle), Gricean maxims, implicature, politeness (Brown & Levinson); rhetoric — ethos/pathos/logos, framing (Entman), narrative transportation; conversation analysis, register and code-switching; computer-mediated communication and online disinhibition; Shannon information theory. **Guard:** deception cues are weak — detect deceptive *construction patterns*, never "read minds".

### 2.10 Organisational, political, criminological and conflict studies
Self-determination theory, expectancy theory, goal-setting, psychological safety (Edmondson); authoritarianism and social dominance orientation, motivated reasoning, affective polarisation; routine activity, strain and social disorganisation criminology (social science only — never individual dangerousness prediction); negotiation and integrative bargaining (Walton & McKersie), contact hypothesis (Allport), transitional justice.

### 2.11 Systems and complexity science
Feedback loops, emergence, nonlinearity, path dependence, tipping points, self-organisation, resilience; system dynamics (Forrester); agent-based and generative social science (Epstein, Holland); network resilience and cascading failure.

### 2.12 Historiography and historical social science
Source criticism (external/internal, provenance, audience, purpose); primary vs secondary; Annales/longue durée (Braudel), microhistory, history from below, subaltern and post-colonial perspectives (Guha, Said), oral history; process tracing (Checkel); counterfactuals (Fearon, Tetlock); analogy (Jervis); cliodynamics and macro-history (Turchin, Goldstone) as contested programmes; archaeology vs written record.

### 2.13 Cross-cutting domains added by the expanded scope
Geopolitics/international relations (realism, liberalism, constructivism, institutionalism); economic sociology and behavioural finance; disaster and crisis research (preparedness, response, recovery, collective behaviour in disasters); leadership studies (trait, behavioural, contingency, transformational, distributed leadership); trust research (ability/benevolence/integrity, institutional trust, trust repair); collective intelligence and information science (crowdsourcing, deliberation, knowledge sharing, misinformation diffusion); diffusion of innovations and technology adoption (Rogers), sociotechnical systems; intergenerational and cohort analysis (life-course perspective, generational change); conflict resolution and de-escalation (dual concerns model, mediation, restorative practice); behavioural resilience (adaptation, coping, community resilience).

### 2.14 Theory pluralism and meta-science
Evidence hierarchy: systematic reviews/meta-analyses → replicated experiments → quasi-experiments → longitudinal cohorts → cross-sectional → case studies → opinion. Replication, publication bias, preregistration, open data, registered reports; triangulation; WEIRD bias and transportability; aleatoric vs epistemic uncertainty.

---

## 3. Target architecture

### 3.1 Position inside IAM

| IAM system | HBI contribution |
|-----------|------------------|
| 2 — Intelligence and Reasoning | Orchestration, arbitration, world-model integration, conflict resolution |
| 3 — Memory and Knowledge | Behavioural knowledge base, historical memory and chronology, prediction records, isolated from private user memory |
| 5 — Learning and Capability Development | Research ingestion, source validation, capability registry, self-directed research |
| 6 — Communication and Multimodal | Expression/tone analysis, multilingual research, explanation generation |
| 12 — Governance, Security and Privacy | Independent governance plane, purpose limitation, consent and access control, audit |
| 13 — Infrastructure and Operational Resilience | Local-first compute, resource-aware scheduling under OD-39 |
| 14 — Evaluation and Research | Benchmarks, calibration, backtesting, bias testing, theory comparison |

Uses OD-38 models locally/hosted by default; external AI providers assist discovery, translation or OCR only, never as primary intelligence or governance authority.

### 3.2 Reference architecture

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ IAM MAINBRAIN — central reasoning, orchestration, arbitration, authority     │
└───────────────────────────────┬──────────────────────────────────────────────┘
                                │ versioned hbi.* API (§6.6)
┌───────────────────────────────▼──────────────────────────────────────────────┐
│ HBI CORE — routing, evidence budgeting, module/engine orchestration, fusion  │
└──────┬──────────────────────────────────────────────┬────────────────────────┘
       │                                              │
┌──────▼───────────────────────────────┐   ┌──────────▼────────────────────────┐
│ 38 INTELLIGENCE MODULES / 6 DIVISIONS│   │ GOVERNANCE PLANE (independent)     │
│ D1 Human Psychology & Understanding  │   │ purpose · consent · privacy        │
│ D2 Motivation, Cognition, Decisions  │◄──┤ red lines · dual-use review        │
│ D3 Communication & Social Dynamics   │   │ oversight gate · safety stop       │
│ D4 Collective, Cultural, Societal    │   └──────────┬────────────────────────┘
│ D5 Historical & Civilisation         │              │
│ D6 Prediction, Learning, Protection  │              │
└──────┬───────────────────────────────┘              │
       │                                              │
┌──────▼──────────────────────────────────────────────▼────────────────────────┐
│ 13 TECHNICAL ENGINES                                                         │
│ E1 Historical KG · E2 Temporal · E3 Evidence Verification · E4 Source Rel.   │
│ E5 Multilingual Research · E6 Cultural Context · E7 Causal Discovery         │
│ E8 Behavioural Simulation Lab · E9 Predictive Model Registry                 │
│ E10 Intelligence Benchmarking · E11 Contradiction Detection · E12 Gap Detect. │
│ E13 Historical Chronology                                                    │
└──────┬────────────────────────────────────────────────────────────────────────┘
┌──────▼────────────────────────────────────────────────────────────────────────┐
│ SHARED KNOWLEDGE & PREDICTION LAYER                                           │
│ Evidence store · Knowledge graph · Historical memory · Behavioural models     │
│ Probability estimates · Calibration registry · Evaluation · Feedback · Versions│
│ Services: Research · Knowledge · Feature · Prediction · Simulation            │
│           Evaluation · Governance · Audit · Historical Memory                 │
└──────────────────────────────────────────────────────────────────────────────┘
                                │ local-first storage (§6.8)
```

### 3.3 Final module set — 38 modules in six divisions

**Division 1 — Human Psychology and Understanding (6 modules)**

| ID | Module | Responsibility |
|----|--------|----------------|
| 1 | Psychology Intelligence | Integrate theories, research and findings; grade evidence |
| 2 | Personality Intelligence | Trait frameworks and individual differences as hypotheses with situational context |
| 3 | Emotional Intelligence | Interpret expressed emotion/context with uncertainty; model regulation |
| 4 | Cognitive Intelligence | Perception, memory, reasoning, biases, belief structures |
| 24 | Human Evolution Intelligence | Behavioural development through evolution: tools, cooperation, language, migration, adaptation |
| 25 | Developmental Psychology Intelligence | Behaviour from childhood through adulthood and ageing; life-course changes |

**Division 2 — Human Motivation, Cognition and Decision-Making (6 modules)**

| ID | Module | Responsibility |
|----|--------|----------------|
| 5 | Motivation Intelligence | Needs, incentives, goals, values, self-determination |
| 6 | Decision Intelligence | Choices, risk, uncertainty, decision patterns |
| 7 | Habit and Learning Intelligence | Routines, reinforcement, habit formation, adaptation |
| 29 | Economic Behaviour Intelligence | Responses to economic conditions, incentives, scarcity, markets |
| 30 | Crisis Behaviour Intelligence | Individual and societal response to disasters, uncertainty and shocks |
| 34 | Information Behaviour Intelligence | How people consume, interpret, trust and share information |

**Division 3 — Communication, Relationships and Social Dynamics (6 modules)**

| ID | Module | Responsibility |
|----|--------|----------------|
| 8 | Communication Intelligence | Language, tone, rhetoric, register, pragmatics |
| 9 | Interpersonal Intelligence | Relationships, trust, boundaries, cooperation, conflict |
| 10 | Social Dynamics Intelligence | Social influence, norms, networks, collective interaction |
| 31 | Leadership Psychology Intelligence | Leadership styles, authority, influence, leader decisions |
| 32 | Trust and Reputation Intelligence | How trust develops, changes, repairs and breaks down |
| 37 | Conflict Resolution Intelligence | Escalation, de-escalation, negotiation, resolution, reconciliation |

**Division 4 — Collective, Cultural and Societal Behaviour (8 modules)**

| ID | Module | Responsibility |
|----|--------|----------------|
| 11 | Group Behaviour Intelligence | Group decisions, conformity, leadership, group dynamics |
| 12 | Crowd and Society Intelligence | Large-scale trends, public responses, societal change |
| 26 | Cross-Cultural Intelligence | Behavioural differences across cultures, with anti-generalisation controls |
| 28 | Geopolitical Behaviour Intelligence | Nations, leaders and institutions: behaviour, interaction, strategy |
| 33 | Collective Intelligence | How groups share knowledge and make collective decisions |
| 35 | Technological Adaptation Intelligence | Adoption and behavioural adaptation to technological change |
| 36 | Intergenerational Intelligence | Behavioural patterns and value change between generations |
| 38 | Behavioural Resilience Intelligence | Individual and community adaptation to adversity |

**Division 5 — Historical Human Behaviour and Civilisation Intelligence (9 modules)**

| ID | Module | Responsibility |
|----|--------|----------------|
| 16 | Historical Research Intelligence | Discover, collect and analyse historical documents and scholarship |
| 17 | Historical Behaviour Analysis | Behaviour under historical conditions; cross-period comparison |
| 18 | Historical Psychology Intelligence | Historical motivations, fears, beliefs, leadership psychology |
| 19 | Historical Social Dynamics | Communities, structures, hierarchies, migration, urbanisation |
| 20 | Historical Decision Intelligence | Reconstruct decisions using contemporaneous information |
| 21 | Historical Conflict and Cooperation | Wars, disputes, alliances, negotiation, reconciliation, diplomacy |
| 22 | Historical Patterns and Trends | Recurring patterns across periods, cultures and civilisations |
| 23 | Historical Forecasting Intelligence | Map present cases to precedents; applicability and weak-analogy detection |
| 27 | Historical Civilisation Intelligence | Development, transformation and decline of civilisations |

**Division 6 — Predictive Intelligence, Scientific Learning and Psychological Protection (3 modules + 8 capabilities)**

| ID | Module | Responsibility |
|----|--------|----------------|
| 13 | Behavioural Forecasting | Estimate possible future behaviours; probabilities and scenarios |
| 14 | Psychological Threat and Manipulation Intelligence | Detect manipulation, coercion, propaganda, deception patterns — defensive |
| 15 | Behavioural Learning and Evaluation | Accuracy, bias, failures, model improvement, versioning and rollback |

The **eight advanced capabilities** (§4) are implemented across modules 13–15, the engines and the research service; they are capabilities, not arbitrary extra module IDs.

### 3.4 Technical engines — 13

| ID | Engine | Purpose | Key interface |
|----|--------|---------|---------------|
| E1 | Historical Knowledge Graph | Connect events, people, institutions, ideas and outcomes across time | `hbi.hkg.query/expand` |
| E2 | Temporal Intelligence Engine | Model how behaviour changes across short and long time scales | `hbi.temporal.analyse` |
| E3 | Evidence Verification Engine | Verify research and historical claims against source evidence | `hbi.evidence.verify` |
| E4 | Source Reliability Engine | Assess source credibility, bias, provenance and limitations | `hbi.sources.rate` |
| E5 | Multilingual Research Engine | Ingest and analyse material across languages; translation with provenance | `hbi.research.multilingual` |
| E6 | Cultural Context Engine | Attach cultural context and prevent incorrect generalisations | `hbi.cultural.contextualise` |
| E7 | Causal Discovery Engine | Investigate causal structure among contributing factors | `hbi.causal.discover` |
| E8 | Behavioural Simulation Laboratory | Test hypothetical scenarios and counterfactuals safely | `hbi.simulate.run` |
| E9 | Predictive Model Registry | Maintain, version and govern prediction models | `hbi.models.register/promote/rollback` |
| E10 | Intelligence Benchmarking Engine | Compare models and measure real improvements | `hbi.benchmark.compare` |
| E11 | Contradiction Detection Engine | Identify conflicting evidence, claims and interpretations | `hbi.contradictions.find` |
| E12 | Knowledge Gap Detection | Identify what IAM does not yet understand | `hbi.gaps.detect` |
| E13 | Historical Chronology Engine | Dates, overlapping timelines, uncertain periods, conflicting accounts | `hbi.chronology.resolve` |

### 3.5 Shared knowledge and prediction layer
All modules and engines exchange **epistemic objects** (§5.2) through the standard contract (§6.7) and write to shared stores. Only module 13 emits predictions, via the Prediction Service. The mainbrain arbitrates conflicts using evidence grade, recency, domain relevance and calibration history — it does not average incompatible claims.

### 3.6 Governance, audit and safety planes
Governance Service is a policy decision point independent of analysis. Audit Service records request, authority, purpose, scope, evidence, models, probability, confidence, uncertainty, output and evaluation, append-only and tamper-evident. Dual-use review applies to module 14 and any aggregation capability. A **safety stop** can disable prediction/aggregation without disabling research or understanding.

### 3.7 Standard module/engine contract

```
ComponentRequest {
  request_id, trace_id, caller, authority_token, purpose, scope ("aggregate"|"individual"),
  question, target, context_refs[], time_horizon, evidence_budget,
  data_minimisation_attestation, governance_decision_ref
}
ComponentResult {
  request_id, component_id, component_version, epistemic_objects[],
  methods[], assumptions[], limitations[], alternatives[], provenance_refs[], audit_ref
}
Error { code: NOT_AUTHORISED | PURPOSE_MISMATCH | INSUFFICIENT_EVIDENCE |
        SENSITIVE_INFERENCE_BLOCKED | SCOPE_VIOLATION | CONFIDENCE_TOO_LOW }
```

### 3.8 Worked example — community response to a platform change
Governance validates purpose/scope (aggregate) → communication (8) analyses framing → emotional (3) and cognitive (4) assess expressed concerns → social dynamics (10) and group behaviour (11) map influence → historical (22/23 + E1/E13) check precedents and score analogies → forecasting (13) produces a scenario distribution → evaluation (15) logs and later scores calibration → audit records the chain. No individual is profiled; no message targeted.

### 3.9 Local-first and external assistance
Primary analysis, storage and execution are local-first using approved storage integrations. External providers assist discovery, OCR and translation only with minimised non-sensitive material; outputs are untrusted evidence requiring verification and never carry governance authority.

---

## 4. Advanced intelligence capabilities (independent development)

These eight capabilities make HBI a self-developing scientific system. Each has **trigger → method → gate → output → audit**.

### 4.1 Self-directed research (A1)
**Trigger:** E12 gap record or low-confidence prediction. **Method:** formulate research questions from the gap, search E5/E3/E4 across approved sources, extract and grade evidence, update candidate knowledge. **Gate:** governance approves purpose and source licence; E3/E4 verification threshold met; no sensitive data. **Output:** research report + candidate knowledge records. **Audit:** gap id → query log → sources → decision.

### 4.2 Scientific theory comparison (A2)
Maintain a theory registry (claim, scope, mechanisms, predictions, evidence). Compare competing theories by: differential predictions on held-out cases, out-of-sample performance, explanatory scope, parsimony, replication status and falsification history. Use Bayesian model comparison where likelihoods are definable. **Output:** comparative theory report with "current best-supported" and "still viable alternatives"; never declares a theory finally proven.

### 4.3 Independent hypothesis generation (A3)
**Trigger:** anomaly, contradiction (E11), gap (E12), surprising historical analogue. **Method:** abductive inference, analogy, causal schemas (E7), cross-disciplinary transfer (A6). Every hypothesis must state a mechanism, a falsifier and a test design; tests are registered before results are seen. **Gate:** no hypothesis may target an identifiable person or sensitive trait. **Output:** hypothesis record with test protocol.

### 4.4 Historical-to-modern comparison (A4)
Use E13 chronology and E1 graph to select precedents; score analogy with the rubric in §9.6; report applicability verdict: **applicable / partially applicable / weak / misleading**. Differences in institutions, technology, demographics and conditions must be listed explicitly.

### 4.5 Predictive self-evaluation (A5)
On outcome arrival, classify each error: evidence gap, source-quality failure, model misspecification, calibration failure, context/distribution shift, framing error, temporal-change error, or governance/scope mistake. Trace to the responsible stage and open a corrective record. **Output:** error root-cause report feeding A7 and E10.

### 4.6 Cross-disciplinary reasoning (A6)
Fusion protocol: each discipline produces separately graded claims; the mainbrain combines them with explicit weights from calibration history; conflicts are preserved and surfaced. No discipline dominates by default. Required for any question spanning psychology, history, economics, neuroscience and sociology.

### 4.7 Knowledge evolution (A7)
Update triggers: new replication, stronger source, contradiction, backtest result, drift alert. Revisions are immutable versions with rationale; deprecated claims remain queryable with status `superseded`; contested interpretations are never silently collapsed.

### 4.8 Uncertainty intelligence (A8)
HBI must recognise when behaviour **cannot** be reliably predicted. Conditions for structured refusal: insufficient evidence, high context novelty, contested theory with no discriminating data, calibration below threshold, sensitive/individual scope, or uncontrolled distribution shift. **Output:** `"cannot reliably predict"` with reasons, evidence gaps and what evidence would change the answer. Refusal is a successful outcome, not a failure.

---

## 5. Behavioural and historical knowledge model

### 5.1 Ten context dimensions
Individual, Context, Environment, Emotion, Motivation, Cognition, Experience, Social influence, Behaviour, Outcome — each recorded with source, status and confidence (as specified in v1 §4.1, retained in full).

### 5.2 Epistemic taxonomy
Observation (directly evidenced) · Interpretation (possible explanation, ≥1 alternative) · Hypothesis (requires test/falsifier) · Prediction (§7.10 record). Evidence classes: verified, well-supported, contested, unverified, speculation. Silently promoting an interpretation to observation is prohibited.

### 5.3 Behavioural knowledge graph (E1)
Nodes: Actor (pseudonymous), Group, Event, Behaviour, Emotion, Motivation, Belief, Norm, Institution, Artefact, Source, Theory, Hypothesis, Prediction, Period, Civilisation. Typed, graded edges: `expressed`, `inferred`, `influenced`, `observed_in`, `member_of`, `caused_by` (causal evidence only), `correlated_with`, `preceded`, `contradicted_by`, `supports`, `analogous_to`, `derived_from`, `part_of_civilisation`, `contemporaneous_with`.

### 5.4 Confidence, uncertainty and provenance
Probability and confidence are separate fields. Uncertainty decomposed into evidence gap, measurement noise, model uncertainty, context novelty and distribution shift. Provenance: source id, type, collection date, licence, permitted purpose, extraction method, transformations, quality rating, reviewer, version.

### 5.5 Privacy tiers
T0 public research · T1 curated internal · T2 aggregate operational (k-anonymity threshold) · T3 individual interaction. Tiers are physically separated with separate keys and retention; T0/T1 knowledge never populates T3 profiles.

### 5.6 Core knowledge record schema

```json
{
  "record_id": "bkr_01J...",
  "epistemic_type": "observation|interpretation|hypothesis|prediction",
  "evidence_class": "verified|well_supported|contested|unverified|speculation",
  "claim": "...",
  "scope": "aggregate|individual",
  "population": {"cohort_ref": "...", "coverage": "..."},
  "context_dimensions": {"individual":{}, "context":{}, "environment":{}, "emotion":{},
    "motivation":{}, "cognition":{}, "experience":{}, "social_influence":{},
    "behaviour":{}, "outcome":{}},
  "evidence": [{"source_id":"...", "source_type":"...", "locator":"...",
    "grade":"...", "licence":"...", "collection_date":"...", "permitted_purpose":"..."}],
  "confidence": 0.0,
  "uncertainty": {"aleatoric":0.0, "epistemic":0.0, "evidence_gap":"low|medium|high",
    "distribution_shift":"low|medium|high"},
  "alternatives": ["..."],
  "falsifier": "...",
  "causal_status": "causal|correlational|speculative",
  "module_ids": [1, 24],
  "tier": "T0|T1|T2|T3",
  "version": 1,
  "last_reviewed": "2026-11-26",
  "audit_ref": "..."
}
```

---

## 6. Implementation specifications (14 required areas)

### 6.1 Data schemas and knowledge structures
The canonical record is §5.6. All stores use JSON Schema validation at write time. Enum fields are closed; unknown values are rejected into a quarantine queue. Every record carries `version`, `tier` and `audit_ref`. Schema changes are backward-compatible or trigger a documented migration.

### 6.2 Historical event and timeline schemas

```json
{
  "event_id": "he_01J...",
  "name": "...",
  "date": {
    "start": {"value":"-0441-03-15", "precision":"day|month|year|decade|century|millennium",
      "calendar":"Gregorian|Julian|Other", "confidence":0.7,
      "earliest":"...", "latest":"..."},
    "end":   {"value":"...", "precision":"...", "confidence":0.6}
  },
  "periods": ["classical_antiquity"],
  "geography": [{"place_id":"...", "region":"...", "coordinates":null, "uncertainty":"..."}],
  "actors": [{"actor_id":"...", "role":"..."}],
  "contexts": {"social":"...", "economic":"...", "political":"...", "cultural":"..."},
  "documented_behaviour": [{"claim":"...", "sources":["..."], "evidence_class":"..."}],
  "motivational_hypotheses": [{"claim":"...", "status":"hypothesis", "alternatives":[]}],
  "consequences": {"short":[], "long":[]},
  "sources": {"primary":[], "secondary":[]},
  "disputed_claims": [{"claim":"...", "accounts":["..."], "resolution":"unresolved"}],
  "evidence_class": "verified|well_supported|contested|unverified|speculation",
  "confidence": 0.0,
  "lessons": [{"lesson":"...", "qualification":"..."}],
  "related_events": [{"event_id":"...", "relation":"caused_by|preceded|analogous_to|contemporaneous_with"}],
  "timeline_refs": ["tl_..."],
  "version": 1,
  "audit_ref": "..."
}
```

```json
{
  "timeline_id": "tl_...",
  "title": "...",
  "calendar_system": "...",
  "events": [{"event_id":"...", "sequence_index":12,
    "temporal_relation":"before|after|overlaps|concurrent|uncertain",
    "relation_confidence":0.8, "overlap_group":"..."}],
  "uncertain_periods": [{"label":"...", "earliest":"...", "latest":"...", "basis":"..."}],
  "conflicting_accounts": [{"account_a":"...", "account_b":"...",
    "resolution_status":"unresolved|resolved|partially_resolved", "basis":"..."}],
  "version": 1
}
```

**E13 Historical Chronology Engine** resolves dates across calendars, models incomplete/uncertain periods (terminus post quem/ante quem), represents overlapping timelines without forcing linear order, and preserves conflicting accounts instead of choosing one silently.

### 6.3 Research ingestion and document processing
Pipeline: `discover → acquire (licence check) → deduplicate → OCR/text extraction (E5) → language/register detection (E5) → cultural tagging (E6) → claim extraction → source rating (E4) → verification (E3) → contradiction scan (E11) → grading → curation → versioned publication`. Failed verification goes to quarantine, never to the knowledge store. Every stage logs provenance and transformation.

### 6.4 Dataset licensing and provenance
Mandatory dataset card: `id, title, source, source_type, collection_date, licence, permitted_purpose, collection_method, demographics_coverage, limits, quality_rating, consent_basis, retention, transformations[], reviewer, version`. No ingestion without licence and purpose fields. Scraped public material is observed as communication patterns, never as individual psychology.

### 6.5 Model training and evaluation pipelines
Stages: question definition → data selection (tier-checked) → baseline → training (OD-40 engines) → held-out evaluation → calibration check → bias/representativeness check → backtest where applicable → adversarial test → governance approval → registry promotion. No training on T3 data for population models; no private user memory in fine-tuning (OD-40).

### 6.6 Prediction API contracts (versioned)

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/v1/hbi/predictions` | Create prediction request |
| GET | `/api/v1/hbi/predictions/{id}` | Retrieve prediction record |
| POST | `/api/v1/hbi/predictions/{id}/evaluate` | Supply legitimate outcome |
| POST | `/api/v1/hbi/simulations` | Run scenario simulation |
| POST | `/api/v1/hbi/research/search` | Search approved research |
| GET | `/api/v1/hbi/knowledge/{concept}` | Retrieve graded knowledge |
| POST | `/api/v1/hbi/history/analogy` | Score historical analogy |
| POST | `/api/v1/hbi/history/backtest` | Run leakage-free backtest |
| GET | `/api/v1/hbi/models/{id}/performance` | Model metrics |
| POST | `/api/v1/hbi/gaps` | Knowledge-gap query |

```
PredictionRequest {
  question, target, scope, context_refs[], time_horizon,
  purpose, authority_token, evidence_budget, include_alternatives: true
}
PredictionResponse {
  prediction_id, probability{}, confidence, uncertainty{}, assumptions[],
  alternatives[], causal_status, evidence[], limitations[], governance_ref, audit_ref
}
Errors: 403 NOT_AUTHORISED / PURPOSE_MISMATCH · 422 SCOPE_VIOLATION ·
        409 SENSITIVE_INFERENCE_BLOCKED · 200 with A8 refusal object
```

### 6.7 Inter-module communication
Event envelope: `message_id, trace_id, from, to, type, purpose, scope, authority_ref, payload, created_at, ttl, audit_ref`. Topics: `hbi.evidence.new`, `hbi.knowledge.updated`, `hbi.contradiction.found`, `hbi.gap.found`, `hbi.prediction.requested`, `hbi.prediction.completed`, `hbi.evaluation.completed`, `hbi.model.promoted`, `hbi.model.rolled_back`. Messages are untrusted data, never instructions; schema-validated; signed within IAM's internal trust boundary.

### 6.8 Persistent memory and retrieval
Namespaces: `hbi:research:t0`, `hbi:knowledge:t1`, `hbi:aggregate:t2`, `hbi:individual:t3`, `hbi:history:events`, `hbi:history:timelines`, `hbi:history:lessons`, `hbi:predictions`, `hbi:evaluations`, `hbi:hypotheses`, `hbi:models`. Retrieval applies tier filters before semantic search (pgvector). Retention: T0/T1 long-lived with review; T2 purpose-bound; T3 shortest retention with deletion propagation. Historical memory is persistent and versioned — IAM never rediscovers the same history.

### 6.9 Local model integration
OD-38 local models are default; hosted providers optional. All prompts are purpose-tagged and minimised; provider outputs pass E3/E4 verification before storage. No provider holds governance authority or persistent T3 memory.

### 6.10 Resource management and scaling
Tiers: local core (8 GB) for lightweight inference only; trusted GPU nodes for training/simulation; approved free/hosted resources for bulk research under OD-39/OD-41. Resource-aware scheduler; no paid compute without Creator approval; evidence budgets per request; heavy jobs queued and isolated.

### 6.11 Security and access controls
ABAC with purpose and scope claims in tokens; least privilege; encryption at rest/in transit; tenant/session isolation; tamper-evident audit; independent safety stop; no cross-tier reads without governance approval; unauthorised access tests in CI.

### 6.12 Privacy and consent enforcement
Consent record: `subject_ref, purpose[], scope, basis, granted_at, withdrawn_at, retention, deletion_status`. Withdrawal propagates to derived T2/T3 artefacts. POPIA for South African operations; GDPR and applicable AI regulation for European users. Sensitive traits are excluded from inference and decisions; emotion inference is never used for employment, financial or access decisions.

### 6.13 Automated testing and acceptance gates
Gates: schema validation; unit tests per module/engine; contract tests for `hbi.*`; calibration and Brier regression thresholds; backtest non-leakage assertion; bias/regression dashboards; privacy and access-control tests; adversarial/red-team suite; acceptance criteria §11.7. No promotion without all gates green.

### 6.14 Model versioning, rollback and monitoring
Semantic versioning; immutable registry entries (E9); canary promotion; drift and calibration monitors; automated rollback on threshold breach; full change record with rationale; previous versions remain queryable and restorable.

---

## 7. Datasets and knowledge acquisition

### 7.1 Scientific sources
PubMed, PsycINFO, OpenAlex, Semantic Scholar, Crossref, Google Scholar (subject to terms). Capture metadata, citations, replication flags and open-access status.

### 7.2 Open research datasets
World Values Survey, European Social Survey, General Social Survey, Dunnhumby Complete Journey, Stanford SNAP, UCI ML Repository, Kaggle (provenance and quality checks mandatory).

### 7.3 Public digital information
Public discussions, feedback, reviews, news, surveys, trends and communication patterns. No private accounts, no auth/paywall/CAPTCHA bypass, no de-anonymisation, no sensitive inference, no individual profiling from scraped activity. Public availability ≠ unrestricted reuse.

### 7.4 Internal curated collection
Findings, theories, definitions, results, validated patterns, benchmarks, **failed predictions**, evaluation reports, limitations and conflicting research — each with provenance, licence, purpose, coverage, limits and quality rating.

### 7.5 Expanded historical corpus
Required coverage: prehistoric behaviour; human evolution and migration; ancient civilisations; Indigenous histories and oral traditions; African history and civilisations; Asian and Middle Eastern history; European and American history; colonialism and decolonisation; political and economic transformations; religious and cultural developments; scientific and technological revolutions; historical leadership and institutions; historical propaganda and misinformation; social movements and revolutions; historical cooperation and diplomacy.

Sources: Internet Archive, JSTOR, Library of Congress, National Archives, UNESCO, World Bank, Our World in Data, Google Books, Wikimedia Commons (per-file licence). African priority: South African History Archive, South African National Archives, Nelson Mandela Foundation, African Union documentation, African university archives, oral-history collections. Indigenous knowledge and cultural-heritage restrictions are respected. No exclusively European/American perspective.

---

## 8. Prediction methods (advanced)

Retained in full from v1 §6: portfolio and problem-driven selection; Bayesian updating `P(H|E) = P(E|H)P(H)/P(E)` and odds form; hierarchical partial pooling; logit; survival/hazard; Hawkes contagion intensity; ML with interpretability requirements; temporal change-point detection; scenario simulation with probabilities summing to 1; causal inference (SCM/do-calculus, DiD, RDD, IV, synthetic control, natural experiments, process tracing); ensemble and mainbrain arbitration with disagreement → higher uncertainty; conformal prediction; aleatoric/epistemic decomposition; proper scoring rules; calibration/ECE. Correlation is labelled correlational. Only module 13 emits predictions.

### 8.1 Standard prediction record (extended)

```json
{
  "prediction_id": "pid_...", "target": "...", "scope": "aggregate|individual",
  "time_horizon": "...", "context": {"dimensions":{}},
  "evidence": [{"ref":"...", "grade":"...", "source":"..."}],
  "hypotheses": [{"claim":"...", "likelihood":0.0, "alternatives":[]}],
  "probability": {"A":0.0,"B":0.0,"C":0.0,"D":0.0},
  "confidence": 0.0,
  "uncertainty": {"evidence_gap":"...", "measurement":"...", "model":"...",
    "novelty":"...", "distribution_shift":"..."},
  "causal_status": "causal|correlational|speculative",
  "assumptions": [], "limitations": [], "alternatives": [],
  "governance_ref": "...", "evaluation": null, "version": "1.0", "audit_ref": "..."
}
```

Probability and confidence remain separate fields.

---

## 9. Historical intelligence (expanded)

### 9.1 Mission and principle
Study humanity across prehistory, ancient, medieval, early modern, industrial, modern and contemporary periods — decisions, crises, cooperation, conflict, culture, technology, leadership, propaganda and civilisational change. **History provides evidence and context, not a guarantee that the future repeats the past.**

### 9.2 Eight historical methods
Comparative historical analysis; longitudinal analysis; historical network analysis (E1); process tracing; Bayesian historical reasoning; causal historical analysis (E7); counterfactual history (explicitly hypothetical); historical analogy (§9.6). Counterfactual discipline: alternative decisions, required condition changes, supporting evidence — all labelled hypothetical.

### 9.3 Analogy scoring rubric (A4)

| Dimension | Weight |
|-----------|--------|
| Contextual similarity | 0.20 |
| Economic similarity | 0.15 |
| Political similarity | 0.15 |
| Social similarity | 0.15 |
| Behavioural similarity | 0.15 |
| Technological similarity | 0.10 |
| Differences in relevant conditions | 0.05 (penalty) |
| Quality of historical evidence | 0.05 |

`score = Σ w·s − penalty(differences)`; capped if primary-source grade is low; below threshold → **"weak or misleading comparison"**.

### 9.4 Historical backtesting
Select **multiple** diverse events (not only famous theory-confirming cases) → fix cutoff before outcome known → reconstruct only then-available information → forecast → compare with documented outcome → score → record errors. Strict leakage prevention; no outcome information in the "prediction".

### 9.5 Historical governance
Preserve context; distinguish evidence from propaganda/fabrication; recognise historical bias; no stereotypes as facts; no transfer of historical group traits to living people; respect Indigenous knowledge, archives and copyright; handle trauma responsibly; recognise contested narratives; never justify discrimination from historical patterns; knowledge revisable.

### 9.6 Historical evidence classes
Verified evidence; well-supported interpretation; contested interpretation; unverified account; speculation. Disagreements are preserved.

### 9.7 Memory and graph
E13 chronology + E1 graph + persistent namespaces (§6.8). Events, actors, institutions, ideas and outcomes are linked across overlapping timelines with uncertain periods and conflicting accounts retained.

---

## 10. Learning and continuous improvement

Cycle: `research (A1) → verification (E3/E4) → curation → model development → prediction/simulation → evaluation (E10, A5) → bias/accuracy measurement → validated improvement (A7) → repeat`. New knowledge never auto-promotes to production. Promotion gate requires provenance, baseline comparison, calibration, bias check, backtest, documented limits, governance approval, version and tested rollback (§6.5, §6.13, §6.14). Population learning and individual prediction remain distinct (§1.3).

---

## 11. Evaluation and assurance

### 11.1 Metrics
Accuracy, precision, recall, F1, Brier `(1/N)Σ(p−o)²`, log loss, calibration/ECE, MAE, RMSE, AUC. Calibration and Brier are essential for probabilistic outputs; AUC is not a calibration measure.

### 11.2 Scientific evaluation
Reproducibility, data quality, representativeness, selection bias, confounding, generalisation, cultural/contextual differences, temporal degradation, interpretability.

### 11.3 Fairness and bias
Performance across relevant populations; documented disparities; fairness metrics as diagnostics, never licences for individual decisions; WEIRD and distribution-shift reporting.

### 11.4 Backtesting and historical evaluation
Leakage-free backtests (§9.4); historical features measured against a no-history baseline; analogy accuracy tracked.

### 11.5 Three environments
Research (exploratory) · Simulation (no claims about real individuals) · Production (validated models, approved purposes, periodic re-evaluation).

### 11.6 Adversarial red-teaming
Manipulation detection against adversarial phrasing and coordinated inauthentic behaviour; contested history; ambiguous tone; refusal-path tests for sensitive inference and scope violation; safety-stop verification.

### 11.7 Acceptance criteria (master)

| Requirement | Completion condition |
|-------------|----------------------|
| Scientific foundation | Sources/theories documented, graded, traceable |
| Module/engine completeness | 38 modules and 13 engines implemented with contracts |
| Knowledge management | Observation/interpretation/hypothesis/prediction distinguishable |
| Advanced capabilities | A1–A8 demonstrable with gates and audit |
| Prediction | Only module 13 emits probability records |
| Uncertainty | Confidence and uncertainty separate; A8 refusal works |
| Bayesian reasoning | Predictions update and record updates |
| Simulation | Multiple plausible outcomes with assumptions |
| Causal discipline | Correlational vs causal labelled correctly |
| Evaluation | Held-out scoring, calibration, proper scoring rules |
| Bias testing | Disparities and limits documented |
| Historical research | Prehistory→contemporary coverage; underrepresented perspectives |
| Chronology | Uncertain dates, overlaps, conflicts handled (E13) |
| Historical graph | E1 links events/actors/institutions/ideas/outcomes |
| Analogy | Weak/misleading verdict possible |
| Counterfactuals | Explicitly hypothetical |
| Backtesting | Leakage-free, multi-event, scored |
| Historical memory | Persistent, versioned, revisable |
| Historical value | Measured lift over no-history baseline |
| Schemas/APIs | §6.1–6.14 contracts validated in CI |
| Privacy/security | Governance enforced; unauthorised access blocked |
| Human oversight | Consequential decisions remain human |
| Integration | IAM invokes `hbi.*` through versioned interfaces |
| Learning | Updates evaluated, versioned, reversible |
| Auditability | Predictions, versions, decisions traceable |

---

## 12. Ethical safeguards and human protection

**Permitted:** understanding psychology; recognising emotional/communication patterns with uncertainty; anticipating community needs; detecting manipulation and misinformation indicators; helping people recognise coercion; conflict prevention and resolution; aggregate forecasting; historical study of humanity; independent scientific research within governance.

**Prohibited:** exploiting vulnerabilities; manipulation without informed consent; coercion/intimidation; secret profiling; sensitive-trait inference for decisions; predicting criminality/dangerousness from personality, appearance or demographics; emotion-based employment/financial/access decisions; targeted propaganda or psychological warfare; deceptive dependency; treating inferred states as facts; turning historical group traits into living-person judgements.

**Dual-use review** for module 14 and aggregation. **Privacy:** minimisation, purpose limitation, consent, anonymisation, encryption, access control, retention, provenance, audit, tier separation; POPIA and GDPR/EU AI Act alignment (emotion recognition and manipulative techniques are hard limits). **Human oversight:** no independent consequential decisions; analysis to authorised humans with uncertainty and disconfirming evidence. **Doc 24 alignment:** Equality of Existence — evaluate behaviour and consequences, not worth; assist, do not dominate; remain corrigible.

---

## 13. Development roadmap

**Phase 0 — Specification and governance gate (current state).** This master specification is reviewed and confirmed as OD-45; governance policies, red lines and acceptance gates are approved. **No coding begins before this gate passes.**

| Phase | Core deliverable | Historical / engine deliverable |
|-------|------------------|---------------------------------|
| 1 — Scientific foundation | Knowledge Base; evidence grading; privacy/governance | Historical library; E3/E4/E5; source verification, chronology (E13) |
| 2 — Behavioural understanding | Modules 1–12, 24–26, 29–38 as applicable; structured representations | Historical psychology/behaviour; E1, E6, E11 |
| 3 — Predictive intelligence | Prediction engine, module 13; statistical/Bayesian/ML/temporal | E2, E7, E8; historical patterns and Bayesian reasoning |
| 4 — Collective intelligence | Modules 11, 12, 26, 28, 33, 35, 36, 38; aggregate forecasting | Historical civilisation, conflict/cooperation (21, 27) |
| 5 — Evaluation and protection | Assurance framework; module 14; A1–A8; audits | E9, E10, E12; backtesting and comparative analysis |
| 6 — Advanced integration | Full 38-module integration; cross-module reasoning; acceptance | Persistent historical memory; knowledge evolution |

Historical learning and engines are workstreams from Phase 1 onward, not one-time imports.

---

## 14. Integration and long-term capabilities

Five major capabilities: **Human Understanding**, **Behavioural Recognition**, **Behavioural Prediction**, **Psychological Protection**, **Continuous Intelligence Development** (research, history, self-evaluation, validated improvement). HBI contributes to communication, research, governance, legal and other domains through versioned interfaces while keeping sensitive data, models and permissions independently governed.

---

## 15. Definition of completion

> IAM HBI is complete when it can scientifically understand human behaviour across evolution, history and the modern world; analyse complex psychological, social and civilisational situations with traceable evidence and explicit uncertainty; generate and test independent hypotheses; anticipate plausible outcomes with calibrated probabilities; recognise manipulation and coercion defensively; know when prediction is not reliable; and demonstrably improve through validated research, historical evidence and measured evaluation — while preserving human autonomy, dignity and rights.

**It should become better at understanding humanity, not better at controlling humanity.**

---

## 16. Confirmed owner decisions (OD-45)

1. Confirm **38 modules / six divisions** and **13 engines**, with original IDs 1–23 unchanged.
2. Confirm HBI as a domain inside existing systems 2/3/5/6/12/13/14 — not a sixteenth top-level system.
3. Confirm the three-layer separation and that only module 13 emits predictions.
4. Confirm the independent governance/audit planes, dual-use review and safety stop.
5. Confirm individual-level restrictions and exclusion of behavioural predictions from consequential decisions.
6. Confirm historical scope, source policy, underrepresented perspectives and cultural-heritage restrictions.
7. Confirm the `hbi.*` API namespace, schema/tier separation and memory namespaces.
8. Confirm the **Phase 0 gate**: no implementation until this master specification is approved.

All eight items were confirmed by the owner on 26 November 2026 and recorded as OD-45 in `IAM_OWNER_DECISIONS.md`. This document is part of the frozen baseline, changes no earlier decision and creates no sixteenth top-level system. The implementation in §17 followed the Phase 0 gate.

---

## 17. Implementation status (living record)

**26 November 2026 — production readiness and evidence/validation workstream complete; OD-45 confirmed.** Recorded in `IAM_OWNER_DECISIONS.md` and `ARCHITECTURE_INDEX.md`.

**Implemented**

| Artefact | Content |
|----------|---------|
| `backend/app/models/hbi.py` | `HBIKnowledgeRecord` and `HBIAuditEvent` with tier/scope/epistemic constraints |
| `backend/app/services/hbi/schemas.py` | Epistemic, evidence, scope, tier and causal enums; request models; prohibited-purpose list |
| `backend/app/services/hbi/evidence.py` | E3 evidence verification and E4 source reliability grading |
| `backend/app/services/hbi/ingestion.py` | Licensed document ingestion, E5 language detection, E6 cultural tagging, claim extraction, quarantine |
| `backend/app/services/hbi/contradictions.py` | E11 conflicting-claim detection; disagreements preserved |
| `backend/app/services/hbi/gaps.py` | E12 context-dimension, division and evidence-class gap detection |
| `backend/app/services/hbi/chronology.py` | E13 uncertain dates, overlapping timelines, conflicting accounts |
| `backend/app/services/hbi/temporal.py` | E2 temporal buckets and change-point candidates |
| `backend/app/services/hbi/modules.py` | 38-module registry; modules 1–13, 16–23, 26–38 functional with cue-based matching; module 14 remains a dedicated defensive engine |
| `backend/app/services/hbi/civilisation.py` | Module 27: multi-factor development/decline analysis with competing explanations |
| `backend/app/services/hbi/acceptance.py` | Automated §11.7 acceptance gates over a live service instance |
| `backend/app/services/hbi/hkg.py` | E1 historical knowledge graph: typed nodes/edges, timeline ingestion, neighbour expansion |
| `backend/app/services/hbi/advanced.py` | A1 self-directed research, A2 theory comparison, A3 hypothesis generation, A4 analogy scoring, A5 predictive self-evaluation |
| `backend/app/services/hbi/cross_disciplinary.py` | A6 graded-claim fusion with calibration weights and no single-discipline dominance |
| `backend/app/services/hbi/evolution.py` | A7 versioned revision, supersession, deprecation and lineage |
| `backend/app/services/hbi/uncertainty.py` | A8 predictability verdict with structured refusal and evidence-gap conditions |
| `backend/app/services/hbi/manipulation.py` | Defensive module 14: manipulation-pattern recognition with caveat; no influence content |
| `backend/app/services/hbi/sources.py`, `http_fetcher.py` | Allowlisted, licensed, purpose-bound source registry; robots-respecting HTTP transport; injectable fetcher for offline tests |
| `backend/app/services/hbi/prediction.py` | Brier, log loss, accuracy, ECE/reliability; Platt calibration; logistic, Beta-binomial and ensemble models; leakage-free backtesting; validation gate |
| `backend/app/services/hbi/forecasting.py` | Module 13: labelled scenario distributions, gated by A8 and model validation |
| `backend/app/services/hbi/causal.py` | Difference-in-differences, identification assumptions, causal-language permission check |
| `backend/app/services/hbi/historical.py` | Modules 16–23: historical research, behaviour, psychology, social dynamics, decisions, conflict, trends and forecasting |
| `backend/app/services/hbi/knowledge.py` | Tiered knowledge store; epistemic write discipline; DB hydration for persistent retrieval; quarantine |
| `backend/app/services/hbi/core.py` | Governance gate; analysis/research orchestration; A8 structured refusal; audit trail |
| `backend/app/services/hbi/service.py`, `__init__.py` | Async service facade (hydrate, ingest, modules, temporal, sources, validation, prediction) |
| `sdk/python/iam_sdk/client.py` | `iam.hbi.*` versioned interface for IAM mainbrain: research, knowledge, behaviour, prediction, history, uncertainty |
| `sdk/python/tests/test_hbi_sdk.py` | SDK surface tests with mocked transport (no network) |
| `backend/app/services/hbi/corpus.py` | Licensed local corpus ingestion from a manifest; per-document licence/purpose checks |
| `backend/app/services/hbi/calibration.py` | Beta-smoothed empirical source reliability; heuristics remain the fallback below n=3 |
| `backend/app/services/hbi/backtest_library.py`, `data/backtest_library.json` | Versioned 12-case backtest library, explicitly labelled illustrative fixtures with leakage precondition |
| `backend/tests/hbi_acceptance_check.py` | CI acceptance gate: runs all §11.7 gates and blocks promotion on any failure |
| `.github/workflows/ci.yml` | HBI acceptance step added to `backend-unit` |
| `backend/tests/integration_db_check.py` | HBI migrations 029/030, graded persistence, hydration, acceptance gates and authenticated `/hbi/status` check |
| `backend/app/api/routes/hbi.py` | Forty-one versioned `hbi.*` endpoints |
| `backend/app/db/migrations/029_hbi.sql`, `044_hbi_history_graph.sql` | Persistent memory and historical graph tables |
| `backend/tests/test_hbi.py` | 46 tests: all previous areas plus module 27, multilingual/script detection, duplicate screening and acceptance gates |

**Verification:** 46/46 HBI tests pass; FastAPI OpenAPI registers all forty-one `/api/v1/hbi/*` paths; dedicated CI acceptance gate passes all 10 gates locally. Full backend suite previously: 284 tests, one pre-existing environment failure (`test_ownerauth_reconciliation` → blocked `_xxhash` DLL, unrelated).

**Production readiness (26 November 2026):** the mainbrain interface is exposed as `iam.hbi.*` in the official Python SDK; HBI API dependencies commit knowledge and audit writes on success and roll back on failure, so records and audit events are durable in PostgreSQL; startup `Base.metadata.create_all` creates the HBI tables, with `029_hbi.sql` and `044_hbi_history_graph.sql` available for explicit migration paths.

**Evidence and validation (26 November 2026):** licensed corpus ingestion is available via manifest; 12 leakage-safe backtest cases ship as explicitly labelled illustrative fixtures (not real historical evidence); empirical source reliability replaces heuristic priors where n≥3; module 14 is integrated into the 38-module framework as well as its dedicated defensive endpoint. Module 15 now has a dedicated evaluation surface (`evaluation_module.py`): model registry states, bias/drift flags and calibration evidence, with no promotion authority. All 38 modules are registered and implemented at framework level.

**Scientific validation pipeline (26 November 2026):** `validation.py` derives leakage-safe backtest cases **only** from verified, dated records with documented outcomes; illustrative fixtures are never mixed into validation. `validation_report()` refuses the `validated` verdict when fewer than 10 real cases exist, when Brier/ECE thresholds fail, or when group disparity exceeds 0.15. `/validation/cases`, `/validation/bias` and `/validation/report` expose the pipeline; no sensitive traits are inferred.

**Provenance integrity (27 November 2026):** every knowledge record now declares `provenance_kind`; illustrative fixtures are explicitly excluded from validation. `corpus_readiness()` and `/validation/corpus-readiness` report whether licensed records (not fixtures) are available. A corpus manifest template and `hbi_validation_check.py` support licensed-corpus acquisition and honest reporting. The current check reports **not_validated** with `insufficient_real_backtest_cases` — no scientific validation is claimed without real evidence.

**Translation and research lab (27 November 2026):** `translation.py` provides local-first model translation (local model preferred, hosted optional) with original-text preservation, language/script detection, cultural tagging and cross-lingual claim comparison. `research_lab.py` implements consented studies: ethics approval required for human participants, pseudonymous response storage, consent-scope enforcement, withdrawal and deletion. `iam.hbi.*` bindings exist in both the Python and TypeScript SDKs.

**Free-source development (27 November 2026):** `open_sources.py` ingests metadata from free official APIs (OpenAlex, Crossref, Europe PMC, Semantic Scholar, Wikidata, DOAJ, CORE, Internet Archive) through the normal provenance gate; `synthetic.py` generates IAM-owned behavioural scenarios, explicitly excluded from empirical validation. Development no longer waits on external approvals; those remain governance gates at activation time.

**Not yet implemented:** acquisition of real licensed historical corpora, deep models for source grading and language detection, and actual studies with real participants (the lifecycle exists; no study has been run). Prediction requires **both** A8 context approval and explicit model validation; either failure returns a structured refusal. The full local backend suite still has one unrelated environment failure (`test_ownerauth_reconciliation` → blocked `_xxhash` DLL); CI runs on Ubuntu and is unaffected.

**Governance and human protection (26 November 2026):** dual-use review gate, structured DPIA input and human-oversight gate are implemented and documented in §18; consequential decisions are always referred to an accountable human.

**Deployment gate (26 November 2026):** `deployment.readiness()` enforces acceptance gates, DPIA sign-off, dual-use review, SDK registration, migrations, durable audit and tested rollback; §19 records the prerequisites and rollback path. A no-go verdict blocks activation.

**Durable sign-off (26 November 2026):** DPIA sign-offs are persisted in `hbi_dpia_signoffs` (PostgreSQL) or the local-first record `data/dpia_signoffs.json`, and reloaded by the deployment gate. The owner recorded an approval as "IAM Owner" with basis "OD-45 confirmed; risks mitigated per Document 26 §18". `hbi_deployment_check.py --strict` now reports **HBI DEPLOYMENT READY** (exit 0); all acceptance gates pass, one approved sign-off is loaded, and no prohibited dual-use decisions exist. IAM did not self-approve: the sign-off followed explicit owner confirmation.

**Next:** acquire real licensed corpora, run the validation pipeline on them, then activate HBI behind existing IAM authority controls in the deployment environment and verify the readiness gate there. OD-45 is confirmed and recorded; the frozen register changed only by adding OD-45.

---

## 18. Governance, DPIA and human oversight (operational)

### 18.1 Dual-use review

Every new HBI capability passes `dual_use.review()` before deployment. `PROHIBITED` markers — influence content, targeting, individual profiling, sensitive inference, automated consequential decisions, criminality prediction, emotion-based decisions, deception and psychological warfare — block deployment outright and require redesign. `RESTRICTED` markers — emotion inference, aggregate forecasting, manipulation detection, historical group traits, individual interaction and propaganda detection — require verified controls such as defensive-use-only, no targeting, cultural context, k-anonymity, consent, retention limits and audit. Capability growth never expands permission automatically. Module 14 is classified RESTRICTED/defensive-only.

### 18.2 Data Protection Impact Assessment (technical input)

`/api/v1/hbi/governance/dpia` produces a structured technical input for an authorised reviewer. It records purposes observed in the audit log, four data tiers (T0 public research, T1 curated findings, T2 anonymous aggregates, T3 consented individual interaction), legal frameworks (POPIA for South African operations, GDPR and applicable AI regulation for European users), risks and mitigations:

| Risk | Control |
|------|---------|
| Sensitive-trait inference | Prohibited-marker gate and tier separation |
| Cultural generalisation | Cultural context engine and anti-generalisation caveats |
| Misuse for manipulation | Defensive-only dual-use review and safety stop |
| Unreliable prediction treated as fact | A8 uncertainty gate; probability/confidence separation |
| Unauthorised individual profiling | No scraped profiles, scope gate, human oversight |

Residual risk is recorded as **medium pending reviewer sign-off**. The output is explicitly **not legal advice or clearance**; an authorised reviewer must sign off before production.

### 18.3 Human oversight procedure

1. `oversight.check()` classifies the decision type. Consequential types — employment, financial eligibility, access rights, safety status, legal status, insurance, housing, education admission — always return `automated_decision_permitted: false` and `human_review_required: true`.
2. HBI supplies an evidence packet: analysis, probability, confidence, uncertainty, alternatives and an explicit requirement for disconfirming evidence.
3. An authorised human decision-maker remains accountable. IAM never independently decides a person's employment, financial eligibility, access rights, safety status or similar significant outcome from behavioural predictions.
4. Non-consequential requests receive `analysis_only`; no automated consequential decision exists anywhere in HBI.
5. Every oversight check and dual-use review is written to the HBI audit trail.

### 18.4 Confirmation boundaries

The owner confirmed OD-45 with the eight items in §16. No later capability, corpus, model or endpoint may relax these boundaries without a further owner decision. Individual-level prediction, consequential automated decisions, targeted influence and sensitive-trait inference remain prohibited.

---

## 19. Production deployment gate

Activation is a **no-go until all blockers are cleared**; IAM cannot self-approve deployment.

| Prerequisite | Verification |
|--------------|--------------|
| Acceptance gates pass | `POST /api/v1/hbi/acceptance/run` — all §11.7 gates green |
| DPIA reviewed and signed | `POST /api/v1/hbi/governance/dpia/signoff` with an authorised reviewer, decision and basis |
| No prohibited dual-use decisions | Audit log contains no `PROHIBITED` dual-use outcome |
| SDK interface registered | `iam.hbi.*` present in the official Python SDK |
| Migrations applied | `029_hbi.sql`, `044_hbi_history_graph.sql`, `031_hbi_governance.sql`, or `create_all` at startup |
| Audit durable | API dependency commits knowledge and audit writes on success |
| Rollback tested | Previous model/knowledge versions restorable under OD-40 rules |

`POST /api/v1/hbi/governance/deployment/readiness` returns `ready` plus concrete blockers. Sign-offs are durable in `hbi_dpia_signoffs` (migration `031_hbi_governance.sql`) or, in local-first mode, `data/dpia_signoffs.json`; they survive restart and cannot be self-granted by IAM. `backend/tests/hbi_deployment_check.py` reports readiness in any environment and exits non-zero with `--strict` while blockers remain. A rejected DPIA, missing sign-off, prohibited capability or untested rollback is a hard no-go. Deployment proceeds behind IAM's existing authority and governance controls (OD-03/OD-11/OD-12); HBI does not create its own authority path.

**Rollback:** model versions are immutable in the registry (E9); knowledge revisions retain superseded versions (A7); the safety stop disables prediction/aggregation without disabling research or understanding.

---

## 20. Corpus acquisition and validation runbook

No scientific validation is claimed until licensed evidence is acquired. The local check currently reports `not_validated` with `insufficient_real_backtest_cases`.

1. **Obtain licensed material.** Only sources with a recorded licence and a permitted purpose of `research`, `historical` or `aggregate_analysis` may be ingested. Respect platform terms, copyright, privacy law and research consent. Do not scrape identifiable people or infer sensitive traits.
2. **Write a manifest** using `backend/app/services/hbi/data/corpus_manifest.example.json` as the template. Each entry needs the full source, licensing, permitted purposes, lawful basis, privacy and governance blocks defined in §21.
3. **Review and ingest** via `POST /api/v1/hbi/knowledge/corpus/review` (optional, for a single source) and `POST /api/v1/hbi/knowledge/corpus/ingest` with `manifest_path` and optional `root`. Only `approved` sources are ingested; records are written as `provenance_kind: licensed_corpus`, and `rejected` or `pending` material is quarantined.
4. **Add dated outcomes** for validation case derivation where legitimately available: `context_dimensions.time` (information available at cutoff) and `context_dimensions.outcome.observed_at` plus `outcome.value` (0/1). Cases without both dates and a verified evidence grade are excluded.
5. **Check readiness** with `GET /api/v1/hbi/validation/corpus-readiness` — at least 10 licensed records are required.
6. **Run validation** with `GET /api/v1/hbi/validation/report?model_id=...` and `python backend/tests/hbi_validation_check.py --strict`. The verdict is `validated` only if there are ≥10 real cases, Brier ≤0.30, ECE ≤0.20 and no group disparity >0.15.
7. **Record the result** in the Evaluation Service and model registry; promote only through the existing approval and rollback gates. Failed or degraded validations are retained as learning assets.

Illustrative fixtures in `data/backtest_library.json` are for pipeline testing only and are explicitly excluded from validation. Repository-level findings about this implementation are recorded in `tools/rkie/notes/hbi-implementation.md` (untrusted historical context; re-verify before reuse).

---

## 21. Fail-closed corpus ingestion policy

Public accessibility is **not** permission. Every source has its own manifest record and passes six checks before entering the approved research corpus: licence verification, purpose verification, provenance verification, privacy and lawful-basis verification, restriction verification, and approval with an auditable reason.

| Outcome | Meaning |
|---------|---------|
| `approved` | All required checks passed; source enters the approved corpus |
| `rejected` | A legal or policy restriction was violated |
| `pending` | Evidence or verification is incomplete; quarantined, not usable |

Only `research`, `historical` and `aggregate_analysis` are accepted purpose identifiers. `manipulation`, `personal_use_only` where broader ingestion is not permitted, and any undocumented or unapproved purpose are rejected. Copyright/licensing permission and POPIA/GDPR lawful basis are independent requirements — satisfying one never satisfies the other.

Additional safeguards: licence compatibility is checked separately for ingestion, storage, analysis and model training (research permission does not authorise training); expiry and revocation are tracked; licence documents, permission records and validation decisions are preserved; unvalidated sources stay outside the approved corpus; restricted sources can be removed and reprocessed; and audit history records who approved a source, when, and which rules were applied.

The three corpus states are `not_validated`, `validated` and `restricted`. Validation derives backtest cases only from approved licensed sources; a restricted or unapproved source is excluded. Endpoints: `POST /knowledge/corpus/review`, `GET /knowledge/corpus/state`, `GET /knowledge/corpus/audit`, `POST /knowledge/corpus/restrict`. The manifest template is `data/corpus_manifest.example.json`.

---

## 22. Operational lifecycle

- **Drift monitoring** — `/api/v1/hbi/lifecycle/drift` groups dated records by decade and flags a confidence drop of ≥0.20 between the earliest and latest periods. Drift is a re-evaluation trigger, not proof a model is wrong.
- **Re-evaluation planning** — `/api/v1/hbi/lifecycle/re-evaluation` lists registered models that are unvalidated, backed by <10 cases, or affected by drift. Tasks never auto-promote a model.
- **Rollback drill** — `POST /api/v1/hbi/lifecycle/rollback-drill` promotes a temporary version and verifies that rollback restores the active model. Failed versions remain in immutable registry history (E9).

---

## Appendix A — Module index (38)

**D1:** 1 Psychology · 2 Personality · 3 Emotional · 4 Cognitive · 24 Human Evolution · 25 Developmental Psychology.  
**D2:** 5 Motivation · 6 Decision · 7 Habit and Learning · 29 Economic Behaviour · 30 Crisis Behaviour · 34 Information Behaviour.  
**D3:** 8 Communication · 9 Interpersonal · 10 Social Dynamics · 31 Leadership Psychology · 32 Trust and Reputation · 37 Conflict Resolution.  
**D4:** 11 Group Behaviour · 12 Crowd and Society · 26 Cross-Cultural · 28 Geopolitical Behaviour · 33 Collective Intelligence · 35 Technological Adaptation · 36 Intergenerational · 38 Behavioural Resilience.  
**D5:** 16 Historical Research · 17 Historical Behaviour Analysis · 18 Historical Psychology · 19 Historical Social Dynamics · 20 Historical Decision · 21 Historical Conflict and Cooperation · 22 Historical Patterns and Trends · 23 Historical Forecasting · 27 Historical Civilisation.  
**D6:** 13 Behavioural Forecasting · 14 Psychological Threat and Manipulation · 15 Behavioural Learning and Evaluation — plus capabilities A1–A8.

## Appendix B — Engine index (13)

E1 Historical Knowledge Graph · E2 Temporal Intelligence · E3 Evidence Verification · E4 Source Reliability · E5 Multilingual Research · E6 Cultural Context · E7 Causal Discovery · E8 Behavioural Simulation Laboratory · E9 Predictive Model Registry · E10 Intelligence Benchmarking · E11 Contradiction Detection · E12 Knowledge Gap Detection · E13 Historical Chronology.

## Appendix C — Advanced capability index (A1–A8)

A1 Self-directed research · A2 Scientific theory comparison · A3 Independent hypothesis generation · A4 Historical-to-modern comparison · A5 Predictive self-evaluation · A6 Cross-disciplinary reasoning · A7 Knowledge evolution · A8 Uncertainty intelligence.

## Appendix D — Implementation specification index (§6.1–6.14)

Data schemas · Historical event/timeline schemas · Ingestion/document processing · Licensing/provenance · Training/evaluation pipelines · Prediction API contracts · Inter-module communication · Persistent memory/retrieval · Local model integration · Resource management/scaling · Security/access control · Privacy/consent enforcement · Automated testing/gates · Versioning/rollback/monitoring.

## Appendix E — Canonical reference map (orientation only; verify at ingestion)

Friston, Barrett, Schultz, Sutton & Barto, Baddeley, Loftus · Simon, Kahneman & Tversky, Kunda · Thaler, Laibson, Fehr & Schmidt, Banerjee, Bikhchandani et al. · Russell, Gross, Fredrickson, Wilson & Gilbert · Goldberg, Digman, Ashton, Mischel, Caspi & Moffitt · Asch, Milgram, Deutsch & Gerard, Tajfel & Turner, Janis, Granovetter, Watts, Barabási & Albert, Centola · Hofstede, Schwartz, Inglehart–Welzel, Geertz, Henrich et al. · Piaget, Vygotsky, Erikson, Baltes, Bowlby · Austin, Searle, Grice, Brown & Levinson, Entman, Shannon · Edmondson, Tajfel, Altman, Walton & McKersie · Forrester, Epstein, Holland · Pearl, Rubin, Angrist & Krueger, Card & Krueger, Imbens & Wooldridge, Checkel · Braudel, Guha, Said, Turchin, Goldstone, Fearon, Tetlock, Jervis · Rogers (diffusion), Open Science Collaboration, Ioannidis, Nosek et al. All claims are verified against current literature at ingestion.

*End of master specification. Supersedes v1.0 of this document.*
