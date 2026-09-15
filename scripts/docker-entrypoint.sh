#!/bin/sh
set -e

echo "==> Initialising database..."
python scripts/init_db.py --seed

echo "==> Ingesting knowledge base into Milvus..."
python scripts/ingest.py || echo "Warning: ingestion failed (data dir missing?). RAG will not work until ingest.py is run manually."

echo "==> Starting API..."
exec uvicorn chatbot.api.main:app --host 0.0.0.0 --port 8000
