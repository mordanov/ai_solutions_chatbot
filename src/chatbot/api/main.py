"""FastAPI application — REST interface for the parking chatbot."""
import logging
import time
import uuid

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from langchain_core.messages import HumanMessage
from pydantic import BaseModel

from chatbot.approval.models import ApprovalDecision
from chatbot.config import settings
from chatbot.workflow.graph import compiled_graph
from chatbot.workflow.state import ConversationState

logger = logging.getLogger(__name__)
app = FastAPI(title="Parking Chatbot API", version="1.0.0")
_bearer = HTTPBearer(auto_error=False)


# ------------------------------------------------------------------
# Schemas
# ------------------------------------------------------------------

class ChatRequest(BaseModel):
    session_id: str = ""
    message: str


class ChatResponse(BaseModel):
    session_id: str
    response: str
    intent: str | None
    latency_ms: int


# ------------------------------------------------------------------
# Auth helper
# ------------------------------------------------------------------

def _require_admin(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> None:
    if creds is None or creds.credentials != settings.admin_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorised")


# ------------------------------------------------------------------
# Routes
# ------------------------------------------------------------------

@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    session_id = req.session_id or str(uuid.uuid4())
    start = time.monotonic()
    try:
        initial_state = ConversationState(
            session_id=session_id,
            messages=[HumanMessage(content=req.message)],
        )
        raw = compiled_graph.invoke(initial_state)
        response_text = (
            raw.get("response_final") or raw.get("response_draft") or "No response generated."
        )
        intent = raw.get("intent")
    except Exception as exc:
        logger.error("chat endpoint error: %s", exc)
        raise HTTPException(status_code=500, detail="Internal server error") from exc

    latency_ms = int((time.monotonic() - start) * 1000)
    return ChatResponse(
        session_id=session_id,
        response=response_text,
        intent=intent,
        latency_ms=latency_ms,
    )


@app.get("/admin/reservations/pending")
async def list_pending_reservations(_: None = Depends(_require_admin)) -> list[dict]:
    """Return all pending (undecided, non-expired) approval requests."""
    from chatbot.approval.store import pending_store

    return [req.model_dump(mode="json") for req in pending_store.get_all_pending()]


@app.post("/admin/reservation/{request_id}/approve", status_code=204)
async def approve_reservation(
    request_id: str,
    _: None = Depends(_require_admin),
) -> None:
    """Record an admin approval decision for a pending reservation."""
    from datetime import UTC, datetime

    from chatbot.approval.service import ApprovalService
    from chatbot.approval.store import pending_store
    from chatbot.storage.client import ReservationStorageClient

    req = pending_store.get_by_request_id(request_id)
    if req is None:
        raise HTTPException(status_code=404, detail="Reservation request not found")
    try:
        ApprovalService().record_decision(request_id, "approved")
    except ValueError as exc:
        raise HTTPException(status_code=409, detail="Reservation request is no longer actionable") from exc

    approval_time = datetime.now(UTC).strftime("%Y-%m-%d %H:%M")
    period = f"{req.start_datetime} → {req.end_datetime}"
    try:
        await ReservationStorageClient().write_record(
            name=f"{req.first_name} {req.surname}",
            car_number=req.license_plate,
            reservation_period=period,
            approval_time=approval_time,
        )
    except Exception as exc:
        logger.error("Storage write failed for request %s: %s", request_id, exc)


@app.post("/admin/reservation/{request_id}/reject", status_code=204)
async def reject_reservation(
    request_id: str,
    body: ApprovalDecision | None = None,
    _: None = Depends(_require_admin),
) -> None:
    """Record an admin rejection decision for a pending reservation."""
    from chatbot.approval.service import ApprovalService
    from chatbot.approval.store import pending_store

    if pending_store.get_by_request_id(request_id) is None:
        raise HTTPException(status_code=404, detail="Reservation request not found")
    reason = body.reason if body else None
    try:
        ApprovalService().record_decision(request_id, "rejected", reason=reason)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail="Reservation request is no longer actionable") from exc


@app.post("/admin/reload-knowledge", status_code=204)
async def reload_knowledge(_: None = Depends(_require_admin)) -> None:
    """Trigger a full knowledge base re-ingestion."""
    from pathlib import Path

    from chatbot.knowledge.vector_store import MilvusVectorStore
    from chatbot.rag.ingestion import ingest_documents

    store = MilvusVectorStore()
    store.drop_collection()
    data_dir = Path("data/parking_info")
    count = ingest_documents(data_dir, store)
    logger.info("Reloaded %d chunks into Milvus", count)
