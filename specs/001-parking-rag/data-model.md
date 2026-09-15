# Data Model: Parking Chatbot RAG Foundation

**Branch**: `001-parking-rag` | **Date**: 2026-08-11

---

## Overview

Data splits into two stores aligned with the constitution's separation mandate:

| Store | Purpose | Technology |
|-------|---------|------------|
| Vector store | Semantic search over static parking facts | Milvus |
| Relational DB | Structured operational data (prices, hours, availability, reservations) | PostgreSQL / SQLite |

---

## Vector Store — Static Knowledge

### Collection: `parking_knowledge`

Stores chunked, embedded representations of static parking documents.

| Field | Type | Notes |
|-------|------|-------|
| `id` | string (UUID) | Primary key, auto-generated at ingestion |
| `content` | varchar | Raw text of the chunk (up to ~2 000 chars) |
| `embedding` | float vector (1536) | OpenAI `text-embedding-3-small` |
| `source` | varchar | Source document filename or URL |
| `section` | varchar | Logical section label (e.g. `location`, `pricing`, `rules`) |
| `chunk_index` | int | Position of chunk within source document |
| `created_at` | datetime | Ingestion timestamp |

**Retrieval**: cosine similarity, top-k = 5, optional `section` metadata filter.

**Re-indexing**: full collection drop-and-reload triggered by `scripts/ingest.py`.

---

## Relational Schema

### Table: `parking_rate`

Stores current and historical pricing.

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | integer | PK, auto-increment |
| `rate_type` | varchar(32) | NOT NULL — `hourly`, `daily`, `monthly`, `overnight` |
| `amount` | numeric(10,2) | NOT NULL |
| `currency` | char(3) | NOT NULL, default `EUR` |
| `valid_from` | timestamp | NOT NULL |
| `valid_until` | timestamp | nullable — NULL means currently active |
| `description` | text | nullable |

**Business rules**:
- At most one active rate per `rate_type` (valid_until IS NULL).
- `amount` ≥ 0.

---

### Table: `parking_hours`

Operating hours per day of week.

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | integer | PK, auto-increment |
| `day_of_week` | smallint | NOT NULL, 0 = Monday … 6 = Sunday |
| `open_time` | time | nullable — NULL when `is_closed = true` |
| `close_time` | time | nullable — NULL when `is_closed = true` |
| `is_closed` | boolean | NOT NULL, default false |

**Business rules**:
- One row per `day_of_week` (unique constraint).
- `open_time` < `close_time` when `is_closed = false`.

---

### Table: `parking_availability`

Near-real-time snapshot of space counts. Single-row table (upsert pattern).

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | integer | PK, value always 1 |
| `total_spaces` | integer | NOT NULL, > 0 |
| `available_spaces` | integer | NOT NULL, ≥ 0 |
| `reserved_spaces` | integer | NOT NULL, ≥ 0 |
| `updated_at` | timestamp | NOT NULL, auto-updated |

**Business rules**:
- `available_spaces` + `reserved_spaces` ≤ `total_spaces`.

---

### Table: `reservation_draft`

Collects reservation data during the chatbot dialogue. One row per session.

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | uuid | PK |
| `session_id` | varchar(128) | NOT NULL, UNIQUE |
| `first_name` | varchar(100) | nullable |
| `surname` | varchar(100) | nullable |
| `license_plate` | varchar(20) | nullable |
| `start_datetime` | timestamp | nullable |
| `end_datetime` | timestamp | nullable |
| `status` | varchar(16) | NOT NULL, default `draft` |
| `created_at` | timestamp | NOT NULL |
| `updated_at` | timestamp | NOT NULL |

**Status values**: `draft` → `submitted` → `confirmed` / `rejected`

**Business rules**:
- `start_datetime` < `end_datetime`.
- `license_plate` matches pattern `[A-Z0-9]{2,10}` (configurable).
- `first_name` and `surname` must be non-empty strings after stripping whitespace.
- Transition to `submitted` requires all five fields non-null and valid.

---

### Table: `evaluation_record`

Stores offline RAG evaluation runs.

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | uuid | PK |
| `question` | text | NOT NULL |
| `expected_answer` | text | NOT NULL |
| `relevant_chunk_ids` | jsonb | NOT NULL — list of expected chunk IDs |
| `retrieved_chunk_ids` | jsonb | NOT NULL — list of retrieved chunk IDs |
| `generated_response` | text | nullable |
| `recall_at_k` | float | nullable |
| `precision_at_k` | float | nullable |
| `latency_ms` | integer | nullable |
| `model_version` | varchar(64) | nullable |
| `evaluated_at` | timestamp | NOT NULL |

---

## LangGraph Workflow State

The `ConversationState` Pydantic model passed between graph nodes:

```
ConversationState
  session_id: str
  messages: list[BaseMessage]          # full conversation history
  intent: str | None                   # "info_query" | "reservation" | "out_of_scope"
  retrieved_chunks: list[Document]     # last retrieval result
  reservation: ReservationDraft | None # in-progress reservation fields
  response_draft: str | None           # pre-filter LLM output
  response_final: str | None           # post-filter output
  error: str | None                    # last error message if any
```

---

## State Transitions

```
IDLE ──► ROUTING ──► RETRIEVING ──► GENERATING ──► FILTERING ──► RESPONDING
                 └──► COLLECTING_RESERVATION ──► VALIDATING ──► GENERATING ──► FILTERING ──► RESPONDING
                 └──► OUT_OF_SCOPE ──► RESPONDING
```

Any node may transition to `ERROR` on unrecoverable failure; `ERROR` transitions
to `RESPONDING` with a safe fallback message.
