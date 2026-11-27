# IAM — Web3 (thirdweb) and Umbrel Bitcoin/Lightning Integration Plan

**Version:** 1.0 · 27 November 2026
**Status:** **PROPOSED — implementation plan, not an architecture decision, not an implementation claim.**
**Authority:** `ARCHITECTURE_INDEX.md`, `IAM_FINAL_CONSOLIDATION.md`, `IAM_OWNER_DECISIONS.md`,
`IAM_BLOCKCHAIN_AND_BANKING.md` (Doc 09), `IAM_FINANCIAL_INTELLIGENCE_AND_ECONOMIC_INDEPENDENCE_SPEC.md` (Doc 25).
**Method:** repository inspection of `D:\AI\project-aura` at the working tree present on 27 November 2026.
No source code, migrations, OpenAPI output, decision register or architecture index was changed by this plan.

---

## 1. Purpose

Map the proposed thirdweb Web3 subsystem (WIBO) and the Umbrel Bitcoin/LND/CLN node
integration onto the **existing** IAM repository without duplicating its financial,
security, approval, provider-registry or ledger systems.

The proposed architecture is deliberately constrained by two locked facts found in
the repository:

1. **OD-23:** thirdweb is a **free-only** provider inside a replaceable Blockchain
   Integration Framework — not a core dependency, not a paid service.
2. **OD-04 / OD-25:** **zero standing budget**; every outgoing payment or transfer
   needs a signed Creator approval. There is no autonomous spending path to extend.

---

## 2. What actually exists today (source code is the truth for "what runs")

| Responsibility | Existing implementation | Current behaviour |
|---|---|---|
| Blockchain adapter | `backend/app/services/blockchain/service.py` | OD-23 free-only, testnet-only, **no network call is ever made**; writes are recorded only after `blockchain.write` signed authority; `CryptoActivity` rows + `AuditEvent`. |
| Blockchain API | `backend/app/api/routes/financial_adapters.py` (`/api/v1/blockchain`) | `/policy`, `/status`, `POST|GET /activities`. |
| Config | `backend/app/core/config.py` (lines 256–263) | `blockchain_enabled=False`, `blockchain_provider="thirdweb"`, `blockchain_rpc_url`, `blockchain_chain_id="11155111"`, env-var **names** for client id/secret, `blockchain_allow_mainnet=False`. |
| Spend authority | `backend/app/services/financial_policy.py` | `authorize_transaction()`; income autonomous; expense/transfer require signed `approval_id`; hard band **$1–$10 per transaction**, $100 monthly cap. |
| Creator authority | `backend/app/services/creatorapproval_service.py` | `check_authorization(action, requested_level, target_ref)`; ED25519 signature over one-time challenge; `LEVEL_ORDER = 1..4`; expiry, revocation, audit. |
| Ledger / reconciliation | `backend/app/services/ledger_service.py` | double-entry reconciliation, P&L, incoming receipts need separate `receive_payment` signed authority. |
| Provider gates | `backend/app/services/financial_intelligence/provider_registry.py`, `policy.py`, `provider_catalogue.py`, migration `030` | 8 gates; 37 seeded candidates; all unreviewed, all adapters disabled. `thirdweb` is **not** a candidate entry yet. |
| Secrets | `backend/app/core/secrets.py` | `<ENV>_FILE` Docker secret support, `read_secret()`, `enforce_secret_policy()` with placeholder rejection; `CredentialReference` model stores name/store/path only. |
| Field encryption | `backend/app/services/crypto_service.py` | AES-GCM **for conversation content**, not a wallet/key vault. Do not repurpose it as key storage. |
| Paper trading | `backend/app/services/trading/paper.py`, migration `023` | `simulation_only=true`, limits, emergency stop. |
| Banking adapter | `backend/app/services/banking/service.py` | consent-gated, no payment submission. |
| Audit | `backend/app/models/security.py` `AuditEvent` | append-only **by convention only** — no hash chain, no DB trigger preventing UPDATE/DELETE. |

**No Bitcoin, Lightning, wallet, Web3, x402, DeFi, NFT, bridge or RPC code exists in
`backend/`.** The only `lightning` match is the unrelated Lightning AI research
platform adapter in `backend/app/services/ai_research/adapters.py`.

---

## 3. Conflicts between the proposed scope and the frozen architecture

These must be resolved by the owner before implementation, not silently designed around.

