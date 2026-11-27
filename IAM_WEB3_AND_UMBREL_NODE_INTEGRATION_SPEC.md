# IAM — Web3 and Self-Hosted Bitcoin/Lightning Integration Specification

**Document:** 30 (proposed addendum to Documents 01–29)  
**Version:** 1.0 · 27 November 2026  
**Status:** **PROPOSED — awaiting a signed owner decision (OD-50).** A chat message is not authority. This document does not alter the frozen baseline, `IAM_OWNER_DECISIONS.md`, `ARCHITECTURE_INDEX.md` or any locked decision until OD-50 is confirmed through `CreatorApprovalService.decide()` with an ED25519 signature over a one-time challenge. It is a design specification, **not** an implementation or security-validation claim.  
**Parent:** `IAM_FINAL_CONSOLIDATION.md`, `ARCHITECTURE_INDEX.md`, `IAM_OWNER_DECISIONS.md`  
**Related:** Doc 09 `IAM_BLOCKCHAIN_AND_BANKING.md` (OD-23/24/25), Doc 25 `IAM_FINANCIAL_INTELLIGENCE_AND_ECONOMIC_INDEPENDENCE_SPEC.md` (OD-44), `IAM_IMPLEMENTATION_TECHNOLOGY_ADDENDUM.md`, Doc 15 (OD-31), Doc 14 (OD-30), Doc 28 (OD-48), `IAM_SECURITY_AND_INTERNET_POLICY.md`, `IAM_PRIVACY_AND_SECRETS.md`, `IAM_API_CONTRACTS.md`, `IAM_DATABASE_DESIGN.md`, `IAM_WEB3_AND_NODE_INTEGRATION_PLAN.md`, `IAM_OD50_SIGNOFF_SHEET.md`  
**Proposed decision:** OD-50 (Web3 operations and self-hosted Bitcoin/Lightning node adapters)  
**Governing principle:** **IAM remains the brain; infrastructure providers are replaceable. Capability is not authority, and access is not permission to spend.**

---

## 0. Executive summary

IAM gains a permanent, provider-independent Web3 capability and three independent
self-hosted node connections. Both are placed **inside existing systems** as engines
and adapters — no new top-level system, no new AI identity, no new authority over the
Creator, and no dependency of IAM's core reasoning on any external blockchain provider.

The specification is governed by four immutable distinctions:

1. **Intelligence vs infrastructure.** IAM reasons, plans, validates and governs.
   thirdweb, Bitcoin Core, LND and CLN provide data and transport.
2. **Capability vs authority.** Being able to build, simulate or broadcast a transaction
   is not permission to broadcast it. Every value movement needs signed Creator approval.
3. **Free vs paid.** OD-23 permits free-tier and self-hosted open-source infrastructure
   only. An exhausted allowance pauses the adapter; it never silently upgrades.
4. **One intelligence, three nodes.** Bitcoin Core, LND and CLN keep separate identities,
   wallets, channels, balances, credentials and histories. IAM compares them; it never
   merges them or assumes a shared wallet.

No Bitcoin, Lightning, wallet, Web3, x402, DeFi, NFT, bridge or RPC implementation exists
in the repository at the time of writing. The sole existing blockchain code is the
free-only, no-network-call adapter in `backend/app/services/blockchain/service.py`,
which this specification **extends** rather than duplicates.

---

## 1. Proposed owner decision OD-50

The following text is proposed for addition to `IAM_OWNER_DECISIONS.md` **only after**
the owner signs a Creator approval request. It is reproduced here for review.

