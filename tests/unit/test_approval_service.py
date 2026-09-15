"""Unit tests for ApprovalService.record_decision()."""
from unittest.mock import MagicMock

import pytest

from chatbot.approval.models import ApprovalRequest
from chatbot.approval.service import ApprovalService
from chatbot.approval.store import PendingStore


def _fresh() -> tuple[PendingStore, ApprovalService]:
    from chatbot.approval import store as store_mod
    store_mod._by_session.clear()
    store_mod._by_request.clear()
    mock_notifier = MagicMock()
    svc = ApprovalService(notifier=mock_notifier)
    return store_mod, svc


def _seed_request(session_id: str = "s1") -> ApprovalRequest:
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


def test_record_decision_approve():
    _fresh()
    req = _seed_request("s-approve")
    _, svc = _fresh()
    # Re-seed after clearing
    from chatbot.approval.store import pending_store
    pending_store.add(req)
    result = svc.record_decision(req.request_id, "approved")
    assert result.decision == "approved"
    assert result.decided_at is not None


def test_record_decision_reject_with_reason():
    _fresh()
    req = _seed_request("s-reject")
    from chatbot.approval.store import pending_store
    pending_store.add(req)
    _, svc = _fresh()
    pending_store.add(req)
    result = svc.record_decision(req.request_id, "rejected", reason="Fully booked")
    assert result.decision == "rejected"
    assert result.reason == "Fully booked"


def test_record_decision_unknown_raises():
    _fresh()
    _, svc = _fresh()
    with pytest.raises(KeyError):
        svc.record_decision("nonexistent-id", "approved")


def test_create_request_sends_email():
    _fresh()
    mock_notifier = MagicMock()
    svc = ApprovalService(notifier=mock_notifier)
    req = svc.create_request(
        session_id="s-create",
        first_name="Bob",
        surname="Jones",
        license_plate="XYZ999",
        start_datetime="2026-08-20 09:00",
        end_datetime="2026-08-21 09:00",
    )
    mock_notifier.send_approval_request.assert_called_once()
    assert req.session_id == "s-create"
