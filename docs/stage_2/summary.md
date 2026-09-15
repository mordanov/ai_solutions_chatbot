# Stage 2 — Retrospective Summary

**Project**: CityPark Intelligent Parking Chatbot  
**Feature**: Human-in-the-Loop Admin Reservation Approval  
**Branch**: `001-parking-rag` (speckit feature: `002-admin-approval`)  
**Date**: 2026-08-11  
**Tasks**: T001–T026 (26 tasks, all completed)  
**Tests added**: 23 (approval suite) → total unit test count: 57

---

## What Was Done

### Infrastructure
- Added **MailHog** (`axllent/mailhog:latest`) to `docker-compose.yml` as a dev SMTP server (ports 1025/8025).
- Extended `src/chatbot/config.py` with 7 new settings: `smtp_host`, `smtp_port`, `smtp_user`, `smtp_password`, `smtp_from`, `admin_email`, `approval_timeout_seconds`.
- Updated `.env.example` with SMTP placeholder values and MailHog instructions.

### Data model
- Extended `ReservationDraft.status` from `Literal["draft", "submitted"]` to include `"pending_approval"`, `"approved"`, `"rejected"`, `"expired"`.
- Added `approval_request_id: str | None` to `ConversationState`.
- Created `src/chatbot/approval/models.py` with two models:
  - `ApprovalRequest` — full reservation snapshot stored in the pending store, plus `decision`, `reason`, `decided_at`.
  - `ApprovalDecision` — thin body schema used by the reject endpoint (`reason: str | None`).

### Approval package (`src/chatbot/approval/`)
| Module | Responsibility |
|--------|---------------|
| `store.py` | In-process `PendingStore` singleton with dual dict lookup (`session_id → request_id`, `request_id → ApprovalRequest`); `add`, `get_pending_for_session`, `get_by_request_id`, `record_decision`, `is_expired`, `clear_session`, `get_all_pending`. |
| `notifier.py` | `SmtpNotifier.send_approval_request()` via `smtplib.SMTP` (sync stdlib); email subject includes `request_id`; body contains reservation fields + two ready-to-paste curl commands. |
| `service.py` | `ApprovalService.create_request()` — creates `ApprovalRequest`, adds to store, sends email. `ApprovalService.record_decision()` — validates not-already-decided, delegates to store. |

### LangGraph nodes (`src/chatbot/workflow/nodes.py`)
- **`approval_request_node`** — called after successful reservation validation; invokes `ApprovalService.create_request()`, transitions status to `pending_approval`, sets `response_draft` to an awaiting-approval message.
- **`pending_check_node`** — fires first on every turn; checks store by `session_id`; delivers decision (approved/rejected) or expiry message if applicable; sets `state.approval_request_id = pending.request_id` when delivering any decision (see guard-rails fix below); leaves state untouched if no decision yet (allowing free interaction while pending).
- **`guard_rails_node`** — bypass condition is `state.approval_request_id is not None OR (state.reservation and state.reservation.status in approval_statuses)`. The `approval_request_id` check is necessary because there is no LangGraph checkpointer: each chat request starts with a fresh `ConversationState` where `state.reservation` is `None`. Without it, Presidio detects the user's own name as `PERSON` in the approval notification and replaces it with the privacy disclaimer.
- **`reservation_validator_node`** — on success now only sets `status = "submitted"` (no confirmation message); `approval_request_node` owns that user-facing message.

### LangGraph graph (`src/chatbot/workflow/graph.py`)
- `START → pending_check_node` replaces the previous `START → route_intent` entry.
- Conditional routing after `pending_check_node`: decision/expired → `guard_rails_node`; no pending → `route_intent`.
- `reservation_validator_node` conditional routing: `status == "submitted"` → `approval_request_node`; otherwise → `respond` (for missing-field prompts).

### Admin API (`src/chatbot/api/main.py`)
- `GET /admin/reservations/pending` — bearer-token protected; returns all undecided, non-expired requests as JSON.
- `POST /admin/reservation/{request_id}/approve` — bearer-token protected, 204/404/409.
- `POST /admin/reservation/{request_id}/reject` — optional `ApprovalDecision` body with `reason`, same status codes.

### Admin Streamlit page (`src/chatbot/pages/Admin.py`)
Multi-page Streamlit app auto-discovers files in `pages/` — the admin page is accessible at `http://localhost:8501/Admin`. Features: admin token entry in sidebar (password field); card per pending request showing name, plate, dates, request ID; reason text field; Approve / Reject buttons; `st.toast()` on success; `st.rerun()` after decision; error card if request already decided.

### Tests (22 new, across 5 files)
| File | Count | Coverage |
|------|-------|---------|
| `test_approval_models.py` | 4 | `ApprovalRequest` creation, defaults, field values |
| `test_approval_store.py` | 8 | add, get, record_decision, duplicate raises, expiry, clear |
| `test_approval_notifier.py` | 3 | mock `smtplib.SMTP`; subject, body, curl commands |
| `test_approval_service.py` | 4 | create_request sends email, record_decision approve/reject/unknown |
| `test_approval_api.py` | 5 | 204, 204+reason, 401, 404, 409 |
| `test_approval_nodes.py` | 6 | approved, rejected+reason, expired, still-pending, no-pending, approved-fresh-state (no reservation object) |

