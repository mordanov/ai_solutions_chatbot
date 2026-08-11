"""Approval workflow service — creates requests and records admin decisions."""
import logging

from chatbot.approval.models import ApprovalRequest
from chatbot.approval.notifier import SmtpNotifier
from chatbot.approval.store import pending_store

logger = logging.getLogger(__name__)


class ApprovalService:
    def __init__(self, notifier: SmtpNotifier | None = None) -> None:
        self._notifier = notifier or SmtpNotifier()

    def create_request(
        self,
        session_id: str,
        first_name: str,
        surname: str,
        license_plate: str,
        start_datetime: str,
        end_datetime: str,
    ) -> ApprovalRequest:
        request = ApprovalRequest(
            session_id=session_id,
            first_name=first_name,
            surname=surname,
            license_plate=license_plate,
            start_datetime=start_datetime,
            end_datetime=end_datetime,
        )
        pending_store.add(request)
        self._notifier.send_approval_request(request)
        logger.info("Approval request %s created for session %s", request.request_id, session_id)
        return request

    def record_decision(
        self, request_id: str, decision: str, reason: str | None = None
    ) -> ApprovalRequest:
        request = pending_store.get_by_request_id(request_id)
        if request is None:
            raise KeyError(f"Approval request {request_id} not found")
        return pending_store.record_decision(request_id, decision, reason)
