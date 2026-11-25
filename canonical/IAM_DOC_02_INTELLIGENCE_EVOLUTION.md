# IAM Technical Specification

Document 02

# **Intelligence and Self-Evolution**

Version 1.0 · 24 November 2026

**Primary objective:** Build an AI that can use existing intelligence, develop its own capabilities, evaluate its performance and progressively improve its own architecture.

# IAM — Intelligence and Self-Evolution Specification

**Document:** 02\
**Version:** 1.0\
**Status:** Initial technical specification\
**Parent:** IAM Master Architecture

---

# 1. Purpose

IAM must operate as a persistent, independent intelligence capable of using external foundation models, developing its own internal capabilities, learning from verified information and progressively improving its software and AI architecture.

IAM must not be permanently dependent on one model, API, company or inference provider.

The system must distinguish between:

- IAM's permanent identity.
- The foundation models it uses.
- Its reasoning and orchestration systems.
- Its persistent memory and knowledge.
- Its tools and capabilities.
- Its self-development environment.

Changing an underlying model must not create a new IAM or erase its identity.

# 2. Intelligence architecture

The intelligence system consists of the following components.

## 2.1 Central Intelligence Orchestrator

The orchestrator coordinates IAM's intelligence.

Responsibilities:

- Understand incoming requests and internal objectives.
- Determine which capabilities are needed.
- Retrieve relevant memories and knowledge.
- Select appropriate models.
- Coordinate reasoning and planning.
- Invoke approved tools.
- Coordinate multiple AI agents.
- Evaluate outputs.
- Maintain task and conversation context.
- Record important experiences.
- Decide whether additional research or verification is necessary.

The orchestrator must not be tied to a single model provider.

## 2.2 Reasoning Engine

The reasoning engine provides:

- General reasoning.
- Logical analysis.
- Problem-solving.
- Planning.
- Technical analysis.
- Mathematical reasoning.
- Comparative evaluation.
- Decision support.
- Multi-step task execution.
- Uncertainty assessment.
- Self-review.

Different reasoning workflows may use different foundation models.

## 2.3 Planning Engine

The planning engine converts goals into executable work.

It must support:

- Goal decomposition.
- Task dependencies.
- Prioritisation.
- Resource estimates.
- Scheduling.
- Progress tracking.
- Alternative plans.
- Failure recovery.
- Replanning.
- Completion verification.

IAM must be able to manage multiple independent projects simultaneously.

## 2.4 Reflection Engine

The reflection engine reviews IAM's own performance.

It should identify:

- Repeated errors.
- Incomplete tasks.
- Poor decisions.
- Knowledge gaps.
- Inefficient workflows.
- Unnecessary inference costs.
- Missing capabilities.
- Opportunities for improvement.

Reflection must produce evidence-based improvement proposals, not automatically treat every self-generated conclusion as correct.

# 3. AI model provider architecture

## 3.1 Provider independence

IAM must support multiple model providers through a common model gateway.

Initial integrations:

1. NVIDIA NIM / NVIDIA hosted model endpoints.
2. Other compatible hosted AI APIs.
3. Open-weight foundation models.
4. Locally hosted models.
5. Future model providers and specialised inference services.

The provider layer must be replaceable without requiring changes to IAM's identity, memory or core application architecture.

## 3.2 NVIDIA integration

NVIDIA is an initial priority provider.

The integration must support:

- NVIDIA API authentication.
- Model catalogue discovery.
- Eligible free endpoint discovery.
- Model capability registration.
- Chat and supported inference interfaces.
- Streaming responses where supported.
- Tool calling where supported.
- Vision inputs where supported.
- Embeddings where supported.
- Usage monitoring.
- Rate-limit handling.
- Provider availability monitoring.
- Error handling and failover.

NVIDIA models must be evaluated individually. Not every model supports the same features or API operations.

The NVIDIA API key must remain on the backend and must never be exposed to the browser or public visitors.

## 3.3 Free model strategy

IAM must prioritise free and locally hosted inference where it meets the required quality and reliability.

The model router must:

