import uuid
from pathlib import Path

import httpx

bootstrap = ""
for line in Path(".env").read_text(encoding="utf-8").splitlines():
    if line.startswith("IAM_BOOTSTRAP_API_KEY="):
        bootstrap = line.split("=", 1)[1].strip().strip('"').strip("'")

r = httpx.post(
    "http://localhost:8000/api/v1/auth/bootstrap",
    headers={"X-Bootstrap-Key": bootstrap},
    json={"name": "freenode-" + uuid.uuid4().hex[:8], "scope": "admin"},
    timeout=15,
)
r.raise_for_status()
print(r.json()["key"])
