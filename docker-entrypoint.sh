#!/bin/bash
set -e

# Wait for ChromaDB if CHROMA_HOST is set
if [ -n "$CHROMA_HOST" ]; then
    echo "Waiting for ChromaDB at $CHROMA_HOST:$CHROMA_PORT..."
    while ! nc -z $CHROMA_HOST $CHROMA_PORT; do
      sleep 1
    done
    echo "ChromaDB is up!"
fi

# Run ingestion if vector_db is empty or requested via env
if [ "$RUN_INGESTION" = "true" ] || [ ! -d "/app/vector_db" ]; then
    echo "Running data ingestion..."
    python ingestion/ingest_data.py
fi

# Start the application
echo "Starting DevOps Log Analyzer API..."
exec uvicorn main_api:app --host 0.0.0.0 --port 8000
