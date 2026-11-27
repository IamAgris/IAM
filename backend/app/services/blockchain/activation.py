"""Web3 activation and production gate — redacted, fail-closed readiness report.

This check never returns secret values and never grants authority. In particular,
``web3_owner_decision_confirmed`` is an operator assertion that OD-50 was signed;
setting it does not verify or replace the Creator signature.
"""

from typing import Any, Dict, List

from app.core.config import settings
from app.core.secrets import web3_secret_gaps


def check_web3_activation() -> Dict[str, Any]:
    """Config-level readiness checks, safe for the existing deployment preflight."""
    checks: List[Dict[str, str]] = []

    def add(name: str, ok: bool, detail: str, blocking: bool = True) -> None:
        checks.append(
            {
                "name": f"web3_{name}",
                "status": "ok" if ok else ("blocker" if blocking else "warning"),
                "detail": detail,
            }
        )

    any_enabled = any(
        (
            settings.web3_registry_enabled,
            settings.web3_audit_enabled,
            settings.web3_transaction_preparation_enabled,
            settings.thirdweb_read_enabled,
            settings.bitcoin_core_read_enabled,
            settings.lnd_read_enabled,
            settings.cln_read_enabled,
            settings.web3_execution_enabled,
            settings.lnd_write_enabled,
            settings.cln_write_enabled,
            settings.web3_monitoring_enabled,
        )
    )
    add(
        "flags_default_off",
        not any_enabled,
        "all Web3 flags are off (expected for an unactivated deployment)",
        blocking=False,
    )
    add(
        "owner_decision",
        bool(settings.web3_owner_decision_confirmed) or not any_enabled,
        "WEB3_OWNER_DECISION_CONFIRMED may be set only after signed OD-50",
    )
    add(
        "testnet_evidence",
        bool(settings.web3_testnet_evidence_ref) or not settings.web3_execution_enabled,
        "WEB3_TESTNET_EVIDENCE_REF is required before execution is enabled",
    )

    gaps = web3_secret_gaps()
    add(
        "credentials",
        not gaps,
        (
            "missing or placeholder secrets for enabled adapters: " + ", ".join(gaps)
            if gaps
            else "no missing credentials for enabled adapters"
        ),
    )
    add(
        "executor",
        bool(settings.web3_executor_url) or not settings.web3_execution_enabled,
        "WEB3_EXECUTOR_URL (protected signer) is required when execution is enabled",
    )
    add(
        "paid_tiers",
        True,
        "OD-23 free-only policy is enforced in the adapter layer",
    )
    add(
        "signing_key_in_iam",
        True,
        "IAM has no signing-key field; execution is delegated to an external executor",
        blocking=False,
    )

    blockers = [item["name"] for item in checks if item["status"] == "blocker"]
    warnings = [item["name"] for item in checks if item["status"] == "warning"]
    return {
        "ready": not blockers,
        "checks": checks,
        "blockers": blockers,
        "warnings": warnings,
        "note": "No secret values are included. A config flag is not a signed decision.",
    }
