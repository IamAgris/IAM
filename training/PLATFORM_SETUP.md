# Free GPU platform setup: Colab and Kaggle

This guide connects both free notebook platforms to the same IAM fine-tuning branch.
It does not create cloud resources, activate paid services, or authorise billing.

## Hard cost and safety rules

- Use only the platforms' free GPU allocation.
- Do not enable paid compute, credits, Pro/Plus upgrades, pay-as-you-go, or automatic upgrades.
- If a free GPU is unavailable or a quota is exhausted, stop and wait or switch to the other free platform.
- Never put a GitHub token, Hugging Face token, password, or other secret in a notebook, Git commit, dataset, or training log.
- The repository is public, so cloning it does not require a GitHub token.
- Do not push model weights/checkpoints to GitHub. They are large, may be sensitive, and must stay in persistent platform storage or an approved model-artifact store.
- The Qwen2.5-Coder-3B-Instruct licence gate in README.md remains in force. Research/evaluation only until commercial rights are confirmed.

## Shared source of truth

- Repository: https://github.com/IamAgris/IAM
- Branch: `research/qwen25-coder-3b-sft`
- Training entry point: `training/scripts/train_qlora.py`
- Dataset validator: `training/scripts/validate_dataset.py`
- Dataset format: JSONL with required `instruction` and `output` fields.
- Keep training, validation, and final evaluation data separate.

Both workers should clone the same branch. They are separate training sessions, not a shared live filesystem. Do not run two jobs against the same checkpoint directory simultaneously.

## Google Colab (free)

1. Open https://colab.research.google.com/ and sign in.
2. Create a new notebook. In Runtime settings, select a GPU only if a free GPU is offered. Do not select any paid compute option.
3. Mount Google Drive so checkpoints survive a notebook reset.
4. Run the following in a notebook cell:

```python
from google.colab import drive
drive.mount("/content/drive")

!git clone --branch research/qwen25-coder-3b-sft --single-branch https://github.com/IamAgris/IAM.git /content/IAM
%cd /content/IAM
!git rev-parse --short HEAD
!nvidia-smi
```

5. Create `training/data/train.jsonl` and `training/data/validation.jsonl` from the approved dataset. Keep private or licensed data out unless its use is authorised.
6. Install the requirements in the disposable notebook environment. If needed, first install a PyTorch build compatible with the GPU runtime:

```python
!pip install -r training/requirements.txt
!python training/scripts/validate_dataset.py training/data/train.jsonl
!python training/scripts/validate_dataset.py training/data/validation.jsonl
```

7. Use a persistent Drive directory for output. For example:

```python
OUTPUT_DIR = "/content/drive/MyDrive/IAM-training/qwen25-coder-3b-sft"
!python training/scripts/train_qlora.py \
  --train-file training/data/train.jsonl \
  --validation-file training/data/validation.jsonl \
  --output-dir "$OUTPUT_DIR"
```

If a session is interrupted, inspect the saved checkpoint and resume only using a
checkpoint produced by the same run/configuration. Add `--resume` to the same command
to continue from the latest checkpoint in `$OUTPUT_DIR`. Do not overwrite a completed run.

## Kaggle Notebooks (free)

1. Open https://www.kaggle.com/code and sign in.
2. Create a notebook and select a GPU accelerator only when a free GPU allocation is available. Do not enable paid products or billing.
3. Add the approved training dataset as a private Kaggle Dataset input, or create the files in the notebook session from an authorised source.
4. Clone the same branch:

```bash
!git clone --branch research/qwen25-coder-3b-sft --single-branch https://github.com/IamAgris/IAM.git /kaggle/working/IAM
%cd /kaggle/working/IAM
!git rev-parse --short HEAD
!nvidia-smi
```

5. Install the training requirements and validate the input files:

```bash
!pip install -r training/requirements.txt
!python training/scripts/validate_dataset.py /kaggle/input/YOUR_DATASET/train.jsonl
!python training/scripts/validate_dataset.py /kaggle/input/YOUR_DATASET/validation.jsonl
```

Replace `YOUR_DATASET` with the actual mounted Kaggle dataset directory. Use the real file paths shown under `/kaggle/input`.

6. Write checkpoints under `/kaggle/working`. At the end of a run, use Kaggle's notebook **Save Version** action with output saving enabled so the output files are retained as a notebook version. Confirm that the adapter/checkpoint files appear in the saved output before ending the session. Do not assume temporary session files persist without saving a version.

## Returning results to IAM

For every run, retain a small run manifest alongside the adapter containing:
- repository branch and exact commit SHA;
- base model ID, exact revision and licence evidence;
- dataset identifiers and SHA-256 hashes (do not include private dataset contents);
- package versions, GPU type, seed and full training arguments;
- start/end time, exit status, logs, and checkpoint location;
- evaluation results against the untouched base model on the held-out test set.

Transfer only approved adapters, manifests, logs and evaluation summaries to the designated persistent artifact location. Do not commit large weights or datasets to GitHub. Do not use an unapproved public model hub as storage.

## Important limitations

- Colab and Kaggle do not share live storage or automatically synchronise running jobs.
- GitHub provides versioned source code, not GPU execution or durable checkpoint storage.
- The account owner must sign in, choose the free GPU option, attach/mount storage and approve any platform prompts. This repository guide cannot grant those account permissions.
- GPU availability, session duration and free quotas vary. If a platform offers no free GPU, stop there and use the other free option; never pay to continue.