> **OD-50 — Web3 operations and self-hosted Bitcoin/Lightning nodes.**
> Add a permanent, provider-independent Web3 and node-integration capability **inside
> existing IAM systems** (principally financial, development, security and
> orchestration), not as a sixteenth or seventeenth top-level system and not as a new
> AI identity. Approve (a) extension of the existing OD-23 free-only blockchain
> adapter with read-only and prepare-only capabilities across verified networks; and
> (b) three **independent** adapters for the operator's self-hosted Bitcoin Core, LND
> and Core Lightning nodes over an encrypted private network, read-only first. All
> outgoing payments, transfers, swaps, broadcasts, channel operations, key rotations
> and governance changes require signed Creator approval under OD-03/OD-04/OD-25;
> IAM never grants itself financial authority. Credentials, keys, macaroons, runes and
> RPC secrets are held in Docker secrets (OD-07) and never enter model context, ordinary
> database fields, logs or notes. No paid thirdweb tier, no paid RPC, no paid gas
> sponsorship and no automatic provider upgrade is permitted without separately
> reopening OD-23. Testnet/regtest first; mainnet value movement requires a separate
> signed production gate. This decision does not change identity (OD-01), signing
> (OD-03), financial authority (OD-04/OD-25), protected core (OD-11), Creator channels
> (OD-18/19/42), model set (OD-38/OD-46), resources (OD-39), research (OD-41) or any
> other locked decision. **A chat message is not authority; confirmation requires a
> verified ED25519 signature over the one-time challenge.**

### 1.1 Companion decisions the owner must resolve

| ID | Question | Recommendation |
|---|---|---|
| OD-23-a | May any paid thirdweb product ever be used? | **No** — retain free-only |
| OD-04-a | May IAM hold a standing crypto operational budget? | **No** — retain zero standing budget |
| OD-25-a | Add authorization level 5? | **No** — protected operations stay level 4 + action allowlist |
| OD-50-a | Scope ceiling for the first build | Read-only + prepare-only + approval-gated execution (P1–P8) |
| OD-50-b | Mainnet value movement | Deferred to a separate signed production gate |

The one-page owner sign-off sheet with accept/reject checkboxes and the exact register
text is `IAM_OD50_SIGNOFF_SHEET.md`. Each recommendation is independent: rejecting one
does not reopen or alter any other locked decision. The defaults are the only combination
that fits the frozen architecture — OD-23 forbids paid tiers, OD-04 forbids standing
budgets, adding level 5 is an OD-11 protected-core change, and Doc 25 §8 requires
simulation before value movement.

---

## 2. Scope

### 2.1 Adds

- Provider-independent `BlockchainProvider` and `LightningProvider` interfaces with a
  per-provider/per-network capability registry.
- Read-only blockchain and Lightning intelligence: blocks, transactions, events,
  balances, UTXOs, channels, peers, liquidity, fees, invoices and payments.
- Prepare-only transaction building, simulation, gas/nonce management and route quotes.
- Approval-gated execution: broadcast, pay, invoice, swap, bridge, channel operations.
- x402 service discovery and purchase **preparation**; no autonomous payment.
- Append-only, tamper-evident audit records and reconciliation to the existing ledger.
- Three independent node identities under one comparison interface.

### 2.2 Extends

- `backend/app/services/blockchain/service.py` — the OD-23 free-only adapter.
- `backend/app/services/financial_intelligence/provider_registry.py` — the eight gates.
- `backend/app/services/financial_policy.py` — the OD-04 spend path.
- `backend/app/services/ledger_service.py` — reconciliation and incoming receipts.
- `backend/app/services/creatorapproval_service.py` — the sole authorization gate.
- `backend/app/api/routes/financial_adapters.py` — the existing `/api/v1/blockchain` surface.
- `sdk/PROTOCOL.md` and `IAM_OPENAPI.json` — versioned contracts.

### 2.3 Does not

- Create a new top-level system, a treasury AI, or a second finance/security stack.
- Change any locked decision or the system count.
- Expose private keys, seed phrases, macaroons, runes or RPC passwords to the model,
  browser, SDK clients, logs, notes or ordinary database fields.
- Enable autonomous spending, paid thirdweb tiers, mainnet value transfer without a
  signed gate, DAO voting, token launches, NFT marketplaces or DeFi investment in P1–P8.
- Treat timeout as failure, or retry a broadcast/payment without verifying state first.
- Claim any capability is implemented or security-tested until its acceptance tests pass.

---

## 3. Permanent governing axioms

1. **Free-only means free-only.** No paid plan, add-on, overage, paid RPC capacity,
   paid storage, paid gas sponsorship or paid Engine/Transactions upgrade. Self-hosted
   open-source Engine is permitted. An exhausted allowance pauses the adapter.
