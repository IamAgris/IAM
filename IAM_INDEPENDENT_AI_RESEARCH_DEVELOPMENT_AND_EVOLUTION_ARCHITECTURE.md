# IAM — Independent AI Research, Development and Evolution Architecture

**Status:** CONFIRMED — owner decision OD-41, 25 November 2026. Requirements frozen; no further subsystem proliferation.  
**Purpose:** One parent programme covering how IAM researches, designs, reproduces, trains, compresses, evaluates, protects, deploys and maintains its own models — from 512 MB / 2005-era legacy machines to larger general-purpose foundation models — without depending on a single external AI provider.  
**Integrates:** OD-36 (AI SDK/framework research), OD-38 (foundation model), OD-39 (resource manager), OD-40 (MEFE)  
**Child specifications:** `IAM_MODEL_EVOLUTION_AND_FINE_TUNING_SPEC.md`, `IAM_RESOURCE_AND_WORKLOAD_MANAGER_SPEC.md`, `IAM_FOUNDATION_MODEL_AND_INTELLIGENCE_SPEC.md`

> Scope note: this is a planning checklist, not a claim that these systems already exist. Research discoveries may extend it without creating a new subsystem for every technique.

---

## 1. Parent programme — 14 engines

| # | Engine | Responsibility |
|---|--------|----------------|
| 1 | MEFE — Model Evolution and Fine-Tuning Engine | Fine-tuning, continual learning, distillation, improvement |
| 2 | MicroMind — Ultra-Low-Resource AI | Tiny language models for 512 MB–1 GB and legacy hardware |
| 3 | Architecture Research Engine | New neural architectures, attention mechanisms, model design |
| 4 | Model Compression Laboratory | Quantisation, pruning, weight sharing, format experiments |
| 5 | Legacy Hardware Engine | Old CPUs, 32-bit compatibility, memory/performance optimisation |
| 6 | Model Training Infrastructure | Orchestration, distributed compute, interruption recovery |
| 7 | Dataset Intelligence Engine | Discovery, licensing, preparation, quality control, lineage |
| 8 | Model Reproduction Engine | Research reproduction, format conversion, architecture analysis |
| 9 | Model Evaluation Laboratory | Capability benchmarks, scientific validation, regressions |
| 10 | Adaptive Inference Engine | Hardware-aware loading, context and runtime optimisation |
| 11 | Neural-Symbolic Intelligence Engine | Compact models + external memory + deterministic reasoning |
| 12 | Distributed Intelligence Engine | Collaborative low-resource nodes, federated learning |
| 13 | Model Security and Integrity Engine | Training security, provenance, protected signed releases |
| 14 | Model Registry and Deployment Engine | Versioning, portability, distribution, rollback |

---

## 2. Research and architecture scope

- Neural architecture search; hypothesis generation; ablation testing; scaling-law research; data-mixture optimisation; token efficiency; catastrophic-forgetting prevention; model calibration; interpretability and mechanistic interpretability.
- Transformer, recurrent (RWKV), state-space (Mamba), RetNet, hybrid, mixture-of-experts and hierarchical architectures — benchmarked, not assumed.
- Tokenizer and language research: compact vocabularies, multilingual and morphologically rich languages (including isiZulu, isiXhosa, Sesotho, Setswana, Afrikaans), code-switching, normalisation, language identification, conversation-state compression.
- Advanced intelligence research: compositional, multi-step, causal, abstract, mathematical reasoning; structured knowledge; metacognition; uncertainty; error correction; continual adaptation; transfer learning. Evaluate independently of fluent output.

---

## 3. Data and training scope

- Dataset discovery, provenance, licensing, version control and lineage; consent/withdrawal workflows; PII detection; copyright assessment; synthetic-data verification; contamination analysis; deletion/retraining policies; backup and recovery.
- Training from scratch, fine-tuning, continued pretraining, teacher–student distillation, curriculum learning, dataset distillation, low-resource multilingual training.
- Distributed training, gradient accumulation/checkpointing, mixed precision, optimiser-state compression, interrupted-training recovery, sharding, scheduling, hardware-aware batching, reproducibility, experiment tracking, auto-hyperparameter optimisation and cost estimation.
- Prevent forgetting; measure how much data each capability actually needs.

---

## 4. Compression, legacy hardware and deployment

- Quantisation 8/4/3/2-bit, mixed precision, per-channel/group quantisation, weight clustering, structured/unstructured pruning, layer reduction, embedding/vocabulary compression, activation optimisation, weight sharing, selective precision. Smaller files do not automatically mean faster inference on old CPUs.
- 32-bit addressing limits; SSE/SSE2 detection and no-SIMD fallback; CPU-specific compilation; cache-aware and aligned algorithms; memory mapping and HDD-aware loading; integer/fixed-point inference; custom quantised matmul; single-core and multithreaded paths; power/thermal optimisation.
- Compatibility profiles: Pentium III/4, early Athlon, 32-bit and 64-bit x86, ARM, 512 MB/1 GB/2 GB RAM, HDD/SSD, lightweight Linux and selected older Windows; legacy boot and BIOS research; cross-compilation; offline installers.
- Formats: GGUF, ONNX, Safetensors, PyTorch, TensorFlow, compact custom formats; conversion, tokenizer portability, cross-runtime validation, signed integrity verification; version/architecture/licence/provenance/evaluation metadata retained with every export.

