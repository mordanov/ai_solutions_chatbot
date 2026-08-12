# Stage 3 & 4 Retrospective

**Branches**: `002-admin-approval` → `003-mcp-reservation-storage`  
**Date**: 2026-08-12  
**Workflow**: speckit (specify → plan → tasks → implement)

---

## What Was Done

### Stage 3 — Human-in-the-Loop Admin Approval (branch `002-admin-approval`)

| Component | File(s) | Description |
|-----------|---------|-------------|
| Approval data model | `approval/models.py` | `ApprovalRequest`, `ApprovalDecision`, `ApprovalStatus` |
| In-memory store | `approval/store.py` | `PendingStore` with session + request-id indexes |
| SMTP notifier | `approval/notifier.py` | Sends approval-request email to admin via SMTP |
| Approval service | `approval/service.py` | `record_decision()`, expiry check |
| LangGraph nodes | `workflow/nodes.py` | `pending_check_node` + `approval_request_node` |
| Guard-rails fix | `workflow/nodes.py` | PII bypass now handles `approval_request_id` path correctly |
| Admin API | `api/main.py` | `POST /approve`, `POST /reject`, `GET /pending` |
| Marp presentation | `specs/002-admin-approval/presentation.md` | 12-slide deck for stakeholder demo |
| Summary doc | `specs/002-admin-approval/summary.md` | Implementation summary |
| Unit tests | `tests/unit/` | 57 tests passing on completion |

### Stage 4 — MCP Reservation Storage (branch `003-mcp-reservation-storage`)

| Component | File(s) | Description |
|-----------|---------|-------------|
| Config | `config.py` | `reservations_file_path` setting via `RESERVATIONS_FILE_PATH` |
| Writer | `storage/writer.py` | `ReservationWriter`: append + `fcntl.LOCK_EX` + pipe sanitization + validation |
| MCP server | `storage/server.py` | `MCPServer` with `@server.tool()` decorator; runnable as `python -m chatbot.storage.server` |
| MCP client | `storage/client.py` | `ReservationStorageClient`: spawns subprocess per call via stdio transport |
| API integration | `api/main.py` | `approve_reservation` calls storage client after `record_decision`; failure is non-fatal |
| Tests | `tests/unit/test_storage_*.py` | 14 new tests (writer ×6, server ×3, client ×3, api ×2) |
| README | `README.md` | Stage 4 section, `storage/` in project structure, `RESERVATIONS_FILE_PATH` documented |
| .gitignore | `.gitignore` | `data/reservations.txt` excluded |
| .env.example | `.env.example` | `RESERVATIONS_FILE_PATH=data/reservations.txt` added |
| Total tests | — | **71 passing** (up from 57) |

---

## What Was NOT Done

| Item | Reason | Impact |
|------|--------|--------|
| No integration test (subprocess + real file write) | Unit tests mock the MCP session; no test spawns the actual subprocess | End-to-end flow is not automatically verified; `quickstart.md` covers it manually |
| No retry on storage failure | Deferred by design — approval is not rolled back, failure is only logged | A missed approval record requires manual recovery |
| No deduplication of records | MCP server is idempotent from the file side — duplicate calls write duplicate lines | Caller must ensure single-call semantics |
| No persistent MCP server process | Fresh subprocess per write; kept simple for low-write-frequency use case | ~200 ms startup overhead per approval; not suitable if throughput increases |
| T016 README update (partial) | Stage 4 section and `RESERVATIONS_FILE_PATH` added; demo walkthrough for Stage 4 not written inline (covered in `quickstart.md`) | Quickstart is the authoritative E2E guide |

---

## What Was Good

**speckit workflow discipline.** The full specify → plan → research → data-model → contracts → tasks → implement cycle caught the mcp v1 vs v2 API mismatch *before* writing any source code. Having `contracts/mcp-tool-contract.md` gave a clear, reviewable target before a single line was written.

