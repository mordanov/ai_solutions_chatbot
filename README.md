# CityPark Chatbot

An intelligent parking reservation chatbot built with LangChain, LangGraph, and a
Milvus vector database. Stage 1 of a 4-stage delivery.

## Architecture

```
User → Streamlit UI → FastAPI → LangGraph Workflow
                                    ├── Intent Router
                                    ├── RAG Pipeline (Milvus + OpenAI)
                                    ├── Dynamic Data Node (PostgreSQL)
                                    ├── Reservation Collector
                                    ├── Guard Rails (Presidio + rules)
                                    └── Respond
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.11+ |
| LLM | OpenAI GPT-4o |
| Embeddings | text-embedding-3-small |
| Vector DB | Milvus (Docker) |
| Relational DB | PostgreSQL / SQLite |
| Workflow | LangGraph StateGraph |
| API | FastAPI |
| UI | Streamlit |
| Guard Rails | Presidio + regex rules |

## Prerequisites

- Python 3.11+
- Docker + Docker Compose
- OpenAI API key

## Installation

```bash
# Clone the repo
git clone <repo-url>
cd chatbot

# Create a virtual environment
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements-dev.txt

# Configure environment
cp .env.example .env
# Edit .env and set OPENAI_API_KEY and other values
```

## Environment Variables

See `.env.example` for the complete list. Required:

| Variable | Description |
|----------|-------------|
| `OPENAI_API_KEY` | OpenAI API key |
| `DATABASE_URL` | SQLAlchemy URL (default: SQLite) |
| `MILVUS_URI` | Milvus server URI |
| `ADMIN_TOKEN` | Bearer token for `/admin/reload-knowledge` |

## Running

### 1 — Start infrastructure

```bash
docker compose up -d
```

### 2 — Initialise the database

```bash
python scripts/init_db.py --seed
```

### 3 — Ingest parking knowledge

```bash
python scripts/ingest.py
```

### 4 — Start the API

```bash
uvicorn chatbot.api.main:app --reload
```

### 5 — Start the Streamlit UI

```bash
streamlit run src/chatbot/app.py
```

Open <http://localhost:8501> in your browser.

## Running Tests

```bash
# Unit tests only (no external services required)
pytest tests/unit/ -v

# All tests including integration (requires Docker Compose stack)
pytest -v
```

## Project Structure

```
src/chatbot/
├── config.py          — Pydantic Settings (env vars)
├── app.py             — Streamlit UI
├── api/main.py        — FastAPI routes
├── workflow/          — LangGraph state, graph, nodes
├── rag/               — Ingestion, retriever, pipeline
├── knowledge/         — Milvus abstraction (VectorStorePort)
├── data/              — SQLAlchemy models, repository, seed
├── reservation/       — ReservationDraft model + validator
├── guard_rails/       — Presidio PII scanner + rule blocklist
└── evaluation/        — Recall@5 / Precision@5 metrics + runner
```

## RAG Setup

The knowledge base is built from Markdown files in `data/parking_info/`.
To re-index after editing those files, run:

```bash
python scripts/ingest.py
```

Or call the admin endpoint:

```bash
curl -X POST http://localhost:8000/admin/reload-knowledge \
     -H "Authorization: Bearer $ADMIN_TOKEN"
```

## Evaluation

```bash
python scripts/evaluate.py
```

Prints Recall@5, Precision@5, and average latency to stdout.
Writes a full JSON report to `eval/report_<timestamp>.json`.

## Evaluation Results

*To be populated after a live run against the seeded knowledge base.*
