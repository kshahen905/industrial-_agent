# Build Stage
FROM python:3.10-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user --default-timeout=1000 \
    --index-url https://download.pytorch.org/whl/cpu \
    -r requirements.txt || \
    pip install --no-cache-dir --user --default-timeout=1000 -r requirements.txt

# Final Stage
FROM python:3.10-slim

# Install runtime dependencies (nc for entrypoint wait loop)
RUN apt-get update && apt-get install -y --no-install-recommends \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/root/.local/bin:$PATH" \
    LITE_MODE=false \
    CHROMA_HOST=chromadb \
    CHROMA_PORT=8000 \
    OLLAMA_BASE_URL=http://host.docker.internal:11434 \
    PYTHONPATH=/app

WORKDIR /app

# Copy installed dependencies from builder
COPY --from=builder /root/.local /root/.local

# Copy application code
COPY . .

# Make entrypoint script executable
RUN chmod +x docker-entrypoint.sh

# Expose API port
EXPOSE 8000

# Use entrypoint script
ENTRYPOINT ["./docker-entrypoint.sh"]
