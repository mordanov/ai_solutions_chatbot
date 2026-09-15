# MCP Tool Contract: Reservation Storage Server

**Server name**: `reservation-storage`  
**Transport**: stdio (spawned as subprocess)  
**Protocol**: MCP 1.0 (JSON-RPC 2.0)  
**Date**: 2026-08-12

---

## Tools Exposed

### `write_reservation_record`

Appends one approved reservation record to the storage file. Idempotent from the file's perspective (calling twice with the same data writes two lines — callers are responsible for avoiding duplicate calls).

#### Input Schema

```json
{
  "type": "object",
  "properties": {
    "name":                { "type": "string", "description": "Guest full name (first + surname)" },
    "car_number":          { "type": "string", "description": "Vehicle license plate number" },
    "reservation_period":  { "type": "string", "description": "Formatted period: 'YYYY-MM-DD HH:MM → YYYY-MM-DD HH:MM'" },
    "approval_time":       { "type": "string", "description": "UTC approval timestamp: 'YYYY-MM-DD HH:MM'" }
  },
  "required": ["name", "car_number", "reservation_period", "approval_time"]
}
```

#### Success Response

```json
{
  "content": [
    {
      "type": "text",
      "text": "ok: Alice Smith | ABC123 | 2026-08-15 10:00 → 2026-08-16 10:00 | 2026-08-12 14:30"
    }
  ],
  "isError": false
}
```

The `text` field contains `"ok: "` followed by the exact line written to the file.

#### Error Response

```json
{
  "content": [
    {
      "type": "text",
      "text": "error: <human-readable message>"
    }
  ],
  "isError": true
}
```

Error cases:
- `error: name must not be empty`
- `error: car_number must not be empty`
- `error: reservation_period must not be empty`
- `error: approval_time must not be empty`
- `error: write failed: <OS error message>`

---

## Server Lifecycle

**Start**: The server is launched by the client via `asyncio.create_subprocess_exec("python", "-m", "chatbot.storage.server")`. It reads from stdin and writes to stdout using the MCP stdio protocol.

**Initialization**: The client sends `initialize` → server responds with capabilities. The server advertises `tools: [write_reservation_record]`.

**Shutdown**: The server exits when stdin is closed (client disconnects).

**Reconnect**: A new subprocess is spawned for each write operation. The server process is not kept alive between calls. This ensures clean state and avoids zombie processes. For the low write-frequency of reservation approvals, the subprocess startup overhead (< 200ms) is acceptable.

---

## Configuration

The server reads the following environment variables at startup:

| Variable | Default | Description |
|----------|---------|-------------|
| `RESERVATIONS_FILE_PATH` | `data/reservations.txt` | Absolute or relative path to the storage file |

The file is created if it does not exist. The parent directory must already exist.

---

## Security Model

- **Network exposure**: None. Communication is strictly via stdin/stdout of a child process.
- **Caller trust**: The server trusts any message received via stdin. Caller authentication is the responsibility of the process that spawns the server (the FastAPI application, which already enforces admin-token auth on the approve endpoint).
- **File access**: The storage file is only writable by the server process. The file path is set via environment variable — it cannot be overridden by tool arguments.
- **Input sanitization**: All string fields have ` | ` replaced with ` / ` before being written to prevent line-parsing ambiguity.

---

## Testing Contract

A contract test MUST verify:

1. Calling `write_reservation_record` with valid inputs returns `isError: false` and a response whose `text` starts with `"ok: "`.
2. The written line matches the format `{name} | {car_number} | {reservation_period} | {approval_time}`.
3. Calling with an empty `name` returns `isError: true` with a message containing `"name"`.
4. Two sequential calls produce two separate lines in the file.
