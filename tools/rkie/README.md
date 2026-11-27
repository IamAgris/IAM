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

## Phase 2 — code intelligence features

All of these are local, deterministic Python features under `tools/rkie/`:

```powershell
python tools/rkie/repo_intel.py build                         # AST + SQLite FTS5 indexes
python tools/rkie/repo_intel.py --json symbol IntelligenceRouter
python tools/rkie/repo_intel.py --json search "modelrouter"
python tools/rkie/repo_intel.py --json impact backend/app/api/routes/modelrouter.py
python tools/rkie/repo_intel.py --json health
python tools/rkie/repo_intel.py --json history "OD-46"
python tools/rkie/repo_intel.py --json git changelog --from-ref HEAD~5
python tools/rkie/repo_intel.py --json memory record auth --files AGENTS.md
python tools/rkie/repo_intel.py --json memory verify auth
python tools/rkie/repo_intel.py --json benchmark
python tools/rkie/agent_api.py plan --input '{"question":"who calls X?"}'
```

| Feature | Implementation |
|---------|----------------|
| AST index | `intel_core.CodeIndex` — definitions, imports, calls, routes, ORM models, spec/decision links |
| Hybrid search | `intel_core.HybridSearch` — exact symbols > filenames > SQLite FTS5 > fuzzy fallback |
| Impact analysis | `change_impact()` — changed symbols → call sites, importers, routes, models, tests, specs |
| Repository health | cycles, dead-symbol candidates, sources without tests, broken doc references |
| Git intelligence | pickaxe, blame, diff stat, changelog between refs |
| Investigation memory | `notes/memory/*.json` with file hashes; `verify` marks evidence stale |
| Search benchmark | fixed query set, recall@20 and latency recorded in `index/benchmark.json` |
| Agent interface | `agent_api.py` — `search`, `symbol`, `impact`, `history`, `remember`, `verify_memory`, `health`, `benchmark`, `plan` |

`agent_api.py` is the stable model-independent interface: Qwen2.5:3B may call
it, but indexing, ranking and verification stay deterministic tools.

Current benchmark: **recall@20 = 1.0** on five fixed queries. Current health
report lists real broken documentation references and dead-symbol candidates;
those are findings, not false alarms to suppress.

## Additional Phase 2 services

```powershell
python tools/rkie/index_migrations.py --check --json
python tools/rkie/watch_index.py --once --json
python tools/rkie/multi_repo.py list --json
python tools/rkie/agent_coordination.py status --json
python tools/quality/mypy_debt.py --top 10
python tools/quality/check_workflows.py --json
```

- **Semantic retrieval** — `semantic.py` builds a local TF-IDF vector index
  (`index/semantic.sqlite`) and returns cosine-ranked results labelled
  `source: semantic`. It supplements exact/FTS results, never replaces them.
  It is deliberately lexical-semantic and local; a neural embedding model can
  be swapped in behind the same interface later.
- **Index schema migrations** — `index_migrations.py` versions the index
  contract (`index/INDEX_SCHEMA.json`) and checks/rebuilds derived indexes.
- **Background indexing** — `watch_index.py` polls file hashes and rebuilds
  only on change; `--once` is the CI-safe mode, without it the process loops.
- **Multi-repository registry** — `config/repositories.json` marks each repo's
  role and authority. External research results are labelled `authority:
  external` and are never treated as implementation evidence.
- **Persistent agent coordination** — `agent_coordination.py` stores topic
  claims with leases in `index/agent-coordination.json` so parallel agents do
  not duplicate investigations or collide on files.
- **Quality tracking** — `tools/quality/mypy_debt.py` ranks typing debt;
  `check_workflows.py` statically validates all workflow YAML and script
  references.

## Local models, watchers and external sync

```powershell
python tools/rkie/embeddings.py
python tools/rkie/watch_index.py --watch-os --interval 30
python tools/rkie/external_sync.py --apply --json
python tools/rkie/external_sync.py --verify --json
python tools/quality/run_local_ci.py --only workflows
```

- `embeddings.py` is a **local-only adapter** for Ollama embeddings. It is
  enabled against a locally running Ollama instance with `nomic-embed-text`
  (768 dimensions). `neural.py` lazily embeds only the shortlist from exact/FTS
  retrieval and caches vectors by file hash in `index/neural-cache.sqlite`;
  results are labelled `source: neural_rerank` and never replace exact/filename
  hits. If the endpoint is unreachable it fails closed and the TF-IDF index
  remains authoritative. Check with `python tools/rkie/neural.py status --json`. No content is sent externally.
- `watch_index.py --watch-os` uses `watchdog` for OS-level file events;
  the default mode still polls hashes and works without that dependency.
- `external_sync.py` synchronises metadata from registered external sources
  into `index/external-knowledge.json`, always labelled `authority: external`.
  It performs no network access and never merges external text into the
  authoritative implementation index.
- `tools/quality/run_local_ci.py` runs the deterministic gates locally in CI
  order. It is a simulation, not GitHub Actions.

### Setting up embeddings on another machine

```powershell
./tools/rkie/setup_local_embeddings.ps1          # Windows: install/start Ollama, pull model, enable config
./tools/rkie/setup_local_embeddings.ps1 -CheckOnly
```
```bash
./tools/rkie/setup_local_embeddings.sh           # Linux/macOS
./tools/rkie/setup_local_embeddings.sh --check
```

If Ollama cannot be installed natively, `setup_ollama_docker.ps1` runs it in a
container instead (`docker run -p 11434:11434 ...`), pulls the model and
enables the same config. The adapter fails closed to TF-IDF where no local
model exists; the re-rank test skips automatically in those environments.
Runner setup is documented in `tools/quality/SELF_HOSTED_RUNNER.md`.

## Still not implemented

Neural embeddings where neither Ollama nor the bootstrap script can be used
(the adapter fails closed to TF-IDF there), actual reduction of the ~2,000-error
mypy baseline (the ratchet and debt tracker exist; a libcst codemod is provided
but Windows App Control blocks libcst's native extension on this host), and an
actual GitHub Actions run (workflow steps were executed locally in Docker, but
Actions itself remains external).
