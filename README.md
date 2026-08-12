# CityPark Chatbot

An intelligent parking reservation chatbot built with LangChain, LangGraph, and a
Milvus vector database. Stages 1–4 delivered.

## Architecture

```
User → Streamlit UI → FastAPI → LangGraph Workflow
                                    ├── Pending Check Node        ← Stage 3
                                    ├── Intent Router
                                    ├── RAG Pipeline (Milvus + OpenAI)
                                    ├── Dynamic Data Node (PostgreSQL)
                                    ├── Reservation Collector
                                    ├── Approval Request Node     ← Stage 3
                                    ├── Guard Rails (Presidio + rules)
                                    └── Respond

Admin SMTP Email ←──────────────────┘
Admin curl approve/reject ──────────→ POST /admin/reservation/{id}/approve|reject
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
| `ADMIN_TOKEN` | Bearer token for admin endpoints |
| `SMTP_HOST` | SMTP server host (MailHog: `localhost`) |
| `SMTP_PORT` | SMTP server port (MailHog: `1025`) |
| `ADMIN_EMAIL` | Email address that receives approval requests |
| `APPROVAL_TIMEOUT_SECONDS` | Seconds before a pending request expires (default: `300`) |
| `RESERVATIONS_FILE_PATH` | Path to the approved reservations audit log (default: `data/reservations.txt`) |

## Running

### 1 — Start infrastructure (includes MailHog for dev SMTP)

```bash
docker compose up -d
# MailHog web UI available at http://localhost:8025
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
├── approval/          — Stage 3: ApprovalRequest model, PendingStore, SmtpNotifier, ApprovalService
├── storage/           — Stage 4: MCP server + ReservationWriter (approved record audit log)
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

## Stage 3: Human-in-the-Loop Admin Approval

When a user submits a complete reservation, the chatbot:

1. Sends an email to `ADMIN_EMAIL` via SMTP containing full reservation details and two curl commands to approve or reject.
2. Transitions the reservation status to `pending_approval` and informs the user.
3. On every subsequent user message, `pending_check_node` checks for an admin decision. When one arrives the user is notified immediately; if the timeout elapses the request is marked `expired`.

### Demo walkthrough

```bash
# 1 — Submit a reservation via the chat UI (or API):
curl -s -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"session_id":"demo","message":"Book a space for Alice Smith, plate ABC123, 15 Aug 10am to 16 Aug 10am"}'

# 2 — Check MailHog for the approval email: http://localhost:8025
#     Copy the REQUEST_ID from the email subject line.

# 3 — Approve (replace <REQUEST_ID> and <ADMIN_TOKEN>):
curl -s -X POST http://localhost:8000/admin/reservation/<REQUEST_ID>/approve \
  -H "Authorization: Bearer <ADMIN_TOKEN>"

# 4 — Send any message in the same session — the bot reports the approval.

# 5 — To reject instead (optional reason in body):
curl -s -X POST http://localhost:8000/admin/reservation/<REQUEST_ID>/reject \
  -H "Authorization: Bearer <ADMIN_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"reason": "No available spaces on those dates"}'
```

For the full walkthrough including timeout testing, see `specs/002-admin-approval/quickstart.md`.

## Stage 4: MCP Reservation Storage

When an administrator approves a reservation via `POST /admin/reservation/{id}/approve`, the system automatically records the approval to a persistent text file using an embedded **MCP (Model Context Protocol) server** subprocess.

### Storage format

Each approved record is appended as one pipe-delimited line:

```
Alice Smith | ABC123 | 2026-08-15 10:00 → 2026-08-16 10:00 | 2026-08-12 14:30
```

Fields: `Name | Car Number | Reservation Period | Approval Time (UTC)`

### Storage file location

Configurable via `RESERVATIONS_FILE_PATH` (default: `data/reservations.txt`). The file is created on the first approval if it does not exist. This file is excluded from version control.

### Architecture

The `chatbot.storage` package contains three modules:

- **`writer.py`** — `ReservationWriter`: appends one record with `fcntl.LOCK_EX` for concurrent-write safety
- **`server.py`** — MCP server: exposes `write_reservation_record` tool; run as a subprocess (`python -m chatbot.storage.server`)
- **`client.py`** — `ReservationStorageClient`: spawns the server via stdio transport, calls the tool, raises `RuntimeError` on failure

Storage write failures are logged but do not roll back the approval decision — the user still receives their chat notification.

## Evaluation

```bash
python scripts/evaluate.py
```

Prints Recall@5, Precision@5, and average latency to stdout.
Writes a full JSON report to `eval/report_<timestamp>.json`.

## Evaluation Results

*To be populated after a live run against the seeded knowledge base.*
