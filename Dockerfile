# Pwnagotchi Dashboard Docker Image
# Multi-stage build for production optimization

# Build stage
FROM python:3.11-slim as builder

# Set build arguments
ARG BUILD_DATE
ARG VCS_REF
ARG VERSION=latest

# Add metadata
LABEL maintainer="Pwnagotchi Team" \
      description="Pwnagotchi Dashboard - Production Web Interface" \
      version="${VERSION}" \
      build-date="${BUILD_DATE}" \
      vcs-ref="${VCS_REF}"

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Upgrade pip and install wheel
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Copy requirements first for better caching
COPY requirements.txt /tmp/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r /tmp/requirements.txt gunicorn

# Production stage
FROM python:3.11-slim as production

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    FLASK_ENV=production \
    PYTHONPATH=/app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    wireless-tools \
    net-tools \
    iproute2 \
    procps \
    sudo \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create application user
RUN groupadd -r pwnagotchi && \
    useradd -r -g pwnagotchi -d /app -s /bin/bash pwnagotchi

# Copy virtual environment from builder stage
COPY --from=builder /opt/venv /opt/venv

# Create necessary directories
RUN mkdir -p /app /var/log/pwnagotchi /etc/pwnagotchi && \
    chown -R pwnagotchi:pwnagotchi /app /var/log/pwnagotchi /etc/pwnagotchi

# Set working directory
WORKDIR /app

# Copy application files
COPY --chown=pwnagotchi:pwnagotchi . /app/

# Create configuration file
RUN echo '{\
  "server": {\
    "host": "0.0.0.0",\
    "port": 8080,\
    "debug": false\
  },\
  "security": {\
    "secret_key": "docker-default-key-change-in-production",\
    "rate_limit": {\
      "per_day": 1000,\
      "per_hour": 200,\
      "per_minute": 30\
    }\
  },\
  "logging": {\
    "level": "INFO",\
    "file": "/var/log/pwnagotchi/api.log",\
    "max_size": "10MB",\
    "backup_count": 5\
  },\
  "pwnagotchi": {\
    "name": "pwnagotchi-docker",\
    "scan_interval": 5,\
    "auto_mode": true\
  }\
}' > /etc/pwnagotchi/config.json && \
    chown pwnagotchi:pwnagotchi /etc/pwnagotchi/config.json

# Create health check script
RUN echo '#!/bin/bash\ncurl -f http://localhost:8080/api/status || exit 1' > /usr/local/bin/healthcheck.sh && \
    chmod +x /usr/local/bin/healthcheck.sh

# Switch to application user
USER pwnagotchi

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD /usr/local/bin/healthcheck.sh

# Default command
CMD ["gunicorn", \
     "--bind", "0.0.0.0:8080", \
     "--workers", "4", \
     "--worker-class", "sync", \
     "--worker-connections", "1000", \
     "--max-requests", "1000", \
     "--max-requests-jitter", "100", \
     "--timeout", "30", \
     "--keep-alive", "2", \
     "--preload", \
     "--access-logfile", "/var/log/pwnagotchi/access.log", \
     "--error-logfile", "/var/log/pwnagotchi/error.log", \
     "--log-level", "info", \
     "--capture-output", \
     "backend_api:app"]
