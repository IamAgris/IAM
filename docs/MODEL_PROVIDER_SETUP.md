# IAM — Model Provider Keys: How & Where

## Short answer

Real AI already works without a hosted key: the OD-46 local primary
(`qwen2.5:3b` via Ollama) streams responses locally. Hosted providers are
**optional delegates** for heavier tasks.

A NVIDIA key **is already configured in `.env`** and is actively used for
hosted inference through the LiteLLM gateway.

## Where keys live (important distinction)

| Key type | Where it goes | Who adds it |
|---|---|---|
| **Provider API key** (NVIDIA, Dashscope) | `D:\AI\project-aura\.env` → passed into the LiteLLM + backend containers | You (one PowerShell command) |
| **Gateway credential** (OD-51 vault) | Encrypted DB via `/api/v1/models/credentials` | Only with a signed Creator authorization |

The vault does **not** hold provider API keys — those stay in LiteLLM config/.env.

## How (one command)

```powershell
cd D:\AI\project-aura
.\scripts\set-model-key.ps1 -Provider nvidia -Key "nvapi-YOUR_KEY"
# or: .\scripts\set-model-key.ps1 -Provider dashscope -Key "sk-YOUR_KEY"
```

The script writes the key to `.env` and recreates the backend container.

To get a key: https://build.nvidia.com → sign in → open a model → "Get API key".

## Verified hosted models from the current `.env` key (27 Nov 2026)

Registered as static aliases in `infra/litellm/config.yaml`, using exact
catalogue IDs so **IAM options → Model mode → Manual** selections are callable:

| Alias / model ID | Status |
|---|---|
| `nvidia-nemotron-3.5-lightning` (bootstrap) | ✅ verified |
| `mistralai/mistral-large-4-1t-a52b` | ✅ verified |
| `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning` | ✅ verified |
| `google/gemma-3-4b-it`, `google/gemma-3-12b-it` | ❌ listed by `/v1/models` but return 404 on chat with this key |
| `minimaxai/*`, `moonshotai/*`, `z-ai/*` | ❌ time out on chat with this key |

**Important:** the discovery catalogue lists *all* models the key can see, but
not all are callable via `/v1/chat/completions`. Only verified aliases are
registered; a model not in `config.yaml` cannot be used for chat.

### Why static aliases, not runtime registration?

`ProviderModelRegistrar` normally registers discovered models through LiteLLM's
`/model/new`, which needs LiteLLM's own Prisma database. In this environment the
Prisma CLI hangs during migration, and LiteLLM refuses to baseline IAM's
existing `aura_db`. Therefore free chat models are registered statically in
`infra/litellm/config.yaml` instead. No key literal ever appears in that file —
all use `os.environ/NVIDIA_API_KEY`.

## Verify

```powershell
Invoke-RestMethod -Uri http://localhost:8000/api/v1/models/readiness | ConvertTo-Json
$b='{"model":"mistralai/mistral-large-4-1t-a52b","messages":[{"role":"user","content":"Hi"}]}'
Invoke-WebRequest -Uri http://localhost:8000/api/v1/models/chat -Method Post -Body $b -ContentType application/json
```

In the UI: **IAM options** → **Connections** shows registered vault credentials;
**Model mode** → *manual* lists free hosted models; *hybrid* keeps local primary
with authorised delegation.

## Hosted AI helps the local brain (OD-51)

The local primary (`local-qwen-3b`) stays the brain. Hosted models are
**specialist helpers only**: `hybrid` mode calls IAM's delegation workflow,
which requires a signed Creator authorization for `model.delegate`, asks the
hosted specialist, then has the **local model verify and accept** only the
findings it agrees with. The configured delegate is
`mistralai/mistral-large-4-1t-a52b` (verified free on the `.env` key). IAM
cannot self-authorize delegation.

## Rules

- `NVIDIA_FREE_ONLY=true` — paid usage stays disabled; no silent overage.
- Keys never enter prompts, memory, browser bundles, or logs.
- Never paste a key into the chat window.
- To remove: blank the key in `.env`, then `docker compose up -d --force-recreate litellm backend`.
- LiteLLM startup can take ~60–90 s while it loads the cost map; wait for
  `/health/liveliness` before testing.