2. **Unknown capability is a deny.** A network, method or provider not present in the
   verified capability registry is unavailable. No silent fallback that changes signing
   authority, transaction semantics or security policy.
3. **Prepare is not execute.** Building, simulating or quoting a transaction never
   broadcasts it. Broadcast requires a distinct signed authorization.
4. **Zero standing budget.** Incoming receipts never create spending authority. Every
   outgoing value movement needs its own signed approval, the $1–$10 per-transaction
   band and the $100 monthly cap (OD-04).
5. **Separate domains.** Operational, treasury, project, development and user wallets
   are never mixed. Treasury and protected operations need creator approval.
6. **Three nodes, one interface.** LND and CLN have distinct node IDs, channels,
   balances, credentials and payment histories. A combined view is comparison only.
7. **Keys never cross into intelligence.** Credential references, not values, are stored
   in application data. The model sees addresses and hashes, never secrets.
8. **Irreversibility is assumed.** Blockchain and Lightning payments are treated as
   final unless the specific protocol provides a documented reversal.
9. **Audit survives providers.** IAM owns wallet metadata, transaction records,
   policy decisions and audit history; they survive provider replacement.
10. **Fail closed.** Missing configuration, expired approval, unverified TLS, unknown
    chain, malformed response or provider outage produces a denial/pause, never a guess.

---

## 4. Capability map — proposed scope onto frozen architecture

The twelve proposed WIBO modules and the Umbrel additions are **engines inside existing
systems**, not new top-level systems. This mirrors the Doc 09 ten-engine pattern and the
OD-45/OD-49 placement rule.

| Proposed capability | Frozen home | Implementation shape |
|---|---|---|
| 01 Wallet intelligence & management | Doc 09 engine 3 (Wallet & Treasury) | `web3_wallets` registry; metadata only |
| 02 Smart account infrastructure | Doc 09 engine 3 / development | ERC-4337 support behind capability registry |
| 03 Blockchain intelligence | Doc 09 engine 2 (Network) | read-only adapter + network registry |
| 04 Cryptocurrency intelligence | Doc 25 financial departments | research-only; extends existing market research |
| 05 Smart contract intelligence | Doc 09 engine 4 | analysis/deploy engines; testnet first |
| 06 Token & digital asset management | Doc 09 engines 4/5 | token registry; asset metadata |
| 07 DeFi | Doc 09 engine 7 | individually enabled, governed; no auto-invest |
| 08 Cross-chain operations | Doc 09 engines 2/5 | bridge research + approval-gated execution |
| 09 Web3 payments & commerce | Doc 25 payment management | existing `financial_policy` spend path |
| 10 AI agent economy & x402 | Doc 25 payment management | discovery + prepare-only purchase; escrow policy |
| 11 Web3 development & deployment | Doc 09 engine 4 / development systems | contracts, tests, sandbox, no unreviewed prod deploy |
| 12 Blockchain security & governance | Doc 09 engines 8/9/10 | risk engine, audit, approval, emergency stop |
| Bitcoin Core node | Doc 09 blockchain framework | `bitcoin_core_adapter.py`, read-only RPC |
| LND node | Doc 09 blockchain framework | `lnd_adapter.py`, separate identity |
| Core Lightning node | Doc 09 blockchain framework | `cln_adapter.py`, separate identity |
| Unified node intelligence | existing financial/development systems | comparison interface only |

---

## 5. Architecture

```
IAM — Primary Intelligence (local Qwen, reasoning, memory, governance)
        │
        ├── Existing governed planes (unchanged)
        │     CreatorApprovalService · financial_policy · LedgerService
        │     ProviderRegistryService · AuditEvent · CredentialReference
        │
        ├── Web3 & Node Intelligence (engines inside existing systems)
        │     research · analysis · transaction preparation · risk · monitoring
        │
        ├── Universal Web3 Adapter (this spec)
        │     BlockchainProvider / LightningProvider protocols
        │     capability registry · network registry · wallet registry
        │     provider health · failover (read-only) · audit writer
        │
        └── Providers
              thirdweb (free tier only)     Bitcoin Core (self-hosted)
              independent EVM providers     LND (self-hosted, separate)
                                            CLN (self-hosted, separate)
```

