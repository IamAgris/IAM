# Web3 / Umbrel node integration (proposed Doc 33 / OD-53) — implementation map

**Date:** 27 November 2026 · **Based on:** current working tree (uncommitted). Verified
locally with `Search-IAMRepo.ps1 -Mode files` for `blockchain`, `web3`, `lnd`, `cln` and
`-Mode docs` for `OD-50`/`OD-53`. OD-53 is **not** confirmed; this note is navigation,
not authority. Re-verify against current files before reusing it.

## Why OD-53 / Doc 33

`IAM_OWNER_DECISIONS.md` and `ARCHITECTURE_INDEX.md` already assign **OD-50 / Document 30**
to the confirmed Voice & Hearing System and OD-51/OD-52 to Docs 31–32. The original Web3
proposal used colliding numbers; all proposal documents, the Creator request script and
code comments were renumbered to OD-53 / Doc 33. A cached `OD-50` reference is stale.

## Existing systems reused (not duplicated)

| Existing system | File | Reuse |
|---|---|---|
| Creator authority | `backend/app/services/creatorapproval_service.py` | all Web3 writes call `check_authorization`; no second approval engine |
| OD-04 spend gate | `backend/app/services/financial_policy.py` | `authorize_transaction()` enforces signed approval, caps and monthly limit |
| Provider gates | `backend/app/services/financial_intelligence/provider_registry.py`, `provider_catalogue.py` | 8 gates; thirdweb + three node candidates added, all unreviewed |
| Ledger | `backend/app/services/ledger_service.py` | read-only reconciliation in `blockchain/reconciliation.py` |
| Secrets | `backend/app/core/secrets.py`, `config.py` | `<NAME>_FILE` Docker secrets; conditional production checks |

## Implementation files

| Path | Role |
|---|---|
| `backend/app/models/web3.py`, `backend/app/db/migrations/054_web3_and_nodes.sql` | 15 tables, append-only hash-chained audit trigger |
| `backend/app/services/blockchain/providers/` | thirdweb (free-only), Bitcoin Core, LND, CLN read adapters + allowlists; execute methods deny |
| `backend/app/services/blockchain/governance.py` | action→level map, `ExecutionAuthorization`, signed-approval recheck at execution |
| `backend/app/services/blockchain/{audit,transaction_manager,wallet_registry,node_service,reconciliation,monitoring,activation}.py` | core lifecycle, registries, alerting and activation gate |
| `backend/app/services/blockchain/{defi,x402,contracts,nft,dao,cross_chain,threat_intel,onchain_analysis}.py` | research/prepare modules (Doc 33) |
| `backend/app/services/blockchain/{keccak,secp256k1,wallet_ecosystem}.py` | real SIWE verification without a new dependency |
| `backend/app/services/blockchain/{transaction_ops,registries,emergency,accounting,web3_learning,business,non_evm,fiat}.py` | operations and governance records |
| `backend/app/api/routes/web3.py`, `web3_extended.py` | `/api/v1/web3*`, `/api/v1/nodes*` (admin scope) |
| `backend/tests/test_web3_adapters.py`, `test_web3_extended.py`, `test_web3_ops.py` | 54 tests |

## Gates and status

54 Web3 tests pass; full suite passed 893 tests; `ruff`, `compileall`, migration order,
OpenAPI drift and 10 HBI acceptance gates pass. All feature flags default-off; migration
has not been applied to a live DB; no network call was made and no credential was read.

## External inputs still required at runtime (not development blockers)

Signed OD-53 challenge; Umbrel inspection results; restricted LND/CLN credentials and
thirdweb secret; operator-reviewed executor URL. Procedure:
`IAM_WEB3_ACTIVATION_RUNBOOK.md`. Helper: `scripts/umbrel_web3_credentials.sh`.
