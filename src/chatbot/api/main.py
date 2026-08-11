"""FastAPI application — REST interface for the parking chatbot."""
import logging
import time
import uuid

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from langchain_core.messages import HumanMessage
from pydantic import BaseModel

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
