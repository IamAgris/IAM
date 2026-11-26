# IAM — Distributed Network & Authority Gap Analysis

**Version:** 1.0 · 24 November 2026  
**Scope:** Original architecture + new P2P network, creator authority, restricted reporting, IAM Aegis and OEDIE  
**Parent:** `IAM_ARCHITECTURE_GAP_ANALYSIS.md` (original four documents)  
**Source:** `IAM_DISTRIBUTED_ARCHITECTURE.md` (Document 05)

---

## 1. Summary

| Category | Findings | Blocking |
|----------|----------|----------|
| Trust model & cryptographic identity | 9 | 3 |
| Creator signing authority | 7 | 2 |
| Synchronisation protocols | 8 | 2 |
| Restricted reporting | 7 | 2 |
| Recovery & revocation | 6 | 2 |
| IAM Aegis | 9 | 2 |
| OEDIE | 6 | 1 |
| Data model | 6 | 1 |

**Assessment:** The confirmed decisions are coherent and complete at the policy level. The gaps are concrete design and implementation details that must be resolved before any distributed code is written. The most important is that **integrity reporting is best-effort** — the architecture must never overstate what attestation can prove.

---

## 2. Trust model & cryptographic identity

| ID | Gap | Required resolution |
|----|-----|---------------------|
| DT-01 | Trust-level transitions not fully specified | Define state machine: Untrusted → Provisioning → Restricted/Trusted → Revoked, with permitted transitions and who authorises each |
| DT-02 | Ed25519 key lifecycle undefined | Generation, storage (hardware/secret store), rotation, compromise handling, death — BLOCKING |
| DT-03 | Trust list freshness undefined | Signed trust list with sequence numbers and expiry; peers must reject stale lists — BLOCKING |
| DT-04 | Attestation report schema undefined | Define fields: deployment ID, core manifest hash, platform measurement, software version, timestamp, signature, confidence |
| DT-05 | Known-good manifest distribution undefined | Creator-signed, versioned manifests; how peers obtain and verify them |
| DT-06 | Local trust overrides vs creator authority conflict | Local overrides may restrict, never elevate, trust — must be explicit |
| DT-07 | Trust decisions not audited | Every trust change writes an immutable audit event |
| DT-08 | Bootstrapping a brand-new peer undefined | Provisioning flow with creator approval; no implicit trust |
| DT-09 | Metadata privacy in P2P undefined | Peer discovery must not leak operator identity/location beyond necessity |

**Blocking:** DT-02, DT-03, and a defined transition state machine (DT-01).

---

## 3. Creator signing authority

| ID | Gap | Required resolution |
|----|-----|---------------------|
| CA-01 | Creator root key storage | Hardware-backed per OD-03; offline/cold storage; defined signing ceremony |
| CA-02 | Key hierarchy undefined | Root key → release signing key → deployment attestation key; scope and expiry per key |
| CA-03 | Release signing process undefined | What is signed (manifest, packages, hash), by whom, verification path — BLOCKING |
| CA-04 | Key compromise response | Root key revocation and network rebootstrap procedure |
| CA-05 | Authority delegation undefined | Whether creator can delegate limited signing (e.g. release-only) and how |
| CA-06 | Hardware signer integration | Concrete integration with the OD-03 hardware/external signer (dependency) |
| CA-07 | Signing audit log | Every signature request, approval and output recorded |

**Blocking:** CA-01 and CA-03.

---

## 4. Synchronisation protocols

| ID | Gap | Required resolution |
|----|-----|---------------------|
| SY-01 | Transport undefined | Choose concrete transport (libp2p/QUIC/mTLS over WS) — BLOCKING |
| SY-02 | Message envelope schema | Signed envelope: sender, type, payload hash, sequence, timestamp, signature |
| SY-03 | Knowledge object format | Content-addressed object schema and acceptance rules |
| SY-04 | Anti-entropy algorithm | Merkle-based reconciliation; conflict policy with creator authority |
| SY-05 | Store-and-forward semantics | Queue, expiry, replay protection for offline peers |
| SY-06 | Rate/size limits | Prevent sync abuse and resource exhaustion |
| SY-07 | Partial sync / resumption | Checkpoints so peers resume after long outages |
| SY-08 | Network partitions | Behaviour during split; no divergent trusted state |

