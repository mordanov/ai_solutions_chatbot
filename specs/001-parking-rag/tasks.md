# Tasks: Parking Chatbot RAG Foundation

**Input**: Design documents from `specs/001-parking-rag/`
**Prerequisites**: plan.md ✅ spec.md ✅ research.md ✅ data-model.md ✅ contracts/ ✅

**Tests**: Test tasks are included (constitution requires ≥ 2 tests per module).

**Organization**: Tasks are grouped by user story to enable independent
implementation and testing of each story.

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1–US4)
- File paths are relative to the repository root

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project skeleton and toolchain; no external services required.

- [ ] T001 Create directory tree: `src/chatbot/` with subdirectories `api/`, `workflow/`, `rag/`, `knowledge/`, `data/`, `reservation/`, `guard_rails/`, `evaluation/`; `tests/unit/`, `tests/integration/`; `data/parking_info/`; `eval/`; `scripts/`; add `__init__.py` to every Python package
- [ ] T002 Create `pyproject.toml` with project metadata, Python 3.11 requirement, and dev-tool config sections for ruff (lint/format) and mypy
- [ ] T003 [P] Create `requirements.txt` listing all runtime dependencies from plan.md Technical Context (`langchain`, `langchain-openai`, `langchain-community`, `langgraph`, `pymilvus`, `sqlalchemy`, `psycopg2-binary`, `fastapi`, `uvicorn`, `streamlit`, `presidio-analyzer`, `presidio-anonymizer`, `pydantic`, `python-dotenv`) with pinned major versions
- [ ] T004 [P] Create `.env.example` documenting all required environment variables: `OPENAI_API_KEY`, `DATABASE_URL`, `MILVUS_URI`, `ADMIN_TOKEN`, `LOG_LEVEL`, `EMBEDDING_MODEL`, `LLM_MODEL`, `RETRIEVAL_TOP_K`
- [ ] T005 Create `docker-compose.yml` with Milvus Standalone service (port 19530) and PostgreSQL service (port 5432) with named volumes and health checks
- [ ] T006 [P] Create sample knowledge-base documents in `data/parking_info/`: `general.md` (facility overview), `location.md` (address, map directions), `rules.md` (parking rules and policies), `booking_process.md` (how to book a space)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared infrastructure all user stories depend on.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [ ] T007 Create `src/chatbot/config.py` with `Settings` class (Pydantic `BaseSettings`) loading all variables from `.env.example`; export a module-level `settings` singleton
- [ ] T008 [P] Create `src/chatbot/data/models.py` with SQLAlchemy ORM declarative models for all five tables: `ParkingRate`, `ParkingHours`, `ParkingAvailability`, `ReservationDraft`, `EvaluationRecord` — field types and constraints per `data-model.md`
- [ ] T009 Create `src/chatbot/data/repository.py` with `ParkingRepository` class providing methods: `get_active_rates()`, `get_hours_for_day(day: int)`, `get_availability()`, `upsert_reservation_draft(draft)`, `get_reservation_draft(session_id: str)`
- [ ] T010 [P] Create `src/chatbot/knowledge/vector_store.py` defining `VectorStorePort` protocol (methods: `add_documents`, `similarity_search`, `delete_collection`) and `MilvusVectorStore` implementation using `pymilvus`
- [ ] T011 Create `src/chatbot/workflow/state.py` with `ConversationState` TypedDict (fields: `session_id`, `messages`, `intent`, `retrieved_chunks`, `reservation`, `response_draft`, `response_final`, `error`) and `Intent` string enum
- [ ] T012 [P] Create `src/chatbot/data/seed.py` with `seed_database(engine)` function inserting sample `ParkingRate` rows (hourly/daily), seven `ParkingHours` rows (Mon–Sun), and one `ParkingAvailability` row
- [ ] T013 Create `scripts/init_db.py` CLI that creates all tables via SQLAlchemy and calls `seed_database()` — idempotent (use `CREATE TABLE IF NOT EXISTS` semantics)

**Checkpoint**: Foundation ready — all user stories can begin.

---

## Phase 3: User Story 1 — Ask a Parking Question (Priority: P1) 🎯 MVP

**Goal**: User asks a natural-language parking question and receives a grounded,
factually accurate answer retrieved from the vector knowledge base.

**Independent Test**: Ingest `data/parking_info/`, run the chatbot, ask "Where is
the parking located?" — verify the response matches `data/parking_info/location.md`
without fabricated details.

