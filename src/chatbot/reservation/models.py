from enum import Enum
from typing import Literal

from pydantic import BaseModel


class ReservationField(Enum):
    first_name = "first_name"
    surname = "surname"
    license_plate = "license_plate"
    start_datetime = "start_datetime"
    end_datetime = "end_datetime"


class ReservationDraft(BaseModel):
    first_name: str | None = None
    surname: str | None = None
    license_plate: str | None = None
    start_datetime: str | None = None
    end_datetime: str | None = None
    status: Literal["draft", "submitted", "pending_approval", "approved", "rejected", "expired"] = "draft"
