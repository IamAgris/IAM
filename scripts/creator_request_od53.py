"""Prepare the signed Creator approval request for OD-53.

IAM never self-approves. This script only creates a pending request through the
official Creator approval API and prints the challenge that the Creator hardware
signer must sign. Set IAM_ENDPOINT and IAM_API_TOKEN in the environment.

This does NOT change the repository, the decision register or the architecture
index. OD-53 becomes CONFIRMED only after CreatorApprovalService.decide() verifies
an ED25519 signature over the one-time challenge.

Usage:
    python scripts/creator_request_od53.py
    python -m iam_sdk.creator_cli sign <request_id> --approve \
        --signer "<hardware signer command>" --signer-id <signer-id>
"""

import json
import os
import sys

import httpx

ACTION_TYPE = "architecture.decision.confirm"
TARGET_REF = "OD-53"
RISK_LEVEL = "4"
CHANNEL = "creator_cli"
SUMMARY = (
    "Confirm Document 33: provider-independent Web3 operations and three independent "
    "self-hosted Bitcoin/Lightning node adapters inside existing IAM systems"
)
CONSEQUENCES = [
    "Extends the OD-23 free-only blockchain adapter with read-only and prepare-only capabilities; no paid tier is enabled.",
    "Adds three independent node adapters (Bitcoin Core, LND, CLN) over a private network, read-only first; their identities and histories are never merged.",
    "Every outgoing value movement still requires signed Creator approval under OD-04/OD-25; IAM gains no standing budget.",
    "Credentials stay in Docker secrets and never enter model context, ordinary database fields, logs or notes.",
    "Creates no new top-level system, no new AI identity and no change to any other locked decision.",
]
REASON = (
    "Owner requested a Web3 and self-hosted Bitcoin/Lightning capability; "
    "see IAM_WEB3_AND_UMBREL_NODE_INTEGRATION_SPEC.md §1 for the exact proposed decision text."
)


def main() -> int:
    endpoint = os.environ.get("IAM_ENDPOINT", "http://127.0.0.1:8000").rstrip("/")
    token = os.environ.get("IAM_API_TOKEN")
    if not token:
        print("IAM_API_TOKEN is required", file=sys.stderr)
        return 2

    payload = {
        "action_type": ACTION_TYPE,
        "target_ref": TARGET_REF,
        "risk_level": RISK_LEVEL,
        "channel": CHANNEL,
        "summary": SUMMARY,
        "consequences": CONSEQUENCES,
        "reason": REASON,
    }
    response = httpx.post(
        f"{endpoint}/api/v1/creator/requests",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )
    if response.status_code != 202:
        print(f"request failed: {response.status_code} {response.text[:500]}", file=sys.stderr)
        return 1

    result = response.json()
    print(json.dumps({
        "request_id": result.get("request_id"),
        "target_ref": TARGET_REF,
        "channel": CHANNEL,
        "challenge_hash": result.get("challenge_hash"),
        "signing_message": f"{result.get('challenge_hash')}|approved",
        "expires_at": result.get("expires_at"),
        "status": result.get("status"),
        "note": "A chat message is not authority. Only a verified ED25519 signature approves OD-53.",
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
