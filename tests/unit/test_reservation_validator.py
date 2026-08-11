"""Unit tests for reservation field validation."""
import pytest

from chatbot.reservation.models import ReservationDraft
from chatbot.reservation.validator import validate_reservation


def _full_draft(**overrides) -> ReservationDraft:
    base = dict(
        first_name="Alice",
        surname="Smith",
        license_plate="AB1234",
        start_datetime="2026-09-01 10:00",
        end_datetime="2026-09-01 14:00",
    )
    base.update(overrides)
    return ReservationDraft(**base)


def test_valid_draft_has_no_errors():
    assert validate_reservation(_full_draft()) == []


def test_invalid_license_plate_rejected():
    errors = validate_reservation(_full_draft(license_plate="!@#$"))
    assert any("licence plate" in e for e in errors)


def test_valid_alphanumeric_plate_accepted():
    assert validate_reservation(_full_draft(license_plate="XY9876")) == []


def test_end_before_start_raises_error():
    errors = validate_reservation(
        _full_draft(start_datetime="2026-09-01 14:00", end_datetime="2026-09-01 10:00")
    )
    assert any("end" in e and "after" in e for e in errors)


def test_missing_fields_accumulate():
    draft = ReservationDraft()
    errors = validate_reservation(draft)
    field_names = ["first name", "surname", "licence plate", "start", "end"]
    for name in field_names:
        assert any(name in e for e in errors), f"Expected error for '{name}' in {errors}"
