"""In-process pending approval store keyed by session_id."""
from datetime import datetime, timezone

from chatbot.approval.models import ApprovalRequest
from chatbot.config import settings

# Two lookup indexes: session_id → request_id, request_id → ApprovalRequest
_by_session: dict[str, str] = {}
_by_request: dict[str, ApprovalRequest] = {}


class PendingStore:
    def add(self, request: ApprovalRequest) -> None:
        _by_session[request.session_id] = request.request_id
        _by_request[request.request_id] = request

    def get_pending_for_session(self, session_id: str) -> ApprovalRequest | None:
        request_id = _by_session.get(session_id)
        if request_id is None:
            return None
        return _by_request.get(request_id)

    def get_by_request_id(self, request_id: str) -> ApprovalRequest | None:
        return _by_request.get(request_id)

    def record_decision(
        self, request_id: str, decision: str, reason: str | None = None
    ) -> ApprovalRequest:
        req = _by_request.get(request_id)
        if req is None:
            raise KeyError(f"Request {request_id} not found")
        if req.decision is not None:
            raise ValueError(f"Request {request_id} has already been decided")
        if self.is_expired(request_id):
            raise ValueError(f"Request {request_id} has expired")
        req.decision = decision  # type: ignore[assignment]
        req.reason = reason
        req.decided_at = datetime.now(timezone.utc)
        return req

    def is_expired(self, request_id: str) -> bool:
        req = _by_request.get(request_id)
        if req is None:
            return False
        age = (datetime.now(timezone.utc) - req.created_at).total_seconds()
        return age > settings.approval_timeout_seconds

    def clear_session(self, session_id: str) -> None:
        request_id = _by_session.pop(session_id, None)
        if request_id:
            _by_request.pop(request_id, None)


pending_store = PendingStore()
