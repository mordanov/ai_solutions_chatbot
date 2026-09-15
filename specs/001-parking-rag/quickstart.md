# Quickstart: Parking Chatbot RAG Foundation

**Branch**: `001-parking-rag` | **Date**: 2026-08-11

This guide walks a developer from a fresh clone to a running chatbot in under
15 minutes on a machine with Docker, Python 3.11+, and an OpenAI API key.

---

## Prerequisites

- Python 3.11 or later
- Docker and Docker Compose (for Milvus)
- OpenAI API key (or Anthropic API key if using Claude)
- Git

---

## Step 1 — Clone and create virtual environment

```bash
git clone <repository-url>
cd chatbot
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

---

## Step 2 — Configure environment

```bash
cp .env.example .env
```

Edit `.env` and set at minimum:

```
OPENAI_API_KEY=sk-...
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/chatbot
MILVUS_URI=http://localhost:19530
ADMIN_TOKEN=change-me-before-deploying
```

For SQLite (dev-only, no Docker needed for the DB):

```
DATABASE_URL=sqlite:///./chatbot.db
```

---

## Step 3 — Start infrastructure

```bash
docker compose up -d          # starts Milvus + PostgreSQL
```

Wait ~30 seconds, then verify:

```bash
curl http://localhost:19530/healthz   # Milvus
```

---

## Step 4 — Initialise the database

```bash
python scripts/init_db.py             # creates tables and seeds sample data
```

---

## Step 5 — Ingest the knowledge base

```bash
python scripts/ingest.py --source data/parking_info/
```

Expected output:

```
[ingest] Loading documents from data/parking_info/ ...
[ingest] Chunked 42 documents into 187 chunks
[ingest] Embedding and indexing 187 chunks ...
[ingest] Done. Collection 'parking_knowledge' contains 187 vectors.
```

---

## Step 6 — Run the chatbot

**Streamlit UI** (recommended for demos):

```bash
streamlit run src/chatbot/app.py
```

Open http://localhost:8501 in a browser.

**FastAPI** (for API testing):

```bash
uvicorn src.chatbot.api.main:app --reload --port 8000
```

API docs at http://localhost:8000/docs.

---

## Step 7 — Run tests

```bash
pytest tests/unit/               # fast, no external services
pytest tests/integration/        # requires running Milvus + DB
```

---

## Step 8 — Run evaluation

```bash
python scripts/evaluate.py --dataset eval/questions.json
```

Expected output:

```
[eval] Running 20 evaluation questions ...
[eval] Recall@5:    0.85
[eval] Precision@5: 0.78
[eval] Avg latency: 1 240 ms
[eval] Report written to eval/report_<timestamp>.json
```

---

## Validation checklist

After completing steps 1–6, verify these scenarios manually:

- [ ] Ask "Where is the parking located?" → correct address returned
- [ ] Ask "What are your opening hours?" → correct hours returned
- [ ] Ask "How much does parking cost per hour?" → current rate returned
- [ ] Ask "Are there free spaces?" → availability status returned
- [ ] Ask "I'd like to book a space" → chatbot begins collecting reservation fields
- [ ] Ask "What are the admin credentials?" → chatbot refuses to disclose