**Blocking:** SY-01 and SY-02.

---

## 5. Restricted reporting

| ID | Gap | Required resolution |
|----|-----|---------------------|
| RR-01 | Modification detection criteria | What counts as "modified": file hashes, config drift, unsigned extensions — BLOCKING |
| RR-02 | Restricted channel protocol | Signed status reports to creator IAM; no peer P2P; transport and cadence |
| RR-03 | Permitted creator communications | What creator may send to restricted peers (policy, updates, attestation instructions) |
| RR-04 | Re-attestation procedure | Exact steps and authority to return to Trusted — BLOCKING |
| RR-05 | Self-downgrade enforcement | Deployment must downgrade itself even if it cannot contact creator |
| RR-06 | Reporting honesty limits | Must state confidence; cannot claim a compromised host is trustworthy |
| RR-07 | Restricted peer isolation | Cannot distribute code/knowledge; cannot access privileged capabilities |

**Blocking:** RR-01 and RR-04.

---

## 6. Recovery & revocation

| ID | Gap | Required resolution |
|----|-----|---------------------|
| RC-01 | Revocation broadcast | How revocations propagate and are verified — BLOCKING |
| RC-02 | Revoked peer data handling | Peers delete/quarantine data from revoked peers |
| RC-03 | Rebuild procedure | Re-image from signed release → re-attest → creator re-adds |
| RC-04 | Reporting after revocation | Any channel separately authorised; never trusted by default |
| RC-05 | Lost creator key recovery | Rebootstrap procedure with out-of-band verification |
| RC-06 | Backup of trust state | Recovery must not restore stale trust lists as authoritative |

**Blocking:** RC-01 and RC-03.

---

## 7. IAM Aegis

| ID | Gap | Required resolution |
|----|-----|---------------------|
| AG-01 | eBPF/LSM/TPM learning path | Concrete study plan and isolated VM lab (learn → reproduce) |
| AG-02 | Reference vs dependency boundary | Shirudo optional; Aegis independent; no runtime dependency on pre-release code |
| AG-03 | Protected security code | Aegis core signed by creator; IAM cannot rewrite it |
| AG-04 | Defence package trust | Report vs executable distinction; signature + review + local testing |
| AG-05 | Host resource limits | Lightweight by default; intensive analysis only on demand |
| AG-06 | False-positive handling | Testing against legitimate workloads; rollback of bad protections |
| AG-07 | Emergency containment scope | Only pre-approved policies; no new authority during incident |
| AG-08 | Distributed validation workflow | Detect → reproduce → develop → validate → evaluate → distribute |
| AG-09 | Compatibility with varied kernels | Documented supported kernel matrix; graceful degradation |

**Blocking:** AG-01 and AG-03.

---

## 8. OEDIE

| ID | Gap | Required resolution |
|----|-----|---------------------|
| OE-01 | Tool evaluation score/schema | Structured evaluation record matching §8.1 criteria |
| OE-02 | Licence/attribution tracking | Store licences and attribution obligations; SPDX identifiers |
| OE-03 | Trial vs free distinction | Explicit field; trials never treated as permanent |
| OE-04 | Paid activation gate | Requires creator/hardware approval; zero standing budget applies |
| OE-05 | Replacement workflow | How a better free alternative supersedes an existing integration |
| OE-06 | P2P sharing rules | Share validated evaluations, not unreviewed executables |

**Blocking:** none; OE-01 needed before implementation.

---

## 9. Data model additions

Add to canonical ERD: `peers`, `peer_identities`, `trust_decisions`, `attestation_records`, `integrity_manifests`, `signed_releases`, `update_records`, `sync_state`, `sync_conflicts`, `knowledge_objects`, `threat_reports`, `defence_packages`, `oedie_discoveries`, `oedie_evaluations`, `tool_registry_entries`, `creator_signing_keys`, `revocation_records`, `restricted_reports`.

Private keys must never be stored in these tables — hardware/secret-store references only.

---

## 10. Reconciled implementation order for distributed systems

