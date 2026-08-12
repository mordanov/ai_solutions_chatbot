# Tasks: Approved Reservation Storage Service

**Input**: Design documents from `specs/003-mcp-reservation-storage/`  
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅, quickstart.md ✅

**Organization**: Tasks are grouped by user story to enable independent implementation and testing.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Add MCP dependency and configuration before any story work begins.

- [X] T001 Add `mcp>=1.0,<2.0` to `requirements.txt`
- [X] T002 [P] Create `src/chatbot/storage/__init__.py` (empty package marker)
- [X] T003 [P] Add `reservations_file_path: str = "data/reservations.txt"` setting to `src/chatbot/config.py`
- [X] T004 [P] Add `RESERVATIONS_FILE_PATH=data/reservations.txt` entry to `.env.example`

---

## Phase 2: Foundational (Blocking Prerequisite)

**Purpose**: `ReservationWriter` is the core I/O unit shared by all user stories. Must exist before MCP server, client, or API integration.

**⚠️ CRITICAL**: Phases 3–5 cannot begin until T005 is complete.

- [X] T005 Implement `ReservationWriter` class in `src/chatbot/storage/writer.py` with `__init__(self, file_path: str)` and `write(self, name: str, car_number: str, reservation_period: str, approval_time: str) -> str`; opens file in append mode, creates parent dirs if needed; uses `fcntl.flock(LOCK_EX)` for exclusive write lock; flushes before releasing; returns the exact line written

**Checkpoint**: `ReservationWriter` usable — all story phases can now proceed.

---

## Phase 3: User Story 1 — Automatic Record on Approval (Priority: P1) 🎯 MVP

**Goal**: When admin approves a reservation via the API, the record is automatically written to the storage file.

**Independent Test**: Call `POST /admin/reservation/{id}/approve` with a valid request → verify `data/reservations.txt` contains a new line with the approved reservation data.

### Tests for User Story 1

- [X] T006 [P] [US1] Write 4 unit tests for `ReservationWriter` in `tests/unit/test_storage_writer.py`: (1) creates file when not exists, (2) appends correct pipe-delimited line, (3) sequential writes produce separate lines in order, (4) returns the exact written line string

### Implementation for User Story 1

- [X] T007 [P] [US1] Implement MCP server in `src/chatbot/storage/server.py`: create `mcp.server.Server("reservation-storage")`, register `list_tools()` returning one `Tool(name="write_reservation_record", ...)`, register `call_tool()` handler that reads `RESERVATIONS_FILE_PATH` env var and delegates to `ReservationWriter.write()`; add `async def main()` using `stdio_server()` context manager; add `if __name__ == "__main__": asyncio.run(main())`
- [X] T008 [US1] Implement `ReservationStorageClient` in `src/chatbot/storage/client.py` with `async def write_record(self, name, car_number, reservation_period, approval_time) -> None`; uses `StdioServerParameters(command="python", args=["-m", "chatbot.storage.server"])`, spawns subprocess via `stdio_client`, opens `ClientSession`, calls `initialize()` then `call_tool("write_reservation_record", {...})`; raises `RuntimeError` if result has `isError: true` (depends on T007)
- [X] T009 [US1] Integrate storage client into `approve_reservation` endpoint in `src/chatbot/api/main.py`: after `ApprovalService().record_decision(request_id, "approved")` succeeds, retrieve `req` from store, format `approval_time = datetime.now(UTC).strftime("%Y-%m-%d %H:%M")` and `period = f"{req.start_datetime} → {req.end_datetime}"`, then `await ReservationStorageClient().write_record(name=f"{req.first_name} {req.surname}", car_number=req.license_plate, reservation_period=period, approval_time=approval_time)`; wrap in try/except and `logger.error(...)` on failure but do NOT rollback the approval (depends on T008)

**Checkpoint**: US1 complete — approve via API, storage file gets a new line. Test with `quickstart.md` steps 3–4.

---

## Phase 4: User Story 2 — Data Completeness and Consistency (Priority: P2)

**Goal**: Each stored record contains all four fields in the correct format; pipe characters in field values don't corrupt the line.

**Independent Test**: Approve a reservation where the guest name contains ` | `; verify the storage line still has exactly 4 pipe-delimited parts.

### Tests for User Story 2

- [X] T010 [P] [US2] Write 3 unit tests for MCP server tool handlers in `tests/unit/test_storage_server.py` (call handlers directly, no subprocess): (1) `call_tool("write_reservation_record", valid_args)` returns `isError: false` and `text` starting with `"ok: "`; (2) result text contains all four field values; (3) unknown tool name returns `isError: true`

### Implementation for User Story 2

- [X] T011 [US2] Add pipe sanitization and empty-field validation to `ReservationWriter.write()` in `src/chatbot/storage/writer.py`: replace ` | ` with ` / ` in each of the four input fields before formatting; raise `ValueError` if any field is empty after strip (depends on T005)
- [X] T012 [US2] Add empty-field validation to `call_tool` handler in `src/chatbot/storage/server.py`: catch `ValueError` from `ReservationWriter.write()` and return `[TextContent(type="text", text=f"error: {exc}")]` with `isError=True` instead of propagating; add try/except for all other exceptions too (depends on T007)

