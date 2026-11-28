# IAM — Architecture Independence & Hardware Adaptation

**Document:** 08 (addendum to Documents 01–07)  
**Version:** 1.0 · 25 November 2026  
**Status:** FROZEN — permanent architecture requirement  
**Confirmed decision:** OD-22 (ARM64 + x86-64 support)

---

## 1. Mission

IAM must remain independent of any single processor architecture or hardware vendor. It must be capable of operating, developing, testing, optimising and deploying its software across supported ARM64/AArch64 and x86-64/AMD64 environments, adapting its capabilities to the resources available on each device.

**Important distinction:** architecture independence does **not** mean every AI model or application runs on every device. IAM must detect actual compatibility and adapt its workload rather than assume universal support.

---

## 2. Supported architectures

| Architecture | Examples |
|---|---|
| ARM64 / AArch64 | AWS Graviton, Ampere Altra, Raspberry Pi 4/5, Apple Silicon (with suitable OS/runtime) |
| x86-64 / AMD64 | AMD EPYC/Ryzen, Intel Xeon/Core |
| GPU-accelerated | NVIDIA GPU systems, supported ARM64 GPU platforms |
| Low-resource devices | ARM single-board computers, modest ARM servers |

---

## 3. Architecture Independence and Hardware Adaptation Engine (AIHAE)

AIHAE responsibilities:

1. Detect whether running on ARM64 or x86-64.
2. Detect CPU instructions/features, RAM, storage and accelerators.
3. Select compatible software packages and dependencies.
4. Build and run software for different architectures.
5. Select suitable AI models and inference engines.
6. Optimise memory usage and CPU performance.
7. Cross-compile applications for other supported architectures.
8. Test software on ARM64 before deployment.
9. Move projects and permitted knowledge between ARM64 and x86-64 environments.
10. Detect unsupported components and find compatible replacements.

---

## 4. Component compatibility matrix

| Component | ARM64 requirement |
|---|---|
| Ubuntu Server | ARM64 builds |
| Docker | Multi-platform images (`linux/amd64`, `linux/arm64`) |
| Python / FastAPI | ARM64-compatible dependencies |
| PostgreSQL / pgvector | ARM64-compatible builds |
| Redis | ARM64-compatible builds |
| LiteLLM | Python dependency compatibility |
| Ollama | Verify support for the specific ARM64 device |
| vLLM / SGLang | Verify CPU/GPU and ARM64 support per configuration |
| Playwright | Compatible browser binaries |
| AI models | Model-specific ARM64 inference compatibility |

Docker images must support both `linux/amd64` and `linux/arm64` wherever practical.

---

## 5. Workload distribution

- Raspberry Pi → lightweight IAM node
- ARM server → backend, database or development workers
- x86-64 server → other workloads
- GPU system → demanding inference
- Trusted P2P nodes → share validated knowledge across architectures

Not every node needs every capability. IAM distributes workloads according to available resources and compatibility. ARM64 and x86-64 deployments must communicate and synchronise compatible knowledge regardless of hardware.

---

## 6. Acceptance criteria

1. Detects architecture (ARM64 / x86-64) at runtime.
2. Detects CPU features, RAM, storage and accelerators.
3. Selects compatible dependencies and models.
4. Builds multi-architecture container images.
5. Cross-compiles and tests for ARM64 before deployment.
6. Migrates permitted projects/knowledge between architectures.
7. Detects unsupported components and finds replacements.
8. Adds no hard dependency on a single hardware vendor.
9. ARM64 and x86-64 peers synchronise compatible knowledge.
10. Degrades gracefully on low-resource devices.

---

## Implementation note — multi-arch build (27 November 2026)

`scripts/build-multiarch.ps1` builds backend and frontend images for `linux/amd64` and
`linux/arm64` with buildx, exporting one loadable Docker archive per platform under
`artifacts/multiarch/`. It creates a `docker-container` builder when none exists and
requires QEMU emulation for cross-architecture builds on this AMD64 host.

**Verified 27 November 2026:** `project-aura-backend:arm64` built and loaded locally;
`docker image inspect --format '{{.Architecture}}'` returns **arm64** (image size ~1.03 GB,
id `sha256:3e27adbef5d719ed8825af83152124f38a0799d65ba0e72211d9951772f95fcc`).
Arm64 Chromium, Firefox and WebKit were downloaded into `/ms-playwright` during the build.

The earlier failure was caused by the builder stage using `BUILDPLATFORM`, which produced
amd64 wheels and omitted Playwright from the copied site-packages. `backend/Dockerfile`
now builds on `TARGETPLATFORM` with a non-silent dependency install.

A frontend arm64 image has not been built yet; the build script can produce it with
`-Services frontend`.
