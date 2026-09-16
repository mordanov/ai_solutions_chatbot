"""Unit tests for SmtpNotifier — mocks smtplib.SMTP."""
import email
import email.header
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


def _parse_email(mock_smtp):
    raw = mock_smtp.sendmail.call_args[0][2]
    msg = email.message_from_string(raw)
    subject_parts = email.header.decode_header(msg["Subject"])
    subject = "".join(
        p.decode(enc or "utf-8") if isinstance(p, bytes) else p
        for p, enc in subject_parts
    )
    body = ""
    for part in msg.walk():
        if part.get_content_type() == "text/html":
            body = part.get_payload(decode=True).decode("utf-8")
            break
    return subject, body


@patch("chatbot.approval.notifier.smtplib.SMTP")
def test_send_email_subject_contains_name_and_id(mock_smtp_cls):
    mock_smtp = MagicMock()
    mock_smtp_cls.return_value.__enter__ = MagicMock(return_value=mock_smtp)
    mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)

    notifier = SmtpNotifier()
    notifier.send_approval_request(_make_request())

    assert mock_smtp.sendmail.called
    subject, _ = _parse_email(mock_smtp)
    assert "Alice Smith" in subject
    assert "req-abc-123" in subject


@patch("chatbot.approval.notifier.smtplib.SMTP")
def test_send_email_body_contains_approve_and_reject_commands(mock_smtp_cls):
    mock_smtp = MagicMock()
    mock_smtp_cls.return_value.__enter__ = MagicMock(return_value=mock_smtp)
    mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)

    notifier = SmtpNotifier()
    notifier.send_approval_request(_make_request())

    _, body = _parse_email(mock_smtp)
    assert "approve" in body.lower()
    assert "reject" in body.lower()
    assert "ABC123" in body


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
