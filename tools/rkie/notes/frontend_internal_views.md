# Frontend internal views and read-only proxy (27 November 2026)

Per `frontend/AGENTS.md`, Next.js 16.4.6 docs in `frontend/node_modules/next/dist/docs/`
were read before writing code (project structure, server/client components, route handlers).

> **Historical snapshot (27 November 2026).** The four routable pages described here were subsequently removed or moved under underscore-prefixed (non-routable) directories. Current routable pages are `/`, `/suggestions`, `/conversations` and `/conversations/[id]`. Re-verify before relying on this note.

## Frontend shape at the time of this note

An external consolidation removed the old `app/_freesandboxes` and
`app/_financial-intelligence` private pages and the sidebar, and added:
`frontend/components/iam/panels/{tone,ai-network,free-sandboxes,financial-intelligence}-panel.tsx`.
Those panels are self-contained client components. Four thin routable pages now render them:
`app/tone`, `app/ai-network`, `app/freesandboxes`, `app/financial-intelligence`.

## Server-only proxy

`frontend/app/iam-proxy/[...path]/route.ts` injects `IAM_PROXY_TOKEN` on the server and
allows only read-only/analysis paths. The browser never holds an IAM credential.

Allowlisted:
- `/api/v1/tone/analyze` (POST), `/api/v1/tone/records` (GET)
- `/api/v1/network/agents`, `/interactions`, `/collaborations`, `/agents/{id}/profile`,
  `/agents/{id}/interviews` (GET)
- `/api/v1/free-sandboxes/{status,providers,environments,policy,expiry-calendar}` (GET)
- `/api/v1/prediction-markets/{policy,markets,adapter/status,adapter/policy,forecast/policy}` (GET)
- `/api/v1/gaming-intelligence/{policy,records}`, `/api/v1/investment-intelligence/{policy,records}`
- `/api/v1/provider-registry/{entries,policy}`

Excluded: Creator authority, spending, provisioning, catalogue seed and other mutations.

`frontend/lib/secure-api.ts` provides `secureGet()` with an axios-like response so panels
only swap `api.get` for `secureGet`; POST actions stay on the authenticated `api` client.

## Configuration

`IAM_PROXY_TOKEN` must be an **admin-scoped** key: `/api/v1/network` and
`/api/v1/free-sandboxes` are in `ADMIN_PREFIXES`. It is passed to the frontend container
only in `docker-compose.yml`, documented in `.env.example`, and never as `NEXT_PUBLIC_*`.

## Verification (before final rebuild)

- Proxy GETs: free-sandboxes status/providers/environments 200; prediction-markets
  policy/markets 200; gaming/investment records 200; provider-registry entries 200.
- Disallowed `POST /iam-proxy/api/v1/free-sandboxes/provision` → 403.
- DB fix during verification: `provider_registry_entries.gates_reviewed` added via
  migration 020 (model had the column, live DB did not).