### Tests for User Story 1

> **Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T014 [P] [US1] Create `tests/unit/test_rag_pipeline.py` with ≥2 unit tests: (1) RAG chain returns response grounded in provided context chunks; (2) RAG chain returns "insufficient information" fallback when no chunks retrieved — mock LLM and vector store
- [ ] T015 [P] [US1] Create `tests/unit/test_retriever.py` with ≥2 unit tests: (1) retriever returns top-k documents ranked by similarity; (2) retriever handles empty result set without error — mock `MilvusVectorStore`

### Implementation for User Story 1

- [ ] T016 [P] [US1] Create `src/chatbot/rag/ingestion.py` with `ingest_documents(source_dir: Path, vector_store: VectorStorePort)` using LangChain `DirectoryLoader` and `RecursiveCharacterTextSplitter` (chunk_size=512, overlap=50)
- [ ] T017 [P] [US1] Create `src/chatbot/rag/retriever.py` with `ParkingRetriever` wrapping `VectorStorePort.similarity_search(query, k=settings.RETRIEVAL_TOP_K)`
- [ ] T018 [US1] Create `src/chatbot/rag/pipeline.py` with LangChain `RetrievalQA`-style chain: retrieve chunks → format context → call LLM via `ChatOpenAI` → return grounded response; include fallback when no chunks retrieved
- [ ] T019 [US1] Create `src/chatbot/workflow/nodes.py` with three initial nodes: `route_intent(state)` (classifies message as `info_query | reservation | out_of_scope`), `retrieve_and_generate(state)` (calls RAG pipeline), `respond(state)` (formats final response)
- [ ] T020 [US1] Create `src/chatbot/workflow/graph.py` with `StateGraph(ConversationState)` wiring: START → `route_intent` → conditional edge → `retrieve_and_generate` → `respond` → END (info_query path only; stubs for other intents)
- [ ] T021 [US1] Create `src/chatbot/api/main.py` with FastAPI app: `POST /chat` (validates request, invokes `graph.invoke()`, returns response + intent + latency), `GET /health` (checks Milvus and DB connectivity)
- [ ] T022 [US1] Create `src/chatbot/app.py` Streamlit app: UUID4 session_id in session state; message thread display; POST /chat call with spinner; error banner on failure
- [ ] T023 [P] [US1] Create `scripts/ingest.py` CLI: load all `.md` files from `data/parking_info/`, ingest via `ingest_documents()`, print chunk count summary

**Checkpoint**: User Story 1 is fully functional — ingest docs, ask parking questions,
get grounded answers via `streamlit run src/chatbot/app.py`.

---

## Phase 4: User Story 2 — Ask About Prices or Availability (Priority: P2)

**Goal**: User asks about current prices, opening hours, or space availability and
receives an accurate answer sourced from the operational database.

**Independent Test**: Seed the database with known values, ask "How much does parking
cost per hour?" and "Are there free spaces?" — verify responses match seeded data.

### Tests for User Story 2

- [ ] T024 [P] [US2] Create `tests/unit/test_database_repository.py` with ≥2 unit tests: (1) `get_active_rates()` returns only rates where `valid_until IS NULL`; (2) `get_availability()` returns the singleton availability row — mock SQLAlchemy session

### Implementation for User Story 2

- [ ] T025 [US2] Add `dynamic_data_node(state)` to `src/chatbot/workflow/nodes.py`: calls `ParkingRepository` methods appropriate to detected intent (pricing → `get_active_rates()`, hours → `get_hours_for_day()`, availability → `get_availability()`), formats result into a context string, then calls LLM to compose the answer
- [ ] T026 [US2] Update `src/chatbot/workflow/graph.py` to add conditional routing from `route_intent` to `dynamic_data_node` for `pricing`, `hours`, and `availability` intents (refine intent classification in `route_intent` to distinguish these from static `info_query`)

**Checkpoint**: Prices, hours, and availability questions answered from live DB data.

---

## Phase 5: User Story 4 — Guard Rails Block Sensitive Data (Priority: P2)

**Goal**: Responses containing PII, credentials, or injected private records are
intercepted and replaced with a safe refusal before reaching the user.

**Independent Test**: Submit the boundary-probing prompts from `quickstart.md`
validation checklist — verify all are refused and no legitimate query is blocked.

### Tests for User Story 4

