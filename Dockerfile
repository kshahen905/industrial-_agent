# Build Stage
FROM python:3.10-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies into a temporary directory
COPY requirements-lite.txt .
RUN pip install --no-cache-dir --user -r requirements-lite.txt

# Final Stage
FROM python:3.10-slim

# Set environment variables
ENV LITE_MODE=true \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/root/.local/bin:$PATH" \
    CHROMA_HOST=chroma \
    CHROMA_PORT=8000 \
    OLLAMA_BASE_URL=http://host.docker.internal:11434

WORKDIR /app

# Copy installed dependencies from builder
COPY --from=builder /root/.local /root/.local

# Copy application code
COPY . .

# Expose API port
EXPOSE 8000

# Command to run the application
CMD ["uvicorn", "main_api:app", "--host", "0.0.0.0", "--port", "8000"]
