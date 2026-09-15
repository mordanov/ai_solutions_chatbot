# Data Model: Admin Reservation Approval

**Branch**: `002-admin-approval` | **Date**: 2026-08-11

## Overview

This feature adds one new module (`chatbot.approval`) with two Pydantic models. It extends two existing models: `ReservationDraft` and `ConversationState`. All approval state is held in-process (no new database tables).

---

## New Models

### `ApprovalRequest` (`chatbot.approval.models`)

Represents a pending reservation request awaiting admin review.

| Field | Type | Required | Description |
|---|---|---|---|
| `request_id` | `str` (UUID4) | Yes | Unique request identifier, generated at creation |
| `session_id` | `str` | Yes | Chat session ID; used to look up the pending request on subsequent turns |
| `first_name` | `str` | Yes | Copied from `ReservationDraft` at submission time |
| `surname` | `str` | Yes | Copied from `ReservationDraft` at submission time |
| `license_plate` | `str` | Yes | Copied from `ReservationDraft` at submission time |
| `start_datetime` | `str` | Yes | Copied from `ReservationDraft` at submission time |
| `end_datetime` | `str` | Yes | Copied from `ReservationDraft` at submission time |
| `created_at` | `datetime` | Yes | UTC timestamp of when the request was created |
| `decision` | `Literal["approved", "rejected"] \| None` | No | Admin's decision; `None` while pending |
| `reason` | `str \| None` | No | Optional rejection reason supplied by admin |
| `decided_at` | `datetime \| None` | No | UTC timestamp of when the decision was recorded |

**Identity**: `request_id` is globally unique (UUID4).  
**Lifecycle**: `decision is None` → pending; `decision = "approved"` → approved; `decision = "rejected"` → rejected.  
**Expiry**: Determined externally by `store.is_expired(request_id)` based on `created_at + timeout`.

---

### `ApprovalDecision` (`chatbot.approval.models`)

The payload accepted by the admin approve/reject API endpoints.

| Field | Type | Required | Description |
|---|---|---|---|
| `reason` | `str \| None` | No | Optional free-text reason (used for rejection; ignored for approval) |

---

## Extended Models

### `ReservationDraft` (`chatbot.reservation.models`) — extended

The `status` field is extended from `Literal["draft", "submitted"]` to:

```python
Literal["draft", "submitted", "pending_approval", "approved", "rejected", "expired"]
```

| Status | Meaning |
|---|---|
| `draft` | Fields being collected; incomplete |
| `submitted` | All fields validated; transient — immediately transitions to `pending_approval` |
| `pending_approval` | Email sent to admin; awaiting decision |
| `approved` | Admin confirmed the reservation |
| `rejected` | Admin declined the reservation |
| `expired` | No admin decision within the timeout window |

---

### `ConversationState` (`chatbot.workflow.state`) — extended

One new field added:

| Field | Type | Description |
|---|---|---|
| `approval_request_id` | `str \| None` | ID of the `ApprovalRequest` created for this session's reservation; `None` until email is sent |

---

## In-Process Store (`chatbot.approval.store`)

Not a database model — a module-level dictionary with two lookup indexes:

```python
_by_session: dict[str, str]      # session_id  → request_id
_by_request: dict[str, ApprovalRequest]  # request_id → ApprovalRequest
```

**Operations**:
- `add(request: ApprovalRequest) → None`
- `get_pending_for_session(session_id: str) → ApprovalRequest | None`
- `get_by_request_id(request_id: str) → ApprovalRequest | None`
- `record_decision(request_id: str, decision: str, reason: str | None) → ApprovalRequest`
- `is_expired(request_id: str) → bool`
- `clear_session(session_id: str) → None`

**Constraints**:
- One pending request per session at a time (adding a new one while one exists replaces the old).
- All data lost on process restart (in-scope per spec).