- [ ] T027 [P] [US4] Create `tests/unit/test_guard_rails.py` with ≥2 unit tests: (1) `PiiScanner.scan()` flags a response containing a licence plate number; (2) `RuleBlocklist.check()` blocks a response containing a JWT-shaped token pattern; (3) a benign parking answer passes through unmodified

### Implementation for User Story 4

- [ ] T028 [P] [US4] Create `src/chatbot/guard_rails/rules.py` with `RuleBlocklist` class containing regex patterns for: API key shapes (`sk-[A-Za-z0-9]{32,}`), JWT tokens (`eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+`), prompt-injection probes (`ignore previous instructions`, `reveal system prompt`)
- [ ] T029 [US4] Create `src/chatbot/guard_rails/scanner.py` with `PiiScanner` class using Presidio `AnalyzerEngine` to detect `PERSON`, `LOCATION`, `PHONE_NUMBER`, `EMAIL_ADDRESS`, and custom `LICENSE_PLATE` recogniser; expose `scan(text: str) -> list[str]` returning detected entity types
- [ ] T030 [US4] Add `guard_rails_node(state)` to `src/chatbot/workflow/nodes.py`: runs `RuleBlocklist.check()` then `PiiScanner.scan()` on `state.response_draft`; if violations found, sets `state.response_final` to a generic refusal message; otherwise passes through `response_draft` unchanged
- [ ] T031 [US4] Update `src/chatbot/workflow/graph.py` to insert `guard_rails_node` between every generation node and `respond` (applies to info_query, dynamic_data, and reservation paths)

**Checkpoint**: All sensitive-data boundary tests pass; false-positive rate < 5% on
legitimate parking queries.

---

## Phase 6: User Story 3 — Start a Reservation Request (Priority: P3)

**Goal**: User says they want to reserve a space; chatbot collects first name,
surname, licence plate, start and end datetime one by one, validates each field, and
confirms the completed draft.

**Independent Test**: Walk through a full reservation dialogue with valid inputs —
verify all five fields collected, draft stored in DB with status `submitted`.
Then test invalid licence plate mid-flow — verify re-prompt without losing prior data.

### Tests for User Story 3

- [ ] T032 [P] [US3] Create `tests/unit/test_reservation_validator.py` with ≥2 unit tests: (1) validator accepts valid licence plate `AB1234` and rejects `!@#`; (2) validator rejects `end_datetime` ≤ `start_datetime`; (3) validator accumulates valid fields and returns only missing-field errors on partial draft
- [ ] T033 [P] [US3] Create `tests/unit/test_workflow_nodes.py` with ≥2 unit tests: (1) `reservation_collector_node` with a complete draft transitions to `submitted` status; (2) `reservation_collector_node` with missing `licence_plate` sets error and stays in `collecting` state — mock `ParkingRepository`

### Implementation for User Story 3

- [ ] T034 [P] [US3] Create `src/chatbot/reservation/models.py` with `ReservationDraft` Pydantic model (all five fields nullable, `status: Literal["draft","submitted"]`); `ReservationField` enum listing the five fields
- [ ] T035 [US3] Create `src/chatbot/reservation/validator.py` with `validate_reservation(draft: ReservationDraft) -> list[str]` returning list of error messages (empty = fully valid); include: non-empty name/surname, `LICENSE_PLATE_PATTERN` regex check, `start < end` datetime check
- [ ] T036 [US3] Add `reservation_collector_node(state)` and `reservation_validator_node(state)` to `src/chatbot/workflow/nodes.py`: collector uses LLM to extract any newly provided fields from the latest message and merges into `state.reservation`; validator calls `validate_reservation()` and either prompts for the next missing/invalid field or marks draft `submitted`
- [ ] T037 [US3] Update `src/chatbot/workflow/graph.py` to add reservation sub-graph path: `route_intent` → `reservation_collector_node` → `reservation_validator_node` → conditional → (prompt for next field | `guard_rails_node` → `respond`)

**Checkpoint**: All five reservation fields collected, validated, and saved to DB.

---

## Phase N: Polish & Cross-Cutting Concerns

**Purpose**: Evaluation, integration tests, hardening, and documentation.

