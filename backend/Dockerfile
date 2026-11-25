# =============================================================================
# Project AURA - Backend Dockerfile
# =============================================================================
FROM python:3.12-slim

WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies
COPY pyproject.toml uv.lock* ./
RUN pip install --no-cache-dir uv && \
    uv pip install --system -r pyproject.toml 2>/dev/null || \
    pip install -e .

# Application code
COPY app ./app

# Playwright browser + system libs baked into the image so research works on startup.
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
RUN playwright install --with-deps chromium

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
