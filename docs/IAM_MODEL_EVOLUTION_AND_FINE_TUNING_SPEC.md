# IAM — Model Evolution and Fine-Tuning Engine (MEFE)

**Status:** CONFIRMED — owner decision OD-40, 25 November 2026 (part of the frozen baseline)  
**Type:** Permanent subsystem spanning systems 5 (Learning and Capability Development), 11 (Self-Evolution and Model Independence) and 14 (Evaluation and Research)  
**Related:** `IAM_FOUNDATION_MODEL_AND_INTELLIGENCE_SPEC.md` (Doc 23 / OD-38), `IAM_AI_SDK_AND_FRAMEWORK_RESEARCH_SPEC.md` (Doc 20 / OD-36), `IAM_RESOURCE_AND_WORKLOAD_MANAGER_SPEC.md` (proposed)

---

## 1. Purpose

Give IAM a controlled, ongoing capability to take existing open-weight models, improve them with carefully selected data, create specialist models, and eventually develop its own foundation models. Fine-tuning must never mean IAM silently changing its own weights — every change is tested, versioned and approved.

IAM's identity and protected architecture remain independent of these models.

## 2. Engine phases

1. **Data collection** — approved documents, code, examples, conversations with permission, research and datasets.
2. **Data preparation** — clean, deduplicate, classify, validate, filter and format training examples.
3. **Training and fine-tuning** — train adapters or fine-tune approved base models.
4. **Evaluation** — accuracy, reasoning, coding, safety, regressions and resource usage.
5. **Model registry and deployment** — version, approve, deploy, monitor and roll back.

This is a continuous improvement cycle, not a one-off pipeline.

## 3. Technologies to evaluate (not install-all)

| Technology | Role |
|------------|------|
| Hugging Face Transformers | Loading models, tokenizers, datasets and architectures — core framework |
| PEFT | LoRA / QLoRA adapters without updating all parameters — best starting point for limited hardware |
| TRL | SFT, preference optimisation and RL methods |
| Unsloth | Memory-efficient fine-tuning for supported models/hardware |
| Axolotl | Configurable pipelines across model families and methods |
| MLflow | Experiment, dataset, version, parameter and evaluation tracking |

IAM evaluates compatibility and picks the best combination; none is mandatory.

## 4. Training methods to support

| Method | Purpose |
|--------|---------|
| Full fine-tuning | Update most or all weights |
| LoRA | Train small adapters |
| QLoRA | Fine-tune quantised models with lower memory |
| SFT | High-quality example responses |
| DPO | Preference optimisation from comparisons |
| Knowledge distillation | Strong teacher → smaller student |
| Continued pretraining | Domain-specific corpus adaptation |
| Reinforcement learning | Optimise against designed rewards |

Start with **SFT + QLoRA**; add DPO and distillation once evaluation infrastructure is mature.

## 5. Specialist models

IAM should develop specialist models rather than fine-tuning one model to do everything:

- IAM Coding Intelligence
- IAM General Reasoning
- IAM Research Intelligence
- IAM Cybersecurity Defence Intelligence
- IAM Communication Intelligence
- IAM Mathematics Intelligence
- IAM Legal Research Intelligence
- IAM Data Analysis Intelligence
- IAM Multilingual Intelligence

They are coordinated by central IAM intelligence and must **not** become independent identities or gain authority over the protected core.

## 6. RAM and training-cost policy

The 8 GB VPS runs orchestration, datasets, model registry and lightweight inference. **Substantial training must not run there.**

- Use trusted nodes with suitable GPUs for training.
- Discover legitimate free GPU training environments when available.
- Use hosted training resources only with creator approval where payment is involved.
- Pause/resume supported jobs when resources are unavailable.
- Store checkpoints in approved object storage.
- Deploy smaller quantised models back to the core.

LoRA reduces memory but does not make every model trainable on 8 GB.

## 7. Safeguards (every fine-tuning operation)

1. Dataset provenance and licensing checks.
2. Personal-data and consent controls.
3. Training-data poisoning detection.
4. Separation of private user conversations from general training.
5. Baseline and post-training benchmarks.
6. Security and safety evaluations.
7. Model versioning and reproducibility.
8. Creator approval before changing the protected primary model.
9. Automatic rollback if deployment performs worse.
10. Record of what changed, why and which data was used.

Fine-tuning must not be used to store private user memories — those belong in the permission-controlled memory system.

## 8. Architecture

```
IAM — Central Intelligence
  Identity · Memory · Planning · Decision-making · Governance
        |
  Model Development Engine (MEFE)
    Dataset Engine      — preparation and validation
    Training Engine     — fine-tuning and optimisation
    Evaluation Engine   — testing and comparison
    Model Registry      — versions and releases
        |
  Local models (core and specialist nodes)
  Hosted models (optional teachers, reviewers, specialists)
```

## 9. Distinctions to preserve

- **Fine-tuning:** improving an existing model.
- **Model development:** experimenting with architectures, tokenisation, datasets and training approaches.
- **Foundation-model development:** training a new model from scratch — substantially more data, compute and engineering.

Support all three eventually; start with fine-tuning and specialist models.

## 10. Implementation hooks

- `backend/app/services/` — dataset, training, evaluation and registry services (new).
- `backend/app/models/modelindependence.py` — experiment and model-version records.
- `tests/model_competition/` — reusable evaluation harness and evidence format.
- `iam/skills/` — Skill Forge packages for repeatable training/evaluation jobs.
- OD-11 / OD-19 — protected-core and signed creator approval gates before any primary-model change.