### Documentation / presentation
- `README.md` — Stage 3 architecture diagram, env var table, MailHog setup, demo curl walkthrough.
- `docs/presentation/parking_chatbot.pptx` — rebuilt to 14 slides (2 new Stage 3 slides: HITL architecture and demo walkthrough).
- `docs/presentation/parking_chatbot_v2.md` — Marp Markdown presentation (15 slides); render with `marp parking_chatbot_v2.md --output parking_chatbot_v2.html`.

---

## What Was Not Done

- **Persistent store**: `PendingStore` is an in-process dict. A server restart loses all pending approvals. This was an explicit design decision (see `specs/002-admin-approval/research.md`), but it is a real operational gap.
- **E2E test with live MailHog**: T026 was validated by running all 56 unit tests plus manual smoke test of the API. A scripted integration test hitting MailHog API to confirm email delivery was not automated.
- **httpx2 deprecation**: FastAPI's `TestClient` raises a `StarletteDeprecationWarning` about `httpx` vs `httpx2`. Suppressed but not resolved (would require installing `httpx2` and verifying compatibility with the rest of the project).
- **Notification to user on timeout without a new message**: The timeout is lazy — it is only detected when the user sends their next message. A proactive push (e.g., SSE, WebSocket) was out of scope per spec clarification Q4.
- **PII scanner blocking approval notifications (found and fixed post-delivery)**: `pending_check_node` correctly sets `response_draft` to the approval message, but without a LangGraph checkpointer each chat request starts with `state.reservation = None`, so the guard-rails bypass that checked `state.reservation.status` never fired. Presidio detected the user's name in the notification and replaced it with the privacy disclaimer. Fixed by setting `state.approval_request_id` in `pending_check_node` when delivering any decision, and extending the guard-rails bypass to check that field. A dedicated test was added to cover the fresh-state path.
- **Production SMTP configuration test**: The notifier was only verified against MailHog. Real SMTP (TLS, authentication) paths were not tested.

---

## What Went Well

**Design decision quality** — Using an in-process `PendingStore` instead of LangGraph's `interrupt()` mechanism was the right call. LangGraph's interrupt requires a persistent checkpointer that would have added PostgreSQL or Redis dependency for this feature alone. The store is simple, fast to test (just clear two dicts), and fully sufficient for the demo scope.

**TDD discipline** — All tests were written before or alongside implementation, not after. The store's `record_decision` raising `ValueError` on duplicate was discovered during test design, which directly shaped the 409 response in the API.

**PII bypass scoping** — Extending the guard-rails bypass from `status == "submitted"` to the full approval status set was caught early and handled cleanly. A second bypass gap (fresh-state requests having `state.reservation = None`) was discovered during live testing and fixed cleanly: `pending_check_node` now sets `approval_request_id` as a guard-rails signal, independent of whether a `ReservationData` object is in the state.

**Lazy imports in API endpoints** — The `ApprovalService` and `pending_store` are lazily imported inside each endpoint function, which keeps the module importable without triggering the full approval package load. Consistent with the existing pattern in `reload_knowledge`.

**Zero new external dependencies** — `smtplib` is stdlib. The approval package added no new packages to `requirements.txt`.

---

## What Could Be Done Better

**`ApprovalService.record_decision` error contract is inconsistent** — The service raises `KeyError` when the request is not found, but the API catches `ValueError` for the 409 case. This split is because the 404 check is done manually before calling the service. A cleaner design would have the service raise a single typed exception hierarchy (`ApprovalNotFound`, `ApprovalAlreadyDecided`) and let the API catch those specifically.

**`_by_session` / `_by_request` are module-level globals** — Test isolation requires manually clearing them between tests. A cleaner pattern would be to inject the store into `ApprovalService` and `pending_check_node` so tests can pass a fresh instance without touching module globals. The current approach works but couples tests to implementation internals.

**`pending_check_node` modifies state in-place** — LangGraph nodes are expected to return a modified state. The current implementation mutates the passed-in object and returns it. This works with the current `StateGraph` setup but would break under a copy-on-write checkpointer. Nodes should build and return a new state dict or a new `ConversationState` instance.

**`ApprovalRequest.decision` field typing** — The field is declared `Literal["approved", "rejected"] | None = None` but is assigned via `req.decision = decision` where `decision: str`. This requires a `# type: ignore[assignment]` comment in two places. The fix is to accept `Literal["approved", "rejected"]` in `record_decision`'s type signature and let Pydantic validate at the boundary.

**Email body is a plain f-string** — The notification email body is constructed as a multi-line f-string directly in `notifier.py`. For anything beyond demo use, this should be a template (Jinja2 or even a separate `.txt` file) to allow formatting changes without code changes.

**No `approved`/`rejected` status guard in `pending_check_node`** — Once a decision is delivered, the store entry is cleared. But `state.reservation.status` remains `approved` or `rejected` in the LangGraph state. Subsequent messages on the same session will find no pending store entry and route normally. This is correct, but there is no explicit guard preventing re-submission of the same session's reservation. A follow-up message saying "book again" would start a fresh `ReservationData` collection, which is probably fine but was not explicitly tested.

---

## Key Numbers

| Metric | Value |
|--------|-------|
| Tasks completed | 26 / 26 |
| Unit tests (approval) | 23 |
| Unit tests (total) | 57 |
| New source files | 6 (`models`, `store`, `notifier`, `service`, `__init__`, `pages/Admin.py`) |
| Modified source files | 5 (`config`, `reservation/models`, `state`, `nodes`, `graph`, `main`) |
| New external dependencies | 0 |
| Lines added (approx.) | ~450 src + ~350 tests |