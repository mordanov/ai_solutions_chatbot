# Feature Specification: Approved Reservation Storage Service

**Feature Branch**: `003-mcp-reservation-storage`  
**Created**: 2026-08-12  
**Status**: Draft  
**Input**: MCP server integration for writing approved reservation data to persistent storage

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Automatic Record on Approval (Priority: P1)

When the administrator approves a parking reservation, the system automatically records that reservation in persistent storage without any additional manual step. The record captures who was approved, for which vehicle, for what period, and when the decision was made. This gives the parking facility a reliable, human-readable log of all approved reservations.

**Why this priority**: Core business requirement — without this, approved reservations have no durable record outside the in-memory approval store, which is lost on restart.

**Independent Test**: A reservation can be submitted, approved through the admin interface, and then verified to appear in the storage file with all required fields — independently of any other feature.

**Acceptance Scenarios**:

1. **Given** a reservation request is pending admin decision, **When** the administrator approves the reservation, **Then** a new line is appended to the reservations file in the format `Name | Car Number | Reservation Period | Approval Time`.
2. **Given** multiple reservations have been approved at different times, **When** the storage file is read, **Then** all approved reservations are present as separate lines in chronological order.
3. **Given** the storage file does not yet exist, **When** the first reservation is approved, **Then** the system creates the file and writes the first entry successfully.

---

### User Story 2 - Data Completeness and Consistency (Priority: P2)

Each stored record contains complete, unambiguous information: the guest's full name, their vehicle's license plate, the exact reservation window (start and end datetime), and the timestamp of the approval decision. Records are consistently formatted so they can be read, audited, or imported by other tools without custom parsing logic.

**Why this priority**: Incomplete or inconsistently formatted records undermine the value of the log. A record missing the approval time, for example, cannot be used for audit purposes.

**Independent Test**: Approved reservations can be inspected in the storage file; each line contains all four required fields in the prescribed format.

**Acceptance Scenarios**:

1. **Given** a reservation with first name "Alice", surname "Smith", plate "ABC123", period "2026-08-15 10:00 → 2026-08-16 10:00", **When** the reservation is approved at 2026-08-12 14:30, **Then** the stored line reads `Alice Smith | ABC123 | 2026-08-15 10:00 → 2026-08-16 10:00 | 2026-08-12 14:30`.
2. **Given** a rejection decision, **When** the administrator rejects a reservation, **Then** no entry is written to the storage file (only approvals are recorded).

---

### User Story 3 - Secure and Reliable Storage Access (Priority: P3)

The storage service rejects write attempts from any caller that is not the authorized reservation approval system. Unauthorized access attempts are denied and logged. The service remains available even under repeated invalid requests and does not corrupt existing records when write errors occur.

**Why this priority**: Storage integrity is a compliance concern. An open or unprotected write channel would allow anyone to inject fake reservation records.

**Independent Test**: Attempting to write to the storage service without valid authorization credentials results in a rejection; the storage file is unchanged.

**Acceptance Scenarios**:

1. **Given** an unauthorized caller attempts to write a reservation record, **When** the request is received by the storage service, **Then** the service denies the request and the storage file is not modified.
2. **Given** the storage service encounters a write error (e.g., disk full), **When** the error occurs mid-write, **Then** any previously written records remain intact and uncorrupted.
3. **Given** a valid approval is processed while the storage file is temporarily locked by another process, **When** the lock is released, **Then** the record is written successfully without data loss.

---

### Edge Cases

- What happens when the storage destination is read-only or permissions are denied?
- How does the system handle two approvals happening at nearly the same time (concurrent writes)?
- What if the reservation data contains pipe (`|`) characters that could corrupt the fixed delimiter format?
- What happens if the storage file is deleted or moved while the service is running?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST write a record to persistent storage automatically every time an administrator approves a parking reservation.
- **FR-002**: Each stored record MUST contain exactly four fields: full name (first + surname), license plate, reservation period (start and end datetime), and approval timestamp.
- **FR-003**: Records MUST be stored in a pipe-delimited format: `Name | Car Number | Reservation Period | Approval Time`.
- **FR-004**: System MUST append new records to existing storage without overwriting previous entries.
- **FR-005**: System MUST reject write requests from callers that cannot present valid authorization credentials.
- **FR-006**: System MUST NOT write any record for rejected or expired reservations — only approved reservations are stored.
- **FR-007**: System MUST handle write failures gracefully without corrupting previously stored records.
- **FR-008**: The storage service MUST be accessible by the reservation approval workflow as an integrated component.

### Key Entities

- **ApprovedReservationRecord**: Represents one line in the storage file. Attributes: full name (string), license plate (string), reservation period (start datetime + end datetime), approval timestamp (datetime). Uniqueness: no explicit deduplication — each approval event produces exactly one record.
- **StorageFile**: The persistent text file holding all approved reservation records. One file per deployment; append-only.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Every admin approval results in a storage record within 2 seconds of the approval decision being recorded.
- **SC-002**: 100% of approved reservations are present in the storage file after a complete session (zero records dropped).
- **SC-003**: Unauthorized write attempts are rejected 100% of the time; no unauthorized records appear in the storage file.
- **SC-004**: The storage file format is consistent across all entries — any line can be parsed by splitting on ` | ` into exactly four fields.
- **SC-005**: The service remains operational after encountering and recovering from a write error, with no corruption to previous records.

## Assumptions

- The storage destination is a text file on the local filesystem accessible to the service process.
- The service is co-located with (or network-accessible from) the reservation approval workflow.
- Only approved reservations need to be recorded; rejected and expired reservations do not require a durable log.
- The reservation period format uses ISO-like datetime strings (`YYYY-MM-DD HH:MM`) and the `→` separator as shown in the example: `2026-08-15 10:00 → 2026-08-16 10:00`.
- Approval timestamp precision is to the minute (not seconds).
- The storage file path is configurable via environment variable with a sensible default.
- Concurrent access scenarios (two approvals at the same moment) are handled by the service — callers do not need to coordinate writes themselves.
- The authorization mechanism for the storage service reuses existing admin token infrastructure already in place from Stage 2.
