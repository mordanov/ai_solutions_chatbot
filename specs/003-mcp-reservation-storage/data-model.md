# Data Model: Approved Reservation Storage Service

**Branch**: `003-mcp-reservation-storage` | **Date**: 2026-08-12

---

## Entities

### ReservationRecord

Represents one approved reservation as stored in the text file. This is a value object — it is never updated once written; corrections are recorded as new entries.

| Field | Type | Source | Constraints |
|-------|------|---------|-------------|
| `name` | `str` | `ApprovalRequest.first_name + " " + ApprovalRequest.surname` | Non-empty; any contained ` \| ` replaced with ` / ` |
| `car_number` | `str` | `ApprovalRequest.license_plate` | Non-empty; ` \| ` → ` / ` |
| `reservation_period` | `str` | `"{start_datetime} → {end_datetime}"` | Formatted from `ApprovalRequest` fields |
| `approval_time` | `str` | UTC datetime at point of `record_decision` call | `YYYY-MM-DD HH:MM` format |

**Serialized line format** (written to file):
```
{name} | {car_number} | {reservation_period} | {approval_time}
```

**Example**:
```
Alice Smith | ABC123 | 2026-08-15 10:00 → 2026-08-16 10:00 | 2026-08-12 14:30
```

---

### StorageFile

The persistent text file holding all approved reservation records.

| Property | Value |
|----------|-------|
| Encoding | UTF-8 |
| Line ending | `\n` (LF) |
| Mode | Append-only; records are never deleted or modified |
| Path | Configurable via `RESERVATIONS_FILE_PATH` env var; default `data/reservations.txt` |
| Created by | Storage service on first write (if file does not exist) |

---

## Data Flow

```
Admin POSTs /approve
       │
       ▼
pending_store.get_by_request_id(request_id)   ← retrieve full ApprovalRequest
       │
       ▼
ApprovalService.record_decision("approved")   ← mutate pending store
       │
       ▼
ReservationStorageClient.write_record(...)    ← async MCP tool call
       │
       ▼
MCP server subprocess
       │
       ▼
ReservationWriter.write(record)               ← fcntl lock → append → flush
       │
       ▼
StorageFile (data/reservations.txt)
```

---

## Relationships to Existing Entities

| This entity | Existing entity | Relationship |
|-------------|-----------------|-------------|
| `ReservationRecord` | `ApprovalRequest` (`approval/models.py`) | Derived from; shares `first_name`, `surname`, `license_plate`, `start_datetime`, `end_datetime` |
| `StorageFile` | filesystem | Owned by the storage service; no DB table |

`ReservationRecord` is a write-once projection of the approved `ApprovalRequest`. There is no back-reference from the file to the request ID intentionally — the file is a human-readable audit log, not a queryable database.

---

## State Transitions

The storage service is stateless from the perspective of the calling API. Each write is independent:

```
write_record(record) → OK  (line appended)
                    → ERROR (file not writable, disk full, etc.) — exception propagates to caller
```

There is no retry or queuing logic. If a write fails, the caller (API endpoint) receives an HTTP 500 error. The pending store entry is still recorded (approval is not rolled back), ensuring the chat user still receives their notification.

---

## Validation Rules

| Rule | Check | Where enforced |
|------|-------|----------------|
| `name` non-empty | `len(name.strip()) > 0` | `ReservationWriter` |
| `car_number` non-empty | `len(car_number.strip()) > 0` | `ReservationWriter` |
| `reservation_period` non-empty | `len(reservation_period.strip()) > 0` | `ReservationWriter` |
| `approval_time` non-empty | `len(approval_time.strip()) > 0` | `ReservationWriter` |
| Pipe sanitization | Replace ` \| ` with ` / ` in all fields | `ReservationWriter` |