| # | Proposed scope | Locked constraint | Resolution |
|---|---|---|---|
| C1 | "Select supported Engine/Transactions product and API version"; paid Engine/Transactions, paid RPC, paid storage | OD-23 forbids paid plans, upgrades, overage, paid gas sponsorship (Doc 09 §3.1) | Use free SDK/API quotas and **self-hosted open-source Engine only**. Any paid product requires a signed owner reopening of OD-23. |
| C2 | "Operational wallet with limited balance", "narrowly defined payments without approval", agent budgets, x402 auto-pay | OD-04 zero standing budget; OD-25 protected operations need creator approval | No standing crypto budget. x402 payments are **prepared/simulated only** until each payment gets its own signed Creator approval. A budget authority would be a signed OD-04 change. |
| C3 | Transaction authorisation **Level 5** (creator approval) | `LEVEL_ORDER` only supports 1–4; protected-core changes need OD-11 signed approval | Map protected operations to **level 4 + explicit action allowlist** (`treasury.withdraw`, `key.rotate`, `contract.upgrade`, `governance.change`). Adding level 5 to the engine is a protected-core change requiring signed approval. |
| C4 | "TypeScript SDK as primary implementation", React Native, Engine/Transactions as primary backend | Doc 01 §5 + Implementation Addendum: backend **Python/FastAPI**, TypeScript only web/SDK; OD-08 ARQ unchanged | Backend adapters in **Python** (`httpx`/JSON-RPC/REST) behind `BlockchainService`; thirdweb TypeScript SDK only in `frontend/` and `sdk/typescript/`. Node gateways (self-hosted Engine, Umbrel connector) are external HTTP services behind a Python adapter. |
| C5 | 12–20 new top-level Web3 modules; "permanent subsystem" with own intelligence | Doc 09 §3.3 already defines **10 engines inside existing systems**; OD-45/OD-49 patterns put new capabilities inside existing systems with **no new top-level system** | Implement WIBO as engines inside existing `financial`, `development`, `security` and `orchestration` systems. No seventeenth top-level system. |
| C6 | Bitcoin/LND/CLN connection and Tailscale | No owner decision covers self-hosted Bitcoin/Lightning nodes; OD-23 covers thirdweb only | Request a **new owner decision (proposed OD-50)** defining this as a separate, self-hosted adapter family. Do not fold it into OD-23 or into thirdweb. |
| C7 | "Immutable audit records" | `AuditEvent` is a plain table, mutable via normal DB access | New append-only `blockchain_audit_log` table with hash chaining + DB `UPDATE/DELETE` revocation, or a signed external WORM store. Gap must be closed before any write path. |
| C8 | "Full Web3 integration" including mainnet, treasury, token launches, DAO voting, DeFi investment | Doc 09 acceptance: testnets during development; mainnet needs separately authorised funds; Doc 25 §8 "simulated first", no real trading in first implementation | Free testnets and read-only mainnet *research* first; no mainnet value transfer until signed approval and a separate production gate. |

---

## 4. Proposed placement (no duplicate systems)

```
backend/app/services/
├── blockchain/                     # EXTEND — do not create a parallel service
│   ├── service.py                  # existing free-only policy + write gate
│   ├── providers/                  # NEW: universal adapter package
│   │   ├── base.py                 # BlockchainProvider protocol + capability registry
│   │   ├── thirdweb_adapter.py     # free-only; env-name credentials; read-first
│   │   ├── bitcoin_core_adapter.py # read-only RPC via Umbrel connector
│   │   ├── lnd_adapter.py          # REST + TLS macaroon; separate identity
│   │   └── cln_adapter.py          # CLNRest + rune; separate identity
│   ├── network_registry.py         # chain id, native asset, gas, confirmations, capability state
│   ├── wallet_registry.py          # metadata only — never keys
│   ├── transaction_manager.py      # build/simulate/nonce/gas/queue; NO broadcast by default
│   ├── intelligence/               # read-only chain/block/tx/token/holder analysis
│   └── audit.py                    # hash-chained append-only audit writer
├── financial_intelligence/
│   ├── provider_catalogue.py       # ADD thirdweb, Umbrel Bitcoin Core, LND, CLN candidates
│   └── provider_registry.py        # REUSE 8 gates before any adapter enablement
├── financial_policy.py             # REUSE for any spend; extend with crypto action types
├── ledger_service.py               # REUSE for reconciliation and P&L
└── creatorapproval_service.py      # REUSE for every authorization check
```

