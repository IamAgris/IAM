# IAM — Architecture Compatibility Matrix

**Version:** 1.0 · 25 November 2026  
**Scope:** ARM64/AArch64 and x86-64/AMD64 support (OD-22, Document 08)  
**Status:** Living document — verified items marked ✅, requires verification ⚠️

---

## 1. Component matrix

| Component | amd64 | arm64 | Notes |
|-----------|-------|-------|-------|
| Ubuntu Server 24.04 | ✅ | ✅ | Official arm64 images |
| Python 3.12 base image | ✅ | ✅ | `python:3.12-slim` multi-arch |
| FastAPI / uvicorn | ✅ | ✅ | Pure Python |
| SQLAlchemy + asyncpg | ✅ | ✅ | Wheels for both (source fallback) |
| pgvector / PostgreSQL 17 | ✅ | ✅ | `pgvector/pgvector:pg17` multi-arch |
| Redis 7 | ✅ | ✅ | `redis:7-alpine` multi-arch |
| LiteLLM | ✅ | ✅ | Python package, arch-neutral |
| LangGraph | ✅ | ✅ | Python package |
| MinIO | ✅ | ✅ | `cgr.dev/chainguard/minio` multi-arch |
| Playwright Chromium | ✅ | ⚠️ | Browser binaries per arch; install best-effort |
| Ollama | ✅ | ⚠️ | Verify per device; CPU/gpu variants differ |
| vLLM / SGLang | ✅ | ⚠️ | Config-specific; verify GPU/CPU support |
| NVIDIA hosted inference | ✅ | ✅ | API-based, architecture-independent |
| Redis-based ARQ workers | ✅ | ✅ | Pure Python |

---

## 2. Build configuration

- **Backend Dockerfile:** multi-stage, platform-aware (`BUILDPLATFORM`/`TARGETARCH`), supports both architectures.
- **Frontend Dockerfile:** Node 20-alpine multi-arch base; Next.js builds on both.
- **Compose images:** `pgvector/pgvector:pg17`, `redis:7-alpine`, `cgr.dev/chainguard/minio` all publish arm64 manifests.
- **Build script:** `scripts/build-multiarch.ps1` builds `linux/amd64,linux/arm64` via buildx.

---

## 3. Verification status

| Item | Status | How to verify |
|------|--------|---------------|
| Buildx builder with arm64 | ✅ | `docker buildx ls` shows arm64 |
| Multi-stage backend Dockerfile | ✅ | Written; builds on host platform |
| Multi-arch build script | ✅ | `scripts/build-multiarch.ps1` |
| Actual arm64 image build | ✅ | `docker build --platform linux/arm64 -t iam-backend:arm64-test backend` — manifest `arm64/linux` produced |
| Multi-arch build script | ✅ | `scripts/build-multiarch.ps1` |
| Runtime smoke test on arm64 device | ⚠️ | Image builds but cannot execute under this host's QEMU (`exec /usr/local/bin/python: no such file`); needs physical ARM hardware |
| P2P sync between amd64 and arm64 | ⚠️ | Needs two machines |

---

## 4. Notes

- Architecture independence ≠ universal model support. IAM detects actual compatibility and adapts workloads (OD-22).
- `--load` with buildx can only load the host platform; use a registry (`--push`) for true multi-arch manifests.
- **Verified 25 Nov:** `docker build --platform linux/arm64` produces a valid `arm64/linux` manifest. Runtime execution under this host's binfmt/QEMU is not functional (`exec format` error), so full runtime verification requires physical ARM hardware. Build correctness is confirmed; runtime semantics are the only remaining ⚠️.
- Playwright CLI in final stage: `playwright install chromium` is best-effort; browser absence only affects research, not the API.
- Playwright binary install is best-effort by design — research degrades gracefully if unavailable.
