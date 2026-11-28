# Frontend Implementation Note

**Status:** Scope locked. Verified with Next.js 16.4.6.

## What is live

**Owner decision (28 November 2026): IAM has exactly one frontend page.**

- `frontend/app/page.tsx` — the only page; renders `IAMInterface`. It accepts a
  `?conversation=<id>` query parameter for deep-links, so no second route is
  needed. Conversation selection, creation and deletion happen inside the
  interface's history drawer.
- `frontend/app/iam-proxy/[...path]/route.ts` is a server-only route handler, not a page.

Removed on 28 November 2026 because they duplicated the single interface:
`app/suggestions/page.tsx`, `app/conversations/page.tsx` and
`app/conversations/[id]/page.tsx`. Their capabilities remain in `IAMInterface`:
Focus/Recall/Create modes, contextual suggestions, public knowledge nodes and
the conversation history drawer. Legacy URLs redirect to `/` via
`frontend/next.config.js` (`/conversations/:id` → `/?conversation=:id`).

The underscore-prefixed directories (`_ai-network`, `_financial-intelligence`,
`_freesandboxes`, `_iics`, `_tone`) are retained as historical source only; Next.js
does not route them, so they are not part of the live frontend surface. Their
capabilities belong in the backend for IAM's core brain and the local primary
model (`local-qwen-3b` / Qwen2.5) to use — see `IAM_ARCHITECTURE_COMPLETION_AUDIT.md`
and the backend capability audit note in `tools/rkie/notes/`.

`frontend/lib/iam-server-api.ts` is a server-only Data Access Layer. It contains
additional read helpers (capabilities, skills, languages, identity, memory,
conversations) for reuse, but those views are **not** frontend pages.

**Scope rule:** the frontend is exactly one user-facing page. Everything else is
backend, email or service functionality for IAM to use: no Creator UI (OD-19),
no operator/admin UI, no research, governance, Skill Forge, cybersecurity,
ARTEX, identity, memory or learning pages. Do not add browser pages for those
domains, and do not restore the earlier standalone pages as routes.

**Creator approvals are IAM's runtime mechanism, not a development-tool
permission.** When IAM wants to perform a privileged act (spend, delegate,
release a model, change legal authority) IAM asks the Creator and the Creator
signs an approval. This lives in `backend/app/services/creatorapproval_service.py`,
`backend/app/services/creator_keys.py`, `backend/app/api/routes/creatorapproval.py`
and is never a browser page.

## Security model

The DAL reads the backend credential from `IAM_USER_API_KEY` on the **server**
and sends it as a Bearer token. It is never imported by a Client Component and
never reaches the browser bundle. `IAM_API_URL` defaults to `http://localhost:8000`.
Visitors do not log in; the frontend is open and this single user-scope credential
is used server-side on their behalf.

Pages use `export const dynamic = "force-dynamic"` so data is fetched at request
time, not baked into the build. When no key is configured, pages degrade to a
clear "Backend not configured" state instead of failing.

## Next.js compliance

`frontend/AGENTS.md` requires reading the bundled docs before writing code. The
relevant guides consulted were `01-getting-started/03-layouts-and-pages.md`
(`searchParams` is a Promise in Next.js 16), `04-linking-and-navigating.md`
(`window.location` reads in handlers), `05-server-and-client-components.md`,
`06-fetching-data.md`, `02-guides/data-security.md` and
`02-guides/caching-without-cache-components.md`. The single page is an async
Server Component; interactivity stays in the client `IAMInterface`.

## Verification

- `npm run build` succeeds; `/` is marked dynamic (`ƒ`) because it reads `searchParams`.
- Legacy `/suggestions`, `/conversations` and `/conversations/:id` redirect to `/`
  (or `/?conversation=:id`) through `next.config.js` — no extra routes are created.

## Final scope — do not expand

- No frontend login. The frontend is open; one server-side user-scope credential
  acts on behalf of visitors and is never exposed to the browser.
- Exactly one page. Identity, memory, learning, capabilities, research,
  governance, Skill Forge, cybersecurity, ARTEX and all approvals remain
  backend/email/service functions. Conversations live in the single page's
  history drawer, not in separate routes.
- `lib/api.ts` remains only for client reads used by `IAMInterface`; server reads
  use the DAL.

## Configuration

See `frontend/.env.example` and the `frontend` service in `docker-compose.yml`.
