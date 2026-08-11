"""Pydantic models for the admin reservation approval workflow."""
from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field


class ApprovalRequest(BaseModel):
    request_id: str = Field(default_factory=lambda: str(uuid4()))
    session_id: str
    first_name: str
    surname: str
    license_plate: str
    start_datetime: str
    end_datetime: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    decision: Literal["approved", "rejected"] | None = None
    reason: str | None = None
    decided_at: datetime | None = None


class ApprovalDecision(BaseModel):
    reason: str | None = None
