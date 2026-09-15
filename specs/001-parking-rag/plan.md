# Implementation Plan: Parking Chatbot RAG Foundation

**Branch**: `001-parking-rag` | **Date**: 2026-08-11 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `specs/001-parking-rag/spec.md`

---

## Summary

Build the Stage 1 RAG foundation for an intelligent parking chatbot. The system
retrieves static parking facts from a Milvus vector store and dynamic operational
data (prices, hours, availability) from a PostgreSQL database. A LangGraph workflow
routes each message, runs retrieval, calls the LLM, and passes the response through
a two-layer guard-rail filter before returning it to the user. Reservation data
collection (all five required fields) is handled as a sub-workflow. Retrieval quality
is measured with Recall@5 and Precision@5 against a curated evaluation dataset.

---

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**:
`langchain`, `langchain-openai`, `langchain-community`, `langgraph`,
`pymilvus`, `sqlalchemy`, `psycopg2-binary`, `fastapi`, `uvicorn`,
`streamlit`, `presidio-analyzer`, `presidio-anonymizer`, `pydantic`, `pytest`

**Storage**: Milvus (vector, static knowledge) + PostgreSQL / SQLite (relational,
dynamic data and reservation drafts)

**Testing**: pytest — unit (mocked LLM/DB) + integration (real services)

**Target Platform**: Linux server (Docker Compose); macOS/Windows for local dev

**Project Type**: Conversational chatbot service (REST API + Streamlit UI)

**Performance Goals**: End-to-end p95 response latency < 5 s; ingestion > 100 chunks/min

**Constraints**: No secrets in source control; Milvus runs locally via Docker;
LLM provider switchable via config (OpenAI ↔ Anthropic)

**Scale/Scope**: Single parking facility; single-tenant; < 200 source documents;
20+ evaluation QA pairs

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| Python as primary language | ✅ | Python 3.11+ throughout |
| LangChain for LLM/RAG | ✅ | `langchain`, `langchain-openai`, `langchain-community` |
| LangGraph for stateful workflow | ✅ | Conversation + reservation sub-workflow |
| RAG architecture (8 stages) | ✅ | Ingest → chunk → embed → store → retrieve → context → generate → filter |
| Vector database (Milvus/Pinecone/Weaviate) | ✅ | Milvus — behind `VectorStorePort` abstraction |
| Human-in-the-loop | ⏭ | Stage 3 scope; reservation draft only in Stage 1 |
| Security / no secrets in git | ✅ | `.env.example` pattern; Presidio guard rails |
| Pytest, ≥ 2 tests per module | ✅ | Planned for all 8 business-logic packages |
| Stage 1 of 4-stage delivery | ✅ | Parking info RAG + basic reservation collection |
| Pydantic models for data exchange | ✅ | `ConversationState`, `ReservationDraft` |
| Separation of concerns | ✅ | 8 packages: api, workflow, rag, knowledge, data, reservation, guard_rails, evaluation |

**Post-Phase-1 re-check**: All gates pass. No violations requiring justification.

---

## Project Structure

### Documentation (this feature)

```text
specs/001-parking-rag/
├── plan.md              # This file (/speckit-plan command output)
├── spec.md              # Feature specification
├── research.md          # Phase 0 research decisions
├── data-model.md        # Phase 1 data model
├── quickstart.md        # Phase 1 developer quickstart
├── contracts/
│   └── chat-api.md      # REST API contract
├── checklists/
│   └── requirements.md  # Specification quality checklist
└── tasks.md             # Phase 2 output (/speckit-tasks - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
src/
└── chatbot/
    ├── __init__.py
    ├── config.py                    # Settings (Pydantic BaseSettings)
    ├── app.py                       # Streamlit entry point
    ├── api/
    │   ├── __init__.py
    │   └── main.py                  # FastAPI app + route handlers
    ├── workflow/
    │   ├── __init__.py
    │   ├── state.py                 # ConversationState Pydantic model
    │   ├── graph.py                 # LangGraph StateGraph definition
    │   └── nodes.py                 # Node functions (router, retriever, generator …)
    ├── rag/
    │   ├── __init__.py
    │   ├── ingestion.py             # Document loading + chunking
    │   ├── retriever.py             # Vector search wrapper
    │   └── pipeline.py              # RAG chain (retrieve → context → LLM)
    ├── knowledge/
    │   ├── __init__.py
    │   └── vector_store.py          # Milvus abstraction (VectorStorePort)
    ├── data/
    │   ├── __init__.py
    │   ├── models.py                # SQLAlchemy ORM models
    │   ├── repository.py            # DB access (rates, hours, availability)
    │   └── seed.py                  # Sample data for dev/test
    ├── reservation/
    │   ├── __init__.py
    │   ├── models.py                # ReservationDraft Pydantic model
    │   └── validator.py             # Field-level validation rules
    ├── guard_rails/
    │   ├── __init__.py
    │   ├── scanner.py               # Presidio PII scanner
    │   └── rules.py                 # Rule-based blocklist
    └── evaluation/
        ├── __init__.py
        ├── metrics.py               # Recall@K, Precision@K computation
        └── runner.py                # Evaluation orchestrator

tests/
├── conftest.py
├── unit/
│   ├── test_rag_pipeline.py
│   ├── test_retriever.py
│   ├── test_reservation_validator.py
│   ├── test_guard_rails.py
│   ├── test_workflow_nodes.py
│   └── test_evaluation_metrics.py
└── integration/
    ├── test_vector_store.py
    ├── test_database_repository.py
    └── test_chat_api.py

data/
└── parking_info/                    # Source documents for ingestion
    ├── general.md
    ├── location.md
    ├── rules.md
    └── booking_process.md

eval/
└── questions.json                   # Evaluation dataset (20+ QA pairs)

scripts/
├── ingest.py                        # CLI: load docs → Milvus
├── init_db.py                       # CLI: create tables + seed
└── evaluate.py                      # CLI: run RAG evaluation

docker-compose.yml
requirements.txt
pyproject.toml
.env.example
```

**Structure Decision**: Single Python project. `src/chatbot/` groups by responsibility —
one package per constitution separation-of-concerns item. Test directories mirror
source package boundaries.
