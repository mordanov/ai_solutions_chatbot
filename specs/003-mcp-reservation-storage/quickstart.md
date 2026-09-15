# Quickstart: Approved Reservation Storage Service

**Branch**: `003-mcp-reservation-storage` | **Date**: 2026-08-12

---

## End-to-End Scenario

This walkthrough covers the complete approval-to-storage flow.

### Prerequisites

- The chatbot stack is running (`docker-compose up`).
- A reservation has been submitted via the chat interface (status: `pending_approval`).
- The admin token is set (default: `change-me`).

---

### Step 1 — Submit a reservation

In the Streamlit chat UI (`http://localhost:8501`), have a conversation that ends with a submitted reservation:

```
User: I want to book a parking space
Bot:  Let's start your reservation. What is your first name?
User: Alice
...
User: [provides all required fields]
Bot:  Your reservation request has been sent to the administrator for approval.
```

---

### Step 2 — Check pending approvals

```bash
curl -s -H "Authorization: Bearer change-me" \
  http://localhost:8000/admin/reservations/pending | python -m json.tool
```

Expected output (abbreviated):
```json
[
  {
    "request_id": "abc123...",
    "first_name": "Alice",
    "surname": "Smith",
    "license_plate": "ABC123",
    "start_datetime": "2026-08-15 10:00",
    "end_datetime": "2026-08-16 10:00",
    ...
  }
]
```

---

### Step 3 — Approve the reservation

```bash
curl -s -X POST \
  -H "Authorization: Bearer change-me" \
  http://localhost:8000/admin/reservation/abc123.../approve
```

Expected: HTTP 204 No Content.

---

### Step 4 — Verify the storage file

```bash
cat data/reservations.txt
```

Expected line:
```
Alice Smith | ABC123 | 2026-08-15 10:00 → 2026-08-16 10:00 | 2026-08-12 14:30
```

---

### Step 5 — Verify the user notification

In the chat UI, send any message. The chatbot should respond:
```
✅ Your reservation has been approved!
Name: Alice Smith | Plate: ABC123
From: 2026-08-15 10:00 → To: 2026-08-16 10:00
```

---

## Integration Test Scenario

A pytest integration test can automate steps 3–4:

```python
import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from chatbot.api.main import app
from chatbot.approval.models import ApprovalRequest
from chatbot.approval import store as store_mod

@pytest.fixture(autouse=True)
def clean():
    store_mod._by_session.clear()
    store_mod._by_request.clear()
    yield
    store_mod._by_session.clear()
    store_mod._by_request.clear()

def test_approve_writes_storage_record(tmp_path, monkeypatch):
    monkeypatch.setenv("RESERVATIONS_FILE_PATH", str(tmp_path / "reservations.txt"))
    
    req = ApprovalRequest(
        session_id="sess-e2e",
        first_name="Alice",
        surname="Smith",
        license_plate="ABC123",
        start_datetime="2026-08-15 10:00",
        end_datetime="2026-08-16 10:00",
    )
    store_mod.pending_store.add(req)
    
    client = TestClient(app)
    r = client.post(
        f"/admin/reservation/{req.request_id}/approve",
        headers={"Authorization": "Bearer change-me"},
    )
    assert r.status_code == 204
    
    lines = (tmp_path / "reservations.txt").read_text().strip().splitlines()
    assert len(lines) == 1
    parts = lines[0].split(" | ")
    assert parts[0] == "Alice Smith"
    assert parts[1] == "ABC123"
    assert "2026-08-15 10:00" in parts[2]
```

---

## Calling the MCP Server Directly

The MCP server can also be invoked as a standalone subprocess for debugging:

```bash
RESERVATIONS_FILE_PATH=/tmp/test_reservations.txt \
  python -m chatbot.storage.server
```

Then in a separate terminal, send a JSON-RPC `initialize` followed by a `tools/call` request via stdin. In practice, use the client library rather than raw stdin/stdout.
