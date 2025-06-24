# MBA Job Hunter Backend - Multi-stage Production Dockerfile
# This Dockerfile uses multi-stage builds for optimal image size and security

# ======================
# Stage 1: Builder Stage
# ======================
FROM python:3.11-slim as builder

# Set build arguments
ARG ENVIRONMENT=production
ARG BUILD_DATE
ARG VERSION
ARG VCS_REF

# Set environment variables for build
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DEFAULT_TIMEOUT=100

# Install system dependencies needed for building
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    libpq-dev \
    libffi-dev \
    libssl-dev \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Set working directory
WORKDIR /app

# Copy dependency files
COPY requirements.txt requirements-dev.txt ./

# Create and activate virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt && \
    if [ "$ENVIRONMENT" = "development" ]; then \
        pip install --no-cache-dir -r requirements-dev.txt; \
    fi

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p /app/logs /app/static /app/media && \
    chown -R appuser:appuser /app

# ======================
# Stage 2: Runner Stage
# ======================
FROM python:3.11-slim as runner

# Set build arguments
ARG ENVIRONMENT=production
ARG BUILD_DATE
ARG VERSION
ARG VCS_REF

# Add labels for metadata
LABEL org.opencontainers.image.title="MBA Job Hunter Backend" \
      org.opencontainers.image.description="FastAPI backend service for MBA Job Hunter application" \
      org.opencontainers.image.version="$VERSION" \
      org.opencontainers.image.created="$BUILD_DATE" \
      org.opencontainers.image.revision="$VCS_REF" \
      org.opencontainers.image.source="https://github.com/your-org/mba-job-hunter" \
      org.opencontainers.image.authors="MBA Job Hunter Team" \
      environment="$ENVIRONMENT"

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random \
    PYTHONPATH=/app \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PATH="/opt/venv/bin:$PATH"

# Install only runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Set working directory
WORKDIR /app

# Copy virtual environment from builder stage
COPY --from=builder /opt/venv /opt/venv

# Copy application code from builder stage
COPY --from=builder --chown=appuser:appuser /app /app

# Create necessary directories with proper permissions
RUN mkdir -p /app/logs /app/static /app/media /app/config && \
    chown -R appuser:appuser /app && \
    chmod 755 /app/logs /app/static /app/media

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

# Default command
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]

# ======================
# Stage 3: Development Stage (optional)
# ======================
FROM builder as development

# Install development dependencies
RUN pip install --no-cache-dir -r requirements-dev.txt

# Install additional development tools
RUN pip install --no-cache-dir \
    ipython \
    jupyter \
    black \
    flake8 \
    mypy \
    pytest-cov

# Switch to non-root user
USER appuser

# Expose port for development
EXPOSE 8000

# Development command with hot reloading
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload", "--log-level", "debug"]

# ======================
# Stage 4: Production Stage (default)
# ======================
FROM runner as production

# Production-specific optimizations
ENV ENVIRONMENT=production \
    DEBUG=false \
    LOG_LEVEL=INFO

# Use gunicorn for production
CMD ["python", "-m", "gunicorn", "app.main:app", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000", "--access-logfile", "-", "--error-logfile", "-", "--log-level", "info"]