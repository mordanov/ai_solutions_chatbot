# Stage 3 — Retrospective Summary

**Project**: CityPark Intelligent Parking Chatbot  
**Feature**: MCP Reservation Storage Service  
**Branch**: `003-mcp-reservation-storage`  
**Date**: 2026-08-12  
**Tasks**: T001–T018 (18 tasks, all completed)  
**Tests added**: 14 → total unit test count: 71

---

## What Was Done

### New package: `src/chatbot/storage/`

| Module | Responsibility |
|--------|---------------|
| `writer.py` | `ReservationWriter.write()` — appends one pipe-delimited record to a text file; uses `fcntl.LOCK_EX` for exclusive write lock; sanitizes ` \| ` → ` / ` in all fields; raises `ValueError` on empty fields; creates parent directories if needed; returns the exact line written. |
| `server.py` | MCP server using `MCPServer` from `mcp.server.mcpserver`. Exposes a single tool `write_reservation_record` via `@server.tool()` decorator. Reads `RESERVATIONS_FILE_PATH` from environment and delegates to `ReservationWriter`. Entry point: `python -m chatbot.storage.server`. |
| `client.py` | `ReservationStorageClient.write_record()` — spawns the MCP server as a subprocess via `StdioServerParameters` + `stdio_client` + `ClientSession`; calls `write_reservation_record`; raises `RuntimeError` if the server returns `is_error=True` or if transport fails. |

### Integration

- `src/chatbot/api/main.py` — `approve_reservation` endpoint now retrieves the full `ApprovalRequest` from `pending_store` before calling `record_decision`, then calls `ReservationStorageClient().write_record(...)`. Storage failure is non-fatal: logged via `logger.error`, approval is not rolled back.
- `src/chatbot/config.py` — added `reservations_file_path: str = "data/reservations.txt"` (overridable via `RESERVATIONS_FILE_PATH`).
- `.env.example` — added `RESERVATIONS_FILE_PATH=data/reservations.txt`.
- `requirements.txt` — added `mcp>=2.0,<3.0`; bumped `uvicorn[standard]` to `>=0.31.1` (mcp 2.0.0 requires it).
- `docker-compose.yml` — replaced `mailhog/mailhog:v1.0.1` with `axllent/mailpit:latest` (MailHog has no ARM64 image; Mailpit is a maintained drop-in replacement).
- `.gitignore` — added `data/reservations.txt` (runtime data, not source).

### Tests (14 new, across 4 files)

| File | Count | What it covers |
|------|-------|---------------|
| `test_storage_writer.py` | 6 | creates file on first write; correct pipe-delimited format; sequential writes produce separate lines; returns exact written line; pipe in name sanitized to `/`; empty name raises `ValueError` |
| `test_storage_server.py` | 3 | tool handler returns string starting with `"ok: "`; result contains all four field values; empty name raises `ValueError` (tool function called directly, no subprocess) |
| `test_storage_client.py` | 3 | client calls correct tool with all four args; `is_error=True` response raises `RuntimeError`; all field values pass through unchanged (MCP session mocked) |
| `test_approval_api.py` | +2 | approve endpoint calls storage client with correct args; storage `RuntimeError` does not change 204 response |

Also added an `autouse` mock fixture to `test_approval_api.py` so the existing 5 API tests do not attempt to spawn a real subprocess.

### Documentation

- `README.md` — updated stage count to 1–4; added `storage/` to project structure diagram; added `RESERVATIONS_FILE_PATH` to env var table; added Stage 4 section with storage format, architecture, and failure-handling notes.
- `docs/stage_3/summary.md` — this file.

---

## What Was Not Done

