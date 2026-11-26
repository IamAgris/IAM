"""Bootstrap the first admin and the open frontend's user credential.

Usage:
    IAM_BOOTSTRAP_API_KEY=<key> python scripts/bootstrap_credentials.py

Creates credentials through the authenticated API and writes only the user key
to the frontend env file. Secrets are never printed.

Exit code 1 on failure.
"""

import os
import sys
from pathlib import Path

import httpx

API_URL = os.environ.get("IAM_API_URL", "http://localhost:8000").rstrip("/")
BOOTSTRAP_KEY = os.environ.get("IAM_BOOTSTRAP_API_KEY", "")
ADMIN_NAME = os.environ.get("IAM_ADMIN_KEY_NAME", "main-admin")
USER_NAME = os.environ.get("IAM_USER_KEY_NAME", "frontend-user")
FRONTEND_ENV = Path(
    os.environ.get("IAM_FRONTEND_ENV", Path(__file__).resolve().parents[2] / "frontend" / ".env.local")
)


def post(path: str, payload: dict, headers: dict) -> dict:
    response = httpx.post(f"{API_URL}{path}", json=payload, headers=headers, timeout=30.0)
    if response.status_code >= 300:
        raise RuntimeError(f"{path} failed with HTTP {response.status_code}")
    return response.json()


def main() -> int:
    if not BOOTSTRAP_KEY:
        print("IAM_BOOTSTRAP_API_KEY is required", file=sys.stderr)
        return 1
    try:
        admin = post(
            "/api/v1/auth/bootstrap",
            {"name": ADMIN_NAME, "scope": "admin"},
            {"X-Bootstrap-Key": BOOTSTRAP_KEY},
        )
        user = post(
            "/api/v1/auth/credentials",
            {"name": USER_NAME, "scope": "user"},
            {"Authorization": f"Bearer {admin['key']}"},
        )
        FRONTEND_ENV.parent.mkdir(parents=True, exist_ok=True)
        lines = []
        if FRONTEND_ENV.exists():
            lines = [
                line
                for line in FRONTEND_ENV.read_text(encoding="utf-8").splitlines()
                if not line.startswith("IAM_USER_API_KEY=")
            ]
        lines.append(f"IAM_USER_API_KEY={user['key']}")
        FRONTEND_ENV.write_text("\n".join(lines) + "\n", encoding="utf-8")
        try:
            FRONTEND_ENV.chmod(0o600)
        except OSError:
            pass
    except Exception as exc:
        print(f"Bootstrap failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1

    print(f"Created admin credential '{admin['name']}' and user credential '{user['name']}'")
    print(f"User key written to {FRONTEND_ENV}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
