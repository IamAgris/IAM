"""Owner-run activation of the IPLCI signed compliance policy.

IAM cannot activate its own governance policy. This script must be run by the
Creator/owner with an explicit signer identity and an recorded approval
reference. It never prints credentials and does not edit the decision register.

Required env:
    IAM_ENDPOINT, IAM_API_TOKEN

Example:
    python scripts/iplci_activate_policy.py \
        --signed-by "creator" \
        --approval-ref "OD-48-creator-confirmation"
"""

from __future__ import annotations

import argparse
import json
import os
import sys

import httpx

PROTECTED_RULES = (
    "access_is_not_permission",
    "unknown_never_approved",
    "mandatory_gateway",
    "fail_closed",
    "no_self_modification",
    "human_approval_for_binding_actions",
)
AGENT_LIKE = ("iam", "main", "sdk", "system", "agent", "model")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--signed-by", required=True, help="human/Creator signer identity")
    parser.add_argument("--approval-ref", required=True, help="recorded human approval reference")
    parser.add_argument("--version", default="production-1")
    args = parser.parse_args()

    signer = args.signed_by.strip()
    if not signer or signer.lower() in AGENT_LIKE or signer.lower().startswith(
        ("sub-agent", "plugin:", "external_model:")
    ):
        print("REFUSED: only a human/Creator authority may sign the policy", file=sys.stderr)
        return 2

    endpoint = os.environ.get("IAM_ENDPOINT", "http://127.0.0.1:8000").rstrip("/")
    token = os.environ.get("IAM_API_TOKEN", "")
    if not token:
        print("FAIL: IAM_API_TOKEN is required", file=sys.stderr)
        return 2

    payload = {
        "version": args.version,
        "rules": {rule: True for rule in PROTECTED_RULES},
        "signed_by": signer,
        "human_approval_reference": args.approval_ref,
    }
    headers = {
        "Authorization": f"Bearer {token}",
        "X-IPLCI-Agent-Id": "creator-cli",
    }
    try:
        response = httpx.post(
            f"{endpoint}/api/v1/iplci/policies",
            json=payload,
            headers=headers,
            timeout=30.0,
        )
    except httpx.HTTPError as exc:
        print(f"FAIL: policy activation request failed: {type(exc).__name__}", file=sys.stderr)
        return 1

    if response.status_code >= 400:
        print(f"REFUSED ({response.status_code}): {response.text[:400]}", file=sys.stderr)
        return 1

    record = response.json()
    print(json.dumps({
        "status": record.get("status"),
        "version": record.get("version"),
        "signed_by": record.get("signed_by"),
        "signature": record.get("signature"),
        "note": "IPLCI gateway is now active; removal of a safeguard requires human approval",
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
