"""Unit tests for MCP server tool handler — called directly without subprocess."""
import asyncio
import pytest

from chatbot.storage.server import write_reservation_record


VALID = {
    "name": "Alice Smith",
    "car_number": "ABC123",
    "reservation_period": "2026-08-15 10:00 → 2026-08-16 10:00",
    "approval_time": "2026-08-12 14:30",
}


def test_valid_call_returns_ok_prefix(tmp_path, monkeypatch):
    monkeypatch.setenv("RESERVATIONS_FILE_PATH", str(tmp_path / "r.txt"))
    result = asyncio.run(write_reservation_record(**VALID))
    assert result.startswith("ok: ")


def test_valid_call_result_contains_all_fields(tmp_path, monkeypatch):
    monkeypatch.setenv("RESERVATIONS_FILE_PATH", str(tmp_path / "r.txt"))
    result = asyncio.run(write_reservation_record(**VALID))
    assert "Alice Smith" in result
    assert "ABC123" in result
    assert "2026-08-15 10:00" in result
    assert "2026-08-12 14:30" in result


def test_empty_name_raises_value_error(tmp_path, monkeypatch):
    monkeypatch.setenv("RESERVATIONS_FILE_PATH", str(tmp_path / "r.txt"))
    with pytest.raises(ValueError, match="name"):
        asyncio.run(write_reservation_record(
            name="  ",
            car_number="ABC123",
            reservation_period="2026-08-15 10:00 → 2026-08-16 10:00",
            approval_time="2026-08-12 14:30",
        ))
