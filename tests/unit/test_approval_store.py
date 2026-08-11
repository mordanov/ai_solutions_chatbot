"""Unit tests for PendingStore."""
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest

from chatbot.approval.models import ApprovalRequest
from chatbot.approval.store import PendingStore


def _make_request(session_id: str = "sess-1") -> ApprovalRequest:
    return ApprovalRequest(
        session_id=session_id,
        first_name="Alice",
        surname="Smith",
        license_plate="ABC123",
        start_datetime="2026-08-15 10:00",
        end_datetime="2026-08-16 10:00",
    )


def _fresh_store() -> PendingStore:
    store = PendingStore()
    # Clear module-level dicts between tests
    from chatbot.approval import store as store_mod
    store_mod._by_session.clear()
    store_mod._by_request.clear()
    return store


def test_add_and_get_by_session():
    store = _fresh_store()
    req = _make_request("s1")
    store.add(req)
    found = store.get_pending_for_session("s1")
    assert found is not None
    assert found.request_id == req.request_id


def test_get_by_request_id():
    store = _fresh_store()
    req = _make_request("s2")
    store.add(req)
    found = store.get_by_request_id(req.request_id)
    assert found is not None
    assert found.session_id == "s2"


def test_get_missing_session_returns_none():
    store = _fresh_store()
    assert store.get_pending_for_session("unknown") is None


def test_record_decision_approve():
    store = _fresh_store()
    req = _make_request("s3")
    store.add(req)
    result = store.record_decision(req.request_id, "approved")
    assert result.decision == "approved"
    assert result.decided_at is not None


def test_record_decision_reject_with_reason():
    store = _fresh_store()
    req = _make_request("s4")
    store.add(req)
    result = store.record_decision(req.request_id, "rejected", reason="Full")
    assert result.decision == "rejected"
    assert result.reason == "Full"


def test_duplicate_decision_raises():
    store = _fresh_store()
    req = _make_request("s5")
    store.add(req)
    store.record_decision(req.request_id, "approved")
    with pytest.raises(ValueError, match="already been decided"):
        store.record_decision(req.request_id, "rejected")


def test_is_expired_false_for_fresh():
    store = _fresh_store()
    req = _make_request("s6")
    store.add(req)
    assert not store.is_expired(req.request_id)


def test_is_expired_true_after_timeout():
    store = _fresh_store()
    req = _make_request("s7")
    old_time = datetime.now(UTC) - timedelta(seconds=400)
    req.created_at = old_time
    store.add(req)
    with patch("chatbot.approval.store.settings") as mock_settings:
        mock_settings.approval_timeout_seconds = 300
        assert store.is_expired(req.request_id)


def test_clear_session():
    store = _fresh_store()
    req = _make_request("s8")
    store.add(req)
    store.clear_session("s8")
    assert store.get_pending_for_session("s8") is None
    assert store.get_by_request_id(req.request_id) is None
