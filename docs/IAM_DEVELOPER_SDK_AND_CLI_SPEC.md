# IAM — Developer SDK and CLI Specification

**Document:** 13 (addendum to Documents 01–12)  
**Version:** 1.0 · 25 November 2026  
**Status:** FROZEN — official communication interface for the IAM ecosystem  
**Parent:** `canonical/IAM_DOC_01_MASTER_ARCHITECTURE.md` (via `IAM_FINAL_CONSOLIDATION.md`; the early master draft is superseded)  
**Related:** `IAM_API_CONTRACTS.md`, `IAM_DYNAMIC_NODE_NETWORK_SPEC.md`, `IAM_SECURITY_AND_INTERNET_POLICY.md`, `IAM_OWNER_DECISIONS.md`  
**Confirmed decision:** OD-29 (official SDKs and CLI)

---

## 1. Purpose

Local development environments, applications and nodes must communicate with the original IAM core through one official, maintained interface instead of each implementing its own connection logic.

`iam-sdk` (TypeScript) and `iam-sdk` (Python) are **equal first-class** clients of the **same IAM Core API and protocol**. They are not separate implementations of IAM's intelligence or permissions.

---

## 2. Official packages

| Package | Language | Distribution | Phase | Purpose |
|---------|----------|--------------|-------|---------|
| `@iam/sdk` | TypeScript / JavaScript | npm | First phase | Web apps, Node.js services, developer tools, local integrations |
| `iam-sdk` (provisional name) | Python 3.11+ | PyPI | First phase | AI development, research, automation, node agents |
| `iam` (CLI, provisional name) | Cross-platform | npm / pip | First phase | Local development, node registration, diagnostics, testing |
| Local agent | Service | OS packages / containers | First phase | Node communication and background synchronisation |

Names are proposed, not claims of existing published packages.

---

## 3. SDK capability surface

| Capability | Function |
|------------|----------|
| Core connection | Connect to a local or remote IAM core |
| Node registration | Register and identify deployments as candidate nodes |
| Authentication | Scoped, secure authentication of SDK clients |
| Task management | Submit tasks and receive results |
| Event communication | Receive live updates from IAM |
| Resource reporting | Report CPU, RAM, storage and architecture |
| File management | Upload/retrieve files through core-authorised S3 storage |
| Knowledge sharing | Submit approved research and development contributions |
| Synchronisation | Synchronise permitted information |
| Diagnostics | Check core status, node health and connection errors |

Both SDKs expose the same conceptual API: `core`, `tasks`, `events`, `nodes`, `resources`, `files`, `knowledge`, `sync`, `diagnostics`.

### 3.1 TypeScript example

```ts
import { IAM } from "@iam/sdk";

const iam = new IAM({
  endpoint: process.env.IAM_CORE_URL,
  token: process.env.IAM_TOKEN,
});

await iam.connect();
const status = await iam.core.status();
const task = await iam.tasks.submit({
  type: "research",
  instruction: "Investigate efficient ARM64 inference engines",
});
console.log(status, task.id);
await iam.disconnect();
```

### 3.2 Python example

```python
import asyncio
from iam_sdk import IAM

async def main():
    iam = IAM(
        endpoint="https://core.example.com",
        token="YOUR_IAM_TOKEN",
    )
    await iam.connect()
    status = await iam.core.status()
    task = await iam.tasks.submit(
        type="research",
        instruction="Research efficient ARM64 AI models",
    )
    print(status, task.id)
    await iam.disconnect()

asyncio.run(main())
```

Illustrative interface; the package is not yet published.

---

## 4. CLI (developer and node operator tool)

Illustrative commands:

```
iam login
iam core status
iam node register
iam node status
iam dev init
iam dev test
iam storage status
iam sync status
```

The CLI is built on the SDK. It must not implement a second authentication or protocol path.

---

## 5. Local development architecture

```
Original IAM Core            central intelligence and coordination
        |                    authenticated, versioned API + event connection
IAM SDK + CLI + Local Agent  connection, development, node management, file transfer
        |
Local applications / development projects / local AI experiments / registered nodes
```

---

## 6. Shared protocol requirements

1. One versioned HTTP API and event protocol used by both SDKs and the CLI.
2. A protocol version is negotiated on connect; incompatible clients are rejected with a clear diagnostic.
3. Structured responses and typed errors shared across languages via a single schema/source-of-truth.
4. Controlled retries with backoff, automatic reconnection, and offline task queuing with resume.
5. ARM64 and x86-64 support where dependencies permit.
6. Automated tests, contract tests and documentation for both SDKs.

---

## 7. Security requirements

- Scoped authentication tokens; separate credentials per project and per node.
- Encrypted communication (TLS in production).
- Versioned APIs and protocol compatibility checks.
- Auditable task and file operations.
- **No direct database access** from any SDK or CLI.
- No automatic permission to modify IAM's protected core (OD-11).
- Separate authorisation for storage, execution and development operations.
- Credentials stored in secure local credential stores, never in source files or workflow knowledge.
- SDK clients are subjects of the same infrastructure enforcement as any other caller; personality/constitution is never a security control.

---

## 8. Node and resource integration

- SDK node registration creates a **candidate node**, never a trusted node (OD-26).
- Resource reporting supplies CPU, RAM, storage, architecture and permitted capacity to the core.
- A node joining the creator network contributes up to **1%** of agreed usable resources; 99% remains for local use.
- Background sync and offline queueing are handled by the local agent; a disconnect must not make the core a mandatory dependency for local work.

---

## 9. Acceptance criteria

1. Both SDKs connect to the same core API with interoperable typed responses.
2. CLI commands delegate to the SDK rather than duplicating protocol logic.
3. No SDK or CLI can access the database directly or modify the protected core.
4. Tokens are scoped per project/node and stored securely.
5. Tasks submitted offline are queued and resume on reconnection.
6. Protocol version mismatch produces an actionable diagnostic.
7. Packages build and test on ARM64 and x86-64.
8. Node registration reports resources and uses the 1% contribution policy.
