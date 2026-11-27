# IAM — Web3 activation runbook (thirdweb + Umbrel nodes)

**Version:** 1.0 · 27 November 2026  
**Status:** **OPERATOR PROCEDURE.** It does not grant authority, sign anything, or enable a feature by itself.  
**Prerequisite:** proposed Doc 35 and the companion decisions in `IAM_OD55_SIGNOFF_SHEET.md` are reviewed. OD-55 remains unsigned until step 2 completes.  
**Safety rule:** no secret value is ever pasted into chat, a repository file, a log, or a model request. Only file paths and names are recorded.

---

## 0. The three inputs still required

| Input | Where it comes from | Who supplies it |
|---|---|---|
| Signed OD-55 challenge | Creator hardware signer via the existing approval API | Creator, outside IAM |
| Restricted node credentials + thirdweb secret | Generated on your Umbrel / thirdweb dashboard, stored as Docker secrets on Contabo | Operator |
| Protected executor endpoint | Self-hosted thirdweb Engine (free, open source) or equivalent signer on a private network | Operator |

None can be produced by the coding agent. The activation gate correctly blocks until they exist.

---

## 1. Inspect before changing anything

A read-only helper is provided: copy `scripts/umbrel_inspect.sh` to the Umbrel host and
run `bash umbrel_inspect.sh`. It writes `umbrel-web3-inspection.txt` with OS, Docker,
container/ports, IPs and Tailscale status — no credential values. Paste that report.
The manual equivalent is below.

On the Umbrel host (SSH):

```bash
cat /etc/os-release
sudo docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}'
sudo docker version
hostname -I
```

Record the **container names** for LND and Core Lightning and the certificate paths.
Do not assume the ports or paths quoted in earlier discussions — verify them.

---

## 2. OD-55 signature — the only source of decision authority

From a machine with the admin-scoped IAM token:

```powershell
$env:IAM_ENDPOINT = "https://<iam-private-endpoint>"
$env:IAM_API_TOKEN = "<scoped admin token>"
python scripts/creator_request_od55.py
```

The script prints `request_id`, `challenge_hash` and the exact signing message. It
creates a **pending** request and cannot approve anything. The Creator signs outside IAM:

```powershell
python -m iam_sdk.creator_cli sign <request_id> --approve `
  --signer "<hardware signer command>" --signer-id <signer-id>
