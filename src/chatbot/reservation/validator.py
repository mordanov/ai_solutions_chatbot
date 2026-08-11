"""Field-level validation for reservation drafts."""
import re
from datetime import datetime

from chatbot.reservation.models import ReservationDraft

_PLATE_RE = re.compile(r"^[A-Z0-9]{2,10}$")
_DT_FORMATS = ["%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M", "%d/%m/%Y %H:%M", "%d.%m.%Y %H:%M"]


def _parse_dt(value: str) -> datetime | None:
    for fmt in _DT_FORMATS:
        try:
            return datetime.strptime(value.strip(), fmt)
        except ValueError:
            continue
    return None


def validate_reservation(draft: ReservationDraft) -> list[str]:
    """Return a list of human-readable error/missing-field messages.

    An empty list means the draft is fully valid and ready to submit.
    """
    errors: list[str] = []

    if not draft.first_name or not draft.first_name.strip():
        errors.append("first name is missing")
    if not draft.surname or not draft.surname.strip():
        errors.append("surname is missing")
    if not draft.license_plate:
        errors.append("licence plate is missing")
    elif not _PLATE_RE.match(draft.license_plate.upper().replace("-", "").replace(" ", "")):
        errors.append(f"licence plate '{draft.license_plate}' is not valid (use letters and digits only)")

    start_dt = end_dt = None
    if not draft.start_datetime:
        errors.append("start date/time is missing")
    else:
        start_dt = _parse_dt(draft.start_datetime)
        if start_dt is None:
            errors.append("start date/time format is not recognised (use YYYY-MM-DD HH:MM)")

    if not draft.end_datetime:
        errors.append("end date/time is missing")
    else:
        end_dt = _parse_dt(draft.end_datetime)
        if end_dt is None:
            errors.append("end date/time format is not recognised (use YYYY-MM-DD HH:MM)")

    if start_dt and end_dt and end_dt <= start_dt:
        errors.append("end date/time must be after start date/time")

    return errors
