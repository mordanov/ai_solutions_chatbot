# Stage 1 — Retrospective Summary

**Project**: CityPark Intelligent Parking Chatbot
**Branch**: `001-parking-rag`
**Date**: 2026-08-11

---

## What Was Done

### Infrastructure & Configuration
- Full `src/chatbot/` package tree with 8 sub-packages (`api`, `workflow`, `rag`, `knowledge`, `data`, `reservation`, `guard_rails`, `evaluation`)
- Pydantic `Settings` class loading all config from `.env` with sane defaults
- `docker-compose.yml` for Milvus Standalone (+ etcd + minio) and PostgreSQL, all with health checks
- `.env.example` with every required variable documented
- `pyproject.toml` with ruff, mypy, and pytest configuration

### RAG Pipeline (US1 — Static Q&A)
- LangChain `DirectoryLoader` + `RecursiveCharacterTextSplitter` (512-token chunks, 50-token overlap)
- OpenAI `text-embedding-3-small` embeddings, Milvus cosine similarity, top-k = 5
- `VectorStorePort` ABC with `MilvusVectorStore` implementation (lazy pymilvus imports)
- `build_rag_chain` producing grounded answers with an explicit fallback when no context is retrieved
- `scripts/ingest.py` CLI for full re-indexing
- 4 knowledge-base documents covering location, general info, rules, booking process

### Dynamic Data (US2 — Prices / Hours / Availability)
- SQLAlchemy ORM models for all 5 tables (`ParkingRate`, `ParkingHours`, `ParkingAvailability`, `ReservationDraft`, `EvaluationRecord`) with check constraints and unique constraints
- `ParkingRepository` with typed query methods
- Seed data (4 rate types, 7-day hours schedule, availability snapshot)
- `scripts/init_db.py` CLI — idempotent table creation + optional seeding
- `dynamic_data_node` in the LangGraph workflow routing pricing / hours / availability intents to the DB

### Guard Rails (US4 — Safety)
- `RuleBlocklist` with regex patterns for API keys, JWT tokens, and prompt-injection probes
- `PiiScanner` wrapping Presidio `AnalyzerEngine` with a custom licence-plate regex; gracefully degrades if Presidio is unavailable
- `guard_rails_node` inserted after every generation node in the graph

### Reservation Collection (US3 — Booking)
- `ReservationDraft` Pydantic model + `ReservationField` enum
- `validate_reservation` with field-presence, licence-plate pattern, and start < end checks
- `reservation_collector_node` using LLM structured extraction to merge new fields from each turn
- `reservation_validator_node` prompting for the next missing/invalid field or marking the draft `submitted`

### Workflow & API
- Full LangGraph `StateGraph` with 8 nodes, conditional intent routing, and guard-rails on every response path
- `ConversationState` Pydantic model compatible with LangGraph's `add_messages` reducer
- FastAPI: `POST /chat`, `GET /health`, `POST /admin/reload-knowledge` (Bearer auth)
- Streamlit UI with per-session UUID, threaded message display, spinner, error banner

### Evaluation
- `recall_at_k` and `precision_at_k` pure functions
- `EvaluationReport` dataclass with aggregate properties
- `run_evaluation` runner wiring retriever + chain over a JSON dataset
- 22-question eval dataset covering all four user-story categories
- `scripts/evaluate.py` CLI writing timestamped JSON reports

### Tests & CI
- 26 unit tests across 6 modules, all passing without external services
- Integration test stubs for Milvus and FastAPI (skipped in CI via `pytest.mark.integration`)
- GitHub Actions CI: ruff lint + unit tests on every push to `main` and every PR, Python 3.13
- `pythonpath = ["src"]` in `pyproject.toml` so pytest resolves the `src/` layout without `PYTHONPATH` tricks

---

## What Was Not Done

| Item | Reason |
|------|--------|
| T049 — PowerPoint presentation | Requires a live running stack for screenshots; content depends on actual evaluation results |
| `relevant_chunk_ids` in eval dataset | Chunk IDs are assigned at ingestion time (UUIDs); they are unknown until `ingest.py` has run, so the dataset ships with empty arrays |
| Alembic migrations | Deferred to a later stage; `Base.metadata.create_all` is sufficient for Stage 1 |
| Integration tests in CI | Would require Docker-in-Docker for Milvus; left as a local-run-only concern |
| ANTHROPIC_API_KEY / Anthropic LLM path | Config supports it via `LLM_MODEL` env var, but no Anthropic client is wired into the chain |
| Human-in-the-loop approval | Constitution marks this as Stage 3 scope |

---

## What Went Well

- **Separation of concerns held up.** The 8-package structure mapped cleanly to each feature area and made it straightforward to add nodes to the graph without touching unrelated code.
- **Lazy pymilvus imports.** Moving the `pymilvus` imports inside `MilvusVectorStore` methods meant all 26 unit tests run without Milvus installed — a small change with a large CI impact.
- **Guard rails are additive.** Every generation path flows through `guard_rails_node` by construction; new generation nodes automatically get filtered without requiring a code change to the guard rails module.
- **`VectorStorePort` abstraction.** The ABC decouples retrieval tests from the real Milvus client; swapping to Pinecone or Weaviate later is a one-file change.
- **Pydantic Settings.** A single `settings` singleton handles all config; every module that needs a value imports it rather than reading `os.environ` directly.

---

## What Could Be Done Better

### Testing
- **No mocking of `OpenAIEmbeddings` in ingestion tests.** `test_rag_pipeline.py` patches the class but `ingest_documents` is not unit-tested at all; a real OpenAI call would be made if that function were called in a test.
- **`relevant_chunk_ids` are empty in the eval dataset.** Recall@5 and Precision@5 will always return 0 until someone runs ingestion, captures the real chunk IDs, and back-fills the dataset. This should be automated as part of `ingest.py`.
- **Integration tests have no CI path.** There is no GitHub Actions job that spins up the Docker Compose stack and runs `pytest -m integration`. A separate workflow job with `services:` blocks for Postgres and a Milvus container would close this gap.

### Architecture
- **`retrieve_and_generate` creates a new `MilvusVectorStore` per request.** Every chat call reconnects to Milvus. A module-level singleton (or dependency-injected instance) would be more efficient.
- **`dynamic_data_node` creates a new `ParkingRepository` (and engine) per request.** Same issue — SQLAlchemy engines are meant to be long-lived connection pools.
- **`reservation_collector_node` relies on LLM JSON extraction without a schema.** The prompt asks the model to return JSON but there is no function-calling / structured output guarantee. A `with_structured_output` call on the LLM would be more reliable.
- **`ConversationState` carries `retrieved_chunks` (LangChain `Document` objects).** These are not serialisable to standard JSON, which would break LangGraph checkpointing if persistence is added later. Storing chunk IDs + content as plain dicts would be safer.

### Operational
- **No request-level logging.** The API logs errors but not the incoming `session_id` / `intent` / latency per request at INFO level, which makes debugging a live deployment harder.
- **`ADMIN_TOKEN` defaults to `"change-me"`.** The config default should force an error if the token is not set in production, rather than silently accepting a well-known weak value.
- **`seed.py` uses `datetime.utcnow()`.** This is deprecated in Python 3.12+. Should be `datetime.now(UTC)`.