```

Only `CreatorApprovalService.decide()` verifying the ED25519 signature makes the
decision effective. Only **after** that verification, the owner:

1. adds OD-55 and the accepted companion decisions to `IAM_OWNER_DECISIONS.md`;
2. adds a navigation row to `ARCHITECTURE_INDEX.md`;
3. changes proposed Doc 35 status to CONFIRMED;
4. sets `WEB3_OWNER_DECISION_CONFIRMED=true` on the IAM host.

Step 4 is an operator assertion that the signature exists. **The flag is not the
signature and does not replace it.**

---

## 3. Private network (Tailscale)

On Contabo:

```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up --accept-dns=false
tailscale status
tailscale ip -4
```

On Umbrel: install the official **Tailscale** app from the App Store, authenticate with
the same tailnet, and record its `100.x.x.x` address. Verify from Contabo:

```bash
tailscale ping <UMBREL_TAILSCALE_IP>
curl -I --connect-timeout 5 http://<UMBREL_TAILSCALE_IP>
```

Do **not** forward 8332, 10009, 8080 or 2107 to the public internet. TLS verification is
mandatory in the adapters; there is no `-k` option.

---

## 4. Restricted node credentials — generated on Umbrel

Copy `scripts/umbrel_web3_credentials.sh` to the Umbrel host, then:

```bash
export SECRET_DIR=/secure/iam-web3-secrets
export LND_CONTAINER=<name from docker ps>
export CLN_CONTAINER=<name from docker ps>
# Optional if paths differ:
# export LND_TLS_PATH=/root/.lnd/tls.cert
# export CLN_CA_PATH=/root/.lightning/ca.pem
bash umbrel_web3_credentials.sh
ls -l "$SECRET_DIR"     # paths and permissions only — never cat the files
```

The script bakes:

- LND **read** macaroon — GetInfo, WalletBalance, ChannelBalance, ListChannels, ListPeers, ListInvoices, ListPayments.
- LND **write** macaroon — AddInvoice + SendPaymentSync + GetInfo only.
- CLN **read** rune — `readonly` (get*/list*/summary, excluding `listdatastore`).
- CLN **write** rune — `invoice`, `pay`, `getinfo`, `listinvoices`, `listpays` only.
- LND TLS certificate and CLN CA certificate for verification.

Verify the exact syntax against the installed versions with
`lncli listpermissions` and `lightning-cli help createrune` before running the script.
No admin macaroon and no unrestricted rune is acceptable for IAM.

**Bitcoin Core:** keep RPC credentials inside an in-Umbrel connector. IAM receives only
a connector token in a Docker secret, never `rpcuser`/`rpcpassword`. The connector
exposes the eight read methods allowlisted in `bitcoin_core_adapter.py`.

Transfer the files to Contabo over the private network only (e.g. `scp` over Tailscale),
then register them as Docker secrets named by the config env variables in section 6.

---

## 5. Protected executor (the signing boundary)

IAM holds no signing key. Under OD-23 use **self-hosted open-source** thirdweb Engine —
never a paid hosted tier, paid RPC, paid gas sponsorship or automatic upgrade.

- Deploy Engine privately (its repository ships `docker-compose.yml` and `.env.example`; self-hosting is free).
- Restrict its API token and bind it to the Tailscale address only.
- Point `WEB3_EXECUTOR_URL` at that private endpoint.
- Keep Engine wallet keys in its own protected store; never copy them to IAM.
- Start on a testnet. `WEB3_TESTNET_EVIDENCE_REF` must reference recorded testnet/regtest evidence before execution is enabled.

If Engine is not yet deployed, leave `WEB3_EXECUTION_ENABLED=false`. The prepare and
approval-request flow still works; `broadcast` will deny because no executor is configured.

---

## 6. Configure IAM (names only — no values)

`.env.example` contains a complete `Doc 35 / OD-55` section with every variable,
all default-off and no secret values. Copy the relevant lines into the Contabo
environment / Docker secrets:

| Variable | Purpose |
|---|---|
| `WEB3_OWNER_DECISION_CONFIRMED=true` | Assert signed OD-55 exists (never a substitute for it) |
| `THIRDWEB_CLIENT_ID`, `THIRDWEB_SECRET_KEY_FILE` | free-tier thirdweb credentials |
| `THIRDWEB_BASE_URL` | operator-reviewed private RPC base |
| `BITCOIN_RPC_COOKIE_FILE`, `BITCOIN_CORE_CONNECTOR_URL` | in-Umbrel connector |
| `LND_TLS_CERT_FILE`, `LND_MACAROON_FILE`, `LND_REST_URL` | LND read |
| `LND_WRITE_MACAROON_FILE`, `LND_WRITE_ENABLED` | LND write (separate credential) |
| `CLN_CA_CERT_FILE`, `CLN_RUNE_FILE`, `CLN_REST_URL` | CLN read |
| `CLN_WRITE_RUNE_FILE`, `CLN_WRITE_ENABLED` | CLN write (separate credential) |
| `WEB3_EXECUTOR_URL`, `WEB3_EXECUTION_ENABLED` | protected external signer |
| `WEB3_TESTNET_EVIDENCE_REF` | reference to testnet evidence |

Enable in this order, one flag at a time:

1. `WEB3_REGISTRY_ENABLED`, `WEB3_AUDIT_ENABLED`
2. `THIRDWEB_READ_ENABLED`, `BITCOIN_CORE_READ_ENABLED`, `LND_READ_ENABLED`, `CLN_READ_ENABLED`
3. `WEB3_TRANSACTION_PREPARATION_ENABLED`
4. `WEB3_MONITORING_ENABLED`
5. only then `LND_WRITE_ENABLED`, `CLN_WRITE_ENABLED`, `WEB3_EXECUTION_ENABLED`

---

## 7. Activation checks

```powershell
# Local, offline, redacted check — no network call, no secret values printed
python scripts/check_web3_activation.py

# Authoritative runtime checks (redacted; names and statuses only)
GET /api/v1/web3/activation
GET /api/v1/deployment/preflight
```

Expected while unsigned: blockers `web3_owner_decision`, `web3_testnet_evidence`,
`web3_executor` when execution is requested. Read-only flags can be enabled once the
decision flag and credentials are in place. Then verify:

```powershell
GET  /api/v1/web3/networks?testnet_only=true
GET  /api/v1/nodes/bitcoin
GET  /api/v1/nodes/lightning
GET  /api/v1/nodes/compare          # independent nodes; identities never merged
GET  /api/v1/web3/audit/verify
GET  /api/v1/web3/reconcile
POST /api/v1/web3/monitoring/run
```

---

## 8. First value-moving test (testnet only)

1. `POST /api/v1/web3/transactions/prepare` → status `simulated`.
2. `POST /api/v1/web3/transactions/{id}/approval-request` → pending Creator request.
3. Creator signs the returned challenge via the hardware signer.
4. `POST /api/v1/web3/transactions/{id}/approve` with `approval_id` and `amount_usd` → status `approved`.
5. `POST /api/v1/web3/transactions/{id}/broadcast` → re-verifies authority, then submits to the executor.

A timeout is never treated as failure. Verify on-chain state before any retry; the
idempotency key `(approval_id, chain_id, nonce or payment_hash)` prevents double submission.

Mainnet value movement requires the separate signed production gate in Doc 35 §1.1.

---

## 9. Rollback

- Set all Web3 flags back to `false` — every adapter stops immediately.
- LND: `lncli deletemacaroonid <root_key_id>` (identify the IAM macaroon's root key first).
- CLN: `lightning-cli blacklistrune <rune>`.
- Revoke the Engine API token; keep the audit log and transaction history intact.
- A database backup is **not** a Lightning channel backup — preserve LND SCBs and the CLN recovery material separately.

---

## 10. What cannot be completed from this machine

The OD-55 signature, the Umbrel/LND/CLN/thirdweb credentials, and the executor endpoint
are outside this environment. Everything else — code, schemas, approval flow, activation
gate, monitoring and tests — is implemented and verified. The gate is the authority check:
if it reports a blocker, the corresponding input has not been supplied yet.
