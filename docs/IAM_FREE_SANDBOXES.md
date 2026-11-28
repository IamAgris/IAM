# IAM — Free Sandboxes and Experimentation Platforms

This guide maps IAM (AURA) testing work to free browser-based platforms. Use these
for development and experiments only — none of them is a production host for IAM.

> **Security first:** `IamAgris/IAM` is currently a **public** repository. Never put
> API keys, `.env` files, Creator signing material, or real user data in it. Use
> synthetic test data and keep secrets in each platform's secret store.

---

## Platform map

| IAM requirement | Platform | Notes |
|---|---|---|
| Run IAM Python core / FastAPI backend | **GitHub Codespaces** | Included here via `.devcontainer/` |
| Test TypeScript / npm SDK (`sdk/`) | GitHub Codespaces | Node 20 is installed by the devcontainer |
| Test Python SDK (`sdk/python/`) | Codespaces / Colab | Colab is handy for notebook-style checks |
| Test backend APIs and migrations | GitHub Codespaces | Forwarded ports 8000 / 4000 / 5433 |
| Build the Next.js dashboard | Codespaces / StackBlitz | StackBlitz is best for UI-only prototypes |
| Experiment with LLMs, embeddings, agents | **Google Colab** | Free GPU/TPU when available; sessions are temporary |
| Datasets and model experiments | **Kaggle Notebooks** | Quota-limited; not for hosting |
| Explore/evaluate open models | **Hugging Face** | Inference, embeddings, public demos |
| Host small model demos | Hugging Face Spaces | Static Spaces free; ZeroGPU on eligible accounts |

**Official links**
- GitHub Codespaces — https://github.com/features/codespaces
- StackBlitz — https://stackblitz.com/
- Google Colab — https://colab.research.google.com/
- Kaggle Notebooks — https://www.kaggle.com/code
- Hugging Face — https://huggingface.co/

Free allowances (for example, Codespaces monthly core-hours and storage, GPU
availability in Colab/Kaggle, or ZeroGPU eligibility) change over time. Check each
provider's current pricing page before relying on a quota.

---

## GitHub Codespaces (main development sandbox)

This repository includes a ready-to-use devcontainer:

- `.devcontainer/devcontainer.json` — Python 3.12, Node 20, Docker-in-Docker, GitHub CLI, port forwarding.
- `.devcontainer/setup.sh` — installs backend + dev extras, frontend packages, Playwright Chromium, and creates `.env` from `.env.example`.

### Start

1. GitHub → **Code** → **Codespaces** → **Create codespace on main**.
2. Wait for `postCreateCommand` to finish.
3. Fill in `.env` (never commit it): model API keys, database password, `APP_SECRET_KEY`, etc.
4. Start infrastructure and services:

```bash
docker compose up -d
docker exec -i aura-postgres psql -U aura -d aura_db < backend/app/db/migrations/001_initial_schema.sql

# Terminal 1 - backend
cd backend && uvicorn app.main:app --host 0.0.0.0 --port 8000

# Terminal 2 - frontend
cd frontend && npm run dev
```

Codespaces auto-forwards ports 8000 (API) and 3000 (UI).

### SDK checks

```bash
# Python SDK
python -m pip install -e ./sdk/python
python -c "import iam_sdk; print(iam_sdk)"

# TypeScript SDK / CLI
cd sdk/typescript && npm install && npm run build
cd sdk/cli && npm install
```

---

## AI experimentation sandboxes

These are deliberately separate from the main IAM deployment so experiments
cannot damage its state.

- **Google Colab** — Python notebooks for model/embedding experiments. Install the
  SDK or call the IAM API over a forwarded URL; use synthetic data only.
- **Kaggle Notebooks** — dataset work and GPU-available training experiments.
- **Hugging Face** — browse models, test inference/embeddings, and publish small
  demo Spaces. Do not upload private IAM code or data.
- **StackBlitz** — quick UI prototypes with React/TypeScript; use it for isolated
  interface ideas rather than the full Next.js app.

---

## Recommended split

1. **Codespaces** — primary IAM development, API tests, SDK tests, migrations.
2. **Colab / Kaggle** — AI and ML experiments with free GPU quotas.
3. **Hugging Face** — model evaluation and demo Spaces.
4. **StackBlitz** — throwaway frontend prototypes.

Keep IAM's protected source and all credentials out of public projects, and treat
every free sandbox as temporary and non-private.
