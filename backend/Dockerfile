# backend/Dockerfile
# ==============================
# Vigil Backend - FastAPI / Uvicorn
# ==============================

FROM python:3.11-slim

# Prevent Python from writing .pyc files and buffering stdout
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install system dependencies (curl for health checks, gcc for pip compilation)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        curl \
        gcc \
        && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Create a non-root user for security
RUN addgroup --system appgroup && \
    adduser --system --ingroup appgroup appuser

# Set working directory
WORKDIR /app

# Install Python dependencies (layer caching: only re-install when requirements.txt changes)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
# The .dockerignore excludes venv, __pycache__, .env, etc.
COPY . .

# Change ownership to non-root user
RUN chown -R appuser:appgroup /app

# Switch to non-root user
USER appuser

# Expose the application port
EXPOSE 8001

# Health check: verify the API is responding
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl --fail http://localhost:8001/api/ || exit 1

# Run uvicorn server
# --forwarded-allow-ips='*' is needed when behind nginx reverse proxy
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8001", "--forwarded-allow-ips", "*"]