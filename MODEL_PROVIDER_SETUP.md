# IAM — Adding Model Provider Keys: How & Where

## Short answer

You do **not** need a key for real AI: the OD-46 local primary (`qwen2.5:3b` via
Ollama) is already active and streams real responses. Hosted providers are
**optional delegates** for heavier tasks.

## Where keys live (important distinction)

| Key type | Where it goes | Who adds it |
|---|---|---|
| **Provider API key** (NVIDIA, Dashscope) | `D:\AI\project-aura\.env` → passed into the LiteLLM + backend containers | You (one PowerShell command) |
| **Gateway credential** (OD-51 vault) | Encrypted DB via `/api/v1/models/credentials` | Only with a signed Creator authorization |

The vault does **not** hold provider API keys — those stay in LiteLLM config/.env.

## How (two commands)

```powershell
cd D:\AI\project-aura

# NVIDIA free endpoints (recommended — no card needed)
.\scripts\set-model-key.ps1 -Provider nvidia -Key "nvapi-YOUR_KEY"

# Or Alibaba Dashscope
.\scripts\set-model-key.ps1 -Provider dashscope -Key "sk-YOUR_KEY"
```

The script writes the key to `.env` and recreates the backend container.

## Where to get a key

- NVIDIA: https://build.nvidia.com → sign in → open a model → "Get API key" (starts `nvapi-`)
- Dashscope: Alibaba Cloud console → Dashscope → API-Key management

## Verify after adding

```powershell
Invoke-RestMethod -Uri http://localhost:8000/api/v1/models/readiness | ConvertTo-Json
Invoke-RestMethod -Uri http://localhost:8000/api/v1/models/router/discover/nvidia -Method Post
```

In the UI: open **IAM options** → **Connections** shows registered keys;
**Model mode** → *manual* lists free hosted models; *hybrid* uses local primary +
authorised specialist.

## Rules

- `NVIDIA_FREE_ONLY=true` — paid usage stays disabled; overage never silent.
- Keys never enter prompts, memory, browser bundles, or logs.
- Never paste a key into the chat window.
- To remove: set the key to empty in `.env` and rerun the script (or edit `.env` + `docker compose up -d --force-recreate backend`).
