# Contract: Full-Pipeline Integration Test

**Feature**: 004-langgraph-orchestration  
**Date**: 2026-08-12

---

## Purpose

This contract defines the observable interface that integration tests must exercise to verify that all three pipeline stages are correctly connected end-to-end:

1. **Stage 1–2**: User sends a reservation request → chatbot collects all required fields
2. **Stage 3**: Chatbot submits to admin → admin approves or rejects
3. **Stage 4**: Approval triggers MCP storage write → user receives notification on next turn

---

## Test Scenario A: Full approval path

### Preconditions

- In-memory `PendingStore` (not backed by a database)
- LLM responses mocked to return deterministic intent/extraction results
- `SmtpNotifier` mocked (no real email)
- `ReservationStorageClient.write_record` mocked (no real MCP subprocess)

### Steps and expected outcomes

| Step | Action | Expected state after step |
|------|--------|--------------------------|
| 1 | POST `/chat` `{"session_id": "s1", "message": "I'd like to book parking for Alice Smith, plate AB1234, 10 Aug 10am to 11 Aug 10am"}` | HTTP 200; `intent == "reservation"`; `reservation.status == "submitted"` OR prompt for missing fields |
| 2 | POST `/admin/reservation/{id}/approve` with admin token | HTTP 204; `PendingStore.get_by_request_id(id).decision == "approved"`; `ReservationStorageClient.write_record` called once with correct args |
| 3 | POST `/chat` `{"session_id": "s1", "message": "Any update?"}` | HTTP 200; response contains approval confirmation; `reservation.status == "approved"` |

### Assertions

- `write_record` called with `name="Alice Smith"`, `car_number="AB1234"`, `reservation_period` containing `10 Aug` and `11 Aug`, `approval_time` non-empty.
- Response in step 3 includes "approved" (case-insensitive).

---

## Test Scenario B: Rejection path

### Steps

| Step | Action | Expected state after step |
|------|--------|--------------------------|
| 1 | Submit complete reservation (as above) | `reservation.status == "submitted"` or `pending_approval` |
| 2 | POST `/admin/reservation/{id}/reject` with `{"reason": "No spaces"}` | HTTP 204; `decision == "rejected"`; `write_record` NOT called |
| 3 | POST `/chat` same session | Response contains "rejected" or "not approved"; `reservation.status == "rejected"` |

### Assertions

- `write_record` is never called on rejection.
- Rejection reason echoed or rejection confirmed in user-facing response.

---

## Invariants (must hold for all scenarios)

- Storage write failure on approval does NOT return an error HTTP response; the endpoint returns 204.
- Missing or expired admin decision does NOT block user from continuing other conversations.
- Admin endpoints without a valid bearer token return 401.
