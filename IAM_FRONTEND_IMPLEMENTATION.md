# Frontend Implementation Note

**Status:** Scope locked. Verified with Next.js 16.4.6.

## What is live

The frontend currently has these routable pages (verified against the working tree on 28 November 2026):

- `frontend/app/page.tsx` — `IAMInterface` home view.
- `frontend/app/suggestions/page.tsx` — Focus/Recall/Create prompts and public knowledge nodes.
- `frontend/app/conversations/page.tsx` and `frontend/app/conversations/[id]/page.tsx` — conversation list and detail views.

`frontend/app/iam-proxy/[...path]/route.ts` is a server-only route handler, not a page.
The underscore-prefixed directories (`_ai-network`, `_financial-intelligence`,
`_freesandboxes`, `_iics`, `_tone`) are retained as historical source only; Next.js
does not route them, so they are not part of the live frontend surface.

`frontend/lib/iam-server-api.ts` is a server-only Data Access Layer. It contains
additional read helpers (capabilities, skills, languages, identity, memory,
conversations) for reuse, but those views are **not** frontend pages.

**Scope rule:** the frontend is user-only and consists of the home interface,
the suggestions page and the conversations views. Everything else is backend,
email or service functionality: no Creator UI (OD-19), no operator/admin UI,
no research, governance, Skill Forge, cybersecurity, ARTEX, identity, memory or
learning pages. Do not add browser pages for those domains, and do not restore
the earlier standalone pages as routes.

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
relevant guides consulted were `01-getting-started/05-server-and-client-components.md`,
`06-fetching-data.md`, `02-guides/data-security.md` and
`02-guides/caching-without-cache-components.md`. Pages are async Server Components;
there are no `'use client'` directives in the new code.

## Verification

- `npm run build` succeeds; `/suggestions` is marked dynamic (`ƒ`).
- `next start` smoke test: `/suggestions` returned HTTP 200 and rendered the expected
  headings and unconfigured-state message.

## Final scope — do not expand

- No frontend login. The frontend is open; one server-side user-scope credential
  acts on behalf of visitors and is never exposed to the browser.
- No additional pages. Identity, memory, learning, capabilities, conversations,
  research, governance, Skill Forge, cybersecurity, ARTEX and all approvals remain
  backend/email/service functions.
- `lib/api.ts` remains only for any legacy client reads; new server reads use the DAL.

## Configuration

See `frontend/.env.example` and the `frontend` service in `docker-compose.yml`.