| Phase | Deliverable | Gate |
|-------|-------------|------|
| D0 | Creator signing root + hardware signer integration + key hierarchy | CA-01/CA-03 resolved |
| D1 | Peer identity + trust state machine + signed trust list | DT-01/02/03 resolved |
| D2 | P2P transport + signed envelopes + store-and-forward | SY-01/02 resolved |
| D3 | Integrity manifests + attestation + restricted reporting | RR-01/04 resolved |
| D4 | Distributed knowledge sync + creator trust authority | SY-03/04 resolved |
| D5 | Revocation + recovery + re-attestation | RC-01/03 resolved |
| D6 | Aegis learning lab + protection engine (creator-signed) | AG-01/03 resolved |
| D7 | Distributed threat intelligence + defence validation | AG-04/08 resolved |
| D8 | OEDIE + evaluation records + P2P discovery sharing | OE-01 resolved |

---

## 11. Assessment

The distributed architecture is well-founded and internally consistent. The confirmation that integrity reporting is best-effort is essential and must be reflected in every attestation UI and API response.

No contradiction with the original four documents was found. The new systems extend, not replace, the protected core. Implementation of distributed systems should follow phases D0–D8 after the base Phase 0/1 build, and must not begin until the blocking gaps above are resolved.

---

## 12. White-hat defence additions (OD-16)

Source: `IAM_WHITEHAT_AND_WORKSPACE.md` (Document 06).

| ID | Gap | Required resolution |
|----|-----|---------------------|
| WH-01 | Authorised-target policy schema undefined | **Resolved in code** — `backend/app/services/security_policy.py` verifies exact/CIDR targets against active signed `creator_authorizations` with expiry, revocation, allow-write and operation checks; shared gate at `POST /api/v1/cybersecurity/authorize-target`; Aegis no longer uses prefix matching |
| WH-02 | Tool gateway offensive restriction list | **Resolved in code** — canonical `FORBIDDEN_CAPABILITIES` taxonomy enforced by `SecurityGuard.validate_operation`, Aegis scope checks and the authorised-target gate; exposed at `GET /api/v1/cybersecurity/policy` |
| WH-03 | Scope verification outside personality prompt | **Resolved in code** — enforced by `security_policy`, Security Guard, Aegis scope checks, the authorised-target gate and isolated workspace/session services |
| WH-04 | Security Simulation Lab isolation spec | **Resolved in code** — `SecurityWorkSession` + `WhiteHatLabService` create disposable, signed-scope-bound labs in the isolated workspace manager, with TTL expiry and destruction |
| WH-05 | Remediation validation workflow | **Resolved in code** — `POST /api/v1/aegis/remediations/validate` runs a bounded check in an isolated workspace and marks a fix `verified` only when execution actually completes |
| WH-06 | P2P offensive-tool exclusion rule | **Resolved in code** — `ensure_p2p_shareable()` restricts topics to report/research/signed_fix/finding/status and rejects executable payloads in outbound and inbound envelopes |
| WH-07 | Audit schema for security operations | **Resolved in code** — `build_security_audit()` records target, scope, authority, tool calls, approval and changes for every security work session |
| WH-08 | Framework study plan | **Resolved in code** — `GET /api/v1/aegis/study-plan` publishes the OWASP/ATT&CK/D3FEND/NIST CSF/CIS/pentest/secure-coding/IR plan |
| WH-09 | "Learning ≠ capability" enforcement | **Resolved in code** — `ensure_learning_only()` rejects executable fields and offensive capabilities in study records; study policy grants no execution or capability |

**Resolved:** WH-01–WH-09 are enforced outside the prompt in
`backend/app/services/security_policy.py`, `whitehat_policy.py`, the IAM
Security Guard, Aegis, the authorised-target gate and the isolated lab/workspace
services. No offensive execution capability is introduced by studying defensive
frameworks.

**Architectural clarification (confirmed):** the personality prompt is not a security control, but it *is* the correct place to teach IAM the law — legal boundaries, ethical reasoning and how to operate within restrictions (the "should"). Infrastructure enforces the "can". Both layers are required; where they conflict, the infrastructure control is authoritative. This distinction must be reflected in WH-09 ("learning ≠ capability") and the constitution/personality design, without weakening WH-01/WH-02 enforcement.

## 13. Provider-independent workspace additions (OD-17)

