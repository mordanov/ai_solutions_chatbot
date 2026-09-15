# Tasks: LangGraph Pipeline Orchestration

**Input**: Design documents from `specs/004-langgraph-orchestration/`  
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅, quickstart.md ✅

**Context**: The LangGraph pipeline (stages 1–4) is fully implemented. This feature closes the remaining Stage 4 gaps: complete test coverage for all 9 workflow nodes and 3 routing functions, an end-to-end pipeline integration test, a CI fix for spaCy, and README evaluation results.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)

---

## Phase 1: Setup (CI Fix)

**Purpose**: Unblock CI so all unit tests — including guard-rails tests that require a spaCy model — pass on every PR.

**⚠️ CRITICAL**: This must be done before pushing any new tests, or CI will fail on spaCy import errors.

- [x] T001 Add `python -m spacy download en_core_web_lg` step to `.github/workflows/ci.yml` after the `pip install` step in the `test` job

**Checkpoint**: `ruff check .` and `pytest tests/unit/ -v` both pass in CI.

---

## Phase 2: Foundational (Graph Routing Tests)

**Purpose**: Create `test_workflow_graph.py` covering all three conditional routing functions in `src/chatbot/workflow/graph.py`. These tests are blocking prerequisites — they verify the graph wiring before any node-level stories are exercised end-to-end.

**⚠️ CRITICAL**: No pipeline integration test is meaningful until the routing logic is verified.

- [x] T002 Create `tests/unit/test_workflow_graph.py` and implement 4 tests for `_route_after_intent`: `info_query` → `retrieve_and_generate`; `reservation` → `reservation_collector_node`; `pricing` → `dynamic_data_node`; unknown → `out_of_scope_node`
- [x] T003 Add 2 tests for `_route_after_reservation_validator` to `tests/unit/test_workflow_graph.py`: `reservation.status == "submitted"` → `approval_request_node`; `status == "draft"` → `respond`
- [x] T004 Add 2 tests for `_route_after_pending_check` to `tests/unit/test_workflow_graph.py`: `response_draft` set → `guard_rails_node`; `response_draft` is `None` → `route_intent`

**Checkpoint**: `pytest tests/unit/test_workflow_graph.py -v` passes (8 tests).

---

## Phase 3: User Story 1 — End-to-End Reservation Conversation (Priority: P1) 🎯 MVP

**Goal**: All nodes involved in the conversational flow (RAG Q&A, dynamic data, out-of-scope, reservation collection) are fully unit-tested, verifying that each node correctly reads and writes `ConversationState`.

**Independent Test**: `pytest tests/unit/test_workflow_nodes.py -v` passes with coverage for `retrieve_and_generate`, `dynamic_data_node`, `out_of_scope_node`, and `reservation_collector_node`.

- [x] T005 [P] [US1] Add 2 tests for `retrieve_and_generate` to `tests/unit/test_workflow_nodes.py`: (1) mock LLM + retriever → `response_draft` populated with RAG answer; (2) retriever raises exception → `response_draft` set to fallback message and `error` set
- [x] T006 [P] [US1] Add 2 tests for `dynamic_data_node` to `tests/unit/test_workflow_nodes.py`: (1) `intent="pricing"` with mocked repo returning rate objects → `response_draft` contains price info; (2) `intent="hours"` → `response_draft` contains hours info
- [x] T007 [P] [US1] Add 2 tests for `out_of_scope_node` to `tests/unit/test_workflow_nodes.py`: (1) any state → `response_draft` contains "parking" (polite refusal); (2) verify node does not mutate `messages` or `reservation`
- [x] T008 [P] [US1] Add 2 tests for `reservation_collector_node` to `tests/unit/test_workflow_nodes.py`: (1) LLM returns valid JSON with all fields → `reservation` fields updated; (2) no `HumanMessage` in state → node returns unchanged state without error

**Checkpoint**: `pytest tests/unit/test_workflow_nodes.py -v` passes (8 existing + 8 new = 16 tests for the expanded file).

---

## Phase 4: User Story 2 — Administrator Approves and Records (Priority: P2)

**Goal**: All nodes involved in the approval path are unit-tested (`approval_request_node`, `guard_rails_node`, `pending_check_node` approved/expired cases), and the full approval pipeline integration test passes: POST `/chat` → admin approves → `write_record` called → user gets `✅` notification.

**Independent Test**: `pytest tests/unit/test_workflow_nodes.py tests/unit/test_pipeline_integration.py -v` passes; `write_record` mock is called exactly once on the approval path.

