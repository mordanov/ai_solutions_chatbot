# Data Model: LangGraph Pipeline Orchestration

**Feature**: 004-langgraph-orchestration  
**Date**: 2026-08-12

---

## Core Entity: ConversationState

The single unit of data that flows through the LangGraph `StateGraph`. Every node receives a `ConversationState` and returns an updated one.

| Field | Type | Description |
|-------|------|-------------|
| `session_id` | `str` | Identifies the user's conversation session across turns |
| `messages` | `list[BaseMessage]` | Full conversation history; new messages appended via `add_messages` reducer |
| `intent` | `str \| None` | Classified user intent: `info_query`, `pricing`, `hours`, `availability`, `reservation`, `out_of_scope` |
| `retrieved_chunks` | `list[Document]` | RAG context chunks retrieved from Milvus |
| `reservation` | `ReservationData \| None` | Current reservation draft; `None` until user starts booking |
| `response_draft` | `str \| None` | Pre-guard-rails response text set by content nodes |
| `response_final` | `str \| None` | Post-guard-rails response text sent to the user |
| `error` | `str \| None` | Error message if a node failed; logged but does not halt the graph |
| `approval_request_id` | `str \| None` | UUID of the pending admin approval request; set after `approval_request_node` fires |

---

## Nested Entity: ReservationData

Lives inside `ConversationState.reservation`. Tracks the reservation as it is collected across turns.

| Field | Type | Valid values | Description |
|-------|------|--------------|-------------|
| `first_name` | `str \| None` | Non-empty string | User's first name |
| `surname` | `str \| None` | Non-empty string | User's surname |
| `license_plate` | `str \| None` | Non-empty string | Vehicle license plate |
| `start_datetime` | `str \| None` | ISO-like date/time string | Reservation start |
| `end_datetime` | `str \| None` | ISO-like date/time string | Reservation end |
| `status` | `str` | `draft`, `submitted`, `pending_approval`, `approved`, `rejected`, `expired` | Lifecycle state |

### Status transitions

```
draft
  └─► submitted       (reservation_validator_node: all fields present and valid)
        └─► pending_approval  (approval_request_node: admin email sent)
              ├─► approved    (pending_check_node: admin called approve endpoint)
              ├─► rejected    (pending_check_node: admin called reject endpoint)
              └─► expired     (pending_check_node: APPROVAL_TIMEOUT_SECONDS elapsed)
```

---

## Node I/O Contract

Each node receives the current `ConversationState` and returns an updated copy. The contract below captures which fields each node reads and which it writes.

| Node | Reads | Writes |
|------|-------|--------|
| `pending_check_node` | `session_id`, `reservation` | `reservation.status`, `response_draft`, `approval_request_id` |
| `route_intent` | `messages` | `intent`, `error` |
| `retrieve_and_generate` | `messages` | `retrieved_chunks`, `response_draft`, `error` |
| `dynamic_data_node` | `messages`, `intent` | `response_draft`, `error` |
| `out_of_scope_node` | — | `response_draft` |
| `reservation_collector_node` | `messages`, `reservation` | `reservation` (field updates), `error` |
| `reservation_validator_node` | `reservation` | `reservation.status`, `response_draft`, `error` |
| `approval_request_node` | `session_id`, `reservation` | `approval_request_id`, `reservation.status`, `response_draft`, `error` |
| `guard_rails_node` | `response_draft`, `approval_request_id`, `reservation.status` | `response_final`, `error` |
| `respond` | `response_final`, `response_draft` | `messages` (appends AIMessage) |

---

## Graph Routing Logic

Three conditional routing functions determine the execution path:

| Function | Condition | Target |
|----------|-----------|--------|
| `_route_after_pending_check` | `state.response_draft is not None` | `guard_rails_node` |
| `_route_after_pending_check` | else | `route_intent` |
| `_route_after_intent` | `intent == "info_query"` | `retrieve_and_generate` |
| `_route_after_intent` | `intent in {pricing, hours, availability}` | `dynamic_data_node` |
| `_route_after_intent` | `intent == "reservation"` | `reservation_collector_node` |
| `_route_after_intent` | else | `out_of_scope_node` |
| `_route_after_reservation_validator` | `reservation.status == "submitted"` | `approval_request_node` |
| `_route_after_reservation_validator` | else | `respond` |
