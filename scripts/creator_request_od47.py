"""Prepare the signed Creator approval request for OD-47.

IAM never self-approves. This script only creates a pending request through the
official Creator approval API and prints the challenge that the Creator hardware
signer must sign. Set IAM_ENDPOINT and IAM_API_TOKEN in the environment.

Usage:
    python scripts/creator_request_od47.py --channel creator_email
    python -m iam_sdk.creator_cli challenge <request_id>
    python -m iam_sdk.creator_cli sign <request_id> --approve \
        --signer "<hardware signer command>" --signer-id <signer-id>

The email carrier only transports the challenge. A plain email reply never
authorises anything: only the signed ED25519 challenge does (OD-03/OD-19/OD-42).
"""

import json
import os
import sys

import httpx

ACTION_TYPE = "architecture.decision.confirm"
TARGET_REF = "OD-47"
RISK_LEVEL = "4"
CHANNEL = os.environ.get("IAM_CREATOR_CHANNEL", "creator_cli")
SUMMARY = "Confirm Document 27: Research Acquisition & Legal Intelligence as a permanent IAM capability"
CONSEQUENCES = [
    "Adds twelve acquisition channels and a rights registry; does not alter any earlier decision.",
    "Enables independent training approval; ingestion approval alone never permits training.",
    "Keeps all legal-context entries unverified until counsel records a reference.",
    "Does not change protected-core rules, signing authority or financial authority.",
]
REASON = "Owner requested Creator approval after implementation of Document 27."


def main() -> int:
    endpoint = os.environ.get("IAM_ENDPOINT", "http://127.0.0.1:8000").rstrip("/")
    token = os.environ.get("IAM_API_TOKEN")
    if not token:
        print("IAM_API_TOKEN is required", file=sys.stderr)
        return 2

    if CHANNEL not in {"creator_email", "creator_cli"}:
        print(f"unsupported Creator channel: {CHANNEL}", file=sys.stderr)
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
        "email_carrier_requirements": (
            ["CREATOR_EMAIL", "CREATOR_PUBLIC_KEY", "CREATOR_GATEWAY_SECRET"]
            if CHANNEL == "creator_email" else []
        ),
        "note": "Email/CLI is only a carrier. Only a verified ED25519 signature approves OD-47.",
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
