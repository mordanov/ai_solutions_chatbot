# Tasks: Admin Reservation Approval

**Input**: Design documents from `specs/002-admin-approval/`  
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅, quickstart.md ✅

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel (different files, no blocking dependencies)
- **[Story]**: Which user story this task belongs to (US1/US2/US3)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Docker service, config, and package skeleton — no business logic yet

- [X] T001 Add `mailhog` service (mailhog/mailhog:v1.0.1, ports 1025/8025) to docker-compose.yml
- [X] T002 [P] Add SMTP and approval settings to `src/chatbot/config.py`: smtp_host, smtp_port, smtp_user, smtp_password, smtp_from, admin_email, approval_timeout_seconds
- [X] T003 [P] Create `src/chatbot/approval/` package with empty `__init__.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Data models and store that ALL user story phases depend on

**⚠️ CRITICAL**: Phases 3–5 cannot begin until this phase is complete

- [X] T004 Extend `status` field in `src/chatbot/reservation/models.py` from `Literal["draft", "submitted"]` to `Literal["draft", "submitted", "pending_approval", "approved", "rejected", "expired"]`
- [X] T005 [P] Add `approval_request_id: str | None = None` field to `ConversationState` in `src/chatbot/workflow/state.py`
- [X] T006 [P] Create `ApprovalRequest` and `ApprovalDecision` Pydantic models in `src/chatbot/approval/models.py` per data-model.md
- [X] T007 Implement `PendingStore` class (add, get_pending_for_session, get_by_request_id, record_decision, is_expired, clear_session) with module-level singleton in `src/chatbot/approval/store.py`

**Checkpoint**: Data layer ready — all user story phases can now proceed in priority order

---

## Phase 3: User Story 1 — Reservation Escalated to Admin (Priority: P1) 🎯 MVP

**Goal**: When a user submits a complete reservation, the system creates an `ApprovalRequest`, sends an SMTP email to the admin with full details and curl commands to approve/reject, transitions reservation status to `pending_approval`, and informs the user their request is awaiting approval.

**Independent Test**: Submit a reservation with all valid fields → verify MailHog inbox (http://localhost:8025) receives an email with the reservation details and the correct request_id in the subject line → verify the chatbot replies with a "pending approval" message.

### Tests for User Story 1

- [X] T008 [P] [US1] Write ≥2 unit tests for `ApprovalRequest` model (creation, field defaults, expiry logic) in `tests/unit/test_approval_models.py`
- [X] T009 [P] [US1] Write ≥2 unit tests for `PendingStore` (add, get, record_decision, is_expired, clear) in `tests/unit/test_approval_store.py`
- [X] T010 [P] [US1] Write ≥2 unit tests for `SmtpNotifier` (mock smtplib.SMTP; verify subject, body contains request_id, first_name, approve/reject curl commands) in `tests/unit/test_approval_notifier.py`

### Implementation for User Story 1

- [X] T011 [US1] Implement `SmtpNotifier.send_approval_request(request: ApprovalRequest)` using `smtplib` (sync) in `src/chatbot/approval/notifier.py`; email subject format: `[Parking Reservation] New request from {first_name} {surname} — {request_id}`
- [X] T012 [US1] Implement `ApprovalService.create_request(session_id, reservation_data) -> ApprovalRequest` (creates UUID, adds to store, sends email via notifier) in `src/chatbot/approval/service.py`
- [X] T013 [US1] Add `approval_request_node()` to `src/chatbot/workflow/nodes.py`: calls `ApprovalService.create_request()`, sets `state.reservation.status = "pending_approval"`, sets `state.approval_request_id`, sets `state.response_draft` to awaiting-approval message
- [X] T014 [US1] Update `_route_after_reservation_validator()` in `src/chatbot/workflow/graph.py` to route `status == "submitted"` → `approval_request_node` (replacing the current `guard_rails_node` route)
- [X] T015 [US1] Update `guard_rails_node()` PII bypass in `src/chatbot/workflow/nodes.py` to skip scan when `state.reservation.status in {"pending_approval", "approved", "rejected", "expired"}` (replaces the `"submitted"` check)

**Checkpoint**: US1 fully functional — MailHog receives email, chatbot returns "pending" message

---

## Phase 4: User Story 2 — Admin Reviews and Decides (Priority: P2)

**Goal**: Admin calls `POST /admin/reservation/{request_id}/approve` or `POST /admin/reservation/{request_id}/reject` (bearer token required); the decision is recorded in the pending store.

**Independent Test**: Create an `ApprovalRequest` directly in the store → call approve endpoint with valid token → verify the request's `decision` field is set to `"approved"` and `decided_at` is populated → verify a duplicate approve call returns HTTP 409.

### Tests for User Story 2

- [X] T016 [P] [US2] Write ≥2 unit tests for `ApprovalService.record_decision()` (approve, reject with reason, duplicate call raises error) in `tests/unit/test_approval_service.py`
- [X] T017 [P] [US2] Write ≥2 unit tests for admin endpoints (valid token approve → 204; invalid token → 401; unknown request_id → 404; duplicate decision → 409) using FastAPI `TestClient` in `tests/unit/test_approval_api.py`

### Implementation for User Story 2

- [X] T018 [US2] Add `ApprovalService.record_decision(request_id, decision, reason) -> ApprovalRequest` in `src/chatbot/approval/service.py`; raises `ValueError` if already decided or expired
- [X] T019 [US2] Add `POST /admin/reservation/{request_id}/approve` and `POST /admin/reservation/{request_id}/reject` endpoints to `src/chatbot/api/main.py`; both require bearer token via `_require_admin`; return 204 on success, 404 if not found, 409 if already decided

**Checkpoint**: US2 fully functional — approve/reject endpoints work independently of chatbot

---

## Phase 5: User Story 3 — User Receives Decision (Priority: P2)

**Goal**: On each user message while a reservation is `pending_approval`, `pending_check_node` fires first. If a decision has arrived it delivers the outcome (approved/rejected) before normal processing. If the timeout has elapsed it marks the request expired and informs the user. If still pending, normal flow continues.

**Independent Test**: Insert an already-decided `ApprovalRequest` (approved) into the store → invoke the graph with a new user message on the same session → verify the bot's first response reports the approval → verify the store entry is cleared after delivery.

### Tests for User Story 3

- [X] T020 [P] [US3] Write ≥4 unit tests for `pending_check_node()` covering: approved decision delivered, rejected decision with reason, timeout expired, no pending request (normal flow) — in `tests/unit/test_approval_nodes.py`

### Implementation for User Story 3

- [X] T021 [US3] Implement `pending_check_node()` in `src/chatbot/workflow/nodes.py`: checks store by session_id → if decision arrived sets response_draft and clears store → if expired sets `status = "expired"` and clears store → if still pending returns state unchanged (routes to route_intent)
- [X] T022 [US3] Add `pending_check_node` as first node after `START` in `src/chatbot/workflow/graph.py` with conditional routing: decision/expired → `guard_rails_node`; no pending → `route_intent`

**Checkpoint**: Full end-to-end flow working — submit reservation → admin approves → user notified on next message

---

## Phase 6: Polish & Cross-Cutting Concerns

- [X] T023 [P] Update `.env.example` with SMTP variables (SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_FROM, ADMIN_EMAIL, APPROVAL_TIMEOUT_SECONDS) with safe placeholder values
- [X] T024 Update `README.md` with Stage 3 section: architecture of admin approval flow, new env vars, MailHog setup, quickstart demo steps, link to quickstart.md
- [X] T025 [P] Update `docs/presentation/parking_chatbot.pptx` via `scripts/build_presentation.py`: add Stage 3 slides covering HITL architecture, email notification flow, and approve/reject demo
- [X] T026 Run full end-to-end validation per `specs/002-admin-approval/quickstart.md`: submit reservation, check MailHog, approve via curl, verify user notification, test rejection and timeout paths

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately; T002 and T003 can run in parallel with T001
- **Foundational (Phase 2)**: Depends on T001–T003; T005 and T006 can run in parallel with T004
- **US1 (Phase 3)**: Depends on Phase 2 complete — T008, T009, T010 can run in parallel; T011→T012→T013→T014, T015 parallel with T014
- **US2 (Phase 4)**: Depends on T007 (store) and T006 (models) — can start as soon as Phase 2 completes; T016 and T017 can run in parallel; T018→T019
- **US3 (Phase 5)**: Depends on T007 (store), T013 (approval_request_node) — needs US1 complete; T020 can run in parallel with T021; T021→T022
- **Polish (Phase 6)**: T023 and T025 can run after US1 complete; T024 after all phases; T026 last

### User Story Dependencies

- **US1 (P1)**: Requires Foundational complete — no dependency on US2/US3
- **US2 (P2)**: Requires Foundational complete (store + models) — no dependency on US1/US3 (testable independently with seeded store)
- **US3 (P2)**: Requires US1 complete (pending_check_node reads results of approval_request_node flow)

### Parallel Opportunities

- T002, T003 parallel in Phase 1
- T005, T006 parallel with T004 in Phase 2
- T008, T009, T010 parallel in Phase 3
- T015 parallel with T014 in Phase 3
- T016, T017 parallel in Phase 4
- T018, T019 sequential in Phase 4 (same file)
- T020 parallel with T021 in Phase 5
- T023, T025 parallel in Phase 6

---

## Parallel Example: User Story 1

```bash
# Phase 3 tests (run in parallel, each in its own file):
Task: "Write tests for ApprovalRequest model in tests/unit/test_approval_models.py"   # T008
Task: "Write tests for PendingStore in tests/unit/test_approval_store.py"              # T009
Task: "Write tests for SmtpNotifier in tests/unit/test_approval_notifier.py"           # T010

# Phase 3 implementation (sequential chain):
T011 → T012 → T013 → T014
             T015 (parallel with T014, different area of nodes.py)
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001–T003)
2. Complete Phase 2: Foundational (T004–T007) — **BLOCKS all user stories**
3. Complete Phase 3: User Story 1 (T008–T015)
4. **STOP and VALIDATE**: Check MailHog receives email; chatbot returns "pending" message
5. Demo US1 independently before proceeding

### Incremental Delivery

1. Setup + Foundational → infrastructure ready
2. US1 → email notification working → demo MVP
3. US2 → admin can approve/reject via API → full HITL loop works
4. US3 → user receives in-session notification → Stage 3 complete
5. Polish → presentation, README, validation

---

## Notes

- `[P]` tasks write to different files and have no inter-task blocking dependency
- Tests mock `smtplib.SMTP` — no live MailHog required for unit tests
- Integration test (T026) requires the full docker-compose stack running
- The guard_rails bypass change in T015 replaces the existing `"submitted"` check — do not leave both conditions
- `pending_check_node` must be added as the very first node after START (before `route_intent`) in T022
- After T022 the `compiled_graph` module-level singleton in `graph.py` must be rebuilt — confirm import order is correct
