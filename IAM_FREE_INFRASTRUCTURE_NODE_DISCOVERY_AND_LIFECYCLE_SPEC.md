# IAM — Free Infrastructure Node Discovery and Lifecycle Specification

**Document:** 19 (addendum to Documents 01–18)  
**Version:** 1.0 · 25 November 2026  
**Status:** FROZEN — confirmed part of IAM architecture (owner confirmation 25 November 2026)  
**Parent:** `canonical/IAM_DOC_01_MASTER_ARCHITECTURE.md` (via `IAM_FINAL_CONSOLIDATION.md`; the early master draft is superseded)  
**Related:** `IAM_DISTRIBUTED_ARCHITECTURE.md` §8 (OEDIE), `IAM_DYNAMIC_NODE_NETWORK_SPEC.md` (Doc 10), `IAM_HARDWARE_ADAPTATION.md` (Doc 08), `IAM_DEVELOPER_SDK_AND_CLI_SPEC.md` (Doc 13), `IAM_SECURITY_AND_INTERNET_POLICY.md`, `IAM_OWNER_DECISIONS.md`  
**Confirmed decision:** OD-35 (free infrastructure node discovery and lifecycle)

---

## 1. Scope and relationship to existing architecture

This document **extends** the existing OEDIE free-resource policy (`IAM_DISTRIBUTED_ARCHITECTURE.md` §8, OD-15) and the dynamic node network (Doc 10, OD-26). It does not create a new system or change the core architecture.

The original IAM Core (identified as the Contabo VPS in the source material) remains the permanent intelligence: identity, memory, autonomy, governance and coordination. Umbrel is a trusted local node. Free cloud and platform resources are **supplementary capacity only**, registered and used through the authorised node protocol. The core must remain fully operational when every supplementary node is offline (Doc 10 §2).

**Provider figures below are examples from source material, not verified facts.** Free allowances, credits, regions, instance eligibility, sleep behaviour and expiry rules change. IAM must check current official documentation through OEDIE before relying on any provider, and must never record an advertised allowance as a guarantee.

---

## 2. Candidate infrastructure

| Resource | Role in the network | Verification note |
|----------|---------------------|-------------------|
| Contabo VPS (Core) | Original IAM Core — identity, memory, autonomy, governance, coordination | Permanent core; not a free-tier resource |
| Umbrel | Trusted local node; development and permitted storage | Operator-owned/authorised |
| Google Cloud (e2-micro class) | Lightweight research and testing node | Source material: one eligible e2-micro, limited RAM/shared CPU, selected US regions, limited outbound allowance, billing account required. Free VM regions exclude Johannesburg. Verify all figures live. |
| AWS x86 (t3.micro class) | x86-64 software and background-task testing | Source material: small EC2 instance eligibility with account credits and a time-limited free account plan; verify current plan, credits and expiry. |
| AWS ARM64 (t4g.micro class) | ARM64 development and compatibility testing | Verify ARM64 eligibility and current terms before reliance. |
| Railway | Small API services, temporary dev environments, small database experiments, webhook receivers, prototypes | Source material: small monthly usage credit, limited services/RAM/volume, sleep after inactivity, stop when credit exhausted. Verify live; never use for permanent identity, always-on P2P or essential memory. |
| Vercel | Websites and serverless functions | Verify free-tier scope and commercial restrictions. |
| Cloudflare | Edge services and lightweight storage | Verify free-tier scope and restrictions. |
| Neon | PostgreSQL experiments | Verify free-tier scope, retention and connection limits. |
| Future trusted nodes | Additional free, donated, owned or authorised resources | Discovered continuously; none assumed available. |

Candidate deployments are **not guaranteed simultaneous entitlements**. Google and AWS allowances have separate eligibility rules; a free plan may expire or be suspended.

---

## 3. Node usefulness gate

IAM must not create a node merely because a free VM exists. Before deploying, it evaluates:

