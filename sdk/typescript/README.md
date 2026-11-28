# @iam/sdk (TypeScript)

Official TypeScript/JavaScript client for the IAM Core. See [../PROTOCOL.md](../PROTOCOL.md) and [docs/IAM_DEVELOPER_SDK_AND_CLI_SPEC.md](../../docs/IAM_DEVELOPER_SDK_AND_CLI_SPEC.md).

Published to GitHub Packages as `@iamagris/sdk`. Add the scope to `.npmrc` before installing:

```ini
@iamagris:registry=https://npm.pkg.github.com
//npm.pkg.github.com/:_authToken=${GITHUB_TOKEN}
```

```bash
npm install @iamagris/sdk
```

```ts
import { IAM } from "@iamagris/sdk";

const iam = new IAM({
  endpoint: process.env.IAM_CORE_URL!,
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

Capabilities: `core`, `tasks`, `events`, `nodes`, `resources`, `files`, `knowledge`, `sync`, `diagnostics`, `creator`, plus `integrity`, `uwaie`, `publicRecords`, `legal`, `geo`, `humanPresence`, `assistantLab` and `freeSandbox`.

- Scoped bearer tokens; protocol version header; controlled retries; optional Cloudflare Access service-token headers via `accessClientId` / `accessClientSecret`.
- `creator.pending()`, `creator.challenge()` and `creator.decide()` support locally reviewed, signed Creator decisions. Signatures must be produced by a separate trusted signer; this SDK never generates authority.
- Tasks submitted while disconnected are queued in memory and sent by `tasks.flushQueue()`.
- Node registration creates a candidate node; the 1% contribution policy is core-enforced.
- No database access; no protected-core modification.

Requires Node 18+ (global `fetch`). Build with `npm run build`.
