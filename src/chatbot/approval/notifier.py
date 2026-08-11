"""SMTP email notifier for admin reservation approval requests."""
import logging
import smtplib
from email.mime.text import MIMEText

from chatbot.approval.models import ApprovalRequest
from chatbot.config import settings

logger = logging.getLogger(__name__)


class SmtpNotifier:
    def send_approval_request(self, request: ApprovalRequest) -> None:
        subject = (
            f"[Parking Reservation] New request from "
            f"{request.first_name} {request.surname} — {request.request_id}"
        )
        body = (
            f"A new parking reservation request requires your approval.\n\n"
            f"Reservation details:\n"
            f"  Name:   {request.first_name} {request.surname}\n"
            f"  Plate:  {request.license_plate}\n"
            f"  From:   {request.start_datetime}\n"
            f"  To:     {request.end_datetime}\n"
            f"  ID:     {request.request_id}\n\n"
            f"To APPROVE:\n"
            f"  curl -X POST http://localhost:8000/admin/reservation/{request.request_id}/approve \\\n"
            f"       -H \"Authorization: Bearer <your_admin_token>\"\n\n"
            f"To REJECT:\n"
            f"  curl -X POST http://localhost:8000/admin/reservation/{request.request_id}/reject \\\n"
            f"       -H \"Authorization: Bearer <your_admin_token>\" \\\n"
            f"       -H \"Content-Type: application/json\" \\\n"
            f"       -d '{{\"reason\": \"No spaces available\"}}'\n"
        )
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = settings.smtp_from
        msg["To"] = settings.admin_email

        try:
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as smtp:
                if settings.smtp_user:
                    smtp.login(settings.smtp_user, settings.smtp_password)
                smtp.sendmail(settings.smtp_from, settings.admin_email, msg.as_string())
            logger.info("Approval request email sent for %s", request.request_id)
        except Exception as exc:
            logger.error("Failed to send approval email: %s", exc)
            raise
