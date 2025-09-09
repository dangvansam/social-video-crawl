# Multi-stage build for Social Video Downloader
FROM python:3.11-slim as builder

# Install build dependencies and uv
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    make \
    ffmpeg \
    wget \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && curl -LsSf https://astral.sh/uv/install.sh | sh

# Set working directory
WORKDIR /app

# Copy uv files for better caching
COPY pyproject.toml uv.lock ./

# Install dependencies with uv
ENV PATH="/root/.cargo/bin:$PATH"
RUN uv sync --frozen --no-dev

# Production stage
FROM python:3.11-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    chromium \
    chromium-driver \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 appuser && \
    mkdir -p /app/download /app/logs && \
    chown -R appuser:appuser /app

# Copy Python packages from builder
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /root/.cargo/bin/uv /usr/local/bin/uv

# Set working directory
WORKDIR /app

# Copy application code
COPY --chown=appuser:appuser . .

# Switch to non-root user
USER appuser

# Add venv to PATH
ENV PATH=/app/.venv/bin:$PATH

# Expose port
EXPOSE 8001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8001/health')" || exit 1

CMD ["python", "src/api.py"]