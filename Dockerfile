# =============================================================================
# Stage 1: Builder — install dependencies in a fat image
# =============================================================================
FROM python:3.11-slim AS builder

WORKDIR /build

# System deps for building native extensions (pycairo, argon2-cffi, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libffi-dev \
    python3-dev \
    pkg-config \
    libcairo2-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Install Python deps into a virtual-env so we can copy it cleanly
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir --upgrade pip setuptools wheel \
    && pip install --no-cache-dir -r requirements.txt


# =============================================================================
# Stage 2: Runtime — lean production image
# =============================================================================
FROM python:3.11-slim AS runtime

LABEL description="Migration Validation & Risk Audit Framework"
LABEL version="0.9.0"

WORKDIR /app

# Runtime-only system libs (pycairo needs libcairo2 at runtime)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libcairo2 \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd -r appuser && useradd -r -g appuser -d /app appuser

# Copy the pre-built virtualenv from the builder stage
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Copy application code
COPY . .

# Create required directories
RUN mkdir -p /app/data /app/outputs /app/config /app/reports /app/logs \
    && chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose the port
EXPOSE 8001

# Health check — hit the root endpoint every 30s
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8001/ || exit 1

# Run the application
CMD ["uvicorn", "core.web.app:app", "--host", "0.0.0.0", "--port", "8001"]
