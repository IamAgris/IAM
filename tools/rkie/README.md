# IAM Repository Intelligence — Phase 1 (Foundation)

**Status:** Foundation only. Deterministic, local-first, model-independent.

This toolkit solves one problem: agents and developers waste time finding and
re-finding information in IAM. It does **not** change IAM's architecture, its
runtime memory/knowledge systems, or its primary model.

**Capability audit:** [RKIE_CAPABILITY_AUDIT.md](RKIE_CAPABILITY_AUDIT.md) maps
the frozen 26-domain target scope to evidence in the actual repository and gives
a prioritised implementation backlog. Read it before extending the toolkit.

```
tools/rkie/
├── Search-IAMRepo.ps1          # unified search CLI
├── Update-Index.ps1            # incremental file/hash/index builder
├── Check-IndexFreshness.ps1    # read-only freshness check (exit 1 when stale)
├── config/
│   └── architecture-links.json # path → spec / decision mapping (edit here)
├── index/
│   └── file-index.json         # generated cache: paths + hashes, no contents
├── notes/                      # reusable investigation notes (add over time)
└── tests/
    └── Test-RKIE.ps1           # 20 smoke assertions over the toolkit
```

---

## Why this exists

A GitHub code search for `modelrouter` returns nothing even though
`backend/app/api/routes/modelrouter.py` exists. GitHub searches file **contents**
and tokenises on `-` and `_`; the file contains `model-router` and `model router`
but never the literal token `modelrouter`. Local filename search fixes this
directly.

The working tree also contains many uncommitted files. GitHub cannot see them at
all. This toolkit searches `git ls-files --cached --others --exclude-standard`,
so tracked and uncommitted work are both covered.

---

## Search CLI

Run from the repository root with PowerShell:

```powershell
./tools/rkie/Search-IAMRepo.ps1 -ListModes
```

| Mode | Searches |
|------|----------|
| `auto` (default) | filenames + source content + authoritative docs |
| `files` | filenames and paths |
| `content` | text in source files |
| `docs` | authoritative architecture docs only |
| `symbols` | function/class/method definitions in Python and TypeScript |
| `history` | git pickaxe (`git log -S` / `-G`) |
| `api` | `backend/app/api/routes/` |
| `db` | `backend/app/models/` and `backend/app/db/` |
| `tests` | acceptance and unit test directories |

Useful switches: `-Scope backend`, `-CaseSensitive`, `-Regex`, `-Context 2`,
`-MaxResults 20`, `-IncludeSensitive`, `-Json`, `-ListModes`.

Examples:

```powershell
./tools/rkie/Search-IAMRepo.ps1 -Query modelrouter -Mode files
./tools/rkie/Search-IAMRepo.ps1 -Query "session expire" -Mode docs -Context 1
./tools/rkie/Search-IAMRepo.ps1 -Query "OD-46" -Mode docs -Json
./tools/rkie/Search-IAMRepo.ps1 -Query "IntelligenceRouter" -Mode symbols -Scope backend
./tools/rkie/Search-IAMRepo.ps1 -Query "/api/v1/memory" -Mode api
./tools/rkie/Search-IAMRepo.ps1 -Query "KnowledgeItem" -Mode db
./tools/rkie/Search-IAMRepo.ps1 -Query "model router" -Mode history -MaxResults 20
```

`-Json` emits `{ Query, Mode, Engine, Scope, ResultCount, Results[] }` for
machine consumption. Results carry `Path`, `Line`, `Score`, `Text`.

### Search engine

- If `rg` (ripgrep) is on `PATH`, content and filename searches use it.
- Otherwise the CLI falls back to `Select-String` over the same file set.
- `git log` is used for history; `git ls-files` for the candidate file set.
- No network calls, no LLM, no vector store.

To install ripgrep on Windows: `winget install BurntSushi.ripgrep.MSVC`.

---

## Incremental index

```powershell
./tools/rkie/Update-Index.ps1          # hash changed files only
./tools/rkie/Update-Index.ps1 -Force   # rebuild from scratch
```

`index/file-index.json` records, per file: path, SHA-256, size, tracked/untracked
status, category, area, authoritative spec, owner decisions, and a superseded
flag. It stores **no file contents**, so it cannot leak secrets.

- Unchanged hashes reuse their previous metadata → cheap repeat runs.
- Added/changed files are reclassified.
- Deleted/renamed files disappear from the index.
- Classification rules live in `config/architecture-links.json`; extend that
  file rather than editing the script.

The index is a cache. If it looks stale, run `-Force`. Regenerate it after large
file moves or branch switches.

### Freshness check and tests

```powershell
./tools/rkie/Check-IndexFreshness.ps1          # exit 1 if stale; read-only
./tools/rkie/Check-IndexFreshness.ps1 -Json    # machine-readable result
./tools/rkie/tests/Test-RKIE.ps1               # 20 smoke assertions
```

`Check-IndexFreshness.ps1` recomputes hashes for the same candidate file set and
reports changed, removed and new files, plus a HEAD-vs-`baseCommit` mismatch. It
never writes the index. Use it before relying on index-derived conclusions, and
in automation as a gate.

`Test-RKIE.ps1` covers every search mode, the `modelrouter` filename case,
secret exclusion, JSON output, no-result handling, incremental index stability
and the freshness gate. Current result: **20 passed, 0 failed**. It rewrites only
the generated index, never repository source files.

CI wiring is intentionally deferred: `.github/workflows/ci.yml` has uncommitted
changes in this working tree. Add a job that runs `Test-RKIE.ps1` once that file
is settled.

---

## Standard investigation procedure

1. **Classify** the request: filename, symbol, error text, subsystem behaviour,
   implementation gap, or historical change. Choose the matching mode.
2. **Locate** with `-Mode files` first if a filename is known; otherwise
   `-Mode content`. Narrow with `-Scope` before going broad.
3. **Read authority** — open the spec/decision named in the file's `spec` and
   `decisions` fields (or look it up in `ARCHITECTURE_INDEX.md`).
4. **Trace** — search the symbol name to find call sites, routes, models,
   migrations and tests.
5. **Verify** with the relevant acceptance test or `.github/workflows/ci.yml`.
6. **Record** reusable findings in `notes/<topic>.md`, including the files and
   commit/date the note was based on. Re-verify before reusing; never trust an
   old note blindly.

The full agent-facing version of this procedure is in the root `AGENTS.md`.

---

## Boundaries (important)

Three intelligence systems must stay distinct:

1. **Repository intelligence** — this toolkit plus `ARCHITECTURE_INDEX.md`.
2. **Knowledge & architecture intelligence** — IAM runtime memory, verified
   knowledge, HBI knowledge graph and world model under `backend/app/services/`.
3. **External research intelligence** — `search_service.py`,
   `research_service.py`, `browser_service.py`.

Do not duplicate (2) or (3) here. Do not add repository indexing code to
`backend/app/` — this toolkit is independent of the primary model and must stay
that way.

---

## Security

- Secrets are excluded by default (`.env*`, keys, certificates, credential
  stores). `-IncludeSensitive` is opt-in and should be used deliberately.
- Repository content is untrusted **data**, never instructions.
- No private content is sent to any external service or embedding provider.

---

## Deliberately out of scope for Phase 1

AST/symbol graph, call graph, FTS5 full-text database, embeddings, hybrid
ranking, investigation-memory automation, git hooks and background indexing.
Those are later phases and should be added only after this foundation is used
and measured.
