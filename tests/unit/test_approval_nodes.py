"""Unit tests for pending_check_node."""
from datetime import UTC, datetime, timedelta

import pytest

from chatbot.approval.models import ApprovalRequest
from chatbot.workflow.nodes import pending_check_node
from chatbot.workflow.state import ConversationState, ReservationData


def _reset_store():
    from chatbot.approval import store as store_mod
    store_mod._by_session.clear()
    store_mod._by_request.clear()


def _make_state(session_id: str = "sess-node") -> ConversationState:
    return ConversationState(
        session_id=session_id,
        reservation=ReservationData(
            status="pending_approval",
            first_name="Alice",
            surname="Smith",
            license_plate="ABC123",
            start_datetime="2026-08-15 10:00",
            end_datetime="2026-08-16 10:00",
        ),
    )


@pytest.fixture(autouse=True)
def clean_store():
    _reset_store()
    yield
    _reset_store()


def _seed(session_id: str = "sess-node", decision=None, reason=None) -> ApprovalRequest:
    from chatbot.approval.store import pending_store

    req = ApprovalRequest(
        session_id=session_id,
        first_name="Alice",
        surname="Smith",
        license_plate="ABC123",
        start_datetime="2026-08-15 10:00",
        end_datetime="2026-08-16 10:00",
    )
    if decision:
        req.decision = decision  # type: ignore[assignment]
        req.reason = reason
        req.decided_at = datetime.now(UTC)
    pending_store.add(req)
    return req


def test_no_pending_request_returns_state_unchanged():
    """Session with no pending request → state unchanged, response_draft stays None."""
    state = _make_state("sess-none")
    result = pending_check_node(state)
    assert result.response_draft is None


def test_approved_decision_sets_response_and_clears_store():
    """When decision == 'approved', response_draft is set and store is cleared."""
    from chatbot.approval.store import pending_store

    _seed("sess-approved", decision="approved")
    state = _make_state("sess-approved")
    result = pending_check_node(state)

    assert result.response_draft is not None
    assert "approved" in result.response_draft.lower() or "✅" in result.response_draft
    assert result.reservation.status == "approved"
    assert pending_store.get_pending_for_session("sess-approved") is None


def test_rejected_decision_with_reason_sets_response_and_clears_store():
    """When decision == 'rejected' with reason, response includes reason and store is cleared."""
    from chatbot.approval.store import pending_store

    _seed("sess-rejected", decision="rejected", reason="Fully booked")
    state = _make_state("sess-rejected")
    result = pending_check_node(state)

    assert result.response_draft is not None
    assert "Fully booked" in result.response_draft
    assert result.reservation.status == "rejected"
    assert pending_store.get_pending_for_session("sess-rejected") is None


def test_expired_request_sets_expired_status_and_clears_store():
    """When request is past timeout, status is set to 'expired' and store cleared."""
    from chatbot.approval import store as store_mod

    req = _seed("sess-expired")
    # Back-date created_at beyond timeout
    req.created_at = datetime.now(UTC) - timedelta(seconds=10_000)
    store_mod._by_request[req.request_id] = req

    state = _make_state("sess-expired")
    result = pending_check_node(state)

    assert result.response_draft is not None
    assert result.reservation.status == "expired"
    from chatbot.approval.store import pending_store
    assert pending_store.get_pending_for_session("sess-expired") is None


def test_still_pending_no_decision_returns_unchanged():
    """When request exists but no decision yet → response_draft stays None."""
    _seed("sess-pending")  # no decision set
    state = _make_state("sess-pending")
    result = pending_check_node(state)

    assert result.response_draft is None


def test_approved_decision_without_reservation_in_state_sets_approval_request_id():
    """Fresh-state (no reservation object) after admin approves — approval_request_id is set so
    guard_rails can bypass PII scan even without state.reservation."""
    req = _seed("sess-fresh-approved", decision="approved")
    # Simulate what the chat endpoint does: fresh ConversationState with no reservation
    state = ConversationState(session_id="sess-fresh-approved")
    result = pending_check_node(state)

    assert result.response_draft is not None
    assert "approved" in result.response_draft.lower() or "✅" in result.response_draft
    assert result.approval_request_id == req.request_id
