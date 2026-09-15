"""MCP server — exposes write_reservation_record tool via stdio."""
import asyncio
import os

from mcp.server.mcpserver import MCPServer

server = MCPServer("reservation-storage")


@server.tool()
async def write_reservation_record(
    name: str,
    car_number: str,
    reservation_period: str,
    approval_time: str,
) -> str:
    """Write an approved reservation record to the storage file."""
    from chatbot.config import settings
    from chatbot.storage.writer import ReservationWriter

    file_path = os.environ.get("RESERVATIONS_FILE_PATH", settings.reservations_file_path)
    writer = ReservationWriter(file_path)
    line = writer.write(
        name=name,
        car_number=car_number,
        reservation_period=reservation_period,
        approval_time=approval_time,
    )
    return f"ok: {line}"


if __name__ == "__main__":
    asyncio.run(server.run_stdio_async())