- [x] T009 [P] [US2] Add 2 tests for `approval_request_node` to `tests/unit/test_workflow_nodes.py`: (1) mock `ApprovalService.create_request` → `approval_request_id` set, `reservation.status == "pending_approval"`, `response_draft` contains "administrator"; (2) `ApprovalService` raises → `error` set and `response_draft` contains failure message
- [x] T010 [P] [US2] Add 2 tests for `guard_rails_node` to `tests/unit/test_workflow_nodes.py`: (1) response draft containing PII with `approval_request_id` set → `response_final` equals `response_draft` (PII scan bypassed for approval messages); (2) response draft containing a blocked keyword without `approval_request_id` → `response_final` set to privacy-refusal message
- [x] T011 [P] [US2] Add 2 tests for `pending_check_node` to `tests/unit/test_workflow_nodes.py`: (1) pending request with `decision="approved"` in store → `response_draft` contains "✅" and `reservation.status == "approved"`; (2) expired request → `reservation.status == "expired"` and `response_draft` contains "timed out"
- [x] T012 [US2] Create `tests/unit/test_pipeline_integration.py` and implement `test_full_approval_pipeline`: use `httpx.AsyncClient(app=app)` + mock `_get_llm` to return deterministic reservation extraction JSON + mock `ReservationStorageClient.write_record` → POST `/chat` (full reservation message) → POST `/admin/reservation/{id}/approve` → POST `/chat` (same session) → assert response contains "approved" and `write_record` called once with correct name and car_number

**Checkpoint**: `pytest tests/unit/test_pipeline_integration.py::test_full_approval_pipeline -v` passes.

---

## Phase 5: User Story 3 — Administrator Rejects (Priority: P3)

**Goal**: Rejection path verified: `pending_check_node` correctly handles `decision="rejected"`, and the pipeline integration test confirms `write_record` is never called on rejection.

**Independent Test**: `pytest tests/unit/test_workflow_nodes.py::test_pending_check_node_rejection tests/unit/test_pipeline_integration.py::test_full_rejection_pipeline -v` passes; `write_record` mock is called zero times.

- [x] T013 [US3] Add 1 test for `pending_check_node` rejection case to `tests/unit/test_workflow_nodes.py`: pending request with `decision="rejected"` and optional reason → `reservation.status == "rejected"`, `response_draft` contains "❌" or "not approved"
- [x] T014 [US3] Add `test_full_rejection_pipeline` to `tests/unit/test_pipeline_integration.py`: same setup as T012 but POST `/admin/reservation/{id}/reject` with `{"reason": "No spaces"}` → POST `/chat` same session → assert response contains "rejected" or "not approved" and `write_record` is NOT called

**Checkpoint**: `pytest tests/unit/test_pipeline_integration.py -v` passes (2 tests: approval + rejection).

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Complete remaining node coverage, populate evaluation results, and validate the full suite.

- [x] T015 [P] Add 2 tests for `respond` node to `tests/unit/test_workflow_nodes.py`: (1) `response_final` set → appended as `AIMessage` in `messages`; (2) both `response_final` and `response_draft` are `None` → fallback message appended and `messages` grows by 1
- [x] T016 Run `python scripts/evaluate.py` against the seeded knowledge base and replace the "To be populated" placeholder in `README.md` Evaluation Results section with actual Recall@5, Precision@5, and average latency values
- [x] T017 Run `pytest tests/unit/ -v` and confirm all tests pass; fix any failures before marking this phase complete

**Checkpoint**: `pytest tests/unit/ -v` — all ~93 tests pass. `README.md` Evaluation Results section contains real numbers.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (CI fix)**: No dependencies — start immediately
- **Phase 2 (Foundational)**: Depends on Phase 1 — BLOCKS integration tests
- **Phase 3 (US1)**: Depends on Phase 2 — T005–T008 can run in parallel
- **Phase 4 (US2)**: Depends on Phase 3 — T009–T011 can run in parallel; T012 depends on T009–T011
- **Phase 5 (US3)**: Depends on T012 (pipeline test file exists) — T013 parallel with T014
- **Phase 6 (Polish)**: Depends on all phases — T015 parallel with T016; T017 last

### User Story Dependencies

- **US1 (P1)**: Can start after Foundational (Phase 2) — no other story dependencies
- **US2 (P2)**: Depends on US1 completion (node test file is being expanded incrementally)
- **US3 (P3)**: Depends on T012 from US2 (pipeline test file must exist before adding the rejection test to it)

### Parallel Opportunities

Within Phase 3: T005, T006, T007, T008 all write different test functions to the same file — execute sequentially to avoid edit conflicts, or in parallel if using separate branches and merging.

Within Phase 4: T009, T010, T011 write to `test_workflow_nodes.py` (same file as Phase 3); T012 creates a new file — T012 can run in parallel with T009–T011.

---

## Implementation Strategy

### MVP First (User Story 1 only)

1. Complete Phase 1 (CI fix)
2. Complete Phase 2 (graph routing tests)
3. Complete Phase 3 (US1 node tests)
4. **STOP and VALIDATE**: `pytest tests/unit/ -v` all pass
5. Push — CI is green

### Full Delivery (all stories)

1. Phase 1 → Phase 2 → Phase 3 → Phase 4 → Phase 5 → Phase 6
2. Each phase adds independently verifiable test coverage
3. Final push delivers ~93 passing unit tests + CI fix + README evaluation results

---

## Notes

- [P] tasks within a phase touch different test functions but the same file; execute sequentially unless using parallel branches
- The `test_pipeline_integration.py` mock strategy: patch `chatbot.workflow.nodes._get_llm` to return a mock that yields deterministic reservation JSON, and patch `chatbot.storage.client.ReservationStorageClient.write_record` as an async no-op
- `respond` node and `out_of_scope_node` tests (T007, T015) require no mocking — they are pure state transformations
- After T016, commit `README.md` separately so evaluation results are traceable in git history