1. **Useful additional capacity** — does this node add CPU, RAM, architecture coverage, geography or availability the core actually needs?
2. **Run compatibility** — can it run IAM's node software at the required version and architecture (ARM64 vs x86-64)?
3. **Operational overhead** — networking, patching, monitoring, identity, secrets and support cost.
4. **Security exposure** — trust tier, data isolation, credential handling and attack surface.
5. **Risk vs benefit** — if maintenance outweighs capacity, do not deploy.

A node that cannot demonstrate net benefit is declined, even if free.

---

## 4. Autonomous lifecycle

IAM manages free infrastructure through its existing research/infrastructure stack with resource-aware scheduling:

1. Discover free cloud providers and small compute instances.
2. Check current free-tier eligibility and restrictions from official sources.
3. Compare CPU, RAM, storage, architecture and location.
4. Check whether the node can run IAM's software.
5. Deploy a **restricted** IAM node only when authorised.
6. Register it with the original Core as a candidate node.
7. Monitor availability, performance and quota consumption.
8. Migrate workloads before a free allowance expires.
9. Stop workloads before they create unauthorised charges.
10. Continuously discover better free infrastructure and replace expiring or inferior nodes.

---

## 5. Billing and free-tier discipline

- **Google Cloud requires a billing account.** Exceeding a free allowance on a paid billing account can generate charges. IAM must enforce this distinction rather than assume an advertised "free" service cannot cost money.
- **AWS free account plans have eligibility, credit and expiry rules.** Source material reports expiry or suspension risk; IAM must plan migration before any allowance expiry regardless of the exact policy.
- **Railway-style plans may sleep or stop** when credits are exhausted; such resources are unsuitable for permanent identity, continuous autonomy, essential memory or always-on P2P.
- No paid fallback, no automatic upgrades, no surprise billing, no attempts to bypass free-tier limits or anti-abuse controls.
- Quota alarms, an expiry calendar and a documented migration path are mandatory before a node is put into service.
- Any cost-incurring action requires the existing creator-authorisation path (OD-03, OD-04, OD-25); zero standing budget still applies.

---

## 6. Workload allocation

The Core assigns suitable tasks dynamically; nodes are not permanently specialised (Doc 10 §3):

- research and documentation processing;
- website availability monitoring;
- lightweight AI agents;
- SDK and software testing;
- ARM64 and x86-64 compatibility testing;
- knowledge indexing and synchronisation;
- defensive security monitoring;
- small development experiments.

Supplementary nodes never hold the only copy of identity, essential memory or signing authority.

---

## 7. Registration, trust and isolation

- Node registration creates a **candidate node**, never a trusted node (OD-26, Doc 13).
- Nodes report available resources and operate under the restrictions of the authorised node protocol.
- Voluntary node contributions remain subject to the disclosed 1% resource ceiling (OD-26).
- No credentials, sessions or private user memories are shared with a supplementary node.
- Workloads and data are isolated; revoked nodes are refused across the network (OD-13).
- Replicated binaries are obtained from trusted sources and verified; executable code is never auto-installed from peers (Doc 05 §10).

---

## 8. Hard boundaries

- Free-tier terms are verified live; no advertised allowance is treated as permanent or unlimited.
- No paid upgrades, credit circumvention, fake accounts or evasion of provider restrictions.
- No dependency on any single free provider for core identity, memory, autonomy or governance.
- All infrastructure changes remain within IAM's authority model; protected-core changes require creator approval (OD-11).
- Security monitoring from a node stays defensive (OD-16, Doc 06).

---

## 9. Acceptance criteria

1. Each candidate provider has a record with verified current terms, quotas, architecture, region and expiry/credit status.
2. No node is deployed without a documented usefulness assessment and authorisation.
3. Every node registers with the Core as a candidate and reports resources through the authorised protocol.
4. Quota monitoring, expiry alerts and a migration plan exist before a node carries workload.
5. Workloads stop or migrate before unauthorised charges can occur; no paid fallback is activated.
6. The Core continues operating with all supplementary nodes offline.
7. Node data, credentials and sessions remain isolated; revoked nodes are refused.
8. Findings about providers are validated discoveries that may be shared with trusted nodes, never unverified assumptions.