`backend/app/api/routes/financial_adapters.py` is extended with
`/api/v1/blockchain/{networks,wallets,transactions,payments,status}` and a new
`/api/v1/nodes/{bitcoin,lnd,cln}` router. New API prefixes require `admin` scope
(Doc 25 §24). `sdk/PROTOCOL.md` gains the versioned event/transaction contract;
`IAM_OPENAPI.json` is regenerated and the drift gate must pass.

**LND and CLN stay independent** — separate `node_id`, channels, balances, credentials,
payment history and health. The unified interface only *compares* them; it never merges
them or auto-routes between them.

---

## 5. Universal provider layer and capability registry

Follow Doc 09 §3 and Doc 25 §18: adapters are replaceable; IAM owns its records.

- `BlockchainProvider` protocol: `get_info`, `get_balance`, `get_block`, `get_transaction`,
  `get_logs`, `build_transaction`, `simulate_transaction`, `get_health`.
- `LightningProvider` protocol: `get_node_info`, `get_balance`, `get_peers`, `get_channels`,
  `get_invoices`, `get_payments`, `create_invoice`, `pay_invoice`, `get_health`.
- Capability registry per `(provider, network)` records: verified free tier, quota,
  chain ID, required confirmations, supported methods, last verified date, operator.
  Unknown/unverified capability **fails closed** — no fallback that changes signing
  authority, transaction semantics or security policy.
- Provider health registry tracks outages; failover is read-only unless both providers
  expose the same signed-authorization contract.

---

## 6. Authorization model mapping

| Operation | Level | Existing mechanism |
|---|---|---|
| Read balances, blocks, tx, channels, mempool, portfolio | Autonomous | default-off flag, no approval |
| Build/simulate tx, quote routes, gas estimate | Autonomous | no broadcast; recorded as prepared |
| Create invoice | Policy controlled | level 2 `receive_payment` (same pattern as `LedgerService.record_receipt`) |
| Pay invoice, broadcast tx, swap, bridge, stake, x402 purchase | Explicit approval | level 3–4 signed `approval_id`, plus `authorize_transaction()` caps |
| Treasury withdrawal, key rotation, contract upgrade, governance change | Creator approval | level 4 + action allowlist (C3); key/secret material never in model context |
| Change governance rules / protected core | Creator approval | OD-11 protected-core signed approval |

Every executed action must record `actor`, `approval_id`, chain/node, amount, recipient,
simulation result and audit hash. Replay protection via `(approval_id, chain, nonce or
payment_hash)` idempotency key; a timeout is never treated as failure — verify on-chain
state before any retry.

---

## 7. Credential handling (no keys in the model)

- Extend `config.py` `SECRET_FIELDS` and `secrets.py` placeholder checks with:
  `THIRDWEB_SECRET_KEY`, `BITCOIN_RPC_COOKIE`, `LND_MACAROON`, `CLN_RUNE`,
  `LND_TLS_CERT`, `CLN_CA_CERT` — all supplied via `<NAME>_FILE` Docker secrets (OD-07).
- Keep the existing pattern where config stores **environment-variable names**, never values.
- Store only `CredentialReference(integration_id, secret_name, secret_store, secret_path)`.
  No private key, seed phrase, macaroon, rune or RPC password in `AuditEvent.details`,
  `CryptoActivity`, logs, model context, notes or `tools/rkie/` notes.
- Restricted credentials: read-only macaroon and read-only rune first; no admin macaroon,
  no unrestricted rune. Separate credentials per node and per action class.
- Transport: Tailscale private network; TLS verification mandatory; no `-k`, no public
  8332/10009/8080/2107 port forwarding; no admin credentials to establish connectivity.

---

## 8. Database changes

Implemented migration: **`054_web3_and_nodes.sql`**, appended to `MIGRATION_ORDER.json` as sequence 54 (047–053 were added by concurrent work).
All tables use UUID PK, `created_at`, and references to `financial_transactions` /
`creator_authorizations` where financial.

| Table | Purpose |
|---|---|
| `web3_networks` | chain id, name, native asset, RPC provider ref, confirmations, capability JSON, verified_at |
| `web3_wallets` | wallet_id, domain (`operational`/`treasury`/`project`/`development`/`user`), address, provider ref, **no key material**, spending policy ref |
| `web3_transactions` | prepared/broadcast status, chain, from/to, token, amount, gas, approval_id, idempotency key, tx_hash |
| `web3_assets` / `web3_contracts` | token/contract metadata, standard, verified source, risk flags |
| `node_connections` | provider (`bitcoin_core`/`lnd`/`cln`), node_id, endpoint ref, health state |
| `node_wallet_balances`, `bitcoin_utxos`, `lightning_channels`, `lightning_peers`, `lightning_invoices`, `lightning_payments`, `lightning_events` | snapshots and history; LND/CLN rows always carry `node_id` |
| `blockchain_audit_log` | append-only: seq, prev_hash, entry_hash, event, actor, approval_id, payload JSON |
| `web3_provider_health` | provider, network, availability, latency, last check |

