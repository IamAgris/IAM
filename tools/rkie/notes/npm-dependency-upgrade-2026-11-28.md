# npm dependency upgrades — 28 November 2026

**Basis:** working tree at `a0972c7` (substantial uncommitted owner work; only dependency manifests and SDK tsconfigs were changed). Re-verify against current files before reusing.

## Applied and verified

| Workspace | Change | Verification |
|---|---|---|
| `frontend/` | `lucide-react` 0.460 → 1.83, `tailwind-merge` 2.6 → 3.7, `typescript` 5.9 → 7.0 | `npm ci`, `npm run build`, `npm audit --audit-level=high` all pass |
| `sdk/typescript/` | `typescript` 5.4 → 7.0; added `"types": ["node"]` to `tsconfig.json` | `npm ci`, `npm run build`, `npm test` (4/4), `npm audit` pass |
| `sdk/cli/` | `typescript` 5.4 → 7.0; removed `baseUrl` (removed in TS 7), added `"types": ["node"]` | `npm ci`, `npm run build`, `npm audit` pass |

TS 7 needs explicit `types: ["node"]` for `node:*` imports and globals; `baseUrl` is a removed option and `paths` resolve relative to the tsconfig. No `type: ignore` or test weakening was used.

## Deliberately deferred

- `@types/node` 20 → 26 — all four CI workflows (`ci.yml`, `supply-chain.yml`, `quality-gates.yml`, `publish-sdk.yml`) pin `node-version: '20'`; type definitions must match the runtime.
- `tailwindcss` 3.4 → 4.3 — requires CSS-first config migration that would edit `frontend/app/globals.css`, which contains uncommitted owner work.

## Security state

`pip-audit` on `backend/requirements.lock.txt`: no known vulnerabilities. `npm audit --audit-level=high`: 0 vulnerabilities in all three npm workspaces. These audits detect known CVEs, not staleness; `npm outdated` is the freshness check.