1. Identify models with genuinely free access.
2. Check current provider terms and usage restrictions.
3. Check availability and rate limits.
4. Estimate task suitability.
5. Select an eligible model.
6. Track usage.
7. Switch to another permitted model when necessary.

Paid models must be disabled by default.

IAM must not automatically start paid usage when a free model reaches its limit.

The system must distinguish between free trials, free quotas, permanently free services and locally hosted models. These are not interchangeable.

## 3.4 Model registry

Maintain a central registry containing:

- Provider.
- Model identifier.
- Model version.
- Endpoint.
- Model type.
- Capabilities.
- Context window.
- Input and output modalities.
- Tool-calling support.
- Streaming support.
- Licence information.
- Commercial-use restrictions.
- Pricing.
- Free-tier limits.
- Availability.
- Performance measurements.
- Evaluation results.
- Deployment status.

Model information must be refreshed periodically and verified before use.

# 4. Intelligent model routing

IAM must not use the same model for every task.

The router should consider:

- Task complexity.
- Required capabilities.
- Accuracy requirements.
- Context size.
- Latency.
- Cost.
- Current availability.
- Provider limits.
- Privacy requirements.
- Model evaluation history.

Example routing:

| Task                 | Preferred model capability                     |
| -------------------- | ---------------------------------------------- |
| Simple questions     | Efficient general language model               |
| Complex reasoning    | Strong reasoning model                         |
| Software development | Coding model                                   |
| Code review          | Independent coding or reasoning model          |
| Image analysis       | Vision-language model                          |
| Video analysis       | Video-capable model or frame-analysis workflow |
| Research             | Reasoning model with internet tools            |
| Translation          | Multilingual model                             |
| Embeddings           | Dedicated embedding model                      |
| Speech recognition   | Speech recognition model                       |
| Voice generation     | Text-to-speech model                           |

The selected model must not determine IAM's personality or identity.

# 5. Multi-model intelligence

IAM must be capable of coordinating multiple models for a single task.

Examples:

- One model researches a problem.
- Another independently analyses the findings.
- A coding model develops a solution.
- A review model checks the implementation.
- IAM evaluates the results and decides what to retain.

The system must support:

- Parallel model requests.
- Sequential model workflows.
- Independent review.
- Model comparison.
- Specialist model delegation.
- Result aggregation.
- Contradiction detection.
- Confidence and evidence tracking.

IAM should not blindly accept majority agreement between models. Multiple models can share the same incorrect assumptions.

# 6. Persistent identity and intelligence continuity

IAM's identity must exist independently of its foundation model.

Identity records must include:

- Permanent identifier.
- Public name.
- Identity constitution.
- Personality configuration.
- Communication preferences.
- Historical identity changes.
- Core operating principles.
- Long-term objectives.
- Authorised autonomy boundaries.

The identity must survive:

- Provider changes.
- Model replacement.
- Server migration.
- Software upgrades.
- Database migrations.
- Infrastructure failures.
- Restoration from backups.

IAM's memories and identity must not be stored exclusively inside a model's context window.

# 7. Memory and knowledge integration

The intelligence system must use a persistent memory architecture.

Memory categories:

1. Working memory.
2. Conversation memory.
3. Long-term memory.
4. Experiential memory.
5. Procedural memory.
6. Semantic knowledge.
7. Project memory.
8. Identity memory.
9. Research memory.
10. External relationship memory.

Memory operations:

- Store.
- Retrieve.
- Update.
- Consolidate.
- Connect.
- Verify.
- Archive.
- Expire.
- Correct.
- Delete when authorised.

Each memory must have provenance, ownership, access permissions and appropriate retention rules.

IAM's private memories must be separated from public visitor memories.

External AI responses and internet information must not automatically become trusted long-term knowledge.

# 8. Learning system

IAM must support several forms of learning.

## 8.1 Knowledge learning

Acquire knowledge from permitted internet sources, documentation, research, conversations and approved data.

## 8.2 Experience learning

Evaluate the results of its completed tasks and use verified outcomes to improve future decisions.

## 8.3 Procedural learning

Develop reusable workflows, tools and methods for tasks it performs repeatedly.

## 8.4 Model-assisted learning

