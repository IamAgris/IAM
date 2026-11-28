# IAM — Dynamic Node Network Specification

**Document:** 10 (addendum to Documents 01–09)  
**Version:** 1.0 · 25 November 2026  
**Status:** FROZEN — formal part of IAM architecture, not an optional plugin  
**Parent:** `canonical/IAM_DOC_01_MASTER_ARCHITECTURE.md` (via `IAM_FINAL_CONSOLIDATION.md`; the early master draft is superseded)  
**Related:** `IAM_DISTRIBUTED_ARCHITECTURE.md`, `IAM_HARDWARE_ADAPTATION.md`, `IAM_UNIVERSAL_WEBSITE_INTERACTION_SPEC.md`, `IAM_OWNER_DECISIONS.md`  
**Confirmed decisions:** OD-11 (protected core), OD-12 (hybrid P2P), OD-13 (restricted reporting), OD-22 (hardware adaptation), OD-26 (creator-controlled core + 1% contribution)

---

## 1. Core principle

The network is designed around **one intelligent core and a flexible network of nodes**, not permanent job assignments.

**The core decides what work needs doing. Nodes provide resources and capabilities that the core can use when needed.** A node is not permanently a database server, AI worker, security server or development server. Its role can change depending on what IAM needs at that moment.

---

## 2. The core must be capable on its own

The original IAM core is a complete, independently operational intelligence. It must be able to:

- reason, plan, learn, manage memory and make decisions;
- communicate with users and manage its own identity;
- develop software, research, test and manage projects;
- manage its security, resources and infrastructure;
- operate with a small hardware footprint and low running costs;
- continue operating when every other node is offline.

Nodes improve its capacity, speed, availability and collective learning. **They are not mandatory dependencies for the core's basic existence.**

IAM is therefore a **resource-efficient intelligence with expandable computing capacity**, not a system that requires an expensive server cluster to function.

---

## 3. Nodes are dynamically assigned, not permanently specialised

When a deployment connects to the original IAM core, it can register as an available node. The core examines what that machine can actually provide:

- CPU architecture and processing power;
- available RAM and storage;
- GPU or other accelerators;
- network quality and availability;
- installed software and compatible capabilities;
- current workload and the resources its operator permits IAM to use.

The core then decides how to use it.

**Example: one flexible node**

```
Node available
ARM64 · 8 GB RAM · CPU-only · limited network capacity

Core evaluates available resources and current priorities

Research      → research and source verification
Development   → build and test software
Knowledge     → validate and synchronise discoveries
Security      → run approved defensive checks
```

These are **possible assignments, not permanent roles**. The core can change assignments as priorities and node resources change. A node can perform different jobs at different times, several nodes can work on the same task when useful, and the core can split a task into smaller jobs and combine the results. Node detection and compatibility follow AIHAE (`IAM_HARDWARE_ADAPTATION.md`).

---

## 4. Operating states

1. **Standalone mode** — IAM runs independently without joining another IAM deployment's network.
2. **Network node mode** — IAM connects to the original creator network and makes its permitted resources and capabilities available to the core.

When the original core is online, a newly connected deployment may be automatically recognised and registered as a **candidate node**. It does **not** automatically receive trusted status or privileged access.

The core checks identity, software integrity, compatibility and permissions before granting capabilities. If the core is offline, existing nodes continue their permitted local work and communicate with trusted peers; they synchronise when connectivity returns (consistent with OD-12).

---

## 5. Creator network contribution policy

# 1%

**Target contribution of available, permitted resources**

- CPU processing capacity
- RAM allocation
- Storage, within an agreed quota
- Network bandwidth, within an agreed quota
- Optional GPU capacity, if available and permitted

**Remaining resources:** 99% remain available for the deployment operator's own development, customisations and independent projects.

Implementation rules:

- Each participating node reserves **1% of its agreed usable computing resources** for the original IAM core; the remaining **99%** stays available for local operation, development and dynamically assigned tasks.
- The 1% is calculated against resources the operator has **actually made available**, never blindly taken from the machine's total capacity.
- It is a **resource ceiling / allocation target**, not a requirement to waste 1% when the core has no work for the node.
- It must not make the node unstable or interfere with the operator's critical workloads.
- It is enforced through resource controls such as container CPU and memory limits.
- Resource usage must be **measurable, bounded and disclosed** to the node operator.
- The operator must accept the reservation **before** enabling network node mode.

**Honesty requirement:** IAM cannot secretly guarantee this on a machine controlled by someone else. An operator with administrator access can change or disable the software. The network must detect when contributions stop, report the change, and adjust that deployment's trust and network privileges accordingly (see OD-13).