---

## 5. MicroMind targets (proposed engineering targets, not measured guarantees)

| Available RAM | Model target | Intended use |
|---------------|--------------|--------------|
| 512 MB | 30–50M | Experimental, extremely limited offline assistant |
| 1 GB (primary) | 50–100M | Compact conversation + local tools + document retrieval |
| 2 GB | 100–300M | More capable local model |
| 4 GB+ | 300M–1B | Larger experiments, depending on quantisation |

Architecture research: small decoder-only Transformers, grouped-query attention / reduced KV cache, shared input-output embeddings, small vocabularies, low dimensions, layer weight sharing, short context, sparse computation where it genuinely helps, recurrent/state-space alternatives. llama.cpp is a starting point, not a guarantee of 2005 compatibility; a simplified native runtime may be required.

---

## 6. Adaptive model selection (implemented)

| Available resources | Model tier | Tasks |
|---------------------|-----------|-------|
| Low RAM | 0.5B | Simple text, classification |
| Moderate RAM | 1.5B | Light coding |
| More resources | 3B (`local-qwen-3b`, only local model after OD-38 reopening 25 Nov) | Regular coding |
| High resources | 7B | Complex coding |
| Beyond local capability | Authorised hosted specialist / trusted node | Difficult reasoning |

Selection checks hardware and task complexity, then selects, loads, executes and unloads models as needed. Implemented in `backend/app/services/adaptive_model_selector.py` with cgroup-aware RAM detection, a protected core-service reserve, per-tier context limits, single-request concurrency and best-effort unload (`keep_alive=0`). Integrated into `intel_router_service.select_model` when the caller supplies available aliases. Tests: `backend/tests/test_adaptive_model_selector.py` (8 passing).

---

## 7. External intelligence, offline and distributed operation

- External Intelligence Memory: short-term state, approved long-term memory, knowledge library and skill library — SQLite and compact inverted indexes before vector databases on old hardware.
- Neural-symbolic: deterministic maths, dates, databases, logical rules and sandboxed execution handled by traditional programs; the small model handles language and coordination.
- Offline ecosystem: offline execution, local indexing/retrieval, optional local speech, local commands, offline queues, sync on reconnect, downloadable knowledge/skill packages.
- Distributed MicroMind: independent specialist models, task distribution, shared approved knowledge, lightweight P2P, federated learning experiments. Splitting one model across several slow machines is usually slower than running it on one; start with independent specialists. Never pool RAM across machines.
- Skills without retraining: verified knowledge packages, tools, workflows, deterministic components and optional adapters expand capability while weights stay small.

---

## 8. Evaluation, security and lifecycle

- Benchmark creation, contamination detection, independent comparison, statistical significance, capability-specific tests, hallucination and reasoning-consistency measurement, long-context/multilingual/tool-use/adversarial tests, degradation detection, reproducibility, human evaluation — and preserve failed experiments.
- Model introspection and capability profiles: what each model reliably does, struggles with, hardware needs, context limits, languages, known failure modes, safety limits, training history and benchmark results. Select by measured capability, not name or parameter count.
- Safeguards: instruction hierarchy, prompt-injection resistance, tool permissions, dangerous-command prevention, output validation, sensitive-data handling, privacy, backdoor/poisoning detection, signed updates, secure rollback, capability restrictions. A small model must not receive unrestricted OS access.
- Lifecycle: deprecation, long-term compatibility, security patching, runtime updates, migration, backward compatibility, health monitoring, reproducible builds, rollback, disaster recovery, artifact preservation, model cards, licensing, open-source/commercial distribution, SDKs, local APIs, embedded deployments.

---

## 9. Intellectual-property boundary

Architecture reproduction is lawful only where specifications, weights and licences permit: study public configs, tokenizers, papers and formats; reproduce published architectures; distil using permitted outputs; convert compatible formats. For proprietary systems, restrict work to lawful black-box behaviour study, public information and permitted outputs — no weight extraction, source theft or access-control bypass. The objective is reproducing useful capabilities, not stealing a model.

---

## 10. Long-term ambitions

1. Models that dynamically grow/shrink across hardware tiers via compatible components (not by adding RAM to an ordinary model).
2. Self-designed neural architectures beyond Transformers.
3. Extremely efficient general assistance through small models + memory + tools + symbolic reasoning + specialists.

These are research objectives, not promised capabilities.

---

## 11. Ultimate objective

IAM should be able to research, design, reproduce, train, optimise, compress, reproduce, test, protect, deploy and maintain its own AI models — from legacy-compatible ultra-small assistants to larger general-purpose foundation models — while its identity, memory and protected core remain independent of any model.

