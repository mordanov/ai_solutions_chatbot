"""SMTP email notifier for admin reservation approval requests."""
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from urllib.parse import urlencode

from chatbot.approval.models import ApprovalRequest
from chatbot.config import settings

logger = logging.getLogger(__name__)


class SmtpNotifier:
    def send_approval_request(self, request: ApprovalRequest) -> None:
        base = settings.base_url.rstrip("/")
        token_qs = urlencode({"token": settings.admin_token})
        approve_url = f"{base}/admin/reservation/{request.request_id}/approve?{token_qs}"
        reject_url = f"{base}/admin/reservation/{request.request_id}/reject?{token_qs}"

        subject = (
            f"[Parking Reservation] New request from "
            f"{request.first_name} {request.surname} — {request.request_id}"
        )
        html = (
            f"<p>A new parking reservation request requires your approval.</p>"
            f"<table>"
            f"<tr><td><b>Name</b></td><td>{request.first_name} {request.surname}</td></tr>"
            f"<tr><td><b>Plate</b></td><td>{request.license_plate}</td></tr>"
            f"<tr><td><b>From</b></td><td>{request.start_datetime}</td></tr>"
            f"<tr><td><b>To</b></td><td>{request.end_datetime}</td></tr>"
            f"<tr><td><b>ID</b></td><td>{request.request_id}</td></tr>"
            f"</table>"
            f"<p>"
            f'<a href="{approve_url}" style="background:#22c55e;color:#fff;padding:8px 16px;text-decoration:none;border-radius:4px;margin-right:8px">✅ Approve</a>'
            f'<a href="{reject_url}" style="background:#ef4444;color:#fff;padding:8px 16px;text-decoration:none;border-radius:4px">❌ Reject</a>'
            f"</p>"
        )

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = settings.smtp_from
        msg["To"] = settings.admin_email
        msg.attach(MIMEText(html, "html"))

        try:
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as smtp:
                if settings.smtp_user:
                    smtp.login(settings.smtp_user, settings.smtp_password)
                smtp.sendmail(settings.smtp_from, settings.admin_email, msg.as_string())
            logger.info("Approval request email sent for %s", request.request_id)
        except Exception as exc:
            logger.error("Failed to send approval email: %s", exc)
            # Don't raise — request is already in pending_store; admin can act via the panel
