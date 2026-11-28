#!/usr/bin/env bash
# =============================================================================
# Codespaces / devcontainer post-create setup for IAM (AURA)
# =============================================================================
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "==> Installing Python backend (with dev extras)"
python -m pip install --upgrade pip
python -m pip install -e "./backend[dev]"

echo "==> Installing frontend dependencies"
(cd frontend && npm install)

echo "==> Installing Playwright Chromium for research/browser tooling"
python -m playwright install --with-deps chromium

echo "==> Preparing local environment template"
if [ ! -f .env ] && [ -f .env.example ]; then
  cp .env.example .env
  echo "Created .env from .env.example - fill in your own secrets before running."
fi

echo "==> Setup complete"
echo "Next steps: docker compose up -d, then start the backend and frontend (see docs/IAM_FREE_SANDBOXES.md)."
