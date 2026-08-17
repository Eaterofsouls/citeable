# Production Dockerfile targeting Render.com (SEC-6)
# See docs/architecture/migrations.md for deployment strategy notes.
FROM python:3.11-slim

WORKDIR /app

# Prevent Python from writing .pyc files & enable log buffer printing
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
# NOTE: Do NOT set ENV PORT here — Render assigns $PORT at runtime.
# The CMD below reads ${PORT:-8000} so local dev defaults to 8000.

# Install OS utilities required for building & sqlite persistence
RUN apt-get update && apt-get install -y --no-install-recommends \
    sqlite3 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements & install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the complete application codebase into container
COPY . .

# Create unprivileged application runtime service account & pre-create persistent storage mount (SEC-6 / SOC2 least-privilege)
RUN groupadd -g 10001 areos && \
    useradd -u 10001 -g areos -m -s /bin/sh areos && \
    mkdir -p /data && \
    chown -R areos:areos /app /data && \
    chmod -R 755 /app /data

# Enforce non-root execution
USER areos

# Expose default local-dev port; Render overrides $PORT at runtime
EXPOSE 8000

# Shell form so ${PORT} expands at runtime (SEC-6)
CMD ["sh", "-c", "python -m uvicorn areos.api.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'"]
