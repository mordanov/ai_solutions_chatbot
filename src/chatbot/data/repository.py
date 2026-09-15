from datetime import datetime

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from chatbot.data.models import Base, ParkingAvailability, ParkingHours, ParkingRate


class ParkingRepository:
    def __init__(self, database_url: str) -> None:
        self._engine = create_engine(database_url)

    def create_tables(self) -> None:
        Base.metadata.create_all(self._engine)

    # --- Rates ---

    def get_active_rates(self) -> list[ParkingRate]:
        with Session(self._engine) as session:
            stmt = select(ParkingRate).where(ParkingRate.valid_until.is_(None))
            return list(session.scalars(stmt).all())

    def get_rate_by_type(self, rate_type: str) -> ParkingRate | None:
        with Session(self._engine) as session:
            stmt = (
                select(ParkingRate)
                .where(ParkingRate.rate_type == rate_type)
                .where(ParkingRate.valid_until.is_(None))
            )
            return session.scalars(stmt).first()

    # --- Hours ---

    def get_hours_for_day(self, day_of_week: int) -> ParkingHours | None:
        with Session(self._engine) as session:
            stmt = select(ParkingHours).where(ParkingHours.day_of_week == day_of_week)
            return session.scalars(stmt).first()

    def get_all_hours(self) -> list[ParkingHours]:
        with Session(self._engine) as session:
            stmt = select(ParkingHours).order_by(ParkingHours.day_of_week)
            return list(session.scalars(stmt).all())

    # --- Availability ---

    def get_availability(self) -> ParkingAvailability | None:
        with Session(self._engine) as session:
            return session.get(ParkingAvailability, 1)

    def upsert_availability(
        self, total: int, available: int, reserved: int
    ) -> ParkingAvailability:
        with Session(self._engine) as session:
            record = session.get(ParkingAvailability, 1)
            if record is None:
                record = ParkingAvailability(id=1)
                session.add(record)
            record.total_spaces = total
            record.available_spaces = available
            record.reserved_spaces = reserved
            record.updated_at = datetime.utcnow()
            session.commit()
            session.refresh(record)
            return record