Current implementation status: OD-38 (foundation set; local baseline reopened 25 Nov to `qwen2.5:3b` only, previously benchmark-favoured `qwen2.5-coder:3b` retired from local use), OD-39 (resource manager + RAM profile), OD-40 (MEFE), OD-41 (frozen requirements below), and the adaptive selector described in section 6. The implementation sequence is in `IAM_AI_RESEARCH_IMPLEMENTATION_PLAN.md`.

---

## 15. Distributed AI Research and Compute — permanently included (OD-41)

This capability is part of this architecture, **not** a separate standalone system. It gives IAM a central research coordinator that submits the same experiment format to multiple free platforms, compares results, and keeps all persistent artifacts in IAM-controlled storage.

### Free platforms (evaluated, not permanent hosting)

| Platform | Role | Constraint |
|----------|------|-----------|
| Google Colab | vLLM prototypes, PyTorch experiments, fine-tuning, evaluation | Free GPU availability fluctuates; sessions up to ~12 h; require NVIDIA T4+ for vLLM (compute capability ≥7.5) |
| Kaggle Notebooks | Training experiments, fine-tuning, repeatable benchmarks | Often Tesla P100 (compute capability 6.0) — **below vLLM's 7.5 requirement**; good for training, not a default vLLM host |
| Lightning AI Studios | More substantial GPU development | Free credits/eligibility; verify terms |
| Hugging Face ZeroGPU | Short inference/evaluation demos | ~5 min daily quota; no sustained training or persistent server |

vLLM is an inference/serving engine — an alternative to Ollama, not a replacement for the model. Keep `Qwen2.5-Coder:3B`.

### Central workflow

```
IAM Core — Research Coordinator
  planning · experiment design · task assignment · result analysis
        |  (approved, common-format jobs)
  Kaggle / Colab / Lightning AI / Hugging Face
        v
IAM Model Research Repository (datasets, code, checkpoints, benchmarks, versions)
        v
Evaluation and Model Registry -> validate · compare · approve · retain · deploy · rollback
```

### Toolchain

PyTorch + Transformers (development); PEFT/TRL/Unsloth (fine-tuning); Accelerate/DeepSpeed where suitable (training); Ollama, llama.cpp, vLLM (serving); MLflow (tracking); HF Datasets (data); lm-evaluation-harness + IAM benchmarks (evaluation); IAM-controlled S3-compatible storage (artifacts).

### Realistic free-tier scope

LoRA/QLoRA fine-tuning, small-model-from-scratch research, tokenizer/architecture experiments, permitted distillation, benchmarking Qwen2.5-Coder 3B against candidates, vLLM throughput/memory/concurrency tests where supported, and specialist-model development. A competitive multi-billion-parameter foundation model from scratch is **not** realistic on free quotas.

### Autonomous operation principle

IAM independently manages the full research loop: discover/evaluate platforms, register/configure accounts where permitted, set up environments, design experiments, submit jobs, run tests/benchmarks, analyse and correct failures, save artifacts, compare/select candidates, manage versions/deployment/rollback, and keep researching better methods.

Creator involvement is required **only** for: genuine human actions (identity verification, human-only confirmations), explicit Creator authority (paid services, binding agreements, protected-core changes), or blockers IAM cannot legitimately resolve. IAM must not repeatedly ask permission for routine tasks already within its authority.

### Operating rules

1. Free resources first; no paid compute or automatic upgrades without Creator approval.
2. No dependence on temporary notebooks for IAM's persistent identity, memory or core intelligence.
3. Verify quotas, GPU availability, licences and commercial-use terms live.
4. Checkpoints, code, datasets and results go to IAM-controlled storage before sessions expire.
5. Model development, evaluation and deployment stay under central governance.

### Additional frozen requirements

1. **Autonomous recovery** — detect failed jobs, diagnose, retry, resume from checkpoints, switch platforms.
2. **Intelligent scheduling** — choose platforms by GPU/VRAM/RAM/CPU/storage/quotas and workload needs.
3. **Persistent research environment** — source, data, checkpoints, logs and results survive session expiry.
4. **Platform lifecycle** — discover new providers, monitor quotas, retire unsuitable ones.
5. **Reproducibility** — record model versions, datasets, parameters, hardware, dependencies, configs and benchmarks.
6. **Security and privacy** — protect credentials, verify downloads, isolate untrusted code, prevent private-data leakage.
7. **Independent quality control** — successful training is not proof of quality; validate accuracy, reasoning, coding, safety, resources and regressions.
8. **Research prioritisation** — maximise improvement per unit of free compute; avoid wasted experiments.
9. **Human approval boundaries** — routine work autonomous; paid/binding/protected changes require Creator approval.
10. **Continuous improvement** — learn from failed and successful experiments.

### Five pillars

1. **Discover** — platforms, models, datasets, tools, research opportunities.
2. **Develop** — architectures, training, fine-tuning, distillation, experiments.
3. **Test** — benchmarks, evaluation, failure diagnosis, comparison.
4. **Improve** — learn from experiments, optimise, repeat.
5. **Manage** — preserve research, resources, security, registry, approved deployment.

Security, licensing, privacy, reproducibility, recovery, budget and platform-compliance rules apply across all five pillars.

