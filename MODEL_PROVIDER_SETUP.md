# IAM — Adding a Model Provider Key

IAM is fully built but language generation needs one external model key. Everything
else (memory, research, autonomy, streaming, voice, vision, security) works without it.

## Recommended: NVIDIA free endpoints (no card needed)

1. Go to **https://build.nvidia.com** and sign in.
2. Search for an open model (e.g. `meta/llama-3.3-70b-instruct` or `qwen/qwen2.5-72b-instruct`).
3. Click **Get API key** → copy the key (starts with `nvapi-`).
4. Run in PowerShell:
   ```powershell
   cd D:\AI\project-aura
   .\scripts\set-model-key.ps1 -Provider nvidia -Key "nvapi-YOUR_KEY_HERE"
   ```
5. Open http://localhost:3000 and ask IAM something — you'll see real streamed tokens.

Free tier limits apply; IAM's router enforces `NVIDIA_FREE_ONLY=true` and never
silently switches to paid models. Network gas/fees are unrelated to this key.

## Alternative: Alibaba Dashscope (Qwen)

1. Get a key from Alibaba Cloud Dashscope.
2. Run:
   ```powershell
   .\scripts\set-model-key.ps1 -Provider dashscope -Key "sk-YOUR_KEY"
   ```

## How it works

- The key lives only in `.env` and the backend container environment — **never** in
  the browser, frontend bundle, prompts, or memory.
- `POST /api/v1/models/chat/stream` proxies LiteLLM with the key server-side.
- Without a key, IAM streams a graceful explanation instead of failing.
- To verify: `Invoke-RestMethod -Uri http://localhost:8000/api/v1/models/router/discover/nvidia -Method Post`

## Security reminder

Never commit `.env`. Never paste a key into the chat interface. If a key is
exposed, rotate it at the provider and re-run the script.
