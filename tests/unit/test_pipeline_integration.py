"""
Full pipeline integration tests (all external services mocked).

Covers the complete path:
  POST /chat (reservation intent) →
  pending_store populated →
  POST /admin/reservation/{id}/approve|reject →
  POST /chat (same session) →
  user receives approval/rejection notification.
"""
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from chatbot.api.main import app
from chatbot.config import settings

client = TestClient(app)
ADMIN_HEADERS = {"Authorization": f"Bearer {settings.admin_token}"}

_RESERVATION_JSON = json.dumps({
    "first_name": "Alice",
    "surname": "Smith",
    "license_plate": "AB1234",
    "start_datetime": "2026-08-20 10:00",
    "end_datetime": "2026-08-21 10:00",
})


def _reset_store() -> None:
    from chatbot.approval import store as store_mod
    store_mod._by_session.clear()
    store_mod._by_request.clear()


@pytest.fixture(autouse=True)
def clean_store():
    _reset_store()
    yield
    _reset_store()


def _mock_llm_for_reservation() -> MagicMock:
    """LLM mock: first call → intent 'reservation', second → extraction JSON."""
    llm = MagicMock()
    llm.invoke.side_effect = [
        MagicMock(content="reservation"),
        MagicMock(content=_RESERVATION_JSON),
    ]
    return llm


def _submit_reservation(session_id: str) -> str:
    """POST /chat to submit a reservation; returns the request_id from the store."""
    mock_llm = _mock_llm_for_reservation()
    with (
        patch("chatbot.workflow.nodes._get_llm", return_value=mock_llm),
        patch("chatbot.approval.notifier.SmtpNotifier.send_approval_request"),
    ):
        resp = client.post(
            "/chat",
            json={"session_id": session_id, "message": "Book for Alice Smith, plate AB1234, 20 Aug to 21 Aug"},
        )
    assert resp.status_code == 200

    from chatbot.approval import store as store_mod
    reqs = list(store_mod._by_request.values())
    assert len(reqs) == 1, "Expected exactly one pending request after submission"
    return reqs[0].request_id


# ------------------------------------------------------------------
# T012 — Approval pipeline
# ------------------------------------------------------------------

def test_full_approval_pipeline():
    session_id = "pipeline-approve"

    # Step 1: user submits reservation
    request_id = _submit_reservation(session_id)

    # Step 2: admin approves; storage write is mocked
    mock_write = AsyncMock()
    with patch("chatbot.storage.client.ReservationStorageClient") as MockClient:
        MockClient.return_value.write_record = mock_write
        resp = client.post(f"/admin/reservation/{request_id}/approve", headers=ADMIN_HEADERS)

    assert resp.status_code == 204
    mock_write.assert_awaited_once()
    kw = mock_write.call_args.kwargs
    assert kw["name"] == "Alice Smith"
    assert kw["car_number"] == "AB1234"

    # Step 3: user sends any message in the same session → sees approval notification
    resp3 = client.post(
        "/chat",
        json={"session_id": session_id, "message": "Any update?"},
    )
    assert resp3.status_code == 200
    assert "approved" in resp3.json()["response"].lower()


# ------------------------------------------------------------------
# T014 — Rejection pipeline
# ------------------------------------------------------------------

def test_full_rejection_pipeline():
    session_id = "pipeline-reject"

    # Step 1: user submits reservation
    request_id = _submit_reservation(session_id)

    # Step 2: admin rejects; storage write must NOT be called
    mock_write = AsyncMock()
    with patch("chatbot.storage.client.ReservationStorageClient") as MockClient:
        MockClient.return_value.write_record = mock_write
        resp = client.post(
            f"/admin/reservation/{request_id}/reject",
            headers=ADMIN_HEADERS,
            json={"reason": "No spaces available"},
        )

    assert resp.status_code == 204
    mock_write.assert_not_awaited()

    # Step 3: user sends any message → sees rejection notification
    resp3 = client.post(
        "/chat",
        json={"session_id": session_id, "message": "Any update?"},
    )
    assert resp3.status_code == 200
    response_text = resp3.json()["response"].lower()
    assert "not approved" in response_text or "rejected" in response_text or "❌" in resp3.json()["response"]
