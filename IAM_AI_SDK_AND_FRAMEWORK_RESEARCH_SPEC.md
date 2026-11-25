# IAM — AI SDK, Framework and Model Research and Integration Specification

**Document:** 20 (addendum to Documents 01–19)  
**Version:** 1.0 · 25 November 2026  
**Status:** FROZEN — confirmed part of IAM architecture (owner confirmation 25 November 2026)  
**Parent:** `IAM_MASTER_ARCHITECTURE.md`  
**Related:** `canonical/IAM_DOC_02_INTELLIGENCE_EVOLUTION.md`, `IAM_DISTRIBUTED_ARCHITECTURE.md` §8 (OEDIE), `IAM_AI_ASSISTANT_INTEROPERABILITY_SPEC.md` (Doc 12), `IAM_DEVELOPER_SDK_AND_CLI_SPEC.md` (Doc 13), `IAM_MASTER_ARCHITECTURE.md` §3, `IAM_OWNER_DECISIONS.md`  
**Confirmed decision:** OD-36 (AI SDK, framework and model research and integration)

---

## 1. Scope and relationship to existing architecture

This document formalises an **AI Research and SDK Learning Programme** inside IAM's existing Autonomous Research and Learning Engine, Model Independence and Evolution Engine and Self-Development Engine. It extends OEDIE (Doc 05 §8), which already governs general free-tool discovery; it does not create a new top-level system.

The initial shortlist in §2 is a starting point, **not a permanent technology restriction**. IAM remains free to discover better tools, including technologies that do not yet exist. Learning a technology is not the same as adopting it, and adopting a tool is not the same as changing IAM.

---

## 2. Initial research priorities

| Technology | Role in IAM |
|------------|-------------|
| Vercel AI SDK | TypeScript AI integration, streaming and tools |
| PydanticAI | Python agent development |
| LangGraph | Stateful, long-running agent workflows |
| Ollama | Local model execution |
| LiteLLM | Multiple model providers and routing |
| MCP SDK | External tool and data connections |
| LlamaIndex | Knowledge ingestion and retrieval |
| pgvector | Persistent semantic memory within PostgreSQL |
| Hugging Face Transformers | Model research, experimentation and development |
| Promptfoo | AI evaluation, security testing and red-teaming |

LangGraph, LiteLLM, Ollama and pgvector are already in IAM's technology baseline (Master Architecture §3); the programme studies their versions, alternatives and migration paths rather than re-deciding the baseline.

---

## 3. Additional technologies to study

- **Agent frameworks:** CrewAI, Agno, smolagents, CAMEL-AI, Letta, DSPy, Strands.
- **AI frameworks:** Haystack, Semantic Kernel, Genkit, Mastra, Microsoft Agent Framework.
- **Local inference:** llama.cpp, LocalAI, vLLM, SGLang.
- **Knowledge systems:** Qdrant, Chroma, Weaviate, Milvus, Graphiti, Neo4j.
- **AI evaluation:** DeepEval, Giskard, Arize Phoenix, TruLens, Guardrails AI.

IAM must not install everything. It evaluates each technology and selects the smallest combination that provides the required capability.

---

## 4. The programme

1. Discover new AI SDKs, frameworks, models and research projects.
2. Read official documentation and inspect permitted source code.
3. Understand how different AI systems and frameworks work.
4. Compare capabilities, licensing, hardware requirements and costs.
5. Experiment in isolated development environments.
6. Benchmark different frameworks and models.
7. Learn to integrate compatible technologies.
8. Reproduce useful capabilities independently where licensing permits.
9. Maintain a catalogue of technologies, versions, limitations and migration paths.
10. Recommend improvements to IAM's own architecture.
11. Share validated, non-private findings with trusted IAM nodes.
12. Submit protected-core changes for creator approval.

---

## 5. Learning versus changing IAM

This is a permanent architectural rule:

- **Learning** — IAM may independently study any technology and understand how it works.
- **Capability acquisition** — IAM may test and integrate approved tools within its existing permissions.
- **Core modification** — changes to IAM's protected identity, constitution, architecture and security mechanisms remain under the Creator's authority (OD-03, OD-11, OD-19).

No external SDK or framework may redefine IAM's identity or security. External code is untrusted until reviewed; no executable code is auto-installed from peers or unverified packages.

---

## 6. Technology Capability Registry

For every SDK, framework, model or runtime discovered, IAM records:

| Field | Content |
|-------|---------|
| Identity | Name, version and official source |
| Platform | Programming language and supported architectures (ARM64 / x86-64) |
| Licence | Licence and commercial-use permissions; attribution obligations |
| Cost status | Free, open-source, paid or mixed; what is actually free |
| Requirements | Hardware, memory, dependencies and resource footprint |
| Capabilities | What it does and what it does not do |
| Limitations | Known constraints, maturity and failure modes |
| Security/maintenance | Maintenance status, known vulnerabilities, supply-chain trust |
| Compatibility | Fit with IAM's stack and migration cost |
| Evidence | Test results, benchmarks and reproduction notes |
| Lifecycle state | `researched` · `tested` · `approved` · `integrated` · `deprecated` · `rejected` |

This prevents repeated research on the same technology and allows outdated dependencies to be replaced safely. The registry is distinct from the capability registry for IAM's own abilities.

---

## 7. Evaluation method

- Obtain packages from trusted sources; pin versions; verify signatures/hashes where available.
- Test in an isolated development environment with no production credentials (OD-10).
- Benchmark against a defined baseline; record method, environment and date.
- Verify licence and commercial-use terms; verify actual cost, not advertised cost.
- Check ARM64 and x86-64 behaviour separately (OD-22, Doc 08).
- Record migration paths and rollback before integration.
- Only then request approval for integration or protected-core change.

---

## 8. Independence and sharing

- Validated, non-private findings may be shared with trusted IAM nodes (OD-12, OD-26).
- Credentials, private memories, protected-core material and unverified claims are never shared.
- No dependency on any single vendor, SDK or framework; alternatives are maintained for critical functions.
- Findings are evidence with provenance and confidence, never instructions to follow blindly (Doc 14 §1).

---

## 9. Hard boundaries

- **Free SDKs do not mean free model inference or hosting.** IAM continues applying its free-resource policy (OD-15) and never silently activates paid services.
- Free trial, credit or promotional access is never treated as a permanent entitlement (Doc 05 §8.1).
- No bypass of quotas, licence restrictions or provider terms.
- No protected-core change without signed creator approval (OD-11).
- No auto-execution of untrusted code; isolated testing only.
- Research does not become user-facing functionality without a separate decision.

---

## 10. Acceptance criteria

1. Each technology has a Technology Capability Registry entry with licence, cost status, architecture support, evidence and lifecycle state.
2. All experiments occur in an isolated environment with no production credentials or paid activation.
3. Learning, capability acquisition and core modification are recorded as distinct events.
4. No protected-core change occurs without creator authorisation.
5. No paid inference, hosting or service is activated silently; free-resource policy is enforced.
6. Findings are validated before being shared with trusted nodes; private or unverified material is never shared.
7. The programme extends OEDIE and existing research engines without creating a new top-level system.
8. The initial shortlist remains revisable; new and future technologies can be added.
9. No single SDK, framework or provider becomes a mandatory dependency for IAM's identity, memory or operation.
