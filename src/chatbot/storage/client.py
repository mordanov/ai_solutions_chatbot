"""ReservationStorageClient — spawns the MCP server subprocess per write call."""
import logging

from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

logger = logging.getLogger(__name__)


class ReservationStorageClient:
    async def write_record(
        self,
        name: str,
        car_number: str,
        reservation_period: str,
        approval_time: str,
    ) -> None:
        """Call write_reservation_record via MCP stdio transport. Raises RuntimeError on failure."""
        params = StdioServerParameters(
            command="python",
            args=["-m", "chatbot.storage.server"],
        )
        try:
            async with stdio_client(params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    result = await session.call_tool(
                        "write_reservation_record",
                        {
                            "name": name,
                            "car_number": car_number,
                            "reservation_period": reservation_period,
                            "approval_time": approval_time,
                        },
                    )
        except RuntimeError:
            raise
        except Exception as exc:
            raise RuntimeError(f"MCP storage client error: {exc}") from exc

        if result.is_error:
            text = result.content[0].text if result.content else "unknown error"
            raise RuntimeError(f"MCP storage error: {text}")
