# IAM — OD-50 one-page sign-off sheet

**Version:** 1.0 · 27 November 2026  
**Status:** **PROPOSAL FOR OWNER REVIEW — no decision is made by this sheet.** A chat message, a checked box in a Markdown file and an unsigned request are not authority. OD-50 and its companion decisions become effective only after `CreatorApprovalService.decide()` verifies an ED25519 signature from the configured Creator signer over the one-time challenge.  
**Source documents:** `IAM_WEB3_AND_UMBREL_NODE_INTEGRATION_SPEC.md` (proposed Doc 30) and `IAM_WEB3_AND_NODE_INTEGRATION_PLAN.md`.  
**Rule:** the recommended defaults below are the architect's proposals. The owner may accept or reject each independently. Rejection of any item does not reopen another locked decision.

---

## A. Companion decisions — recommended defaults

| Ref | Question | Recommended default | Effect if accepted | Owner response |
|---|---|---|---|---|
| OD-23-a | May any paid thirdweb product be used? | **No — retain free-only** | Self-hosted open-source Engine and free-tier SDK/RPC/storage only; paid feature pauses the adapter. Keeps OD-23 untouched. | ☐ Accept ☐ Reject ☐ Discuss |
| OD-04-a | May IAM hold a standing crypto operational budget? | **No — retain zero standing budget** | Every outgoing value movement keeps its own signed approval; $1–$10/tx band and $100/month cap stay in force. Keeps OD-04 untouched. | ☐ Accept ☐ Reject ☐ Discuss |
| OD-25-a | Add authorization level 5? | **No — level 4 + action allowlist** | `CreatorApprovalService.LEVEL_ORDER` stays `1..4`; protected operations are level 4 with an explicit action allowlist. No protected-core change. | ☐ Accept ☐ Reject ☐ Discuss |
| OD-50-a | Scope ceiling for the first build | **Read-only + prepare-only + approval-gated execution (P1–P8)** | Defer DAO voting, token launches, NFT marketplace, DeFi investment and mainnet value movement to later decisions. | ☐ Accept ☐ Reject ☐ Discuss |
| OD-50-b | Mainnet value movement | **Deferred to a separate signed production gate** | Testnet/regtest evidence, legal/KYC/tax review and contract security review required before any mainnet spend. | ☐ Accept ☐ Reject ☐ Discuss |

**Why these defaults:** they are the only combination that fits the frozen architecture.
OD-23 already forbids paid tiers; OD-04 already forbids standing budgets; adding level 5
to the approval engine is an OD-11 protected-core change; and Doc 25 §8 requires
simulation before real value movement.

---

## B. Exact proposed decision text for the register

Paste into `IAM_OWNER_DECISIONS.md` only after the signature is verified:

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

---

## C. Sign-off checklist

- ☐ Owner has read proposed Doc 30 (`IAM_WEB3_AND_UMBREL_NODE_INTEGRATION_SPEC.md`).
- ☐ Owner has accepted or rejected each of the five companion decisions in section A.
- ☐ Owner has confirmed the Umbrel inspection results (OS version, containers, ports, Tailscale reachability).
- ☐ `IAM_ENDPOINT` and `IAM_API_TOKEN` are set for the request endpoint.
- ☐ Creator signer is available and its public key matches `CREATOR_PUBLIC_KEY`.
- ☐ Prepared request is created with `scripts/creator_request_od50.py` (no signature yet).
- ☐ Creator signs `challenge_hash|approved` with the external hardware signer.
- ☐ `CreatorApprovalService.decide()` verifies `signer_id`, expiry and ED25519 signature.
- ☐ Only then: add OD-50 to the decision register and a navigation row to `ARCHITECTURE_INDEX.md`.
- ☐ Only then: freeze Doc 30 by changing its status from PROPOSED to CONFIRMED.

---

## D. Commands to prepare the request (no authority granted)

```powershell
# 1. Review the proposal (read-only)
Get-Content IAM_WEB3_AND_UMBREL_NODE_INTEGRATION_SPEC.md

# 2. Prepare the pending request — creates a request, does NOT approve anything
$env:IAM_ENDPOINT = "https://<iam-private-endpoint>"
$env:IAM_API_TOKEN = "<scoped admin token>"
python scripts/creator_request_od50.py

# 3. Creator signs the returned challenge with the external hardware signer
python -m iam_sdk.creator_cli sign <request_id> --approve `
  --signer "<hardware signer command>" --signer-id <signer-id>
```

The script prints the `request_id`, `challenge_hash` and exact signing message. It exits
with code 2 if `IAM_API_TOKEN` is absent. It never calls `/decide` and never holds a
private key.

---

## E. Operator inputs required before activation (names only — no values)

Nothing below is set in the repository. Supply them through Docker secrets on the
IAM host, and set flags only after the signature in section C is verified.

| Input (env / secret name) | Purpose | Required when |
|---|---|---|
| `WEB3_OWNER_DECISION_CONFIRMED=true` | Operator assertion that signed OD-50 exists | any Web3 flag enabled |
| `WEB3_TESTNET_EVIDENCE_REF` | Reference to testnet/regtest evidence | execution enabled |
| `THIRDWEB_CLIENT_ID` / `THIRDWEB_SECRET_KEY_FILE` | free-tier thirdweb credentials | `THIRDWEB_READ_ENABLED=true` |
| `BITCOIN_RPC_COOKIE_FILE` | in-Umbrel connector credentials | `BITCOIN_CORE_READ_ENABLED=true` |
| `LND_TLS_CERT_FILE`, `LND_MACAROON_FILE` (read-only) | LND read access | `LND_READ_ENABLED=true` |
| `LND_WRITE_MACAROON_FILE` | separate write-scoped macaroon | `LND_WRITE_ENABLED=true` |
| `CLN_CA_CERT_FILE`, `CLN_RUNE_FILE` (read-only) | CLN read access | `CLN_READ_ENABLED=true` |
| `CLN_WRITE_RUNE_FILE` | separate write-scoped rune | `CLN_WRITE_ENABLED=true` |
| `WEB3_EXECUTOR_URL` | protected external signer / Engine endpoint | `WEB3_EXECUTION_ENABLED=true` |
| `THIRDWEB_BASE_URL`, `BITCOIN_CORE_CONNECTOR_URL`, `LND_REST_URL`, `CLN_REST_URL` | operator-reviewed private endpoints | matching adapter enabled |

Run the redacted gate before enabling anything:

```powershell
GET /api/v1/web3/activation          # config-level readiness, no secrets returned
GET /api/v1/deployment/preflight     # includes the Web3 activation checks
POST /api/v1/web3/monitoring/run     # requires WEB3_MONITORING_ENABLED=true
```

The gate blocks activation while OD-50 is unsigned, testnet evidence is absent,
the external executor URL is missing, or a required secret is a placeholder.

---

## F. What this sheet does not do

- It does not confirm OD-50 or any companion decision.
- It does not edit the decision register, architecture index or source code.
- It does not authorize network access, wallet creation, payments or migrations.
- It does not replace the Creator's signature with a chat instruction.
