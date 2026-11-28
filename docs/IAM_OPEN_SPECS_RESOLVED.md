# IAM — Resolved Open Specifications (A–G)

**Version:** 1.0 · 25 November 2026  
**Status:** Engineering specifications — resolves the 7 open areas in `IAM_FINAL_CONSOLIDATION.md`  
**Rule:** Where a value is owner-specific, a concrete recommended default is given and marked **provisional** — it must be confirmed before production, but does not block design.

---

## A. Creator Authority & Recovery

### A.1 Creator identity verification
- The creator root key is an **Ed25519** keypair generated in a hardware signer (OD-03) or external signing service.
- The public key (`creator_pubkey`) is the trust anchor, embedded in `creator_signing_keys` and in signed release manifests.
- Every high-impact action requires a signature verifiable against `creator_pubkey`. Email is the carrier; the signature is the authority (Document 07).
- Verification steps: request ID → expiry → signer identity → signature → scope → audited.

### A.2 Key hierarchy
```
Creator Root Key (offline, hardware-backed)
   ├── Release Signing Key (expires 12 months) — signs official releases
   ├── Trust List Signer (expires 6 months) — signs peer trust list, revocations
   └── Approval Signer (expires 1 month) — signs per-action owner approvals
```
- Root key never used for routine signing. Subkeys rotatable without trust rebootstrap.
- All keys stored as hardware/signer references — no private key bytes in DB, prompts or logs.

### A.3 Key protection & recovery
- Root key: hardware token, PIN-gated, offline at rest. Backup: sealed Shamir shares with the owner (provisional: 3-of-5).
- Subkey compromise: revoke with root key, issue new subkey, publish signed revocation.
- Root key loss: out-of-band recovery with owner-held shares + identity proof → new root key → signed trust-list update → peers rebootstrap.

### A.4 Creator server permanently offline
- **IAM does not die.** The trust list is signed and distributed; peers keep a cached copy with sequence numbers and expiry.
- Trust decisions remain valid until a signed update says otherwise. Offline creator = no new authorizations, but existing authority stands.
- High-impact actions requiring fresh approval queue as `pending` until creator authority is restored or a pre-authorized policy (OD-03/OD-04) applies.
- Provision for a designated recovery contact (provisional: one named alternate signer) activated only by owner pre-authorization.

### A.5 Compromised deployment revocation
1. Owner signs a revocation record with deployment ID + reason + timestamp.
2. Revocation published in signed trust list (sequence n+1).
3. Peers reject the revoked peer's messages, drop its data, and refuse sync.
4. Any reporting channel from the revoked peer requires separate authorization and is untrusted by default (OD-13).
5. Re-admission requires re-image from signed release → re-attestation → new signed trust entry.

**Acceptance:** signature verification rejects forged requests; revoked peer refused by all peers; offline creator does not halt IAM; root-key recovery demonstrated with shares.

---

## B. Memory & Knowledge Boundaries

### B.1 Three owners, one model
`memory_items.owner_type` ∈ {`iam`, `visitor`, `public`}; `owner_id` scopes every row. Every query MUST filter by owner. No client-supplied owner ID is trusted.

| Layer | Owner | Visibility | Sync |
|-------|-------|-----------|------|
| IAM identity/self memory | iam | Private to IAM core | Never |
| Visitor conversation memory | visitor | Only that visitor | Never |
| Shared knowledge | public | All authorized contexts | P2P (verified only) |

### B.2 What IAM may learn from conversations
1. **Per-visitor personal memory** — with consent, preferences/facts scoped to that visitor only (OD-05).
2. **Privacy-preserving insights** — only aggregated, non-identifying patterns may enter `collective_insights`. Transformation must strip identifiers and pass a re-identification check. Raw messages never copied to shared knowledge.
3. **General technique learning** — a method learned from user A may be applied for user B, but never with A's data or identity.

### B.3 What may be synchronised over P2P
- **Allowed:** verified knowledge items, threat reports, tool evaluations, signed security fixes, anonymised benchmarks.
- **Never:** visitor messages, personal memory, credentials, owner info, private IAM memory, raw conversation logs.

### B.4 Retention, deletion, privacy rules
| Data | Default retention (provisional) | Deletion |
|------|----------------------------------|----------|
| Session context | until session end | automatic |
| Anonymous visitor memory | 90 days | visitor request / expiry |
| Conversation history | 365 days | visitor request |
| Voice audio | not retained | n/a |
| Uploaded files | 30 days post-analysis | visitor request |
| Shared knowledge | until superseded | owner/consensus review |

