# @iamagris/cli

Official CLI for IAM developers and node operators. It is a thin wrapper over `@iamagris/sdk` — no separate auth or protocol implementation. See [../PROTOCOL.md](../PROTOCOL.md).

Published to GitHub Packages as `@iamagris/cli`. Use the same scoped `.npmrc` as `@iamagris/sdk`:

```ini
@iamagris:registry=https://npm.pkg.github.com
//npm.pkg.github.com/:_authToken=${GITHUB_TOKEN}
```

```bash
npm install -g @iamagris/cli
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