**Checkpoint**: US2 complete — format is always consistent; pipe-in-name doesn't corrupt lines.

---

## Phase 5: User Story 3 — Secure and Reliable Storage Access (Priority: P3)

**Goal**: Unauthorized write attempts are rejected; write errors don't corrupt existing records or silently swallow failures.

**Independent Test**: Call `ReservationStorageClient.write_record()` with an empty `name`; verify `RuntimeError` is raised; verify the storage file is unchanged.

### Tests for User Story 3

- [X] T013 [P] [US3] Write 3 unit tests for `ReservationStorageClient` in `tests/unit/test_storage_client.py` using `unittest.mock.AsyncMock` to mock `ClientSession.call_tool`: (1) successful call passes correct args to `call_tool`; (2) response with `isError: true` raises `RuntimeError`; (3) client passes all four field values through unchanged

### Implementation for User Story 3

- [X] T014 [US3] Add `isError: true` propagation in `ReservationStorageClient.write_record()` in `src/chatbot/storage/client.py`: after `session.call_tool(...)`, check `result.isError`; if true, extract error text from `result.content[0].text` and raise `RuntimeError(f"MCP storage error: {text}")`; also raise `RuntimeError` on any transport or protocol exception (depends on T008)
- [X] T015 [US3] Add additional API-level test coverage in `tests/unit/test_approval_api.py`: (1) `test_approve_endpoint_calls_storage_client` — mock `ReservationStorageClient.write_record` and verify it is called with correct name/car_number/period/approval_time after a 204 response; (2) `test_approve_endpoint_storage_failure_still_returns_204` — mock client to raise `RuntimeError`, verify endpoint still returns 204 and approval is recorded in store (depends on T009)

**Checkpoint**: US3 complete — errors are visible and propagated; the approve endpoint is resilient to storage failures.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Documentation, final test run, and `.gitignore` hygiene.

- [X] T016 [P] Update `README.md` to document: MCP storage service (`src/chatbot/storage/`), `RESERVATIONS_FILE_PATH` env var, format of `data/reservations.txt`, how the storage fits in the approval flow
- [X] T017 [P] Add `data/reservations.txt` to `.gitignore` (storage file is runtime data, not source)
- [X] T018 Run full unit test suite with `pytest tests/unit/ -q` and verify all tests pass (≥ 69 total); fix any failures before marking complete

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — T002, T003, T004 are parallel; T001 must complete before T008 installs
- **Foundational (Phase 2)**: T005 depends on T001–T004 — **BLOCKS all user story phases**
- **US1 (Phase 3)**: T006–T009 depend on T005
  - T006 and T007 can start in parallel after T005
  - T008 depends on T007
  - T009 depends on T008
- **US2 (Phase 4)**: T010–T012 depend on Phase 3 completion
  - T010 and T011 can start in parallel after T005 (T010 tests T007's handler; T011 modifies T005)
  - T012 depends on T007 and T011
- **US3 (Phase 5)**: T013–T015 depend on Phase 4 completion
  - T013 can start in parallel after T008 (tests the client)
  - T014 depends on T008
  - T015 depends on T009 and T014
- **Polish (Phase 6)**: Depends on all user story phases complete

### User Story Dependencies

- **US1 (P1)**: Depends only on Foundational — standalone MVP
- **US2 (P2)**: Depends on US1 (modifies writer and server from US1)
- **US3 (P3)**: Depends on US2 (hardens what US2 adds)

### Parallel Opportunities

- T002, T003, T004 (setup) — all parallel
- T006, T007 (US1 test + server impl) — parallel after T005
- T010, T011 (US2 test + writer validation) — parallel after T005
- T013 (US3 client tests) — parallel after T008
- T016, T017 (polish) — parallel

---

## Parallel Example: User Story 1

```bash
# After T005 (ReservationWriter) is done, start these in parallel:
Task T006: Write tests/unit/test_storage_writer.py (4 tests)
Task T007: Implement src/chatbot/storage/server.py (MCP server)
# Then sequentially:
Task T008: Implement src/chatbot/storage/client.py (depends on T007)
Task T009: Wire into src/chatbot/api/main.py (depends on T008)
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001–T004)
2. Complete Phase 2: Foundational (T005)
3. Complete Phase 3: US1 (T006–T009)
4. **STOP and VALIDATE**: Follow `quickstart.md` steps 1–4; verify a line appears in `data/reservations.txt` after an approval
5. The storage feature is end-to-end usable after just US1

### Incremental Delivery

1. After US1: Every admin approval is recorded (basic audit log)
2. After US2: Records are guaranteed to be consistently formatted and parseable
3. After US3: Storage errors are visible to callers and resilient to bad input

---

## Notes

- The MCP server (`server.py`) must be runnable as a module: `python -m chatbot.storage.server`
- Use `pytest-asyncio` (already in the test environment) for async client tests
- The `fcntl` module is POSIX-only; this is acceptable for the Linux Docker deployment target
- Do NOT add a separate Docker service for the MCP server — stdio transport means it runs as a subprocess of the FastAPI process
- Storage write failures are intentionally non-fatal for the approval flow: the user still gets their chat notification
