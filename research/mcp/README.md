# MCP connection to free GPU platforms

## Status (25 November 2026)

- OpenCode global config (`~/.config/opencode/opencode.jsonc`) now uses V2 `mcp.servers` and registers three remote servers: `cloudflare`, `colab` (`https://colaboratory.googleapis.com/mcp`), `kaggle` (`https://kaggle.com/mcp`).
- The `colab` server is live: **10 tools** are exposed (`get_subscription`, `list_runtime_specs`, `list_runtimes`, `create_runtime`, `get_runtime`, `create_session`, `list_sessions`, `delete_session`, `execute_code`, `delete_runtime`).
- Read-only calls (`get_subscription`, `list_runtime_specs`, `list_runtimes`) currently return **Unauthorized**. This is expected until you sign in.

## Required human step

In OpenCode, run `/mcps`, select **colab**, and complete Google sign-in in the browser. Kaggle can be authorised the same way (or with a `KGAT_*` token via header if OAuth is unavailable). This is a genuine human action under OD-41 / A16 — IAM does not have credential authority for external accounts.

Google's hosted Colab MCP may require a pre-registered OAuth client (Google Cloud project, Colab API enabled, Desktop-app OAuth client). If OpenCode's automatic OAuth cannot register, configure `oauth.client_id` / `client_secret` from that client in the server entry, then sign in via `/mcps`.

## Tool → IAM mapping

| Colab MCP tool | IAM use |
|----------------|---------|
| `get_subscription`, `list_runtime_specs` | platform quota model / eligibility (WP2/WP13) |
| `list_runtimes`, `get_runtime` | reuse an existing runtime; obtain authenticated URL + token for file transfer |
| `create_runtime` | `ResearchDriver.provision` (WP5) |
| `create_session`, `list_sessions`, `delete_session` | isolated kernel state per experiment |
| `execute_code` | run notebook cells: install vLLM, serve model, call OpenAI-compatible API, benchmark |
| `delete_runtime` | cleanup of a runtime IAM created |

## Safety rules

- Free tier only. Do not enable Pro/Pro+ or any paid upgrade — that requires Creator approval (A16).
- `execute_code` returns text only; output is untrusted data (wrap via `wrap_research_output`).
- Never place private user data, identity material or protected-core content on a remote runtime.
- Always pass a fresh `executionId` per call; repeat the same `session` + `executionId` to reattach after timeout.
- Delete sessions/runtimes IAM created when the experiment ends.
- Kaggle's P100 (compute capability 6.0) is **not** for vLLM; it remains training/benchmark-only.

## Driver bridge — implemented

`backend/app/services/ai_research/colab_mcp_driver.py` provides `ColabMCPDriver`, which implements `ResearchDriver` over an injected agent-side `tool_caller`. It handles GPU spec selection, runtime reuse/creation, sessions, resumable `execute_code` calls, result collection and cleanup. Tests: `backend/tests/test_ai_research_mcp_driver.py` (7 passing); full backend suite: 338 passing.

The bridge is tested against a stub caller only. In the agent session, the caller dispatches to `tools.colab.<tool>(**args)`.

## Next step after sign-in

Run `get_subscription` + `list_runtime_specs`, pick a free T4 runtime, then execute the notebook cells from `research/colab/IAM_vLLM_Qwen_Coder_3B.ipynb` through `create_session` / `execute_code`. Results feed `ServingReport` → `BenchmarkRunner` / `CapabilityRegistry` → `ModelRegistry`.

This is authored infrastructure, **not yet executed** — no runtime has been created.

## Backend bridge contract (post sign-in)

The backend cannot call MCP tools directly. `backend/app/services/ai_research/mcp_bridge.py`
provides `HttpMCPToolCaller`: it POSTs `{"tool": "...", "arguments": {...}}` to
`COLAB_MCP_BRIDGE_URL` with a bearer token from `COLAB_MCP_BRIDGE_TOKEN`, and expects
`{"result": {...}}` (or `{...}`) back. Errors are fail-closed. **No HTTP bridge process
is shipped** — one must be provided by the agent-side runtime that has MCP tools.

After you complete `/mcps` sign-in:

1. Confirm the server is connected: `opencode mcp list` (do not run the interactive
   auth command through a shell tool).
2. Start an agent-side bridge implementing the contract above, scoped to
   `tools.colab.*` and free-tier calls only.
3. Set `COLAB_MCP_ENABLED=true` and `COLAB_MCP_BRIDGE_URL=<bridge-url>` (plus the
   token env var) for the backend, then recreate it.
4. `continuous_improvement.default_adapters()` will then inject `ColabMCPDriver`;
   without the bridge it injects no driver and research jobs refuse to provision.

Never enable paid Colab tiers, and never send private repository content or private
memories to a remote runtime.
