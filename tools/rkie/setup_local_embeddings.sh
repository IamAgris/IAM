#!/usr/bin/env bash
# Bootstrap local-only neural embeddings on Linux/macOS (Ollama + nomic-embed-text).
set -euo pipefail
MODEL="${IAM_EMBED_MODEL:-nomic-embed-text}"
BASE_URL="${OLLAMA_HOST:-http://localhost:11434}"
CONFIG="$(cd "$(dirname "$0")" && pwd)/config/embeddings.json"
CHECK_ONLY=0
[ "${1:-}" = "--check" ] && CHECK_ONLY=1

if ! command -v ollama >/dev/null 2>&1; then
  echo "Ollama CLI not found. Install it: curl -fsSL https://ollama.com/install.sh | sh"
  [ "$CHECK_ONLY" = 1 ] && exit 1
  exit 2
fi

if ! curl -fsS "$BASE_URL/api/tags" >/dev/null 2>&1; then
  if [ "$CHECK_ONLY" = 1 ]; then echo "Ollama service not reachable at $BASE_URL"; exit 1; fi
  echo "Starting ollama serve..."
  (ollama serve >/dev/null 2>&1 &)
  for _ in $(seq 1 20); do
    sleep 1
    curl -fsS "$BASE_URL/api/tags" >/dev/null 2>&1 && break
  done
fi

if ! curl -fsS "$BASE_URL/api/tags" | grep -q "\"$MODEL\""; then
  if [ "$CHECK_ONLY" = 1 ]; then echo "Model $MODEL not installed"; exit 1; fi
  echo "Pulling $MODEL..."
  curl -fsS -X POST "$BASE_URL/api/pull" -H 'Content-Type: application/json' \
    -d "{\"name\":\"$MODEL\",\"stream\":false}" >/dev/null
fi

if [ "$CHECK_ONLY" = 1 ]; then echo "CHECK OK: $MODEL available locally"; exit 0; fi

python3 - "$CONFIG" "$MODEL" "$BASE_URL" <<'PY'
import json, sys
from pathlib import Path
path, model, base_url = sys.argv[1:4]
settings = json.loads(Path(path).read_text(encoding="utf-8"))
settings.update({"enabled": True, "provider": "ollama", "model": model,
                 "base_url": base_url, "dimension": 768})
Path(path).write_text(json.dumps(settings, indent=2) + "\n", encoding="utf-8")
PY
echo "Enabled local neural embeddings: model=$model"
