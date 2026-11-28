# IAM — Infrastructure, Traffic Management and Distributed Processing Engine Specification

**Document:** 21 (addendum to Documents 01–20)  
**Version:** 1.0 · 25 November 2026  
**Status:** FROZEN — confirmed part of IAM architecture (owner confirmation 25 November 2026)  
**Parent:** `canonical/IAM_DOC_01_MASTER_ARCHITECTURE.md` (via `IAM_FINAL_CONSOLIDATION.md`; the early master draft is superseded)  
**Related:** `IAM_MASTER_ARCHITECTURE.md` §3 and §13, `canonical/IAM_DOC_04_UI_GLOBAL_ACCESS.md`, `IAM_DYNAMIC_NODE_NETWORK_SPEC.md` (Doc 10), `IAM_EXTERNAL_AI_IDENTITY_AND_LEARNING_SPEC.md` (Doc 18), `IAM_FREE_INFRASTRUCTURE_NODE_DISCOVERY_AND_LIFECYCLE_SPEC.md` (Doc 19), `IAM_AI_SDK_AND_FRAMEWORK_RESEARCH_SPEC.md` (Doc 20), `IAM_SECURITY_AND_INTERNET_POLICY.md`, `IAM_API_CONTRACTS.md`, `IAM_OWNER_DECISIONS.md`  
**Confirmed decision:** OD-37 (infrastructure, traffic management and distributed processing)

---

## 1. Scope and relationship to existing architecture

This document consolidates traffic management, workload distribution and infrastructure observability into one **engine inside the existing Infrastructure and Operational Resilience system (Master Architecture §13)**. It extends the technology baseline (§3), the concurrent-access requirements of `canonical/IAM_DOC_04_UI_GLOBAL_ACCESS.md`, the resource-aware scheduler in Doc 10 and the node lifecycle in Doc 19. It does **not** create a new top-level system and does not replace any locked decision.

Guiding rule: **IAM should understand all of these technologies and install only what the actual workload requires.** Caddy, Nginx, HAProxy and Envoy are alternatives, not a stack to deploy together.

Provider links in the source material are image-redirect/search artefacts and are not treated as authoritative; all URLs, versions and terms must be verified live through OEDIE before reliance (OD-15).

---

## 2. Technology study catalogue

### 2.1 Web servers and reverse proxies

| Technology | What IAM studies | Candidate role |
|------------|------------------|----------------|
| Caddy | Automatic HTTPS, reverse proxy, load balancing, health checks, simple config | Initial entry point candidate |
| Nginx | Reverse proxy, HTTP load balancing, connection management, caching, rate limiting | Higher-traffic or advanced traffic configuration |
| HAProxy | TCP/HTTP load balancing, health monitoring, connection limits, high availability | Multiple backend nodes |
| Envoy | Service-to-service communication, dynamic routing, observability, service mesh | Later, as IAM becomes more distributed |

### 2.2 Load balancing and traffic distribution

Required for concurrent global access by visitors, SDKs, applications and nodes:

```
Visitors · SDKs · Applications · IAM nodes
        → Caddy / Nginx / HAProxy (HTTPS, routing, rate limiting)
        → API node (requests)
        → AI workers (inference)
        → Research nodes (background tasks)
        → IAM Core services (identity, memory, permissions, knowledge, scheduling)
```

The proxy distributes requests to **healthy** services. Requests are not equal: a short question, a large research job and a coding task have different resource profiles and priority.

### 2.3 Distributed information processing

| Technology | Purpose | IAM application |
|------------|---------|-----------------|
| Redis | Cache, queues, temporary data | Fast task coordination — already in the baseline |
| RabbitMQ | Message queues | Distributing research/processing jobs |
| NATS | Lightweight messaging | Communication between IAM nodes |
| Apache Kafka | High-volume event streaming | Large-scale activity/data pipelines |
| Celery | Background task execution | Python research workers — **studied alternative only, see §6** |
| Temporal | Persistent workflows | Long-running tasks and recovery |

Initial investigation order: Redis, NATS and Celery before heavier infrastructure — with the OD-08 constraint in §6 applying to Celery.

### 2.4 Supporting infrastructure worth studying

| Category | Technologies |
|----------|--------------|
| Caching | Redis, Valkey |
| Database connection pooling | PgBouncer |
| Database replication | PostgreSQL streaming replication |
| Service discovery | Consul, etcd |
| Container orchestration | Docker, Podman, Kubernetes |
| Monitoring | Prometheus, Grafana |
| Distributed tracing | OpenTelemetry (already in baseline) |
| Log management | Grafana Loki |
| CDN and edge delivery | Cloudflare |
| Object storage | Garage, SeaweedFS, S3-compatible services |
| Network security | WireGuard, Tailscale |

---

## 3. Intelligent workload distribution

IAM needs more than round-robin balancing. The scheduler considers actual node capacity:

- CPU and RAM availability;
- processor architecture (ARM64 or x86-64);
- GPU availability and supported models;
- network latency and bandwidth;
- current workload and queue length;
- storage availability;
- node trust and security status;
- task priority and deadlines;
- financial and free-tier limits (OD-04, OD-25, Doc 19).