### 5.1 Provider interfaces (versioned contract)

`BlockchainProvider`: `get_info`, `get_balance`, `get_block`, `get_transaction`,
`get_logs`, `build_transaction`, `simulate_transaction`, `get_health`.

`LightningProvider`: `get_node_info`, `get_balance`, `get_peers`, `get_channels`,
`get_invoices`, `get_payments`, `create_invoice`, `pay_invoice`, `get_health`.

A provider that cannot implement a method reports `unsupported`; the registry records
it as unavailable for that provider/network. It never guesses or substitutes.

### 5.2 Capability and network registry

 Per `(provider, network)` entry records: chain ID, native currency, RPC/API reference,
 confirmed free-tier status, quota/limit, supported methods, confirmation requirement,
 contract-standard compatibility, risk notes, `verified_at`, and reviewing operator.
 Unverified entries are disabled. thirdweb is the primary EVM adapter; at least one
 independent RPC/indexing path is retained for comparison and read-only failover.

### 5.3 Node connection rules

- Private transport (Tailscale or equivalent) between the IAM host and the Umbrel host;
  no public forwarding of Bitcoin RPC, LND REST/gRPC or CLNRest ports.
- TLS verification mandatory; no disabled certificate checks.
- Read-only credentials first: restricted LND macaroon, restricted CLN rune, restricted
  Bitcoin RPC credentials. No admin macaroon or unrestricted rune for routine access.
- The exact UmbrelOS version, container names, bound ports and API versions must be
  inspected on the operator's installation before any adapter is configured. Ports and
  endpoints quoted in earlier discussions are **unverified** until tested.
- Umbrel middleware is an optional additional route, not a dependency; direct adapters
  remain authoritative.

---

## 6. Financial authority matrix

| Operation | Level | Mechanism |
|---|---|---|
| Read balances, blocks, transactions, channels, mempool, portfolio | Autonomous | default-off feature flag, no approval |
| Build/simulate transaction, quote routes, estimate gas | Autonomous | no broadcast; recorded as `prepared` |
| Create Lightning invoice | Policy controlled | level 2 `receive_payment` signed authority |
| Pay invoice, broadcast transaction, swap, bridge, stake, x402 purchase | Explicit approval | level 3–4 signed `approval_id` + `authorize_transaction()` caps |
| Treasury withdrawal, key rotation, contract upgrade, ownership/governance change | Creator approval | level 4 + action allowlist; protected-core changes follow OD-11 |
| Change financial governance or signing rules | Creator approval | OD-11 protected-core signed approval |

Required checks before any signed execution: chain ID, recipient, token/contract, amount,
gas/fee, approval level and `target_ref` match, expiry, revocation, replay/idempotency key,
simulation result, malicious-approval detection (including unlimited allowances), and
risk-engine verdict. A mismatch denies.

### 6.1 Transaction lifecycle state machine

Every transaction record follows one state machine. Only a signed approval moves it
from `awaiting_approval` to `approved`; only a separate execution call moves it to
`broadcast`. No code path may skip a state.

```
draft → validated → simulated → awaiting_approval → approved
      → broadcast → confirming → confirmed → reconciled
                 ↘ rejected / expired / failed / replaced / cancelled
```

| State | Entry condition | Allowed exit |
|---|---|---|
| `draft` | user/agent request recorded | `validated` |
| `validated` | chain, recipient, token, amount, contract validated | `simulated` |
| `simulated` | simulation and risk verdict recorded | `awaiting_approval` |
| `awaiting_approval` | signed Creator request created, challenge pending | `approved`, `expired`, `rejected` |
| `approved` | `decide()` verified signature, `approval_id` bound | `broadcast`, `cancelled` |
| `broadcast` | provider accepted the signed transaction | `confirming`, `failed` |
| `confirming` | hash observed, confirmations below requirement | `confirmed`, `replaced` |
| `confirmed` | confirmation requirement met | `reconciled` |
| `reconciled` | ledger entry matched to transaction | terminal |
| `failed` / `replaced` / `cancelled` / `expired` / `rejected` | failure or invalidation | terminal |

A timeout in `broadcast` or `confirming` never triggers a retry by itself: the node/provider
state is queried first, and the idempotency key `(approval_id, chain_id, nonce or payment_hash)`
prevents double submission.

