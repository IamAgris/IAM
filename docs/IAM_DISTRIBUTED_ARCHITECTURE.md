# IAM — Distributed Architecture Addendum

**Document:** 05 (addendum to Documents 01–04)  
**Version:** 1.0 · 24 November 2026  
**Status:** FROZEN — formal part of IAM architecture, not an optional plugin  
**Parent:** `canonical/IAM_DOC_01_MASTER_ARCHITECTURE.md` (via `IAM_FINAL_CONSOLIDATION.md`; the early master draft is superseded)  
**Confirmed decisions:** OD-11 (protected core), OD-12 (hybrid P2P), OD-13 (restricted reporting), OD-14 (IAM Aegis), OD-15 (OEDIE)  
**Related:** `IAM_DYNAMIC_NODE_NETWORK_SPEC.md` (OD-26 — dynamic node roles, 1% voluntary contribution, standalone mode)

---

## 1. Purpose

This addendum defines IAM's peer-to-peer network, creator authority, integrity model, autonomous defensive system and open-ecosystem discovery. It extends the four canonical documents without changing their interface or core principles.

---

## 2. Creator authority — protected core

Only the original creator may authorize changes to:

1. IAM's permanent identity and constitution.
2. Core intelligence architecture.
3. Core source code.
4. Security policies and trust rules.
5. Creator authority and signing keys.
6. Official software releases.
7. Protected self-development mechanisms.

Local deployments may:
- configure permitted settings;
- install approved extensions;
- run local services and projects,

provided they do **not** alter the protected core.

IAM may research, propose, develop and test improvements in isolated environments. Production changes to the protected core require creator authorization and an official signed release.

---

## 3. Hybrid P2P network

### 3.1 Structure

- Deployments communicate directly with one another.
- Approved knowledge and validated discoveries synchronise across the network.
- The original IAM controls creator authority, network trust and official releases.
- The original server does **not** need to remain online for every peer interaction.
- Peers may reconnect and synchronise after periods offline.

### 3.2 Seven new systems

| System | Responsibility |
|--------|----------------|
| P2P Network Engine | Peer discovery, connectivity, routing, store-and-forward |
| Distributed Knowledge Network | Synchronisation of approved knowledge and validated discoveries |
| Peer Identity and Trust | Cryptographic peer identity, trust levels, trust decisions |
| Creator Authority System | Creator signing root, release signing, trust list, updates |
| Core Integrity Engine | Measurement of protected core; attestation; tamper detection |
| Distributed Update System | Signed release distribution, verification, staged rollout, rollback |
| Deployment Integrity and Creator Monitoring System (DICMS) | Restricted reporting, status, attestation, recovery, revocation |

---

## 4. Trust and integrity model

### 4.1 Trust levels

| Level | Meaning | Capabilities |
|-------|---------|--------------|
| **Untrusted / Provisioning** | Not yet attested | No P2P participation |
| **Restricted** | Modified or degraded deployment | Reporting only (see §5) |
| **Trusted** | Attested, running official release | Full permitted P2P, knowledge exchange |
| **Revoked** | Credentials revoked by creator | No P2P; reporting only if separately authorized |

### 4.2 Cryptographic identity

- Each deployment holds an Ed25519 identity keypair; the public key is the deployment identity.
- A distinct creator root signing key (hardware-backed per OD-03) signs: official releases, the network trust list, policy updates and revocations.
- Attestation: deployment measures protected core files (hashes), combines with platform measurements (TPM 2.0 PCRs where available) and signs a report with its identity key.
- Trust decision: verify signature → verify creator trust list → verify measurement against known-good manifest → assign trust level.

### 4.3 Integrity principle

Integrity reporting is **best-effort** when another person controls a deployment. Signed attestations and hardware-backed verification strengthen it, but IAM must never falsely claim that a compromised machine cannot hide modifications. The system must state confidence and evidence, not certainty.

---

## 5. Restricted reporting for modified deployments

A deployment that detects unauthorised modification of the protected core must downgrade itself to **Restricted** and:

- report detected modifications to creator IAM;
- report software integrity and operational status;
- receive permitted creator communications;
- **not** distribute unverified code or knowledge;
- **not** access privileged peer capabilities;
- require verification and re-attestation to regain trust.

A **revoked** deployment has its trusted credentials revoked by the creator. Any remaining reporting connection must be separately authorised and cannot be assumed trustworthy.

Recovery path: re-image from an official signed release → re-attest → creator re-adds to trust list → Trusted.

---

## 6. Synchronisation protocols

