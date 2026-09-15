from typing import Annotated

from langchain_core.documents import Document
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from pydantic import BaseModel


class ReservationData(BaseModel):
    first_name: str | None = None
    surname: str | None = None
    license_plate: str | None = None
    start_datetime: str | None = None
    end_datetime: str | None = None
    status: str = "draft"


class ConversationState(BaseModel):
    session_id: str
    messages: Annotated[list[BaseMessage], add_messages] = []
    intent: str | None = None
    retrieved_chunks: list[Document] = []
    reservation: ReservationData | None = None
    response_draft: str | None = None
    response_final: str | None = None
    error: str | None = None
    approval_request_id: str | None = None