---

## 7. Credentials and secrets

- Add to `SECRET_FIELDS` and `secrets.py` placeholder checks: `THIRDWEB_SECRET_KEY`,
  `BITCOIN_RPC_COOKIE`, `LND_MACAROON`, `CLN_RUNE`, `LND_TLS_CERT`, `CLN_CA_CERT`.
- Supply every value through `<NAME>_FILE` Docker secrets (OD-07). Keep the existing
  convention that configuration stores environment-variable **names**, never values.
- Store only `CredentialReference(integration_id, secret_name, secret_store, secret_path)`.
- Prohibited: private keys, seed phrases, raw macaroons, raw runes, RPC passwords in
  `AuditEvent.details`, `CryptoActivity`, logs, model context, chat output, notes,
  indexes or Git. `CryptoService` is conversation field encryption, not a key vault.
- Rotate credentials on suspected compromise; emergency suspension revokes all active
  node and provider authorizations without deleting audit history.

---

## 8. Data model (migration `047_web3_and_nodes.sql`)

Append as sequence 47 to `MIGRATION_ORDER.json`. UUID primary keys and `created_at`
on every table; foreign keys to `financial_transactions` and `creator_authorizations`
where financial. No key material in any column.

| Table | Purpose |
|---|---|
| `web3_networks` | chain id, name, native asset, provider ref, confirmations, capability JSON, `verified_at` |
| `web3_wallets` | wallet id, domain, address, provider ref, policy ref — metadata only |
| `web3_transactions` | prepared/broadcast state, chain, from/to, token, amount, gas, `approval_id`, idempotency key, tx hash |
| `web3_assets`, `web3_contracts` | token/contract metadata, standard, verified source, risk flags |
| `node_connections` | provider, `node_id`, endpoint ref, health state |
| `node_wallet_balances`, `bitcoin_utxos` | Bitcoin snapshots |
| `lightning_channels`, `lightning_peers`, `lightning_invoices`, `lightning_payments`, `lightning_events` | per-node Lightning records, always keyed by `node_id` |
| `web3_provider_health` | provider, network, availability, latency, last check |
| `blockchain_audit_log` | append-only: `seq`, `prev_hash`, `entry_hash`, event, actor, `approval_id`, payload JSON |

`blockchain_audit_log` is protected by a database trigger rejecting `UPDATE`/`DELETE`,
and entries are hash-chained. A periodic ARQ job verifies the chain. Existing
`AuditEvent` rows remain the general audit stream; blockchain audit entries are written
to both, with the hash stored in `AuditEvent.details`.

### 8.1 Wallet and address registry design (P1 design, not implemented)

**Purpose.** Give IAM a durable, provider-independent record of every address it uses
without ever storing the material that controls it. The registry is metadata only:
an address is a routing destination, **not** an identity and **not** an authority.

#### Wallet domains — separate by construction

| Domain | Purpose | Key custody | Default policy | Notes |
|---|---|---|---|---|
| `operational` | approved service payments, fee payment | provider server wallet / smart account | signed approval per outgoing action | low balance only; never holds treasury funds |
| `treasury` | long-term assets, business income | multisig or protected server wallet | level 4 + signed Creator approval | no autonomous movement; key rotation needs creator approval |
| `project` | per-project funds and contracts | provider server wallet | signed approval, project-scoped `target_ref` | cannot spend across projects |
| `development` | testnet/regtest experiments | testnet wallet | reads autonomous; testnet writes recorded | no production credentials, no mainnet value |
| `user` | user-owned or connected wallets | user custody | IAM never holds the key | linked to an IAM identity, never replaces it |

#### Address identity and lifecycle

- `wallet_id` is a ULID (OD-01) and is immutable. A blockchain address is a property
  of a wallet, not IAM's permanent identity.
- Each address is unique per `(provider, network, address)`; the stored value is
  normalised (EVM lowercase/checksum form; native-chain encoding per network).
- Lifecycle: `proposed → verified → active → suspended → retired`. Only `active`
  addresses may receive or send value. Suspension is reversible by the Creator;
  retirement keeps the audit history.