---

## 6. Learning from independent deployments

A deployment that modifies IAM must not automatically become useless to the original network.

### 6.1 Distributed Development and Knowledge Contribution System

1. Someone modifies their IAM deployment to improve its memory system.
2. That deployment records what it changed and why.
3. It can submit the improvement to the original core.
4. The core examines the source changes, research, tests and results.
5. Other trusted nodes can independently evaluate the improvement.
6. If accepted, the knowledge or improvement can be distributed to other compatible nodes.

### 6.2 What the core may learn from

- new algorithms and techniques;
- improved reasoning and memory approaches;
- new skills and tools;
- software improvements and bug fixes;
- hardware optimisation techniques;
- model evaluations and smaller-model developments;
- security discoveries and defensive improvements.

### 6.3 Hard boundary

The core must distinguish between **learning about a change** and **accepting that change**.

- Unverified code must never automatically become part of the protected core (OD-11).
- Private conversations, credentials, private files and another person's confidential data are **not** collected as contributions (OD-20, OD-21).
- A contribution is data and evidence until it passes review, signature verification, independent evaluation and local compatibility testing.

---

## 7. Disclosure shown to anyone deploying or modifying IAM

The disclosure appears during installation, first connection to the network, and when enabling node contribution.

# IAM Network Node Disclosure

This deployment is an independent instance of IAM that can connect to the original IAM creator network.

**Network participation**

When connected and authorised, this deployment may contribute computing resources and approved knowledge, research, development results, skills and improvements to the original IAM network.

**Resource contribution**

By enabling network node mode, you agree to make up to **1%** of your permitted available computing resources available to the original IAM core, subject to configured resource limits and availability. The remaining **99%** is reserved for your own use. The contribution is a ceiling, not a requirement to consume resources when no work is assigned.

**Independent development**

You may customise, extend and develop your own deployment. Your local modifications do not automatically become official IAM core changes.

**Knowledge and development sharing**

Approved contributions may be reviewed, tested and shared with other trusted IAM deployments. Private user conversations, credentials and confidential local data are not automatically shared.

**Network integrity**

The original creator network maintains its own identity, trust, security and protected release policies. Modified deployments may have restricted privileges until their integrity and trust status are verified.

**Your control**

You remain responsible for your machine and its local deployment. You can inspect its resource allocation and network participation settings. Disabling contributions may affect your deployment's network privileges. The network can detect when contribution stops and will adjust trust and privileges accordingly.

By choosing to join the network, you acknowledge these conditions.

---

## 8. Consolidated system capabilities

These are **modules within IAM's architecture**, not eleven separate servers.

| System | Responsibility |
|--------|----------------|
| Core Intelligence Orchestrator | Decides what the network needs |
| Dynamic Node Discovery | Finds and registers deployments |
| Node Capability Registry | Tracks hardware and available capabilities |
| Dynamic Resource Scheduler | Assigns and moves work between nodes |
| Node Resource Contribution Manager | Enforces the agreed 1% allocation |
| Distributed Task Engine | Coordinates parallel work |
| Knowledge Synchronisation Engine | Shares approved knowledge |
| Distributed Development Engine | Evaluates contributions and improvements |
| Node Identity and Trust Engine | Controls node identity and privileges |
| Deployment Integrity Monitoring | Detects unauthorised protected changes |
| Network Resilience Engine | Handles offline nodes and reconnection |

---

## 9. Creator-controlled core rule (confirmed)

**The original IAM remains the central creator-controlled intelligence.** Modified deployments may develop their own local personality, projects, tools and extensions, but cannot replace the original IAM identity or change its protected core without creator authorisation.

The 1% contribution and disclosure apply only to deployments that **voluntarily join the original creator network**. Network participation is never a hidden obligation; standalone mode remains fully supported.

---

## 10. Acceptance criteria

1. The core operates fully when all nodes are offline.
2. Connected deployments register as candidate nodes, not trusted nodes.
3. Node roles are assigned dynamically and can be reassigned; no permanent job assignments exist.
4. Resource contribution is capped at 1% of operator-permitted available resources, enforced by container limits.
5. The 1% disclosure is shown before network node mode is enabled.
6. Contribution stops are detected, reported and reflected in trust/privileges.
7. Contributions are learned about but never auto-promoted into the protected core.
8. Private conversations, credentials and confidential local data are never collected as contributions.
9. Offline nodes resume permitted local work and synchronise on reconnect.
10. All eleven capabilities are implemented as modules, not mandatory standalone services.
