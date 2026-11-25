"""Creator CLI — review IAM requests and sign decisions locally.

No email is involved. The CLI reads the challenge from the Core API, asks an
external signer command (hardware key, HSM, ssh-agent wrapper, air-gapped tool)
to sign exactly ``<challenge_hash>|<decision>``, and posts the signature back.
The signature — not the message or the channel — is the authority (OD-03/OD-19).

Usage:
    python -m iam_sdk.creator_cli pending
    python -m iam_sdk.creator_cli show <request_id>
    python -m iam_sdk.creator_cli challenge <request_id>
    python -m iam_sdk.creator_cli decide <id> --approve --signature <base64> --signer-id <id>
    python -m iam_sdk.creator_cli sign <id> --approve --signer "python sign_with_key.py"

Environment: IAM_CORE_URL (default http://localhost:8000), IAM_TOKEN (scoped token),
and optionally IAM_CF_ACCESS_CLIENT_ID / IAM_CF_ACCESS_CLIENT_SECRET for Cloudflare Access.
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import binascii
import json
import os
import shlex
import subprocess
import sys
from typing import Any

from .client import IAM

DECISIONS = ("approved", "rejected")


def signing_message(
    challenge: dict[str, Any], decision: str, expected_request_id: str | None = None
) -> str:
    """Exact bytes the Creator signer must sign.

    ``expected_request_id`` is the request the operator asked to decide. When it
    is supplied, the challenge must be for that same request — otherwise a
    challenge for a different request could be signed and replayed.
    """
    if decision not in DECISIONS:
        raise ValueError("decision must be 'approved' or 'rejected'")
    digest = challenge.get("challenge_hash")
    if not isinstance(digest, str) or not digest.strip():
        raise ValueError("challenge_hash is missing from the challenge response")
    returned_id = challenge.get("request_id")
    if expected_request_id and returned_id and returned_id != expected_request_id:
        raise ValueError("challenge request_id mismatch")
    return f"{digest}|{decision}"


def clean_signature(stdout: str) -> str:
    """Validate the signer's base64 output before submitting it."""
    signature = "".join(stdout.split())
    if not signature:
        raise ValueError("signer produced no signature")
    try:
        raw = base64.b64decode(signature, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError("signer output is not valid base64") from exc
    if len(raw) < 16:
        raise ValueError("signature is suspiciously short")
    return signature


def _iam() -> IAM:
    return IAM(
        endpoint=os.environ.get("IAM_CORE_URL", "http://localhost:8000"),
        token=os.environ.get("IAM_TOKEN"),
        access_client_id=os.environ.get("IAM_CF_ACCESS_CLIENT_ID"),
        access_client_secret=os.environ.get("IAM_CF_ACCESS_CLIENT_SECRET"),
    )


def _print(payload: Any) -> None:
    print(json.dumps(payload, indent=2, default=str))


async def _pending(_: argparse.Namespace) -> None:
    _print(await _iam().creator.pending())


async def _show(args: argparse.Namespace) -> None:
    iam = _iam()
    _print(await iam.creator.get(args.request_id))
    _print(await iam.creator.challenge(args.request_id))


async def _challenge(args: argparse.Namespace) -> None:
    _print(await _iam().creator.challenge(args.request_id))


async def _decide(args: argparse.Namespace) -> None:
    decision = "approved" if args.approve else "rejected"
    signature = clean_signature(args.signature)
    _print(await _iam().creator.decide(
        args.request_id, decision, signature, args.signer_id
    ))


async def _sign(args: argparse.Namespace) -> None:
    """Run a local signer command, then submit the signed decision."""
    decision = "approved" if args.approve else "rejected"
    iam = _iam()
    challenge = await iam.creator.challenge(args.request_id)
    message = signing_message(challenge, decision, args.request_id)
    signer_id = args.signer_id or challenge.get("signer_id") or os.environ.get(
        "IAM_CREATOR_SIGNER_ID", ""
    )
    if not signer_id:
        raise ValueError("signer_id is required (--signer-id or challenge/signer env)")

    argv = shlex.split(args.signer)
    if not argv:
        raise ValueError("--signer must be a command")
    if args.signer_input == "stdin":
        result = subprocess.run(
            argv, input=message.encode(), capture_output=True, timeout=args.timeout, check=False
        )
    else:
        result = subprocess.run(
            argv + [message], capture_output=True, timeout=args.timeout, check=False
        )
    if result.returncode != 0:
        raise RuntimeError(
            f"signer failed with exit {result.returncode}: "
            + result.stderr.decode(errors="replace")[:300]
        )
    signature = clean_signature(result.stdout.decode(errors="replace"))

    if args.dry_run:
        _print({"dry_run": True, "request_id": args.request_id, "decision": decision,
                "signature_length": len(signature)})
        return
    _print(await iam.creator.decide(args.request_id, decision, signature, signer_id))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="iam-creator", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("pending").set_defaults(handler=_pending)
    p_show = sub.add_parser("show")
    p_show.add_argument("request_id")
    p_show.set_defaults(handler=_show)
    p_challenge = sub.add_parser("challenge")
    p_challenge.add_argument("request_id")
    p_challenge.set_defaults(handler=_challenge)

    p_decide = sub.add_parser("decide")
    p_decide.add_argument("request_id")
    group = p_decide.add_mutually_exclusive_group(required=True)
    group.add_argument("--approve", action="store_true")
    group.add_argument("--reject", action="store_true")
    p_decide.add_argument("--signature", required=True)
    p_decide.add_argument("--signer-id", required=True)
    p_decide.set_defaults(handler=_decide)

    p_sign = sub.add_parser("sign")
    p_sign.add_argument("request_id")
    group2 = p_sign.add_mutually_exclusive_group(required=True)
    group2.add_argument("--approve", action="store_true")
    group2.add_argument("--reject", action="store_true")
    p_sign.add_argument("--signer", required=True, help="local command that signs the message")
    p_sign.add_argument("--signer-id", help="defaults to challenge or IAM_CREATOR_SIGNER_ID")
    p_sign.add_argument("--signer-input", choices=("arg", "stdin"), default="arg")
    p_sign.add_argument("--timeout", type=int, default=60)
    p_sign.add_argument("--dry-run", action="store_true")
    p_sign.set_defaults(handler=_sign)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        asyncio.run(args.handler(args))
        return 0
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
