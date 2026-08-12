"""Unit tests for admin approve/reject endpoints."""
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from chatbot.api.main import app
from chatbot.approval.models import ApprovalRequest
from chatbot.config import settings


def _reset_store():
    from chatbot.approval import store as store_mod
    store_mod._by_session.clear()
    store_mod._by_request.clear()


def _seed(session_id: str = "sess-api") -> ApprovalRequest:
    from chatbot.approval.store import pending_store
    req = ApprovalRequest(
        session_id=session_id,
        first_name="Alice",
        surname="Smith",
        license_plate="ABC123",
        start_datetime="2026-08-15 10:00",
        end_datetime="2026-08-16 10:00",
    )
    pending_store.add(req)
    return req


@pytest.fixture(autouse=True)
def clean_store():
    _reset_store()
    yield
    _reset_store()


@pytest.fixture(autouse=True)
def mock_storage_client():
    with patch("chatbot.storage.client.ReservationStorageClient") as MockCls:
        mock_instance = AsyncMock()
        MockCls.return_value = mock_instance
        yield MockCls, mock_instance


client = TestClient(app)
HEADERS = {"Authorization": f"Bearer {settings.admin_token}"}


def test_approve_returns_204():
    req = _seed("s-approve")
    resp = client.post(f"/admin/reservation/{req.request_id}/approve", headers=HEADERS)
    assert resp.status_code == 204


def test_reject_with_reason_returns_204():
    req = _seed("s-reject")
    resp = client.post(
        f"/admin/reservation/{req.request_id}/reject",
        headers=HEADERS,
        json={"reason": "No spaces"},
    )
    assert resp.status_code == 204


def test_approve_invalid_token_returns_401():
    req = _seed("s-auth")
    resp = client.post(
        f"/admin/reservation/{req.request_id}/approve",
        headers={"Authorization": "Bearer wrong-token"},
    )
    assert resp.status_code == 401


def test_approve_unknown_request_returns_404():
    resp = client.post("/admin/reservation/nonexistent-id/approve", headers=HEADERS)
    assert resp.status_code == 404


def test_duplicate_approve_returns_409():
    req = _seed("s-dup")
    client.post(f"/admin/reservation/{req.request_id}/approve", headers=HEADERS)
    resp = client.post(f"/admin/reservation/{req.request_id}/approve", headers=HEADERS)
    assert resp.status_code == 409


def test_approve_endpoint_calls_storage_client(mock_storage_client):
    _, mock_instance = mock_storage_client
    req = _seed("s-storage")
    resp = client.post(f"/admin/reservation/{req.request_id}/approve", headers=HEADERS)
    assert resp.status_code == 204
    mock_instance.write_record.assert_called_once()
    kw = mock_instance.write_record.call_args.kwargs
    assert kw["name"] == "Alice Smith"
    assert kw["car_number"] == "ABC123"
    assert "2026-08-15 10:00" in kw["reservation_period"]
    assert "2026-08-16 10:00" in kw["reservation_period"]


def test_approve_endpoint_storage_failure_still_returns_204(mock_storage_client):
    _, mock_instance = mock_storage_client
    mock_instance.write_record.side_effect = RuntimeError("storage failure")
    req = _seed("s-storage-fail")
    resp = client.post(f"/admin/reservation/{req.request_id}/approve", headers=HEADERS)
    assert resp.status_code == 204
