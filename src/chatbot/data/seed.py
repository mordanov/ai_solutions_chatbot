"""Seed the database with sample data for development and testing."""
from datetime import UTC, datetime, time

from sqlalchemy import select
from sqlalchemy.orm import Session

from chatbot.data.models import ParkingAvailability, ParkingHours, ParkingRate

RATES = [
    ParkingRate(
        rate_type="hourly",
        amount=2.50,
        currency="EUR",
        valid_from=datetime(2024, 1, 1),
        description="Standard hourly rate",
    ),
    ParkingRate(
        rate_type="daily",
        amount=15.00,
        currency="EUR",
        valid_from=datetime(2024, 1, 1),
        description="Full-day rate (24 h)",
    ),
    ParkingRate(
        rate_type="monthly",
        amount=120.00,
        currency="EUR",
        valid_from=datetime(2024, 1, 1),
        description="Monthly subscription",
    ),
    ParkingRate(
        rate_type="overnight",
        amount=8.00,
        currency="EUR",
        valid_from=datetime(2024, 1, 1),
        description="Overnight (22:00–08:00)",
    ),
]

HOURS = [
    ParkingHours(day_of_week=0, open_time=time(6, 0), close_time=time(23, 0)),   # Mon
    ParkingHours(day_of_week=1, open_time=time(6, 0), close_time=time(23, 0)),   # Tue
    ParkingHours(day_of_week=2, open_time=time(6, 0), close_time=time(23, 0)),   # Wed
    ParkingHours(day_of_week=3, open_time=time(6, 0), close_time=time(23, 0)),   # Thu
    ParkingHours(day_of_week=4, open_time=time(6, 0), close_time=time(23, 0)),   # Fri
    ParkingHours(day_of_week=5, open_time=time(7, 0), close_time=time(22, 0)),   # Sat
    ParkingHours(day_of_week=6, open_time=time(8, 0), close_time=time(20, 0)),   # Sun
]


def seed(session: Session) -> None:
    """Insert seed data only if each table is empty — safe to call multiple times."""
    if not session.scalars(select(ParkingRate)).first():
        session.add_all(RATES)

    if not session.scalars(select(ParkingHours)).first():
        session.add_all(HOURS)

    if session.get(ParkingAvailability, 1) is None:
        session.add(
            ParkingAvailability(
                id=1,
                total_spaces=350,
                available_spaces=120,
                reserved_spaces=30,
                updated_at=datetime.now(UTC),
            )
        )

    session.commit()