**TDD test structure.** Writing tests that call the tool function directly (not via subprocess) was the right tradeoff: fast, deterministic, no process-spawn overhead. The discovery that `@server.tool()` preserves the original function as a callable made this possible with zero framework overhead.

**Non-fatal storage writes.** Decoupling the approval decision from the storage write was the correct architecture. A failed file write does not roll back an approval — the user still gets their chat notification and the admin's decision is recorded in the in-memory store. This avoids a two-phase-commit problem with no corresponding benefit at this scale.

**Tight module boundaries.** `writer.py` has no MCP dependency; `server.py` has no direct file I/O; `client.py` has no business logic. Each module is independently testable. The `approve_reservation` endpoint composes them at the top.

**Autouse mock for storage client.** Adding the autouse fixture to `test_approval_api.py` was the right call — it prevents the existing 5 API tests from trying to spawn a subprocess, and it's opt-in for the new T015 tests that verify the call arguments.

---

## What Was Bad

**mcp v1 in `requirements.txt` vs v2 installed.** The research phase documented `mcp>=1.0,<2.0` but the installed package was 2.0.0 with a completely different API (`Server` vs `MCPServer`, `@server.list_tools()` vs `@server.tool()`, `stdio_server()` context manager vs `run_stdio_async()`). This was caught before writing code, but it left the plan.md with misleading v1 pseudocode. The final `requirements.txt` specifies `mcp>=2.0,<3.0`.

**tasks.md generated with all items pre-marked `[X]`.** The `speckit-tasks` skill wrote all 18 tasks as completed by mistake. A `sed` one-liner fixed it but this was an invisible error — the tasks looked done before anything was implemented. Caught immediately on inspection.

**No `PYTHONPATH` for the MCP subprocess.** The `chatbot` package is not installed in the project venv (`pip install -e .` was never run). The subprocess spawned by `StdioServerParameters` cannot import `chatbot.storage.server` unless either (a) the package is installed, or (b) `PYTHONPATH` is set in the subprocess environment. This means the real E2E path (not mocked) requires a proper install. This is fine for Docker deployment but is a hidden requirement for local dev.

**Context window compaction mid-implementation.** The previous context ran out at the exact moment implementation was about to start (after all investigation was complete). The summary was accurate but forced a cold restart with no ability to carry over intermediate findings naturally.

---

## What Could Be Done Better

**Pass `PYTHONPATH` to the subprocess explicitly.**  
`StdioServerParameters` accepts an `env` dict. The client could inject `PYTHONPATH=src:$PYTHONPATH` (or the absolute path to `src/`) so the subprocess can import `chatbot` without requiring an editable install. This would make local dev work without `pip install -e .`.

```python
import sys, os
params = StdioServerParameters(
    command=sys.executable,  # use the same venv Python, not bare "python"
    args=["-m", "chatbot.storage.server"],
    env={**os.environ, "PYTHONPATH": ":".join(sys.path)},
)
```

Using `sys.executable` also ensures the subprocess uses the same virtual-environment Python, not a system `python`.

**Write one real integration test.**  
A single `@pytest.mark.integration` test in `tests/integration/` that actually spawns the subprocess and verifies a line appears in a `tmp_path` file would validate the full stack. Right now the integration path is only covered by the manual `quickstart.md` walkthrough.

**Persist the MCP server process.**  
For higher approval throughput, the client could maintain a long-lived subprocess (open once, keep stdin/stdout open across calls). The current per-call subprocess is clean but adds ~200 ms per approval. A connection-pool pattern (one server process, reused across calls) would eliminate this overhead.

**Validate `approval_time` format in `ReservationWriter`.**  
The writer validates non-empty but does not check that `approval_time` matches `YYYY-MM-DD HH:MM`. A malformed timestamp would silently produce an unparseable line. A regex or `datetime.strptime` check would catch this at the boundary.

**Return the written line in `ReservationStorageClient`.**  
The client returns `None`; the written line (echoed back in the `ok: {line}` response) is discarded. Returning it would give the API endpoint something to log (`logger.info("Stored: %s", line)`) rather than relying solely on error paths.