- Ownership verification uses a signed message (SIWE for EVM), provider attestation
  for server wallets, or an explicit Creator approval. Evidence is stored as a
  reference in `web3_wallets`; the signature itself is not a credential.
- Multiple addresses per wallet per network are allowed. Address reuse is recorded
  and flagged for privacy/risk review; it is never silent.

#### Account abstraction and scoped permissions

- ERC-4337 smart accounts are enabled only where the capability registry marks the
  network as supported. Gas sponsorship is free-tier only; paid sponsorship is denied.
- Session keys are scoped by `(wallet_id, network, allowed_methods, expiry, spend_cap)`
  and are signed by the Creator. A session key cannot create another session key.
- Multisig is required for treasury. Any change to signers or thresholds is a
  protected operation (level 4 + allowlist).

#### Address risk and reconciliation

- Each address carries risk flags from independent sources: phishing/drainer reports,
  address-poisoning indicators, sanction/exposure signals and unusual minting or
  approval activity. No single score is authoritative; a positive signal requires
  review, not an automatic verdict.
- Unknown new recipient → level 4 approval. Allowlisted recipient → still bounded by
  the OD-04 caps. Denylisted recipient → hard deny regardless of approval.
- Periodic reconciliation compares registry balances, UTXOs and channel balances with
  provider state and the existing `financial_transactions` ledger. Differences produce
  an alert and an `AuditEvent`, never a silent correction.

#### Wallet design invariants

1. No key, seed phrase, derivation path secret, macaroon or rune in `web3_wallets`,
   `AuditEvent`, logs, model context, notes or Git.
2. A wallet address never grants identity authority; OD-01 ULID remains the identity.
3. Legal ownership of assets follows OD-02 (owner/entity), not IAM.
4. Incoming funds to any wallet never create spending authority (OD-25).
5. Wallet separation is enforced in code by `wallet_id` scoping on every query and
   transaction, not by convention.

---

## 9. API contract (default-off, `admin` scope)

Extend `/api/v1/blockchain`:
`GET /networks`, `GET /wallets`, `POST /transactions/prepare`,
`GET /transactions`, `GET /health`, `GET /policy`, `GET /status`,
`POST /payments/x402/prepare`.

Add `/api/v1/nodes`:
`GET /bitcoin/{info,balance,mempool,transactions}`,
`GET /lnd/{info,balance,channels,peers,invoices,payments,health}`,
`GET /cln/{info,balance,channels,peers,invoices,payments,health}`,
`GET /compare` (read-only comparison; never a merged node).

Every new prefix requires `admin` scope (Doc 25 §24), is default-off, and returns
`403` for unsigned execution attempts. `IAM_OPENAPI.json` is regenerated; the OpenAPI
drift gate must pass.

---

## 10. Security and threat model

Covered by the risk engine: phishing/drainer contracts, malicious or unlimited token
approvals, rug-pull indicators, compromised credentials, suspicious minting, exploit
disclosures, bridge and oracle vulnerabilities, flash-loan patterns, address poisoning,
supply-chain compromise, MEV/sandwich risk, reorganisation/finality risk and stuck or
replaced transactions. Risk signals come from multiple independent sources; no single
score is authoritative.

Additional controls: transaction simulation before signing; slippage protection;
nonce and fee management; idempotency; emergency suspension; daily reconciliation of
internal records against chain/node state; backup verification including LND Static
Channel Backups and the CLN recovery procedure appropriate to the installed version.
A database backup is not a Lightning channel backup.

---

## 11. Implementation phases

