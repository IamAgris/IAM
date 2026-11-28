# IAM — Capability posture matrix

**Version:** 1.0 · 28 November 2026
**Status:** Navigation aid derived from `backend/app/core/config.py`. Re-run the checks after changing a flag.
**Purpose:** make the default-off posture explicit so a deployment cannot be mistaken for a capability test.

"Verified" below means an executable test or a live drill exists in this repository. "Default-off" is a
deliberate OD-15/OD-51 posture: nothing here is enabled by the presence of source code.

## Default-on controls (the protected baseline)

| Flag | Capability | Enforcement / evidence |
|---|---|---|
| `auth_enabled=true` | Scoped API credentials | `auth_middleware.py` + `auth_policy.py`; L1 acceptance |
| `inference_aegis_enabled=true` | Prompt-injection inspection on every message | `test_inference_security_gate.py` |
| `irwm_enabled=true` | Resident-model hard ceiling | `test_irwm_inference_gate.py` |
| `free_models_only=true` | No paid inference | `model_policy.require_authorization` |
| `nvidia_free_only=true` | NVIDIA free-tier filtering | `test_od52_monitoring.py` |
| `iam_context_enabled=true` | Verified knowledge in chat context | `test_iam_context.py` |
| `iam_live_info_enabled=true` | Live-information policy | `test_live_information_policy.py` |
| `browser_enabled=true` | Research browsing (permission-gated) | `test_browser_engine_adapters.py` |
| `lm_eval_suite_enabled=true` | Trusted local evaluation | `test_eval_suite.py`, `test_lm_eval.py` |
| `post_deploy_monitor_enabled=false` | Regression monitor + optional rollback | `test_post_deploy_monitor.py`; hourly ARQ cron |
| `post_deploy_auto_rollback_enabled=false` | Automatic rollback | Still requires signed release gate |

## Default-off capabilities — operator opt-in

| Capability | Flag(s) | What enabling does | Verification |
|---|---|---|---|
| Local Ollama primary | `ollama_enabled` | Uses `local-qwen-3b` as shared primary (OD-46) | Live readiness + `tests/real_inference_smoke.md` |
| Free sandbox provisioning | `free_sandboxes_enabled`, `free_sandbox_discovery_enabled` | Creates remote free environments | Unit tests with stub adapters; no live provider |
| Visible/browser UI mode | `browser_visible_mode_enabled` | Needs DISPLAY/Xvfb, not in default Compose | Adapter fails closed; no live visual run |
| Browser OCR | `browser_ocr_enabled` | Local Tesseract on screenshots | `live_media_service.py` Docker OCR |
| Tor / onion access | `tor_enabled`, `tor_onion_access_enabled`, `tor_bridge_configured` | Creator-controlled; fails closed | `test_tor_intelligence.py` |
| Computer use / mobile agent | `uwai_computer_use_enabled`, `mobile_agent_enabled` | ADB/visual agents | Unit tests only |
| Skill runtime | `skill_runtime_enabled`, `skill_runtime_network_enabled` | Executes skills; `docker` is the reviewed adapter | Stub default; `iam/skills/` empty |
| Workspaces | `workspace_enabled`, `workspace_remote_execution_enabled` | Isolated provider execution | `test_workspaces` (isolation-first) |
| Local model training | `model_development_local_training` | Ollama `/api/create` candidate | `test_local_ollama_training.py` |
| Colab MCP execution | `colab_mcp_enabled` | Requires human `/mcps` Google sign-in | Bridge answers 503 until dispatcher set |
| Blockchain / Web3 | `blockchain_enabled`, `web3_registry_enabled`, `web3_*` | Free-only, prepare-only until `web3_execution_enabled` | `test_web3_*`; no mainnet value movement |
| Banking | `banking_enabled` | Consent-gated adapters | `test_banking` with fakes; no live bank |
| Paper trading | `trading_simulation_enabled` | Simulated portfolios only | Level 5 acceptance |
| Prediction markets / gaming / investment | `*_enabled` flags | Research/forecast only | Unit tests; no live providers |
| Private user email | `user_email_enabled` | Opt-in outbound carrier | `test_user_email.py` (concurrent work) |
| Infisical secrets | `secrets_backend=infisical` | Docker secrets remain fallback | `test_infisical_secrets.py` (concurrent work) |
| ARTEX security engine | `artex_enabled`, `artex_dry_run` | Defensive connector, dry-run default | Connector tests |
| Emergency stop | always on | Creator-signed halt of inference/autonomy/browser/trading | `test_emergency_shutdown.py` |

## How to verify a posture claim

```powershell
python -m ruff check backend
python -m pytest backend/tests -q --cov=app --cov-fail-under=60
python tools/quality/check_infra_drift.py --json
```

For any capability you intend to rely on, require one of:
1. a passing named test in the table above,
2. a documented live drill (DR, signed Creator flow, two-node P2P), or
3. a successful L1–L5 acceptance run in `quality-gates/acceptance`.

Do not treat a default-off flag flipping to `true` as evidence by itself.
