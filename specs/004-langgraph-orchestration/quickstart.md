# Quickstart: Complete Pipeline Walkthrough

**Feature**: 004-langgraph-orchestration  
**Date**: 2026-08-12

This walkthrough demonstrates the complete four-stage pipeline running locally. All four stages are wired end-to-end; this is a dev/demo scenario using MailHog for SMTP.

---

## Prerequisites

```bash
# Start the infrastructure (Milvus, PostgreSQL, MailHog)
docker compose up -d

# Seed the database and ingest parking knowledge
python scripts/init_db.py --seed
python scripts/ingest.py

# Start the API in one terminal
uvicorn chatbot.api.main:app --reload

# Optionally start the Streamlit UI in another terminal
streamlit run src/chatbot/app.py
```

Set `ADMIN_TOKEN=demo-token` in your `.env`.

---

## Step 1 — User submits a reservation

```bash
curl -s -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "demo-session",
    "message": "Hi, I would like to book a parking space for Alice Smith, license plate AB1234, from 20 Aug 2026 at 10am to 21 Aug 2026 at 10am"
  }' | jq .
```

Expected response (paraphrased):
```json
{
  "session_id": "demo-session",
  "response": "Your reservation request has been sent to the administrator...",
  "intent": "reservation",
  "latency_ms": 1234
}
```

---

## Step 2 — Administrator views the pending request

```bash
curl -s http://localhost:8000/admin/reservations/pending \
  -H "Authorization: Bearer demo-token" | jq .
```

Or open MailHog at `http://localhost:8025` to see the approval email.

Copy the `request_id` from the JSON output.

---

## Step 3 — Administrator approves

```bash
curl -s -X POST http://localhost:8000/admin/reservation/<REQUEST_ID>/approve \
  -H "Authorization: Bearer demo-token"
# Returns HTTP 204 No Content
```

Behind the scenes:
1. `ApprovalService.record_decision()` marks the request as `approved` in the in-memory store.
2. `ReservationStorageClient.write_record()` spawns the MCP server subprocess and appends the record to `data/reservations.txt`.

Verify the storage file:
```bash
cat data/reservations.txt
# Alice Smith | AB1234 | 2026-08-20 10:00 → 2026-08-21 10:00 | 2026-08-12 14:30
```

---

## Step 4 — User sends any message to get their notification

```bash
curl -s -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"session_id": "demo-session", "message": "Any update?"}' | jq .response
```

Expected response (paraphrased):
```
"✅ Your reservation has been approved! Name: Alice Smith | Plate: AB1234 | From: 2026-08-20 10:00 → To: 2026-08-21 10:00"
```

---

## Rejection walkthrough (steps 1–2 identical)

```bash
curl -s -X POST http://localhost:8000/admin/reservation/<REQUEST_ID>/reject \
  -H "Authorization: Bearer demo-token" \
  -H "Content-Type: application/json" \
  -d '{"reason": "No spaces available on those dates"}'
# Returns HTTP 204 No Content
# data/reservations.txt is NOT updated
```

Next user message returns:
```
"❌ Your reservation was not approved. Reason: No spaces available on those dates"
```

---

## Running the automated test suite

```bash
# All unit tests (no Docker required)
pytest tests/unit/ -v

# Integration tests (requires Docker stack)
pytest tests/integration/ -v -m integration
```

Key test files for Stage 4:

| File | What it covers |
|------|----------------|
| `tests/unit/test_workflow_graph.py` | Graph routing function unit tests |
| `tests/unit/test_workflow_nodes.py` | All 9 node function unit tests |
| `tests/unit/test_pipeline_integration.py` | Full pipeline (mocked external services) |
