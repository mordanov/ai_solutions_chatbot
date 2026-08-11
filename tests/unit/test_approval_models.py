"""Unit tests for ApprovalRequest and ApprovalDecision models."""
from datetime import datetime, timedelta, timezone

import pytest

from chatbot.approval.models import ApprovalDecision, ApprovalRequest


def test_approval_request_defaults():
    req = ApprovalRequest(
        session_id="s1",
        first_name="Alice",
        surname="Smith",
        license_plate="ABC123",
        start_datetime="2026-08-15 10:00",
        end_datetime="2026-08-16 10:00",
    )
    assert req.request_id  # UUID assigned
    assert req.decision is None
    assert req.reason is None
    assert req.decided_at is None
    assert req.created_at.tzinfo is not None


def test_approval_request_unique_ids():
    make = lambda: ApprovalRequest(
        session_id="s1",
        first_name="A",
        surname="B",
        license_plate="X",
        start_datetime="2026-08-15 10:00",
        end_datetime="2026-08-16 10:00",
    )
    assert make().request_id != make().request_id


def test_approval_decision_reason_optional():
    d = ApprovalDecision()
    assert d.reason is None
    d2 = ApprovalDecision(reason="No spaces")
    assert d2.reason == "No spaces"


def test_approval_request_created_at_is_recent():
    before = datetime.now(timezone.utc)
    req = ApprovalRequest(
        session_id="s1",
        first_name="A",
        surname="B",
        license_plate="X",
        start_datetime="2026-08-15 10:00",
        end_datetime="2026-08-16 10:00",
    )
    after = datetime.now(timezone.utc)
    assert before <= req.created_at <= after
