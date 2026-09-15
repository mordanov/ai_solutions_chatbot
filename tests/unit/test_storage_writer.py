"""Unit tests for ReservationWriter."""
import pytest

from chatbot.storage.writer import ReservationWriter


def test_creates_file_when_not_exists(tmp_path):
    path = tmp_path / "reservations.txt"
    ReservationWriter(str(path)).write(
        "Alice Smith", "ABC123", "2026-08-15 10:00 → 2026-08-16 10:00", "2026-08-12 14:30"
    )
    assert path.exists()


def test_appends_correct_pipe_delimited_line(tmp_path):
    path = tmp_path / "reservations.txt"
    line = ReservationWriter(str(path)).write(
        "Alice Smith", "ABC123", "2026-08-15 10:00 → 2026-08-16 10:00", "2026-08-12 14:30"
    )
    assert line == "Alice Smith | ABC123 | 2026-08-15 10:00 → 2026-08-16 10:00 | 2026-08-12 14:30"
    assert path.read_text() == line + "\n"


def test_sequential_writes_produce_separate_lines(tmp_path):
    path = tmp_path / "reservations.txt"
    w = ReservationWriter(str(path))
    w.write("Alice Smith", "ABC123", "2026-08-15 10:00 → 2026-08-16 10:00", "2026-08-12 14:30")
    w.write("Bob Jones", "XYZ789", "2026-08-16 10:00 → 2026-08-17 10:00", "2026-08-12 15:00")
    lines = path.read_text().strip().splitlines()
    assert len(lines) == 2
    assert "Alice Smith" in lines[0]
    assert "Bob Jones" in lines[1]


def test_returns_exact_written_line(tmp_path):
    path = tmp_path / "reservations.txt"
    returned = ReservationWriter(str(path)).write(
        "Alice Smith", "ABC123", "2026-08-15 10:00 → 2026-08-16 10:00", "2026-08-12 14:30"
    )
    assert returned == path.read_text().splitlines()[0]


def test_pipe_in_name_sanitized(tmp_path):
    path = tmp_path / "reservations.txt"
    line = ReservationWriter(str(path)).write(
        "Alice | Smith", "ABC123", "2026-08-15 10:00 → 2026-08-16 10:00", "2026-08-12 14:30"
    )
    assert " | " not in line.split(" | ")[0]
    assert line.split(" | ")[0] == "Alice / Smith"


def test_empty_name_raises_value_error(tmp_path):
    path = tmp_path / "reservations.txt"
    with pytest.raises(ValueError, match="name"):
        ReservationWriter(str(path)).write(
            "  ", "ABC123", "2026-08-15 10:00 → 2026-08-16 10:00", "2026-08-12 14:30"
        )