Deletion requests (`deletion_requests`) execute within 30 days, cascade all scoped rows, write privacy audit event. Backups expire on their own schedule; deletion is noted for next backup cycle.

**Acceptance:** cross-owner read tests return 404; no raw visitor text in shared knowledge; deletion removes all visitor rows; P2P sync excludes private data.

---

## C. P2P Networking

### C.1 Discovery & authentication
- Discovery: creator-signed bootstrap peer list + optional DHT/rendezvous; no implicit trust from discovery.
- Authentication: mutual Ed25519 handshake; each peer presents signed attestation (identity, release hash, trust level).
- Trust from signed trust list (Section A), cached with sequence numbers.

### C.2 Direct communication & NAT traversal
- Transport: libp2p (or QUIC) with noise encryption; relay fallback for symmetric NAT.
- Candidate flows: direct dial → relay → store-and-forward via trusted peers.
- No public visitor ever joins the P2P overlay; it is private-environment only.

### C.3 Offline synchronisation
- Each peer keeps `sync_state` with last-seen sequence per topic. On reconnect, merkle anti-entropy reconciles.
- Messages carry topic, sequence, signature, timestamp; replay protection via monotonic sequence.

### C.4 Conflict resolution
1. Creator-signed records (trust, releases, revocations) are authoritative.
2. Knowledge conflicts: higher verification score + more independent attestations wins; ties remain unresolved and flagged.
3. Never converge by majority alone — models can share the same error.

### C.5 Malicious-node handling
- Behaviour monitored: invalid signatures, spam, poisoned knowledge, attempted privilege escalation.
- Trust score decreases on evidence; threshold → Restricted; signed revocation → Revoked.
- External code never auto-installed: signature + independent review + local compatibility test (Document 06).

**Acceptance:** forged identity rejected; offline peer syncs after reconnect; conflict resolved by signed authority; malicious peer downgraded/revoked; no offensive tools distributed.

---

## D. Self-Development & Hardware Compatibility

### D.1 Cross-platform build & test
- Multi-arch container images: `linux/amd64` + `linux/arm64` via Docker buildx.
- CI matrix builds and tests both architectures; ARM64 tested natively or emulated (QEMU) before release.
- Every release manifest lists supported architectures and verified dependency versions.

### D.2 Compatibility matrices (provisional — verify per device)
| Component | amd64 | arm64 | Notes |
|-----------|-------|-------|-------|
| FastAPI/Python | ✅ | ✅ | pure Python deps preferred |
| PostgreSQL/pgvector | ✅ | ✅ | ARM64 builds exist |
| Redis | ✅ | ✅ | |
| LiteLLM | ✅ | ✅ | Python deps |
| Ollama | ✅ | ⚠️ | verify per device |
| vLLM/SGLang | ✅ | ⚠️ | GPU/CPU config dependent |
| Playwright | ✅ | ⚠️ | browser binaries per arch |
| NVIDIA inference | ✅ | ✅ | hosted API works on both |

### D.3 Model migration & rollback
- Model changes go through `model_evaluations` vs baseline; no adoption without evidence.
- Identity/memory stored provider-independently; switching model never rewrites identity.
- Rollback: previous signed release + previous model config restored atomically.

### D.4 Signed builds & supply chain
- Release = signed manifest (source hash, dependency SBOM, image digests, build attestation).
- Creator signature required for protected core; unsigned builds cannot be official releases.
- Dependency scanning + secrets scanning in CI; pinned digests.

### D.5 Isolated dev & protected core
- Separate dev VPS (OD-10), no production credentials, no production DB.
- IAM may develop/test in dev; production changes require signed creator approval.
- IAM cannot modify its own security boundaries or signing keys.

**Acceptance:** both arch images build; ARM64 smoke test passes; unsigned release rejected; rollback demonstrated; protected core immutable to IAM.

---

## E. Public Access & Scaling

### E.1 Concurrent targets (provisional — must be load-tested)
| Phase | Target | Basis |
|-------|--------|-------|
| Initial | 50 concurrent sessions | single VPS, hosted inference |
| Scale 1 | 250 | add workers, queue tuning |
| Scale 2 | 1000+ | horizontally scaled workers, provider quotas |

No fixed capacity promised until load tests pass. Benchmark: p95 response < 5s at target concurrency.

