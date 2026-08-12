"""ReservationWriter — append-only file I/O with POSIX file locking."""
import fcntl
from pathlib import Path


class ReservationWriter:
    def __init__(self, file_path: str) -> None:
        self._file_path = file_path

    def write(self, name: str, car_number: str, reservation_period: str, approval_time: str) -> str:
        """Append one pipe-delimited record. Returns the exact line written."""
        for field, value in [
            ("name", name),
            ("car_number", car_number),
            ("reservation_period", reservation_period),
            ("approval_time", approval_time),
        ]:
            if not value.strip():
                raise ValueError(f"{field} must not be empty")

        name = name.replace(" | ", " / ")
        car_number = car_number.replace(" | ", " / ")
        reservation_period = reservation_period.replace(" | ", " / ")
        approval_time = approval_time.replace(" | ", " / ")

        line = f"{name} | {car_number} | {reservation_period} | {approval_time}"

        Path(self._file_path).parent.mkdir(parents=True, exist_ok=True)
        with open(self._file_path, "a", encoding="utf-8") as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                f.write(line + "\n")
                f.flush()
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)

        return line
