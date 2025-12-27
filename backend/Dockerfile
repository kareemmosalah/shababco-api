FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH=/app

WORKDIR /app/

# Install system dependencies (curl for health checks)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast package management
COPY --from=ghcr.io/astral-sh/uv:0.5.11 /uv /uvx /bin/

# ================================
# Stage 2: Dependencies (Production)
# ================================
FROM base AS dependencies

# Install Python dependencies (cached layer)
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev

# ================================
# Stage 3: Application (Production)
# ================================
FROM base AS application

# Copy virtual environment from dependencies stage
COPY --from=dependencies /app/.venv /app/.venv

# Copy application files
COPY ./scripts /app/scripts
COPY ./pyproject.toml ./uv.lock /app/
COPY ./app /app/app

# Sync project (fast since deps already installed)
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# Make scripts executable
RUN chmod +x /app/scripts/*.sh

# Create non-root user for security
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app

USER appuser

# Expose application port
EXPOSE 8000

# Health check for container orchestration
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/utils/health-check/ || exit 1

# Run migrations then start production server
# Uses uvicorn with 4 workers for production
CMD ["/bin/bash", "-c", "/app/scripts/prestart.sh && exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4 --timeout-keep-alive 120 --proxy-headers --access-log"]

# ================================
# Stage 4: Development (Hot Reload)
# ================================
FROM base AS development

# Install ALL dependencies including dev tools
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project

# Copy application files
COPY ./scripts /app/scripts
COPY ./pyproject.toml ./uv.lock /app/
COPY ./app /app/app
COPY ./tests /app/tests

# Sync project with dev dependencies
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen

# Make scripts executable
RUN chmod +x /app/scripts/*.sh

# Run as root in dev for easier debugging
# (volume mounts may have different ownership)

EXPOSE 8000

# Development server with hot reload
CMD ["/bin/bash", "-c", "/app/scripts/prestart.sh && exec fastapi dev --host 0.0.0.0 --port 8000 app/main.py"]
