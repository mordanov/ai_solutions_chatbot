# Research: Approved Reservation Storage Service

**Branch**: `003-mcp-reservation-storage` | **Date**: 2026-08-12

---

## Decision 1 — MCP Transport: stdio vs SSE/HTTP

**Decision**: Use the official `mcp` Python SDK with **stdio transport**.

**Rationale**: The MCP server runs as a subprocess spawned by the FastAPI process. Communication happens via stdin/stdout — not exposed to any network interface. This means:
- Zero additional Docker services
- No network port to secure or expose
- Process-level isolation: only the spawning process can communicate with the server
- Simpler testability (mock the subprocess or call server handlers directly)

The requirement "secure and resistant to unauthorized access" is fully satisfied: an attacker with no OS-level access to the running API process cannot reach the MCP server at all. The API layer (which spawns the server) already enforces admin-token authentication on the endpoints that trigger writes.

**Alternatives considered**:
- **SSE/HTTP transport** — would require an additional Docker service and explicit bearer-token auth on the MCP endpoint. Adds operational complexity without meaningful security improvement in the same Docker network.
- **`fastmcp` wrapper library** — community package; the official `mcp` SDK is maintained by Anthropic and should be preferred.
- **Open-source file-write MCP server** — none with sufficient maintenance or precise format control for the `Name | Car Number | Reservation Period | Approval Time` requirement.
- **LangChain `@tool` decorator** — would not satisfy the "MCP server" requirement from the spec.

---

## Decision 2 — Integration Point: where does the storage write happen?

**Decision**: The write is triggered in the `approve_reservation` FastAPI endpoint immediately after `ApprovalService().record_decision(request_id, "approved")` succeeds.

**Rationale**:
- The approval endpoint is the single point of truth for when an approval is recorded. Writing the storage record at the same time keeps the two operations atomic (both succeed or both fail visibly).
- The endpoint is `async def`, so the MCP client's async `await` call fits naturally.
- Deferring to the LangGraph `pending_check_node` (when user sends next message) would mean writes happen late and only when the user is active — unacceptable for an audit log.
- The endpoint already has the `request_id`; the full `ApprovalRequest` can be retrieved from `pending_store.get_by_request_id()` before the store entry is mutated.

**Alternatives considered**:
- **`ApprovalService.record_decision`** — good option, but mixing async I/O into a sync service method requires `asyncio.run()` which is fragile inside an async event loop.
- **LangGraph `pending_check_node`** — delayed write (only when user sends next message). Not appropriate for an audit log.
- **Background task** (`FastAPI.BackgroundTasks`) — fires after response is sent; makes test assertions harder and hides write failures.

---

## Decision 3 — File Locking for Concurrent Writes

**Decision**: Use `fcntl.flock` with `LOCK_EX` (exclusive lock) on POSIX systems, wrapped in a context manager. Acquire the lock, append the line, flush, release.

**Rationale**: Reservation approvals are rare events (one per booking). The lock window is microseconds for a single line append. `fcntl` is a stdlib module — no new dependency.

**Alternatives considered**:
- **`filelock` library** — cross-platform but adds a dependency.
- **Atomic rename** — overkill for append-only; doesn't solve concurrent append.
- **No locking** — risk of interleaved writes corrupting a line on simultaneous approvals.

---

## Decision 4 — MCP Server Authentication Strategy

**Decision**: No custom auth token on the MCP tool itself. Security is provided at two levels:
1. **Process isolation** (primary): The server communicates via stdio — only the spawning API process can send messages to it.
2. **API-layer auth** (outer): The `POST /admin/reservation/{id}/approve` endpoint requires `Authorization: Bearer {ADMIN_TOKEN}`. No unauthenticated caller can reach the endpoint that triggers the MCP call.

**Rationale**: Adding a duplicate token check inside the MCP tool would be defense-in-depth that obscures where the trust boundary actually is. The subprocess model means network-based unauthorized access is physically impossible — the right boundary to document and test is the API endpoint.

**Alternatives considered**:
- **Token as tool argument** — non-standard MCP usage; the tool signature becomes polluted with auth concerns.
- **SSE transport with Bearer header** — would expose a network endpoint that needs explicit auth middleware. Justified if the storage server needs to run on a different host; not justified for co-located deployment.

---

## Decision 5 — Exact Line Format

**Decision**: `{first_name} {surname} | {license_plate} | {start_datetime} → {end_datetime} | {approval_time_iso_minute}`

**Rationale**: Matches the specification exactly: `Name | Car Number | Reservation Period | Approval Time`. Approval time uses the same ISO-like format already used throughout the system (`YYYY-MM-DD HH:MM` in UTC+00:00).

**Edge case**: If any field value contains the ` | ` delimiter, that field is sanitized by replacing ` | ` with `/` before formatting. This prevents parser ambiguity while keeping the record human-readable.

---

## New Dependency

| Package | Version constraint | Justification |
|---------|--------------------|---------------|
| `mcp` | `>=1.0,<2.0` | Official Anthropic MCP Python SDK |

No other new packages required. File locking via `fcntl` (stdlib). Async subprocess via `asyncio.create_subprocess_exec` (stdlib).
