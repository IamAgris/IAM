# syntax=docker/dockerfile:1
# =============================================================================
# IAM Backend — multi-architecture (linux/amd64, linux/arm64)
# =============================================================================
FROM --platform=$BUILDPLATFORM python:3.12-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
RUN pip install --no-cache-dir uv && \
    (uv pip install --system -r pyproject.toml 2>/dev/null || pip install --no-cache-dir -e .)

# -----------------------------------------------------------------------------
FROM python:3.12-slim

WORKDIR /app

# TARGETARCH is provided automatically by BuildKit — used for platform-specific
# dependency notes. Both amd64 and arm64 packages are available from Debian/pip.
ARG TARGETARCH
ENV IAM_TARGET_ARCH=${TARGETARCH}

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY app ./app

# Playwright browser + system libs. Best-effort and platform-aware; an apt
# hiccup must not block the API image. Research degrades gracefully.
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
# playwright CLI is copied from builder; install browser best-effort (needs system libs
# from the runtime stage). Failure is non-fatal — research degrades gracefully.
RUN (playwright install chromium || true)

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