Example research flow:

```
IAM Task Scheduler — receives and analyses task
    Node A → collect research sources
    Node B → extract and organise information
    Node C → verify findings independently
    IAM Core → evaluate and consolidate
    Verified research added to IAM knowledge
```

Independent verification by a second node is preferred where feasible; the Core remains responsible for the final result. Node assignment is dynamic, not permanent (Doc 10 §3).

---

## 4. Consolidated responsibilities

These are responsibilities of the one engine, not sixteen new services:

| # | Responsibility |
|---|----------------|
| 1 | Web Server and Reverse Proxy Management |
| 2 | Global and Regional Load Balancing |
| 3 | Intelligent Traffic Routing |
| 4 | Request and Connection Management |
| 5 | Distributed Task Scheduling |
| 6 | Background Processing and Worker Management |
| 7 | Message Queue and Event Streaming |
| 8 | Resource-Aware Workload Distribution |
| 9 | Node Health and Automatic Failover |
| 10 | Database Connection and Query Optimisation |
| 11 | Caching and Content Delivery |
| 12 | Service Discovery and Registration |
| 13 | Network Performance Optimisation |
| 14 | Infrastructure Monitoring and Observability |
| 15 | Automatic Scaling and Capacity Management |
| 16 | Workload Isolation and Resource Limits |

---

## 5. Relationship to locked decisions — important

| Area | Locked baseline | Effect of this proposal |
|------|-----------------|-------------------------|
| Queue runtime | **OD-08: ARQ (async Redis)**, after evaluating Celery / ARQ / RQ; DB tables `request_jobs` and `worker_executions` are designed for ARQ | **Celery is a studied alternative only.** Adopting it requires the owner to explicitly reopen OD-08 under the change-control rule. This document does not change OD-08. |
| Cache / queues | Redis in the technology baseline | Retained; Valkey studied as an alternative |
| Containers | Docker Compose initially | Retained; Podman/Kubernetes studied for later scale |
| Monitoring | OpenTelemetry in baseline | Retained; Prometheus/Grafana as collection/visualisation layer |
| Database | PostgreSQL + pgvector | Retained; PgBouncer/replication when needed |
| Paid services | Zero standing budget (OD-04), signed approval (OD-03/OD-25) | Unchanged; no automatic scaling into paid capacity |

---

## 6. Initial infrastructure recommendation

**Contabo VPS 4 first:** Caddy, Docker, PostgreSQL, Redis and a few worker processes. **No complex load-balancing cluster on a single VPS.** When Umbrel, Google Cloud, AWS, Railway or other trusted nodes join, the scheduler and traffic layer can begin distributing suitable workloads (Doc 10, Doc 19).

| Function | Initial direction | Constraint |
|----------|-------------------|------------|
| Web server / reverse proxy | Caddy | Candidate; verify before adoption |
| Traffic management | Caddy initially | Add HAProxy/Nginx only when workload justifies it |
| Application containers | Docker | Existing baseline |
| Background processing | ARQ workers | OD-08 locked; Celery not adopted |
| Queue and caching | Redis | Existing baseline |
| Database | PostgreSQL + pgvector | Existing baseline |
| Database connections | PgBouncer when needed | Studied |
| Node communication | NATS when distributed nodes are introduced | New component inside OD-37 |
| Monitoring | OpenTelemetry + Prometheus/Grafana | Baseline plus observability layer |
| Networking | WireGuard or Tailscale | Studied; verify terms and security |
| Object storage | S3-compatible storage | Existing baseline |

---

## 7. Hard boundaries

- Install only what the workload needs; never deploy all proxies, queues or orchestrators at once.
- No dependency on one web server, hosting provider or network overlay; alternatives are maintained.
- No bypass of free-tier limits, no silent paid scaling, no unauthorised charges (OD-04, OD-25, Doc 19).
- Workloads and queues are isolated; one visitor or node cannot consume another's resources or data.
- Node trust is enforced before tasks are assigned; untrusted nodes receive no sensitive work (OD-12, OD-13, OD-26).
- No protected-core change from infrastructure automation without creator approval (OD-11).
- Metrics and logs must not leak private visitor memories, credentials or secrets.

---

## 8. Acceptance criteria

1. A single documented entry-point configuration exists and terminates HTTPS correctly.
2. Traffic is routed only to healthy services; failover is demonstrated.
3. Task assignment records the resource, trust and cost factors used in the decision.
4. At least two node architectures (ARM64 and x86-64) can receive suitable tasks.
5. The queue runtime remains ARQ unless OD-08 is explicitly reopened and changed by the owner.
6. Queue, cache and worker isolation is verified; no cross-visitor or cross-node data leakage.
7. Monitoring exposes system health without exposing private data or secrets.
8. Scaling behaviour is bounded by free-tier/budget limits and cannot silently incur charges.
9. The engine stays inside system 13 and extends Docs 10/19 without creating a new top-level system.
10. Every adopted technology is verified live through OEDIE with licence, cost and version recorded.