- **No integration test** — all tests mock the MCP session or call the tool function directly. No test spawns the actual `python -m chatbot.storage.server` subprocess and verifies a line is written to a real file. The manual E2E path is documented in `specs/003-mcp-reservation-storage/quickstart.md`.
- **`pip install -e .` not enforced** — the package is not installed in editable mode. The subprocess spawned by `ReservationStorageClient` cannot import `chatbot` unless `pip install -e .` is run or `PYTHONPATH` is set explicitly. The Docker image handles this correctly (package is installed at build time), but local dev requires the extra step.
- **No retry on storage failure** — a missed record requires manual recovery. The approval decision is durable in the in-process store; the file is the audit log.
- **No persistent server process** — a fresh subprocess is spawned per approval call. This is acceptable for the expected write frequency (~1–10 per day) but would not scale to high throughput.

---

## What Went Well

**mcp v2 API discovered before writing code.** The speckit research phase (`research.md`) was planned for mcp v1 API. Before implementation, the actual installed package (v2.0.0) was inspected directly and the API differences were confirmed: `MCPServer` vs `Server`, `@server.tool()` vs `@server.list_tools()` + `@server.call_tool()`, `run_stdio_async()` vs `stdio_server()` context manager. No code was written to the wrong API.

**`@server.tool()` preserves the original function.** In mcp v2, the decorator registers the tool with the server and leaves the original async function callable directly. This made unit testing trivial: `asyncio.run(write_reservation_record(...))` returns the raw string with no subprocess or MCP protocol involved. No mocking of the MCP layer was needed for the server tests.

**Non-fatal storage design.** The approval decision is recorded in the in-process store before the MCP call. If the file write fails, the chat user still receives their notification (the `pending_check_node` reads from the store, not the file). This avoids a two-phase-commit problem with no real benefit at this scale.

**Autouse mock kept existing API tests intact.** Adding `ReservationStorageClient` to the approve endpoint would have silently broken the existing 5 API tests (they would try to spawn a subprocess). The autouse fixture was added in the same commit as the endpoint change, so the tests never had a broken state.

**ARM64 incompatibility caught and fixed.** The `mailhog/mailhog` image warning was a real runtime issue on Apple Silicon and ARM CI runners. Replacing it with `axllent/mailpit` (same ports, same SMTP interface, actively maintained) resolved it without any application config changes.

---

## What Could Be Done Better

**Pass `sys.executable` and `PYTHONPATH` in `StdioServerParameters`.** The subprocess should use the same venv Python as the parent and be able to import `chatbot` without requiring an editable install:

```python
import sys, os
StdioServerParameters(
    command=sys.executable,
    args=["-m", "chatbot.storage.server"],
    env={**os.environ, "PYTHONPATH": "src"},
)
```

Using `"python"` as the command works in Docker (where the package is installed) but not in a bare virtualenv without `pip install -e .`.

**One real integration test.** A single `@pytest.mark.integration` test that spawns the actual subprocess and asserts a line appears in a `tmp_path` file would give confidence that the full stack works. Right now the mocked unit tests verify the logic but not the subprocess plumbing.

**Return the written line from `ReservationStorageClient`.** The MCP response includes `"ok: {line}"` but the client discards it and returns `None`. Returning the line would allow the API to log `"Stored: Alice Smith | ABC123 | ..."` rather than only logging on failure.

**Validate `approval_time` format in `ReservationWriter`.** The writer validates non-empty but not the `YYYY-MM-DD HH:MM` format. A malformed timestamp (e.g., from a future refactor of the endpoint) would produce an unparseable line silently.

**`mcp-tool-contract.md` uses `isError` (camelCase).** The contract document was written for mcp v1. The actual mcp v2 field is `is_error` (snake_case). The contract was not updated after the API discovery.

---

## Key Numbers

| Metric | Value |
|--------|-------|
| Tasks completed | 18 / 18 |
| Unit tests added | 14 |
| Unit tests (total) | 71 |
| New source files | 4 (`writer.py`, `server.py`, `client.py`, `__init__.py`) |
| Modified source files | 5 (`config.py`, `api/main.py`, `requirements.txt`, `.env.example`, `docker-compose.yml`) |
| New external dependencies | 1 (`mcp>=2.0,<3.0`) |
| Storage format | `Name \| Car Number \| Reservation Period \| Approval Time` |
| Lines added (approx.) | ~120 src + ~130 tests |
