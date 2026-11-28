# Multi-arch image build — work in progress (27 November 2026)

## Files

- `scripts/build-multiarch.ps1` — buildx script for backend + frontend, `linux/amd64` and
  `linux/arm64`, exporting `artifacts/multiarch/<service>-<arch>.tar`.
- `docs/IAM_HARDWARE_ADAPTATION.md` — implementation note added at the end; criterion 4 remains
  unverified until an image is built.

## What happened

`docker buildx version` v0.38.1; builders reported `linux/arm64` among platforms (emulated).

- `docker buildx build --platform linux/arm64 --load ./backend` → buildx RPC EOF.
- `docker buildx create --name iam-multiarch --driver docker-container --bootstrap` →
  context deadline exceeded (Docker Desktop engine not responding).
- `docker build --platform linux/arm64 ./backend` → Docker API 500.
- `docker info` then hung and was moved to background; Docker Desktop appears overloaded
  after repeated container rebuilds during this session.

## Next step

Wait for Docker Desktop to recover, re-run `scripts/build-multiarch.ps1`, then verify with:

```
docker image inspect project-aura-backend:arm64 --format '{{.Architecture}}'
```

**Resolved:** after restoring Docker Desktop (`docker desktop restart`), a
`docker-container` buildx builder (`iam-multiarch`) completed the arm64 build.
`backend/Dockerfile` was fixed to build dependencies on `TARGETPLATFORM` instead of the
x86_64 `BUILDPLATFORM` — the original mistake produced amd64 wheels and left Playwright
out of the copied site-packages, causing `playwright: not found` at the final step.

**Verified:** `docker image inspect project-aura-backend:arm64 --format '{{.Architecture}}'`
returns `arm64`. Image ~1.03 GB. Arm64 Chromium, Firefox and WebKit installed.

Frontend arm64 image not yet built.