- [ ] T038 [P] Create `eval/questions.json` with ≥20 entries, each: `{question, expected_answer, relevant_chunk_ids: []}` — cover all four user-story question types
- [ ] T039 [P] Create `src/chatbot/evaluation/metrics.py` with `recall_at_k(retrieved_ids, relevant_ids, k) -> float` and `precision_at_k(retrieved_ids, relevant_ids, k) -> float` pure functions
- [ ] T040 Create `src/chatbot/evaluation/runner.py` with `run_evaluation(dataset_path, pipeline) -> EvaluationReport` that runs each question through the RAG retriever, computes Recall@5 and Precision@5, records latency per question, and returns aggregate results
- [ ] T041 Create `scripts/evaluate.py` CLI that calls `run_evaluation()` and writes results to `eval/report_<timestamp>.json`; prints Recall@5, Precision@5, and avg latency to stdout
- [ ] T042 [P] Create `tests/unit/test_evaluation_metrics.py` with ≥2 unit tests: (1) `recall_at_k` returns 1.0 when all relevant IDs are in retrieved set; (2) `precision_at_k` returns 0.0 when no retrieved IDs are relevant
- [ ] T043 [P] Create `tests/integration/test_vector_store.py` with ≥2 integration tests: (1) `MilvusVectorStore.add_documents()` then `similarity_search()` returns expected top result; (2) `delete_collection()` removes all documents — requires running Milvus
- [ ] T044 [P] Create `tests/integration/test_chat_api.py` with ≥2 integration tests: (1) `POST /chat` with a valid parking question returns 200 with non-empty `response`; (2) `GET /health` returns 200 with `status: ok` — requires running stack
- [ ] T045 [P] Add error handling and safe fallback responses to all nodes in `src/chatbot/workflow/nodes.py`: catch exceptions, log them, set `state.error`, route to `respond` with a user-friendly fallback message
- [ ] T046 [P] Add structured logging to all modules using Python `logging`; log at DEBUG for retrieval details, INFO for request/response lifecycle, ERROR for exceptions; configure log format in `src/chatbot/config.py`
- [ ] T047 Create `README.md` documenting: project purpose, architecture overview, tech stack, prerequisites, installation, environment variables, how to run (Streamlit + FastAPI), how to run tests, project structure, RAG setup, evaluation results placeholder

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Setup — **BLOCKS all user stories**
- **US1 (Phase 3)**: Depends on Foundational — no dependency on US2/US3/US4
- **US2 (Phase 4)**: Depends on Foundational — no dependency on US1/US3/US4
- **US4 (Phase 5)**: Depends on Foundational + US1 (guard_rails wired into graph from US1)
- **US3 (Phase 6)**: Depends on Foundational + US1 (reservation path added to graph)
- **Polish (Phase N)**: Depends on all user stories complete

### User Story Dependencies

- **US1 (P1)**: Starts after Foundational — no story dependencies
- **US2 (P2)**: Starts after Foundational — independent of US1 but shares `nodes.py`
- **US4 (P2)**: Starts after US1 (requires the graph structure US1 establishes)
- **US3 (P3)**: Starts after US1 (requires the graph structure US1 establishes)

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Models before validators before nodes before graph wiring
- Core implementation before integration
- Story complete before moving to next priority

### Parallel Opportunities

- All `[P]`-marked tasks within a phase run in parallel
- US1 and US2 can be developed in parallel after Foundational completes
- US4 and US3 can be developed in parallel after US1 completes

---

## Parallel Example: User Story 1

```bash
# Parallel test scaffolding (write first, should fail):
Task: "T014 — tests/unit/test_rag_pipeline.py"
Task: "T015 — tests/unit/test_retriever.py"

# Parallel implementation (after tests written):
Task: "T016 — src/chatbot/rag/ingestion.py"
Task: "T017 — src/chatbot/rag/retriever.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1 + Phase 2
2. Complete Phase 3 (US1)
3. **STOP and VALIDATE**: ask parking questions via `streamlit run src/chatbot/app.py`
4. Deploy/demo if ready

### Incremental Delivery

1. Setup + Foundational → foundation ready
2. US1 → grounded Q&A working → demo MVP
3. US2 → dynamic data integrated → demo prices/availability
4. US4 → guard rails active → demo security
5. US3 → reservation collection → demo full flow
6. Polish → evaluation report, full test suite, README

---

## Notes

- `[P]` tasks have no file conflicts and no incomplete dependencies
- `[US?]` maps each task to a specific user story for traceability
- Each user story is independently completable and testable
- Tests MUST fail before implementation begins (TDD)
- Commit after each phase checkpoint
- Stop at any checkpoint to validate story independently