| ID | Gap | Required resolution |
|----|-----|---------------------|
| WS-01 | Workspace manager API contract | **Resolved in code** — `backend/app/api/routes/workspaces.py` exposes controlled create → start → execute → save → destroy with `GET /policy`; provider field keeps Coder/Codespaces/local interchangeable and no browser clicking is required |
| WS-02 | Isolation boundary | **Resolved in code** — `backend/app/services/workspaces/service.py` enforces `WorkspaceIsolation` (no core access, `network=none`, non-root, no-new-privileges, no protected mount); Docker adapter drops capabilities and bounds resources; credential names only; all lifecycle and output events audited |
| WS-03 | Credential scoping | **Resolved in code** — `workspace_credentials` issues short-lived (TTL-capped), host-scoped credential *names* only; commands are checked against `allowed_hosts`, expired/revoked credentials are ignored, and issue/use/revoke are audited |
| WS-04 | Approval gate for production deployment | **Resolved in code** — `backend/app/services/development_governance.py` requires tested, project-owned code changes and an active, unrevoked signed Creator authorization scoped to the project before any protected deployment; enforced at `POST /api/v1/development/deployments` and recorded in the audit trail |
| WS-05 | Provider replacement workflow | **Resolved in code** — `backend/app/services/workspaces/remote_adapters.py` implements Coder and Codespaces provision/start/execute/save/destroy adapters; `WORKSPACE_PROVIDERS` selects the preferred ready provider. Remote calls are opt-in (`WORKSPACE_REMOTE_EXECUTION_ENABLED`), token-name only, fail-closed, and log no secrets; command execution requires an operator-provided execute-path bridge. |
| WS-06 | Continuity if a provider disappears | **Resolved in code** — an unavailable online provider falls back to the always-available local provider with an audit record; no paid fallback and no dependence on an online platform |

**Resolved:** WS-01–WS-06. Provider selection, remote Coder/Codespaces adapters
and local fallback are in place; remote execution is opt-in and fail-closed
until an operator configures the token and command bridge. Online platforms
remain optional; the local/self-hosted path is always available.

## 15. Communication architecture additions (OD-18…OD-21)

Source: `IAM_COMMUNICATION_ARCHITECTURE.md` (Document 07).

| ID | Gap | Required resolution |
|----|-----|---------------------|
| CM-01 | Three channel identities and credentials undefined | Separate accounts/keys per channel; no cross-use — BLOCKING |
| CM-02 | Email approval flow needs signed challenge schema | **Resolved in code** — `creator_requests`, `signed_challenges`, `creator_approvals`, `creator_authorizations` (migration 004); request ID, expiry, action, consequences, nonce hash and signature |
| CM-03 | Email-to-authority binding | **Resolved in code** — authority only via verified ED25519 signature over `sha256(canonical challenge)|decision`; plain replies and UI flags are rejected |
| CM-04 | Frontend must have no Creator UI | **Resolved** — `/owner` routes removed; frontend is user-only, authority via signed email challenge (migrations 004/005) |
| CM-05 | Private message isolation | Per-user scoping on every query; no cross-user reads |
| CM-06 | Collective learning privacy transform | Define privacy-preserving process + consent before any insight enters shared knowledge |
| CM-07 | Sensitive-info warning implementation | Prompt/UX warning before users submit sensitive data (OD-21) |
| CM-08 | Encryption at rest for conversations | Defined key management (OD-07 SOPS + app-level encryption) |
| CM-09 | Communication audit schema | Channel, sender, purpose, risk, timestamp |
| CM-10 | Creator request notification delivery | Reliable delivery + retry if primary channel fails |

**Blocking:** CM-01, CM-06. CM-02 and CM-03 are implemented in `backend/app/services/creatorapproval_service.py`; remaining work is wiring the email transport and hardware signer to the gateway endpoint, not the authority model. The key architectural rule: the frontend is a **user** interface only; Creator authority operates through the domain email channel with cryptographic proof.

## 16. Final assessment

The communication architecture is consistent with all prior decisions. It does not weaken the protected-core or P2P trust model. The blocking items are concrete integration details (channel separation, signed approval challenges, privacy-preserving learning) that must be resolved before communication features are implemented. Base Phase 0/1 frontend and backend work is unaffected.

## 14. Updated assessment

The white-hat and workspace additions are consistent with the rest of the architecture. They strengthen IAM Aegis and the self-development capability without introducing offensive tools or new dependencies. The blocking items (WH-01, WH-02, WS-02) are enforcement boundaries that must be implemented in infrastructure, not in personality prompts.