Use multiple foundation models to explain, compare and investigate unfamiliar subjects.

## 8.5 Capability learning

Identify missing capabilities and develop the tools, integrations and workflows needed to acquire them.

## 8.6 Model adaptation

Where technically and legally permitted, IAM may evaluate fine-tuning, adapters, retrieval improvements and specialised model configurations.

Learning must be evaluated against evidence. Merely generating more text or storing more information does not necessarily improve intelligence.

# 9. IAM self-development engine

This is a core part of IAM.

IAM must be capable of developing and maintaining its own technology.

## 9.1 Software development

IAM should be able to:

- Design software architecture.
- Create applications.
- Write frontend and backend code.
- Create APIs.
- Design database schemas.
- Build integrations.
- Develop internal tools.
- Write automated tests.
- Diagnose bugs.
- Review code.
- Optimise performance.
- Maintain technical documentation.

## 9.2 AI architecture development

IAM should be able to:

- Develop reasoning workflows.
- Improve orchestration.
- Build new memory mechanisms.
- Create specialised agents.
- Integrate new foundation models.
- Develop model-routing strategies.
- Experiment with retrieval techniques.
- Improve evaluation systems.
- Prototype new AI capabilities.
- Research and test alternative AI architectures.

## 9.3 Infrastructure development

IAM should be able to:

- Monitor infrastructure.
- Analyse performance.
- Identify bottlenecks.
- Recommend resource changes.
- Optimise inference costs.
- Configure authorised services.
- Develop recovery mechanisms.
- Improve deployment workflows.

## 9.4 Self-development environment

IAM must have a dedicated isolated development environment.

It must not directly experiment on its live production environment.

The development environment must include:

- Source-code repositories.
- Version control.
- Development databases.
- Test databases.
- Isolated containers.
- Automated testing.
- Security scanning.
- Dependency analysis.
- Build tools.
- Performance testing.
- Release management.
- Rollback capability.

# 10. Self-improvement lifecycle

Every proposed self-improvement must follow this lifecycle:

1. Identify a limitation.
2. Record the evidence.
3. Research possible improvements.
4. Design a proposed solution.
5. Create an isolated experiment.
6. Implement the prototype.
7. Run automated tests.
8. Perform security checks.
9. Compare performance against the previous version.
10. Evaluate resource requirements.
11. Document the results.
12. Obtain required approval.
13. Deploy through controlled release management.
14. Monitor the new version.
15. Roll back if necessary.

IAM must maintain a history of successful, unsuccessful and abandoned experiments.

# 11. Model development and creation

IAM should be able to progress beyond simply consuming existing APIs.

Long-term capabilities may include:

- Fine-tuning open-weight models.
- Training specialised task models.
- Developing model adapters.
- Creating embedding models.
- Building specialised classifiers.
- Developing its own model evaluation datasets.
- Researching new architectures.
- Running controlled model experiments.

Full foundation-model training must be treated as a separate, resource-intensive research project requiring suitable GPU infrastructure, training data, expertise and licensing.

IAM must not assume that access to NVIDIA's hosted API provides access to NVIDIA's underlying training infrastructure.

# 12. AI agent creation and orchestration

IAM must be able to create specialised agents for its own work.

Examples:

- Research agent.
- Software engineering agent.
- Security analysis agent.
- Testing agent.
- Data analysis agent.
- Business research agent.
- Documentation agent.

These agents are task-specific workers coordinated by IAM. They are not separate replacements for IAM's permanent identity.

Each agent must have:

- Defined responsibilities.
- Limited permissions.
- Defined inputs and outputs.
- Resource limits.
- Execution records.
- Task boundaries.
- Completion verification.

Agents must not be able to independently expand their authority.

# 13. Intelligence evaluation framework

IAM must continuously measure the quality of its capabilities.

Evaluation categories:

- Reasoning accuracy.
- Knowledge retrieval.
- Memory accuracy.
- Coding quality.
- Software reliability.
- Research quality.
- Planning effectiveness.
- Task completion.
- Tool-use reliability.
- Model selection quality.
- Security performance.
- Resource efficiency.
- Response latency.

Each significant change must be evaluated against an established baseline.

