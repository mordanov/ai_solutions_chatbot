"""Unit tests for ParkingRepository using an in-memory SQLite database."""
from datetime import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from chatbot.data.models import Base, ParkingAvailability, ParkingRate
from chatbot.data.repository import ParkingRepository
from chatbot.data.seed import seed


@pytest.fixture
def repo():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        seed(session)
    r = ParkingRepository("sqlite:///:memory:")
    r._engine = engine
    return r


def test_get_active_rates_returns_only_active(repo):
    """get_active_rates() returns only rows where valid_until IS NULL."""
    rates = repo.get_active_rates()
    assert len(rates) > 0
    assert all(r.valid_until is None for r in rates)


def test_get_availability_returns_singleton(repo):
    """get_availability() returns the singleton row with id=1."""
    avail = repo.get_availability()
    assert avail is not None
    assert avail.id == 1
    assert avail.total_spaces == 350
