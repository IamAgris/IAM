"""Redacted local Web3 activation check — no network calls, no secret values.

Prints only flag states, blocker names and credential *presence*. Use the API
(endpoint /api/v1/web3/activation) for the authoritative runtime check.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.core.config import settings
from app.core.secrets import read_secret
from app.services.blockchain.activation import check_web3_activation

FLAG_NAMES = (
    "web3_registry_enabled",
    "web3_audit_enabled",
    "web3_transaction_preparation_enabled",
    "web3_execution_enabled",
    "web3_monitoring_enabled",
    "thirdweb_read_enabled",
    "bitcoin_core_read_enabled",
    "lnd_read_enabled",
    "lnd_write_enabled",
    "cln_read_enabled",
    "cln_write_enabled",
    "web3_defi_enabled",
    "web3_x402_enabled",
    "web3_nft_enabled",
    "web3_dao_enabled",
    "web3_contract_dev_enabled",
    "web3_cross_chain_enabled",
    "web3_threat_intel_enabled",
    "web3_onchain_analysis_enabled",
    "web3_owner_decision_confirmed",
)

CREDENTIAL_NAMES = (
    "THIRDWEB_CLIENT_ID",
    "THIRDWEB_SECRET_KEY",
    "BITCOIN_RPC_COOKIE",
    "LND_TLS_CERT",
    "LND_MACAROON",
    "LND_WRITE_MACAROON",
    "CLN_CA_CERT",
    "CLN_RUNE",
    "CLN_WRITE_RUNE",
)


def presence(name: str) -> str:
    value = read_secret(name)
    if not value:
        return "missing"
    if any(marker in value.lower() for marker in ("change-me", "changethis")):
        return "placeholder"
    return "present"


def main() -> int:
    report = check_web3_activation()
    print("Web3 activation — REDACTED local report")
    print(f"  status: {report['status']} (inactive = no Web3 flag enabled)")
    print(f"  ready: {report['ready']}")
    print(f"  blockers: {', '.join(report['blockers']) or 'none'}")
    print(f"  warnings: {', '.join(report['warnings']) or 'none'}")
    print("\nFlags (all false = nothing enabled):")
    for name in FLAG_NAMES:
        print(f"  {name}={getattr(settings, name)}")
    print("\nCredential presence (values never shown):")
    for name in CREDENTIAL_NAMES:
        print(f"  {name}: {presence(name)}")
    print("\nOperator inputs not visible to this check:")
    print("  signed OD-55 challenge, Umbrel inspection report, executor reachability")
    print(f"\nMigration file present on disk: {(ROOT / 'backend/app/db/migrations/054_web3_and_nodes.sql').is_file()}")
    print("Applied to a live database: unknown (no database contacted)")
    print("\nNo secret values were printed.")
    return 0 if report["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