### E.2 Anonymous session expiry & recovery
- Session token expires after 30 days inactivity (provisional); renewable on activity.
- Visitor token in secure cookie; clearing browser data → new identity (expected).
- Cross-device continuity only via optional account.
- Returning visitor memory (OD-05) requires same visitor token.

### E.3 Provider quota management
- Router tracks usage per provider/model (`usage_records`), free-only enforced, paid disabled (OD-04).
- On quota/limit: automatic failover to permitted model; user informed; never silently incur cost.

### E.4 Abuse prevention & prioritisation
- Rate limits: per visitor, per IP-derived key, global.
- Request priority: interactive chat > scheduled reflection > experiments.
- Queue backpressure and graceful degradation (cached/short responses) under overload.

### E.5 Regional privacy
- Global baseline (OD-09): consent, retention, deletion, data-subject rights, cross-border transfer notes.
- GeoIP is estimate-only, user-correctable, never identity.

**Acceptance:** load test meets p95 target; session expiry works; quota failover no charge; one visitor cannot exhaust system.

**Implementation note (27 November 2026):** `tests/load_test.py` now exercises 50 concurrent
anonymous sessions with two messages each and records p50/p95/p99 and error counts to
`tests/results/load_test.json`. First run through the optional Caddy edge (`infra/caddy/Caddyfile`,
Compose profile `edge`): 50/50 sessions, 150 requests, 0 errors, p95 2427 ms — within the
5000 ms target. This is a bounded local measurement, not a promise of public capacity.

---

## F. Financial & Legal Operations

### F.1 Legal ownership
- Owner designates a legal entity (OD-02) recorded in `digital_assets.owner_entity` and `business_projects.legal_entity`.
- IAM is not a legal person; it operates under authorization with disclosure.

### F.2 Banking & payment permissions
- Real accounts held by the legal entity; IAM operates via least-privilege, revocable credentials (secret references only).
- Per-action approval via signed creator email (OD-19); zero standing budget (OD-04).

### F.3 Spending limits & approval
- Every expenditure is an approval request with amount, purpose, and signature. No autonomous increases.
- Ledger double-entry; reconciliation report on demand.

### F.4 Tax, KYC/AML
- Legal entity responsible for tax filings, KYC/AML and regulatory compliance. IAM records and reports; it does not assume legal duties.
- Crypto activity logged but constrained by the same approval and legal rules.

### F.5 Contracts & commercial operations
- Contracts executed only by the legal entity/owner. IAM drafts and recommends but cannot sign.
- All external commitments above threshold require explicit signed approval.

**Acceptance:** no spend without approval; ledger reconciles; ownership fields populated; no IAM-signed contracts.

---

## G. Operational Independence

### G.1 Hosting-provider migration
- All state (identity, memory, projects) exported in provider-independent format (ULID genesis + JSON/Markdown export).
- Runbook: export → verify → provision new host → restore → re-attest → update trust list → cut over.

### G.2 Multi-provider backup & recovery
- RPO 24h / RTO 4h (OD-06); daily encrypted backups, off-site copy, separate keys.
- Monthly restore drill; quarterly disaster recovery drill.

### G.3 Monitoring & incident response
- Health checks, alerts, incident records; severity ladder; containment → recovery → post-mortem.
- Aegis monitors host/runtime/network/agents with lightweight default.

### G.4 Hardware failure recovery
- Stateless workers replaced from signed images; stateful DB restored from backup; identity from genesis export.

### G.5 Offline capabilities
- Cached knowledge and trust list allow continued operation when internet unavailable; queue actions for sync.
- No dependence on a single external service for identity or memory.

### G.6 Emergency shutdown & restoration
- Owner-only kill switch: halts autonomous/delegated actions, closes sessions, revokes active tokens, preserves state for investigation, writes audit event.
- Restoration requires explicit owner re-authorization; no automatic self-restart of high-impact operations.

**Acceptance:** migration runbook rehearsed; restore drill meets RTO; kill switch halts actions; no self-restart.

---

## Status

All 7 open areas (A–G) are now **specified**. Provisional owner-specific values are:
- A: Shamir 3-of-5, alternate recovery signer
- E: concurrency targets 50/250/1000, 30-day session expiry
- B: retention periods (90/365/30 days)

These provisional values are engineering defaults, not locked decisions. Everything else is derivable from the 22 locked decisions and Documents 01–08.