Enforce append-only with a DB trigger (`BEFORE UPDATE OR DELETE ... RAISE EXCEPTION`) and
hash chaining verified by a periodic ARQ job. Reconcile on-chain state against
`financial_transactions` through the existing `LedgerService`.

---

## 9. Implementation phases and gates

Each phase ends with tests; a phase is not "complete" until its tests pass.

| Phase | Work | Gate |
|---|---|---|
| **P0 — Decisions & spec** | Owner resolves C1–C8; proposed OD-50 for self-hosted nodes; freeze a Doc 30 spec if accepted | Signed owner decision; ARCHITECTURE_INDEX updated **by owner instruction** |
| **P1 — Registry & secrets** | Migration 047; provider candidates; credential fields; capability registry; audit table | `check_migrations.py` passes; no secret in DB/logs; audit trigger tested |
| **P2 — Read-only thirdweb** | Extend `BlockchainService` with free-tier read adapter; chains; no write path | Read tests with mocked HTTP; `network_calls_made` semantics preserved for `status()`; no paid call |
| **P3 — Read-only Umbrel** | Tailscale check; Bitcoin Core connector; LND REST; CLN CLNRest; separate identities | Connection tests with real endpoints supplied by operator; TLS verified; read-only macaroon/rune |
| **P4 — Unified intelligence** | Portfolio, tx tracing, channel/liquidity comparison, risk signals | Cross-node reports never merge identities; all sources cited |
| **P5 — Prepare-only transactions** | build/simulate, gas, nonce, slippage, route compare, idempotency | No broadcast in any test; signed approval required to enter broadcast state |
| **P6 — Approval-gated execution** | broadcast/pay/invoice/swap/bridge behind signed approval; x402 purchase | Every write test asserts signed approval + caps + audit hash; timeout/retry test |
| **P7 — Accounting & monitoring** | Ledger reconciliation, P&L, health, alerts, emergency suspension, recovery | Reconciliation tests; emergency stop across all adapters; SCB/CLN backup procedure documented |
| **P8 — Production gates** | Legal/KYC/tax review, contract security review, failover drill, audit verification | Owner-signed production approval; testnet/regtest evidence attached |

**Not in scope for P1–P8:** autonomous spending, mainnet value transfer without approval,
DAO voting, token launches, NFT marketplace, DeFi investment, paid thirdweb tiers.
Those are separate, later owner decisions.

---

## 10. Test and CI gates

Add `backend/tests/test_web3_adapters.py`, `test_node_adapters.py`,
`test_blockchain_audit.py`, using the `FakeDB` + patched `CreatorApprovalService`
pattern from `backend/tests/test_financial_adapters.py`.

Mandatory local gates (from `AGENTS.md` §3 and `.github/workflows/`):

```powershell
python tools/api/print_openapi.py --check
python tools/api/check_migrations.py
python -m ruff check backend
python -m unittest discover -s backend/tests -p 'test_*.py' -q
python -m compileall -q backend/app
python backend/tests/hbi_acceptance_check.py
```

`openapi-drift.yml`, `quality-gates.yml`, `supply-chain.yml` and `rkie-tests.yml` must also pass.

Security assertions that must appear in tests:
- paid feature requested → adapter paused, never auto-upgrade;
- write without `approval_id` → denied;
- unsigned / expired / mismatched `target_ref` approval → denied;
- amount above the $1–$10 band or $100 month cap → denied;
- secret values never appear in AuditEvent details or logs;
- LND and CLN node identities remain distinct;
- failover never changes signing authority;
- audit chain verification detects tampering.

---

## 11. Open owner decisions required before implementation

The one-page owner sign-off sheet with recommended defaults and the exact register text
is `IAM_OD50_SIGNOFF_SHEET.md`. The frozen functional scope is proposed as Doc 30 in
`IAM_WEB3_AND_UMBREL_NODE_INTEGRATION_SPEC.md` (including §8.1 wallet/address design and
§6.1 transaction lifecycle). Neither document is authority until OD-50 is signed.

