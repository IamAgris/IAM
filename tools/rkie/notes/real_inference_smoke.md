# Real inference smoke (27 November 2026)

Evidence: `tests/real_inference_smoke.md`.

IAM generated a real answer with the shared primary `qwen2.5:3b` through LiteLLM/Ollama:
HTTP 200, 82.1 s, answer "2+2 equals 4." No mocks or paid provider.

Key files: `infra/litellm/config.yaml` (timeout 300 on `local-qwen-3b`),
`backend/app/core/config.py` (primary alias/tag), `.env` + `docker-compose.yml`.
IRWM admits one resident request at a time; a 503 "one resident request already in
flight" means a background request holds the slot, not a software fault.

Host note: published port 8000 was unreachable from the Windows host during the test;
the identical request through Caddy 8080 worked.