| Phase | Work | Completion gate |
|---|---|---|
| P0 | Owner resolves §1.1; OD-50 signed; this spec frozen as Doc 30 | Verified signature; register/index updated by owner instruction |
| P1 | Migration 047; provider candidates; secret fields; registries; hash-chained audit | `check_migrations.py` passes; no secret in DB/logs; audit trigger tested |
| P2 | Read-only thirdweb adapter; network registry; no write path | Mocked read tests pass; no paid call; `status()` preserves no-network-call semantics |
| P3 | Read-only Bitcoin Core / LND / CLN adapters over private network | Real endpoint tests with operator-supplied config; TLS verified; restricted credentials |
| P4 | Unified intelligence; portfolio, tracing, channel comparison, risk signals | Reports never merge node identities; sources cited |
| P5 | Prepare-only transactions; gas, nonce, slippage, route comparison, idempotency | No broadcast in any test |
| P6 | Approval-gated execution; x402 purchase preparation; invoice/channel operations | Every write test asserts signed approval, caps, audit hash and replay protection |
| P7 | Ledger reconciliation, P&L, health monitoring, alerts, emergency stop, recovery | Reconciliation and emergency-stop tests pass; backup procedures documented |
| P8 | Legal/KYC/tax review, contract security review, failover drill, production gate | Owner-signed production approval with testnet/regtest evidence |

### 11.1 Preparing the OD-50 signature — what can be done without authority

The following is preparatory only. None of it confirms a decision or changes the
repository's frozen files.

| Step | Action | Authority granted |
|---|---|---|
| 1 | Owner reviews Doc 30 and the five companion decisions in `IAM_OD50_SIGNOFF_SHEET.md` | None |
| 2 | Owner records accept/reject for OD-23-a, OD-04-a, OD-25-a, OD-50-a, OD-50-b | None — a proposal state |
| 3 | Operator supplies the Umbrel inspection results and scoped `IAM_API_TOKEN` | None |
| 4 | `python scripts/creator_request_od50.py` creates a **pending** Creator request | None — request only |
| 5 | Creator hardware signer signs `challenge_hash|approved` | Creator authority, outside IAM |
| 6 | `CreatorApprovalService.decide()` verifies signer, expiry, nonce and ED25519 signature | Decision becomes effective |
| 7 | Only then: register entry, architecture index navigation row, Doc 30 status → CONFIRMED | Effective |

IAM never self-approves. A chat message, a checked Markdown box, an unsigned request
and a prepared script are not authority. Until step 6 completes, P1 code, migrations
and network access remain blocked.

---

## 12. Acceptance criteria

1. No paid thirdweb feature is reachable; an exhausted allowance pauses the adapter.
2. No key, seed, macaroon, rune, RPC password or secret key appears in model context,
   database plain fields, logs, notes or Git.
3. Reads work without any write capability enabled.
4. No transaction broadcasts without a valid, unexpired, unrevoked signed approval with
   matching `target_ref`; amounts above the per-transaction or monthly cap are denied.
5. Incoming receipts never create spending authority.
6. LND and CLN remain independent; the combined view is comparison only.
7. Failover never changes signing authority, transaction semantics or policy.
8. Timeout is never treated as failure; retries verify state first.
9. All financial operations reconcile to the existing double-entry ledger.
10. Emergency suspension works across all providers and nodes; recovery is tested.
11. Hash-chained audit verification detects tampering.
12. Every provider has reviewed §18 gates before its adapter is enabled.
13. All CI gates pass: compile, unit tests, HBI acceptance, integration DB check,
    OpenAPI drift, migration check, ruff and supply-chain checks.
14. No duplicate finance, approval, provider-registry, memory or search system added.

---

## 13. Relationship to other documents

- Extends Doc 09 §3 (blockchain framework, ten engines) without replacing it.
- Extends Doc 25 (financial intelligence) using its existing ledger, approval and
  provider-gate systems.
- Subject to OD-01 (identity), OD-03 (signing), OD-04/OD-25 (financial authority),
  OD-07 (secrets), OD-08 (ARQ), OD-11 (protected core), OD-15/OD-35 (free-first,
  replaceable providers), OD-18/19/42 (Creator channels), OD-22 (ARM64/x86-64),
  OD-23 (thirdweb free-only), OD-39 (resources), OD-48 (legal/IP governance) and
  OD-49 (browser/security boundaries).
- Supersedes nothing. It is a proposal until OD-50 is signed; if the owner rejects it,
  this document remains a historical proposal and no implementation proceeds.

**Decision sign-off sheet:** `IAM_OD50_SIGNOFF_SHEET.md` — five companion decisions, exact
register text, checklist and request-preparation commands. It is a proposal, not authority.

**Implementation plan:** `IAM_WEB3_AND_NODE_INTEGRATION_PLAN.md`.
