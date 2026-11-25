# @iam/cli (proposed)

Official CLI for IAM developers and node operators. It is a thin wrapper over `@iam/sdk` — no separate auth or protocol implementation. See [../PROTOCOL.md](../PROTOCOL.md).

**Proposed package name — not published.**

```bash
npm install -g @iam/cli
iam login
iam core status
iam node register my-node
iam node status <id>
iam dev init
iam dev test
iam storage status
iam sync status
```

Configuration: `IAM_CORE_URL`, `IAM_TOKEN`, and optional node resource env vars. `IAM_CONTRIBUTION_PERCENT` defaults to **1** and is disclosed to the operator before node mode is enabled.
