# IAM frontend has exactly one page (28 November 2026)

Owner direction: the frontend is a **single page**. Every other capability is a
backend service for IAM's core brain to use, including the local primary model
`local-qwen-3b` (Qwen2.5-3B, OD-46). Creator approvals are IAM's own runtime
ask-the-Creator mechanism, not a development-agent permission.

## What changed in the working tree

- `frontend/app/page.tsx` — the only page; async Server Component reading
  `searchParams: Promise<{ conversation?: string | string[] }>` and passing
  `initialConversationId` to `IAMInterface`.
- Removed `frontend/app/suggestions/page.tsx`,
  `frontend/app/conversations/page.tsx`, `frontend/app/conversations/[id]/page.tsx`.
- `frontend/next.config.js` — temporary redirects:
  `/conversations/:id` → `/?conversation=:id`, `/conversations` → `/`,
  `/suggestions` → `/`. No new routes are created.
- `frontend/components/iam/interface.tsx` — the history drawer now contains the
  conversation list (select, create, delete) and URL sync via
  `window.history.replaceState`; suggestions and public nodes were already there.
- `docs/IAM_FRONTEND_IMPLEMENTATION.md` updated to the one-page scope rule.

## Creator approval clarification

IAM asks the Creator when it wants a privileged action. Implementation:
`backend/app/services/creatorapproval_service.py`, `creator_keys.py`,
`backend/app/api/routes/creatorapproval.py`. No browser UI (OD-19). Do not
describe this as an OpenCode/development-tool approval.

## Verification (28 November 2026)

- `npm run build` in `frontend/`: success. Routes: `ƒ /`, `○ /_not-found`,
  `ƒ /iam-proxy/[...path]` (route handler, not a page).
- `npx next start -p 3002`: `/` 200, `/?conversation=abc` 200;
  `/suggestions` → 307 `/`, `/conversations/abc` → 307 `/?conversation=abc`.

## Backend capability work

The underscore-prefixed legacy folders (`_ai-network`, `_financial-intelligence`,
`_freesandboxes`, `_iics`, `_tone`) stay non-routed. Their capabilities must be
usable from the backend by IAM/Qwen; audit and wiring status is recorded in
`docs/IAM_ARCHITECTURE_COMPLETION_AUDIT.md` and the backend capability audit result
for this session. Re-verify against current files before relying on this note.
