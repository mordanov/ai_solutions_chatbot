# Contract: Chat API

**Branch**: `001-parking-rag` | **Date**: 2026-08-11

The chatbot exposes a REST API consumed by the Streamlit UI and any future
external clients. All endpoints are JSON over HTTP.

---

## POST /chat

Send a user message and receive a chatbot response.

**Request**

```json
{
  "session_id": "string (required) — stable ID for the conversation session",
  "message":    "string (required) — user's plain-text message, max 4 000 chars"
}
```

**Response 200**

```json
{
  "session_id":  "string — echoed from request",
  "response":    "string — chatbot reply after guard-rail filtering",
  "intent":      "string — detected intent: info_query | reservation | out_of_scope",
  "latency_ms":  "integer — time from request receipt to response ready"
}
```

**Response 400** — invalid request body (missing fields, oversized message)

```json
{ "error": "string — human-readable reason" }
```

**Response 500** — unexpected server error

```json
{ "error": "Internal error. Please try again." }
```

**Constraints**:
- `message` must not be empty after stripping whitespace.
- `message` length ≤ 4 000 characters.
- `session_id` must be non-empty, alphanumeric + hyphens, ≤ 128 chars.

---

## GET /health

Liveness and readiness check.

**Response 200**

```json
{
  "status":   "ok",
  "version":  "string — application version",
  "vector_store": "connected | degraded | unavailable",
  "database":     "connected | unavailable"
}
```

**Response 503** — one or more dependencies unavailable

```json
{
  "status":   "degraded",
  "vector_store": "...",
  "database":     "..."
}
```

---

## POST /admin/reload-knowledge

Triggers a full re-ingestion of the knowledge base from source documents.
Admin-only; requires `Authorization: Bearer <ADMIN_TOKEN>` header.

**Request**: empty body

**Response 202** — ingestion started

```json
{ "message": "Knowledge base reload started." }
```

**Response 401** — missing or invalid token

```json
{ "error": "Unauthorized." }
```

---

## Streamlit UI Contract

The Streamlit app uses the `/chat` endpoint exclusively. It:
- Generates a `session_id` (UUID4) on first load and stores it in session state.
- Displays the conversation as a message thread.
- Shows a spinner while the POST /chat call is in-flight.
- Displays an error banner on 4xx / 5xx responses without crashing.
