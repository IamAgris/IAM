"""End-to-end Creator decision flow for OD-47 (Document 27).

Runs in the live environment with credentials supplied through environment
variables. Never prints secrets. The signed decision is the only authority;
this script does not edit decision registers itself.

Required env:
  IAM_ENDPOINT, IAM_API_TOKEN,
  IAM_CREATOR_CHANNEL=creator_email (default),
  IAM_CREATOR_SIGNER (local command that reads the message on stdin and writes
                      base64 Ed25519 signature to stdout),
  IAM_CREATOR_SIGNER_ID,
  plus the SMTP/private-domain variables checked by creator_email_preflight.
"""

import json
import os
import shlex
import subprocess
import sys

import httpx

from creator_email_preflight import check as preflight

ACTION_TYPE = "architecture.decision.confirm"
TARGET_REF = "OD-47"
RISK_LEVEL = "4"
SUMMARY = "Confirm Document 27: Research Acquisition & Legal Intelligence as a permanent IAM capability"
CONSEQUENCES = [
    "Adds twelve acquisition channels and a rights registry; does not alter any earlier decision.",
    "Enables independent training approval; ingestion approval alone never permits training.",
    "Keeps legal-context entries unverified until counsel records a reference.",
    "Does not change protected-core rules, signing authority or financial authority.",
]


def main() -> int:
    failures = preflight()
    if failures:
        for item in failures:
            print(f"FAIL {item}", file=sys.stderr)
        return 2

    endpoint = os.environ.get("IAM_ENDPOINT", "http://127.0.0.1:8000").rstrip("/")
    token = os.environ.get("IAM_API_TOKEN")
    channel = os.environ.get("IAM_CREATOR_CHANNEL", "creator_email")
    signer = os.environ.get("IAM_CREATOR_SIGNER")
    signer_id = os.environ.get("IAM_CREATOR_SIGNER_ID")
    if not token or not signer or not signer_id:
        print("IAM_API_TOKEN, IAM_CREATOR_SIGNER and IAM_CREATOR_SIGNER_ID are required", file=sys.stderr)
        return 2

    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "action_type": ACTION_TYPE, "target_ref": TARGET_REF,
        "risk_level": RISK_LEVEL, "channel": channel,
        "summary": SUMMARY, "consequences": CONSEQUENCES,
        "reason": "Owner requested Creator approval after implementation of Document 27.",
    }
    created = httpx.post(f"{endpoint}/api/v1/creator/requests", json=payload,
                         headers=headers, timeout=30)
    if created.status_code != 202:
        print(f"request failed: {created.status_code} {created.text[:500]}", file=sys.stderr)
        return 1
    request_id = created.json()["request_id"]

    challenge = httpx.get(f"{endpoint}/api/v1/creator/requests/{request_id}/challenge",
                          headers=headers, timeout=30)
    if challenge.status_code != 200:
        print(f"challenge failed: {challenge.status_code} {challenge.text[:500]}", file=sys.stderr)
        return 1
    digest = challenge.json()["challenge_hash"]
    message = f"{digest}|approved"

    result = subprocess.run(
        shlex.split(signer), input=message.encode("utf-8"),
        capture_output=True, timeout=60, check=False,
    )
    if result.returncode != 0:
        print(f"signer failed with exit {result.returncode}", file=sys.stderr)
        return 1
    signature = "".join(result.stdout.decode("utf-8", errors="replace").split())
    if not signature:
        print("signer produced no signature", file=sys.stderr)
        return 1

    decision = httpx.post(
        f"{endpoint}/api/v1/creator/requests/{request_id}/decide",
        json={"decision": "approved", "signature": signature, "signer_id": signer_id},
        headers=headers, timeout=30,
    )
    if decision.status_code != 200:
        print(f"decision rejected: {decision.status_code} {decision.text[:500]}", file=sys.stderr)
        return 1

    print(json.dumps({
        "request_id": request_id,
        "target_ref": TARGET_REF,
        "challenge_hash": digest,
        "signer_id": signer_id,
        "decision": decision.json().get("status") or "approved",
        "authority": "verified ED25519 signature",
        "next": "Send the request_id to the coding agent to record OD-45-style CONFIRMED.",
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
