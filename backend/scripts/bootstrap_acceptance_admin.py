"""Create a uniquely named admin credential for live acceptance runs.

Prints only the API key to stdout so CI can capture it into IAM_API_KEY without
placing a secret in the repository. Acceptance endpoints require admin scope;
the frontend user key is intentionally not sufficient.
"""

import os
import sys
import uuid

import httpx


def main() -> int:
    api_url = os.environ.get("IAM_API_URL", "http://localhost:8000").rstrip("/")
    bootstrap_key = os.environ.get("IAM_BOOTSTRAP_API_KEY", "")
    if not bootstrap_key:
        print("IAM_BOOTSTRAP_API_KEY is required", file=sys.stderr)
        return 1
    name = f"acceptance-admin-{uuid.uuid4().hex[:12]}"
    try:
        response = httpx.post(
            f"{api_url}/api/v1/auth/bootstrap",
            json={"name": name, "scope": "admin"},
            headers={"X-Bootstrap-Key": bootstrap_key},
            timeout=30.0,
        )
        response.raise_for_status()
        key = response.json()["key"]
    except Exception as exc:
        print(f"admin credential creation failed: {type(exc).__name__}", file=sys.stderr)
        return 1
    print(key)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
