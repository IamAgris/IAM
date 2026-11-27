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
    libpq5 curl ca-certificates ffmpeg libatomic1 libglib2.0-0 libnss3 libnspr4 \
    tesseract-ocr tesseract-ocr-eng \
    libdbus-1-3 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 \
    libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 libxrandr2 \
    libgbm1 libasound2 libpango-1.0-0 libcairo2 \
    libgtk-4-1 libgtk-3-0t64 libxslt1.1 libevent-2.1-7 \
    libharfbuzz-icu0 libepoxy0 libsecret-1-0 libhyphen0 libgles2 \
    libwoff1 libopus0 libwebpdemux2 libenchant-2-2 \
    libgstreamer1.0-0 libgstreamer-plugins-base1.0-0 libgstreamer-plugins-bad1.0-0 \
    libmanette-0.2-0 libflite1 libavif16 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY app ./app

# Playwright browser + system libs. Best-effort and platform-aware; an apt
# hiccup must not block the API image. Research degrades gracefully.
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
# playwright CLI is copied from builder; install browser best-effort (needs system libs
# from the runtime stage). Failure is non-fatal — research degrades gracefully.
RUN (playwright install chromium firefox webkit || true)

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
