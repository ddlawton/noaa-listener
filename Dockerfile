# Use Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*


# Copy all source files (including pyproject.toml, README.md, and noaa_listener/)
COPY . .

# Install uv and project dependencies
RUN pip install --no-cache-dir uv && \
    uv pip install --system --no-cache .

# Create logs directory
RUN mkdir -p logs

# Create a non-root user
RUN useradd -m -u 1000 noaa && \
    chown -R noaa:noaa /app

USER noaa

# Health check
HEALTHCHECK --interval=5m --timeout=3s --start-period=30s --retries=3 \
    CMD python -c "from noaa_listener.database import Database; from noaa_listener.config import get_config; db = Database(get_config()); import sys; sys.exit(0 if db.test_connection() else 1)"

# Default command (can be overridden in docker-compose)
CMD ["python", "-m", "noaa_listener.main"]
