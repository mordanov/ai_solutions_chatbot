# Research: Admin Reservation Approval

**Branch**: `002-admin-approval` | **Date**: 2026-08-11

## Decision 1 — SMTP Library

**Decision**: Use Python stdlib `smtplib` (synchronous) for sending emails from LangGraph nodes.

**Rationale**: LangGraph node functions are synchronous Python callables. Using `smtplib` avoids the complexity of running async code inside synchronous graph nodes. For the demo scope, SMTP calls complete in <1 s against MailHog running on the same Docker network, so sync blocking is acceptable.

**Alternatives considered**:
- `aiosmtplib` — async SMTP, would require `asyncio.run()` inside sync nodes (works but adds noise).
- `emails` / `yagmail` — higher-level wrappers that add a dependency for no benefit over stdlib at this scope.

## Decision 2 — Action Links in Admin Email

**Decision**: Email body contains pre-built curl commands showing the bearer token and endpoint URL. No clickable HTTP links with embedded tokens.

**Rationale**: Embedding the `admin_token` in a clickable `<a href="...?token=...">` URL would expose the token in browser history, server logs, and email headers. Curl commands show exactly what the admin needs to do and keep the token in a copy-paste context rather than a URL. For the MailHog web UI demo, the admin views the email in the browser and copies the curl command.

**Alternatives considered**:
- One-time signed URLs (UUID per request) — more UX-friendly but adds token issuance/validation complexity without spec requirement.
- HTTP action links with bearer token in the Authorization header — not possible to click from email.

## Decision 3 — In-Process Pending Store Design

**Decision**: Module-level dictionary `_store: dict[str, ApprovalRequest]` in `chatbot/approval/store.py`, keyed by `session_id`. A separate `_by_request: dict[str, str]` maps `request_id → session_id` to support the admin API lookup path.

**Rationale**: Simplest structure that supports both lookup paths: the chatbot (session_id → pending request) and the admin API (request_id → decision target). No external dependency; cleared on process restart which is acceptable per spec.

**Alternatives considered**:
- SQLite in-memory / PostgreSQL — durable but unnecessary for single-instance demo; adds schema migration complexity.
- Redis — cross-process but adds an infra dependency without a multi-instance requirement.

## Decision 4 — LangGraph HITL Mechanism

**Decision**: Use external pending_store state rather than LangGraph's native `interrupt()` mechanism. A `pending_check_node` at graph entry checks the store on every turn.

**Rationale**: LangGraph `interrupt()` pauses the graph mid-execution and requires the full graph state to be checkpointed to a persistent store (SQLite/Postgres) to resume after an external event. This would add a LangGraph checkpointer dependency and complicate the single-`compiled_graph` architecture. The polling approach keeps each graph invocation stateless while the pending state lives outside the graph — matching the spec's "free interaction" requirement where the user can continue chatting during the wait.

**Alternatives considered**:
- LangGraph `interrupt()` + SQLite checkpointer — correct HITL-native approach but overengineered for the single-instance demo scope; would also require changing the FastAPI `compiled_graph.invoke()` call to a streaming/resumable pattern.

## Decision 5 — Timeout Handling

**Decision**: Lazy timeout evaluated by `pending_check_node` on the next user message. `ApprovalRequest` stores `created_at` timestamp; `store.is_expired(request_id)` compares `now - created_at > settings.approval_timeout_seconds`.

**Rationale**: Simplest correct approach for the single-instance demo. No background thread or scheduler needed. The user is informed of expiry the moment they next interact with the chatbot. Matches the spec wording "user is notified that their request could not be processed in time."

**Alternatives considered**:
- Background thread checking all pending requests and setting expired status proactively — correct but adds a thread and a wake mechanism for a demo feature; the user would need to poll anyway.

## Decision 6 — MailHog for Demo

**Decision**: Add `mailhog` (mailhog/mailhog:v1.0.1) to docker-compose as a new service on ports 1025 (SMTP) and 8025 (web UI). API service connects via `SMTP_HOST=mailhog`, `SMTP_PORT=1025`.

**Rationale**: MailHog is a well-known zero-configuration SMTP mock for dev/demo. It captures all outgoing emails and exposes them in a web UI at `http://localhost:8025`, making the email visible during the presentation without a real mail server. No authentication required.

**Alternatives considered**:
- `fakesmtp` / `mailpit` — equivalent alternatives; MailHog is more widely documented and available on Docker Hub.
- Real SMTP (Gmail, SendGrid) — requires credentials, not suitable for a self-contained demo.
