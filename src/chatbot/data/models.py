import uuid
from datetime import datetime, time

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    Time,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    pass


class ParkingRate(Base):
    __tablename__ = "parking_rate"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    rate_type: Mapped[str] = mapped_column(String(32), nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="EUR")
    valid_from: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    valid_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        CheckConstraint("amount >= 0", name="ck_parking_rate_amount_non_negative"),
    )


class ParkingHours(Base):
    __tablename__ = "parking_hours"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    day_of_week: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    open_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    close_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    is_closed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    __table_args__ = (
        UniqueConstraint("day_of_week", name="uq_parking_hours_day"),
        CheckConstraint("day_of_week >= 0 AND day_of_week <= 6", name="ck_day_of_week"),
    )


class ParkingAvailability(Base):
    __tablename__ = "parking_availability"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    total_spaces: Mapped[int] = mapped_column(Integer, nullable=False)
    available_spaces: Mapped[int] = mapped_column(Integer, nullable=False)
    reserved_spaces: Mapped[int] = mapped_column(Integer, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        CheckConstraint("total_spaces > 0", name="ck_total_spaces_positive"),
        CheckConstraint("available_spaces >= 0", name="ck_available_spaces_non_negative"),
        CheckConstraint("reserved_spaces >= 0", name="ck_reserved_spaces_non_negative"),
    )


class ReservationDraft(Base):
    __tablename__ = "reservation_draft"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    session_id: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    first_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    surname: Mapped[str | None] = mapped_column(String(100), nullable=True)
    license_plate: Mapped[str | None] = mapped_column(String(20), nullable=True)
    start_datetime: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    end_datetime: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="draft")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )


class EvaluationRecord(Base):
    __tablename__ = "evaluation_record"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    question: Mapped[str] = mapped_column(Text, nullable=False)
    expected_answer: Mapped[str] = mapped_column(Text, nullable=False)
    relevant_chunk_ids: Mapped[str] = mapped_column(Text, nullable=False)  # JSON string
    retrieved_chunk_ids: Mapped[str] = mapped_column(Text, nullable=False)  # JSON string
    generated_response: Mapped[str | None] = mapped_column(Text, nullable=True)
    recall_at_k: Mapped[float | None] = mapped_column(Float, nullable=True)
    precision_at_k: Mapped[float | None] = mapped_column(Float, nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    model_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    evaluated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
