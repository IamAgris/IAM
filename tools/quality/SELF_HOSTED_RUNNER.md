# Creating a runner for IAM workflows

There are three distinct meanings of "runner" here. Pick the one that matches
what you actually need.

## 1. GitHub-hosted runner (already in use)

Every workflow in `.github/workflows/` already runs on GitHub's hosted runners
(`runs-on: ubuntu-latest` / `windows-latest`) when you push or open a PR. There
is nothing to create — just push. This is the safest default for a public
repository.

## 2. Self-hosted runner (your own machine)

Use this only when you need local resources (Ollama, a GPU, an internal network,
docker compose with local images). A self-hosted runner on a public repository
is a security boundary: never run untrusted fork PRs on it.

### Steps

1. In GitHub: **Settings → Actions → Runners → New self-hosted runner**. Choose
   Windows or Linux; GitHub shows exact download/configure commands for your
   runner version.
2. On the host, create a directory (for example `C:\iam-runner`) and run the
   GitHub-provided download + `config.cmd` commands. When prompted:
   - registration token: the short-lived token shown on the setup page,
   - labels: `iam`, `windows`, `local` (comma separated),
   - runner name: e.g. `iam-dev-win`.
3. Start it interactively with `run.cmd`, or install as a service:
   ```powershell
   .\svc.cmd install
   .\svc.cmd start
   ```
4. Confirm it shows **Idle** under Settings → Actions → Runners.
5. Target it from a workflow:
   ```yaml
   jobs:
     local-checks:
       runs-on: [self-hosted, iam, windows]
   ```
   A guarded example is in `.github/workflows/self-hosted.yml`.

### Safety rules

- Set the runner to accept only `workflow_dispatch` or trusted-branch pushes;
  do not run `pull_request` from forks on a self-hosted runner.
- Run it in a dedicated account/VM/container, not a developer workstation with
  secrets on disk.
- Use ephemeral runners where possible (`--ephemeral`) so each job gets a fresh
  environment.
- Never expose repository secrets to jobs on a self-hosted runner unless the
  workflow is fully trusted.

## 3. `act` — run workflows locally with Docker

Docker is available on this machine (`docker --version` reports 29.9.3), so
`act` is the lightest way to execute workflow jobs locally:

```powershell
winget install nektos.act
act --version
act -l                          # list jobs discovered from workflows
act -j rkie-smoke -P ubuntu-latest=catthehacker/ubuntu:act-latest
```

Notes:

- `act` simulates GitHub's environment; it does not provide GitHub tokens,
  secrets or runner labels unless you pass `--secret-file`/`-s`.
- Compose-based acceptance (`quality-gates.yml` `acceptance`) needs host ports
  8000/5433 and may not work inside `act`; run that job directly on the host
  instead.
- Windows-targeted jobs (`rkie-tests.yml`) require a Windows runner; `act`
  primarily runs Linux containers. Use the self-hosted Windows runner for
  those.

## Recommendation

Keep GitHub-hosted runners for all PR checks. Add a labelled self-hosted
runner only for jobs that genuinely need local Ollama/GPU/compose, and gate
those jobs to `workflow_dispatch`. Use `act` for quick local iteration, and
`tools/quality/run_local_ci.py` for the deterministic gates without a runner.
