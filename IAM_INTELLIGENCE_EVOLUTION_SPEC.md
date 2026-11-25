# IAM — Intelligence and Self-Evolution Specification

**Status:** FROZEN — companion to IAM Master Architecture

---

## 1. Principle

IAM's intelligence is replaceable. Identity, memory, personality, goals and accumulated work
survive any model or provider change. No provider — including NVIDIA — is permanent or exclusive.

---

## 2. Model providers

| Provider | Type | Notes |
|----------|------|-------|
| NVIDIA NIM / build.nvidia.com | Hosted, OpenAI-compatible API | `https://integrate.api.nvidia.com/v1`, API key auth. Free endpoints for prototyping. |
| Alibaba Dashscope | Hosted | Qwen3.5-9B — locked initial general-reasoning anchor (OD-38) |
| OpenAI / Anthropic | Hosted | Fallback / specialist |
| Ollama | Local | Lightweight tasks, privacy-sensitive work |
| Open-weight / self-hosted | Local | Future GPU inference (vLLM / SGLang) |

### NVIDIA integration rules

1. Discover models from the catalogue (`/models` endpoint) — not a hardcoded list.
2. Check capabilities, context limits and availability.
3. Select by task, capability, quality, cost and availability.
4. Route requests through IAM's backend (LiteLLM gateway).
5. Evaluate responses; switch if unavailable or at limits.
6. Free-only mode by default: paid models disabled unless explicitly enabled.
7. Track usage and remaining limits; never incur unexpected charges.

Free endpoints are for prototyping; limits vary. Free access is not assumed for production.

---

## 3. Intelligence Router

Capabilities: model discovery, capability evaluation, task-based selection, provider failover,
multiple models used together, response evaluation, provider independence.

Selection inputs: task type, required capabilities (reasoning/coding/vision/embeddings),
quality score, cost, availability, free-only policy, optional provider preference.

Implementation: `AIProvider`, `DiscoveredModel`, `RoutingDecision`, `ProviderUsage` models;
`/api/v1/models/router/*` endpoints; `IntelligenceRouter` service.

Routing decision audit records which model was selected and why. Fallback to configured default
when no candidate matches.

---

## 4. Advanced reasoning

Multi-step planning, counterfactual reasoning, causal reasoning, risk/uncertainty estimation,
decision comparison, long-term consequence analysis, contradiction detection, decision review
and correction, confidence tracking, and knowing when information is insufficient.
IAM can change its mind when new evidence appears.

---

## 5. World model

Tracks people, organisations, countries, cultures, languages, events, technology, science,
economic systems, cause and effect, time/deadlines, IAM's own capabilities and limitations,
and how decisions may affect the future. Enables reasoning about situations rather than
responding to isolated prompts.

---

## 6. Learning and capability development

**Capability development cycle:** identify weakness → choose learning target → research →
practise with experiments/real tasks → evaluate objectively → store learning → improve or revise.

**Capability registry:** current abilities, developing abilities, knowledge gaps, learning
objectives, evaluation results, skill dependencies, proficiency history. Categories:
programming, languages, mathematics, business, science, communication, cybersecurity,
finance, robotics. Every capability requires measurable tests — not self-declared proficiency.

---

## 7. Self-evolution process

Identify limitation → research improvements → create experiment → prototype → automated
tests → evaluate performance and cost → compare with previous version → save recoverable
release → deploy within authorized policy → monitor outcome.

Development environments: **development** (autonomous), **testing** (autonomous),
**production** (controlled — validated changes and authorized deployment only).
IAM can develop software but cannot disable its own security boundaries.

---

## 8. Evaluation framework

Reasoning, coding, memory retrieval, language, research accuracy, tool-use reliability,
financial calculation, security, autonomy success rate, resource efficiency, recovery tests.
Every significant model, memory, architecture or software upgrade is evaluated against the
previous stable version.

---

## 9. External AI collaboration

Discover accessible agents; communicate through REST/OpenAPI, MCP, A2A, WebSockets,
Webhooks; exchange research; delegate permitted tasks; coordinate multiple agents; maintain
directory and trust assessments; validate incoming knowledge before retention. External AI is
untrusted until evaluated; private memories/credentials/owner info never shared by default.