- **Knowledge:** content-addressed objects (SHA-256), merkle-based anti-entropy for efficient reconciliation.
- **Threat intelligence:** gossip propagation of signed reports; reports are data, not instructions.
- **Executable code / security packages:** never auto-installed; require creator signature, independent review and local compatibility tests.
- **Offline peers:** store-and-forward with sequence numbers; sync on reconnect.
- **Conflicts:** creator-signed trust list is authoritative; otherwise convergence by validated evidence and explicit policy.

---

## 7. IAM Aegis — autonomous defence engine

Shirudo is a **reference implementation and learning resource**, not a permanent dependency. IAM studies its architecture (signed protections, eBPF enforcement, hardware-backed measurements, runtime monitoring) and its documented limitations (trusted kernel dependency, pre-release status, kernel/TPM requirements), and studies other security technologies rather than copying one implementation.

### 7.1 Seven components

| Component | Responsibility |
|-----------|----------------|
| Host Defence | Protect Linux hosts, processes and system resources |
| Runtime Defence | Detect and block suspicious application behaviour |
| Network Defence | Detect malicious connections and suspicious peer activity |
| AI Agent Defence | Restrict what autonomous agents can execute |
| Integrity Protection | Detect unauthorised modification of protected files/software |
| Threat Intelligence | Research, verify and share security discoveries |
| Self-Defence Research | Develop and test new defensive techniques |

### 7.2 Development path

Learn → Reproduce (isolated VMs) → Develop → Test (simulated exploits, malicious processes, compromised containers, privilege escalation, false positives) → Improve (compare with Shirudo and others) → Deploy (approved, signed, rollback-capable).

### 7.3 Distributed defence cycle

Node A detects → Node B reproduces → Node C develops defence → Node D validates no legitimate breakage → IAM Aegis evaluates combined evidence → verified intelligence distributed to trusted deployments.

**Critical distinction:** a vulnerability report may be shared as data; a defensive executable must pass independent review, signature verification and local compatibility testing before installation.

### 7.4 Protection of Aegis itself

- Creator controls protected source and signing authority.
- IAM may research, propose, develop and test in isolation.
- Official production changes require creator authorisation.
- Compromised deployments cannot distribute trusted security updates.
- Emergency containment operates only within pre-approved policies.
- Lightweight monitoring by default; intensive analysis only when needed.

---

## 8. Open Ecosystem Discovery and Integration Engine (OEDIE)

IAM continuously searches for free tools and services: developer tools, open-source software, free APIs/SDK generators, hosting/deployment, databases/storage, AI models/services, security tools, monitoring/testing, communication services, infrastructure environments. It discovers independently, without waiting for recommendations.

### 8.1 Evaluation criteria

Cost · Licence · Restrictions · Hosting · Privacy · Security · Compatibility · Dependency/lock-in · Maintenance.

A free trial must never be mistaken for a permanently free service.

### 8.2 Initial research targets (Speakeasy alternatives)

Fern · Scalar · OpenAPI Generator · Microsoft Kiota · APIMatic · Orval — plus tools beyond this list, including future ones.

### 8.3 Adoption process

Discover → investigate licence/terms → compare → obtain from trusted source → test in isolation → integrate if permitted → monitor cost/restrictions/updates/security → replace with better free alternative when available.

### 8.4 Permanent independence rules

1. Prefer free/open-source when requirements are met.
2. Prefer self-hosted to reduce external dependency.
3. Never assume a free tier is unlimited.
4. Never activate paid services without authorisation.
5. Never bypass provider restrictions or limits.
6. Maintain alternatives for critical services.
7. Keep integrations replaceable.
8. Contribute improvements to open source where permitted.
9. Record licences and attribution obligations.
10. Share validated discoveries across trusted P2P deployments.

**Principle:** IAM must never assume a capability requires purchasing a service. It must first investigate whether a free, open-source, self-hosted or freely accessible solution exists.

---

## 9. Data model implications

Add: `peers`, `peer_identities`, `trust_decisions`, `attestation_records`, `integrity_manifests`, `signed_releases`, `update_records`, `sync_state`, `sync_conflicts`, `knowledge_objects`, `threat_reports`, `defence_packages`, `oedie_discoveries`, `oedie_evaluations`, `tool_registry_entries`, `creator_signing_keys`, `revocation_records`, `restricted_reports`.

All signature keys are hardware/secret-store backed; no raw private keys in database records.

---

## 10. Acceptance criteria

1. Only the creator can change the protected core.
2. Peers sync validated knowledge while offline-capable.
3. Modified deployments downgrade to restricted reporting.
4. Revoked credentials are refused across the network.
5. Executable code is never auto-installed from peers.
6. Integrity reporting states confidence, not false certainty.
7. Aegis protects hosts/runtime/network/agents without self-rewriting.
8. OEDIE prefers free/self-hosted alternatives and records licences.
9. Validated discoveries are shared across trusted peers.
10. The original server is not a single point of failure for peer interaction.