1. **OD-50 (proposed):** self-hosted Bitcoin Core + LND + CLN as three independent
   node adapters inside the existing financial/development systems; no new top-level
   system; read-only first; Tailscale private transport.
2. Reopen **OD-23** only if paid thirdweb products are ever wanted (not recommended).
3. Reopen **OD-04/OD-25** only if any standing or autonomous crypto budget is wanted.
4. Decide whether to add a level 5 to `CreatorApprovalService`, or keep protected
   operations as level 4 + action allowlist **(recommended)**.
5. Decide scope ceiling: which of the 54 tracker items are Phase 1 versus deferred.
   This plan recommends read-only + prepare-only + approval-gated execution first.

---

## 12. Acceptance checklist for "integration complete"

- [ ] Every adapter has a registry entry with all 8 gates reviewed.
- [ ] No paid thirdweb feature reachable; no silent provider upgrade.
- [ ] IAM's wallet metadata, tx history and audit log survive provider replacement.
- [ ] Keys/macaroons/runes/cookies never enter model context, DB plain fields, logs or notes.
- [ ] Every outgoing crypto/payment action has signed approval + hard caps + idempotency.
- [ ] Incoming receipts never create spending authority.
- [ ] Transactions reconciled to the double-entry ledger.
- [ ] LND and CLN remain separate; combined dashboard is comparison only.
- [ ] Emergency suspension and disaster recovery tested, including Lightning channel backups.
- [ ] Tamper-evident audit log verified by a scheduled job.
- [ ] All CI gates pass; no duplicate finance, approval, provider or memory system added.

---

## 13. Implementation status (informational)

The read-only foundation (P1–P5), approval-gated execution (P6) and read-only
reconciliation (P7) have been added to the working tree. **Every write path is
default-off and requires a verified signed Creator authorization at execution time.**
No signing key is held by IAM; execution is delegated to an operator-reviewed
external executor. OD-50 remains unsigned, so no feature is enabled by default.

| Phase | Status | Evidence |
|---|---|---|
| P0 proposals | Drafted, unsigned | `IAM_WEB3_AND_UMBREL_NODE_INTEGRATION_SPEC.md`, `IAM_OD50_SIGNOFF_SHEET.md`, `scripts/creator_request_od50.py` (not run) |
| P1 registry/secrets/audit | Implemented | migration `054_web3_and_nodes.sql`; `models/web3.py`; hash-chained `blockchain/audit.py`; secrets and admin scopes wired |
| P2 read-only thirdweb | Implemented | `blockchain/providers/thirdweb_adapter.py`; paid features denied; no broadcast |
| P3 read-only nodes | Implemented | `bitcoin_core_adapter.py`, `lnd_adapter.py`, `cln_adapter.py`; TLS required; allowlists; separate identities |
| P4 unified intelligence | Implemented | `blockchain/node_service.py`; comparison only, no merged node |
| P5 prepare-only | Implemented | `transaction_manager.py` stops at `simulated`; `wallet_registry.py` metadata only |
| P6 approval-gated execution | Implemented | `governance.py` delegates to `CreatorApprovalService` + OD-04 caps; `transaction_manager.py` prepare→request→confirm→broadcast; LND/CLN invoice + pay behind level 2/3 signed authority |
| P7 accounting/monitoring | Implemented (no auto-correction) | read-only `reconciliation.py`, `/web3/reconcile`; `monitoring.py` writes `web3_alert` + high-severity `SecurityIncident`; automated correction deferred |
| P8 production gates | Partial | `activation.py` + `/web3/activation` + existing `/api/v1/deployment/preflight` now gate on signed OD-50 assertion, testnet evidence, executor URL and credentials; owner signature still pending |

Verification run: 25 new adapter/approval/activation/monitoring tests pass; `ruff`,
`compileall`, migration-order check, OpenAPI drift check and the 10 HBI acceptance gates
all pass. The append-only database trigger is defined in migration 054 and has **not**
been applied to a live database in this environment.

---

## 14. Relationship to existing documents

This plan is a **navigation document only**. It does not amend the frozen decision
register, does not create OD-50 until the owner confirms it, and does not claim any
capability is implemented beyond the informational status above. When implementation
and this plan disagree, the frozen specification wins for intent and source code
remains the truth for what runs.

**Concurrent-work note:** at final verification the wider suite had grown to 736 tests
and reported three failures in unrelated modules (`test_iics_foundation` (2) and
`test_p2p_and_aegis` (1)) while the Web3 subset passed in full. Those failures were not
introduced by the Web3 changes and were left untouched.
