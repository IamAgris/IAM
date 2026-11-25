# IAM model fine-tuning

This directory contains a reproducible, isolated QLoRA/SFT workflow for evaluating a
specialised coding model. It does **not** replace IAM's provider-independent model
architecture or change the production model configuration.

## Current target

- Candidate: `Qwen/Qwen2.5-Coder-3B-Instruct`
- Intended role: specialised coding, debugging, code explanation, repository-aware
  development assistance and instruction following.
- Method: 4-bit QLoRA supervised fine-tuning; save adapters separately from base weights.
- Initial output: an experimental adapter, not a production model.

## Free GPU platform setup

See [PLATFORM_SETUP.md](PLATFORM_SETUP.md) for connecting Google Colab and Kaggle
notebooks to this branch. The workflow is strictly free-tier: no paid GPU rentals,
upgrades, automatic billing or surprise charges.

## Important licence gate

The official Hugging Face model card identifies the 3B Instruct weights as
`qwen-research`, not Apache-2.0. The upstream model documentation says the 3B
exception is governed by the Qwen Research License Agreement, which grants use for
non-commercial research/evaluation and requires a separate licence for commercial use.
Do not use this checkpoint or a derivative in a commercial service, commercial product,
or revenue-generating deployment unless the rights holder has granted the required
commercial permission. Check the exact Ollama artifact and its upstream provenance too;
an Ollama tag does not change the underlying weights' licence.

References:
- https://huggingface.co/Qwen/Qwen2.5-Coder-3B-Instruct
- https://huggingface.co/Qwen/Qwen2.5-Coder-3B-Instruct/blob/main/README.md

This workflow is therefore for controlled research/evaluation until the licensing
question is resolved. Keep licence evidence with the model registry record.

## Dataset format

Use JSON Lines, one example per line:

```json
{"instruction":"Write a Python function that returns the factorial of n.","input":"","output":"def factorial(n: int) -> int:\n    if n < 0:\n        raise ValueError(\"n must be non-negative\")\n    return 1 if n < 2 else n * factorial(n - 1)"}
```

Required: `instruction` and `output` strings. Optional: `input` and `system`.
Keep train and validation data in separate files. Never put evaluation examples in the
training file. Remove credentials, personal data, private repository content that IAM is
not authorised to use, malware payloads, and unlicensed third-party code. Record dataset
source, licence, collection date, filtering and deduplication decisions.

Suggested layout (data files are intentionally not committed):

```
training/
  data/
    train.jsonl
    validation.jsonl
  outputs/                 # ignored locally; store approved artifacts in model registry
```

## Setup

Use a disposable GPU notebook or isolated training worker. Do not install the training
stack into IAM's production backend environment.

```bash
python -m venv .venv
# Activate the environment, then:
pip install -r training/requirements.txt
python training/scripts/validate_dataset.py training/data/train.jsonl
python training/scripts/validate_dataset.py training/data/validation.jsonl
```

Install a PyTorch build matching the worker's CUDA runtime before the requirements file
if the environment does not already provide a suitable build.

## Train

```bash
python training/scripts/train_qlora.py \
  --train-file training/data/train.jsonl \
  --validation-file training/data/validation.jsonl \
  --output-dir training/outputs/qwen25-coder-3b-iam-sft-v0.1
```

For a training-only run without validation, omit `--validation-file`. The default base
model is the official Instruct checkpoint. Set `--base-model` only after verifying the
exact model ID, revision, provenance and licence. The script writes adapter weights,
tokenizer files and `run_metadata.json` (every CLI argument plus the planned step and
checkpoint cadence); it does not merge or publish them.

Checkpoint and evaluation intervals are scaled to the planned run length, so short
free-tier jobs still validate and leave a resumable checkpoint. After an interruption,
rerun the same command with `--resume` to continue from the latest checkpoint in the
same output directory. Only resume with the same dataset, configuration and mount;
never overwrite a completed run.

## Evaluation and promotion

Before considering any adapter:
1. Compare the untouched base model and adapter on the same held-out tests.
2. Measure code correctness with executable tests, not just subjective preference.
3. Check instruction adherence, debugging, explanation quality, refusal behaviour,
   latency, memory use and regression on general tasks.
4. Record exact base revision, dataset hashes, package versions, seed, hardware,
   hyperparameters, training logs and evaluation results.
5. Keep the previous stable model available for rollback.

No automatic production promotion is implemented. A human-approved release and the
existing IAM governance boundaries remain required.
