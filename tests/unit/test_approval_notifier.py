"""Unit tests for SmtpNotifier — mocks smtplib.SMTP."""
from unittest.mock import MagicMock, patch

from chatbot.approval.models import ApprovalRequest
from chatbot.approval.notifier import SmtpNotifier


def _make_request() -> ApprovalRequest:
    return ApprovalRequest(
        request_id="req-abc-123",
        session_id="sess-1",
        first_name="Alice",
        surname="Smith",
        license_plate="ABC123",
        start_datetime="2026-08-15 10:00",
        end_datetime="2026-08-16 10:00",
    )


@patch("chatbot.approval.notifier.smtplib.SMTP")
def test_send_email_subject_contains_name_and_id(mock_smtp_cls):
    mock_smtp = MagicMock()
    mock_smtp_cls.return_value.__enter__ = MagicMock(return_value=mock_smtp)
    mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)

    notifier = SmtpNotifier()
    req = _make_request()
    notifier.send_approval_request(req)

    assert mock_smtp.sendmail.called
    args = mock_smtp.sendmail.call_args
    message_str = args[0][2]
    assert "Alice Smith" in message_str
    assert "req-abc-123" in message_str


@patch("chatbot.approval.notifier.smtplib.SMTP")
def test_send_email_body_contains_approve_and_reject_commands(mock_smtp_cls):
    mock_smtp = MagicMock()
    mock_smtp_cls.return_value.__enter__ = MagicMock(return_value=mock_smtp)
    mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)

    notifier = SmtpNotifier()
    req = _make_request()
    notifier.send_approval_request(req)

    message_str = mock_smtp.sendmail.call_args[0][2]
    assert "approve" in message_str.lower()
    assert "reject" in message_str.lower()
    assert "ABC123" in message_str


@patch("chatbot.approval.notifier.smtplib.SMTP")
def test_send_email_uses_configured_recipients(mock_smtp_cls):
    mock_smtp = MagicMock()
    mock_smtp_cls.return_value.__enter__ = MagicMock(return_value=mock_smtp)
    mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)

    notifier = SmtpNotifier()
    req = _make_request()
    notifier.send_approval_request(req)

    from_addr, to_addrs, _ = mock_smtp.sendmail.call_args[0]
    assert from_addr  # non-empty
    assert to_addrs   # non-empty
