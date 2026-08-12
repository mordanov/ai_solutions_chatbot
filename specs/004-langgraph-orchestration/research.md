# Research: LangGraph Pipeline Orchestration

**Feature**: 004-langgraph-orchestration  
**Date**: 2026-08-12

---

## Finding 1: Pipeline implementation status

**Decision**: The LangGraph pipeline is already fully implemented and integrated across features 001–003.

**Evidence**:
- `src/chatbot/workflow/graph.py` — `StateGraph` with 9 nodes wired and compiled.
- `src/chatbot/workflow/nodes.py` — All nodes implemented: `pending_check_node`, `route_intent`, `retrieve_and_generate`, `dynamic_data_node`, `out_of_scope_node`, `reservation_collector_node`, `reservation_validator_node`, `approval_request_node`, `guard_rails_node`, `respond`.
- `src/chatbot/api/main.py` — `POST /chat` invokes `compiled_graph`; `POST /admin/reservation/{id}/approve` calls `ReservationStorageClient` after recording the decision.

**Rationale**: Feature 004 is Stage 4 (Evaluation, Hardening, Delivery). The orchestration itself is done; what remains is test coverage completeness, integration testing of the full pipeline, and documentation hardening.

**Alternatives considered**: Re-implementing the graph with a different topology was considered and rejected — the existing implementation satisfies all constitution requirements.

---

## Finding 2: Test coverage gaps

**Decision**: Three coverage gaps need to close before Stage 4 is complete.

**Evidence**:

| Module | Tests exist | Gap |
|--------|-------------|-----|
| `workflow/nodes.py` — `route_intent`, `reservation_validator_node` | ✅ 4 tests | Only 2 of 9 nodes covered |
| `workflow/graph.py` — routing functions | ❌ None | `_route_after_intent`, `_route_after_reservation_validator`, `_route_after_pending_check` untested |
| Full pipeline (chat → approval → storage → notification) | ❌ None | No end-to-end integration test |

**Rationale**: Constitution Article XIII ("at least two automated tests per application module") requires coverage for `workflow/graph.py` and the remaining nodes. Article XV ("integration tests of all steps during orchestration") requires a pipeline-level test.

**Alternatives considered**: Load testing was listed as a requirement but is not achievable in unit/CI environments without a live stack. Load testing is documented as out-of-scope for automated CI and should be performed manually against a running deployment.

---

## Finding 3: Integration test strategy — mock all external services

**Decision**: Integration tests for the full pipeline mock the LLM (OpenAI), vector store (Milvus), database (SQLite in-memory), SMTP notifier, and MCP storage client. They test workflow routing and state transitions, not external service behavior.

**Rationale**: External service mocking is the standard approach endorsed in the constitution ("External LLM and vector-database dependencies SHOULD be mocked or replaced with test doubles in unit tests"). A "full-pipeline" integration test that requires Docker is valuable but belongs in a separate `integration/` suite not run on every PR. The new pipeline tests will live in `tests/unit/` and mock all I/O.

**Alternatives considered**: Using `pytest-docker` for a real stack was considered. Rejected because it requires Docker-in-CI setup that significantly complicates the CI job and is brittle. The existing `tests/integration/` suite covers real-stack scenarios.

---

## Finding 4: Documentation gaps

**Decision**: The README already covers most Article XI requirements. Two gaps remain:

1. **Evaluation results** — `README.md` contains a placeholder "To be populated after a live run." This should be replaced with actual Recall@5 / Precision@5 values from a `scripts/evaluate.py` run.
2. **Architecture diagram** — The current ASCII diagram is functional but could be expanded to show the MCP storage connection and the Stage 4 audit log path.

**Rationale**: The README covers: project purpose, architecture, stack, prerequisites, installation, env vars, running, tests, project structure, RAG setup, reservation workflow, HITL workflow, evaluation methodology, and known limitations. It is substantially complete.

**Alternatives considered**: Creating a separate `docs/architecture.md` was considered. The README is the standard single entry point; architecture content belongs there.

---

## Finding 5: CI pipeline gap

**Decision**: The existing CI (`.github/workflows/ci.yml`) runs lint + unit tests. It does not download the spaCy model required by Presidio, meaning `test_guard_rails.py` may fail in CI if spaCy is not pre-installed. The CI job should add a spaCy model download step.

**Rationale**: The CI job currently sets `OPENAI_API_KEY=sk-test-placeholder` which is sufficient for mocked tests. The spaCy `en_core_web_lg` model must be explicitly downloaded for Presidio to function.

**Alternatives considered**: Mocking Presidio was considered but rejected — the guard rails tests should test the real scanner against deterministic inputs.