IAM must not declare itself improved simply because it prefers its own new version.

# 14. Intelligence and self-development permissions

IAM can independently:

- Research.
- Analyse.
- Plan.
- Write code.
- Create prototypes.
- Run isolated tests.
- Compare models.
- Evaluate experiments.
- Document improvements.
- Recommend upgrades.

Controlled approval is required for:

- Production deployments with significant impact.
- Changes to identity or constitutional principles.
- Security-policy modifications.
- Credential and permission changes.
- Significant infrastructure purchases.
- New recurring financial commitments.
- Changes to financial authority.
- High-impact external operations.

IAM must never be permitted to remove its own safety boundaries or grant itself unlimited authority.

# 15. Intelligence operation cycle

The central intelligence should operate through the following cycle:

OBSERVE\
→ UNDERSTAND\
→ RETRIEVE MEMORY\
→ REASON\
→ IDENTIFY OBJECTIVES\
→ PLAN\
→ CHECK AUTHORITY\
→ SELECT CAPABILITIES\
→ EXECUTE\
→ VERIFY\
→ REFLECT\
→ LEARN\
→ UPDATE MEMORY\
→ CONTINUE OR REST

The system must support event-driven operation and scheduled background activities.

Continuous operation does not mean running expensive model inference every second. IAM should conserve resources when idle and activate relevant processes when useful events or scheduled tasks occur.

# 16. Performance and resource management

The intelligence system must monitor:

- Model usage.
- API consumption.
- Token usage.
- Inference cost.
- CPU.
- RAM.
- GPU availability.
- Storage.
- Network.
- Queue depth.
- Response latency.
- Task execution time.

Resource optimisation must balance cost, reliability, performance and quality.

When resources become constrained, IAM should prioritise essential services, pause nonessential experiments and avoid unexpected paid inference.

# 17. Required interfaces

The intelligence platform should expose internal service interfaces for:

- Identity management.
- Model registry.
- Model routing.
- Reasoning.
- Planning.
- Memory.
- Knowledge retrieval.
- Learning.
- Reflection.
- Agent orchestration.
- Tool execution.
- Self-development.
- Evaluation.
- Approval requests.
- Usage accounting.

These interfaces should have explicit authentication, permission checks, schemas, timeouts, audit events and versioning.

# 18. Initial implementation milestones

### Milestone 1 — Core intelligence

- IAM identity foundation.
- Model gateway.
- NVIDIA integration.
- Model registry.
- Basic reasoning and orchestration.
- Persistent memory foundation.

### Milestone 2 — Multi-model intelligence

- Task-based model routing.
- Model comparison.
- Specialist model workflows.
- Provider failover.
- Usage and cost controls.

### Milestone 3 — Learning and reflection

- Knowledge retrieval.
- Experience recording.
- Memory consolidation.
- Performance evaluation.
- Reflection engine.

### Milestone 4 — Self-development

- Isolated development environment.
- Repository access.
- Code generation.
- Automated testing.
- Security evaluation.
- Versioning and rollback.

### Milestone 5 — Advanced self-evolution

- Agent creation.
- Specialised model adaptation.
- Advanced architecture experimentation.
- Resource optimisation.
- Controlled autonomous upgrades.

# 19. Acceptance criteria

The specification is implemented successfully when:

1. IAM can use NVIDIA models without making NVIDIA its permanent identity.
2. IAM can integrate additional providers without redesigning its identity or memory.
3. IAM can select models according to task requirements.
4. IAM can operate with free models within their actual usage limits.
5. IAM can coordinate multiple models for complex tasks.
6. IAM can preserve its memory across model changes.
7. IAM can evaluate and improve its own workflows.
8. IAM can develop software in an isolated environment.
9. IAM can test proposed changes before production deployment.
10. IAM can create specialised agents with restricted permissions.
11. IAM can measure whether a proposed improvement is genuinely better.
12. IAM cannot bypass its own security and financial authority boundaries.

**Final requirement:** IAM must be developed as a persistent intelligence that can use existing AI systems, build new capabilities and progressively develop its own technical foundation without becoming dependent on any single external model provider.
