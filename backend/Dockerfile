# ============================================================
# BHOOMI — PRODUCTION BACKEND DOCKERFILE
# Build context: Repository root
# Build command: docker build -f backend/Dockerfile -t bhoomi-backend .
# ============================================================

FROM python:3.11-slim

# Prevent Python from writing .pyc files and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PORT=8000

WORKDIR /app

# Install essential system dependencies (Postgres client, ffmpeg for Sarvam audio processing)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    libpq-dev \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies first to leverage Docker layer caching
COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Create secure non-root application user
RUN groupadd -r bhoomi && useradd -r -g bhoomi -d /app bhoomi

# Copy application source code, runtime ML models, RAG knowledge, and web frontend
COPY backend/ /app/
COPY models/ /app/models/
COPY data/rag/ /app/data/rag/
COPY frontend/web/ /app/frontend/web/

# Ensure proper directory permissions for non-root user runtime operations
RUN mkdir -p /app/uploads /app/data/chroma && \
    ln -sfn /app/frontend /frontend && \
    chmod +x /app/start.sh && \
    chown -R bhoomi:bhoomi /app /frontend

# Switch to non-root user
USER bhoomi

# Expose default HTTP port
EXPOSE 8000

# Production startup: launches background scheduler worker and uvicorn web server
CMD ["/bin/bash", "/app/start.sh"]

