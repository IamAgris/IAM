"""Prepare the signed Creator approval request for OD-54.

IAM never self-approves. This script only creates a pending request through the
official Creator approval API and prints the challenge that the Creator hardware
signer must sign. Set IAM_ENDPOINT and IAM_API_TOKEN in the environment.

This does NOT change the repository, the decision register or the architecture
index. OD-54 becomes CONFIRMED only after CreatorApprovalService.decide() verifies
an ED25519 signature over the one-time challenge.

Usage:
    python scripts/creator_request_od54.py
    python -m iam_sdk.creator_cli sign <request_id> --approve \
        --signer "<hardware signer command>" --signer-id <signer-id>
"""

import json
import os
import sys

import httpx

ACTION_TYPE = "architecture.decision.confirm"
TARGET_REF = "OD-54"
RISK_LEVEL = "4"
CHANNEL = "creator_cli"
SUMMARY = (
    "Confirm Document 34: always-on live information and Web Intelligence policy "
    "as an addendum to the frozen browser and research architecture"
)
CONSEQUENCES = [
    "Adds an always-on Web Access and Live Information Policy to the primary system instructions; no generic 'no real-time access' response.",
    "Adds deterministic search triggers, source-first official-site retrieval, conditional browser escalation and a real free HTTP search adapter.",
    "Adds claim labels, confidence, cross-source corroboration, contradiction detection and prompt-injection redaction to retrieved evidence.",
    "Adds a bounded query cache with freshness TTL, source/claim registration in the existing IICS registry, and managed free-first provider failover.",
    "Adds bounded autonomous monitoring through the existing ARQ runtime; no new top-level system, identity, memory store or model.",
    "Does not change OD-46 shared primary, OD-49 browser architecture, identity, signing, financial authority or protected core.",
]
REASON = (
    "Owner requested a permanent live web research capability for IAM; "
    "see IAM_LIVE_INFORMATION_AND_WEB_INTELLIGENCE_SPEC.md (Document 34) §B "
    "for the exact proposed decision text."
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
    print(
        json.dumps(
            {
                "request_id": result.get("request_id"),
                "target_ref": TARGET_REF,
                "channel": CHANNEL,
                "challenge_hash": result.get("challenge_hash"),
                "signing_message": f"{result.get('challenge_hash')}|approved",
                "expires_at": result.get("expires_at"),
                "status": result.get("status"),
                "note": "A chat message is not authority. Only a verified ED25519 signature approves OD-54.",
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
