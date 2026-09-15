"""Unit tests for ReservationStorageClient — MCP session mocked."""
import asyncio
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from chatbot.storage.client import ReservationStorageClient

VALID = {
    "name": "Alice Smith",
    "car_number": "ABC123",
    "reservation_period": "2026-08-15 10:00 → 2026-08-16 10:00",
    "approval_time": "2026-08-12 14:30",
}


@asynccontextmanager
async def _fake_stdio(*args, **kwargs):
    yield (MagicMock(), MagicMock())


def _session_mock(is_error=False, text="ok: line"):
    session = AsyncMock()
    result = MagicMock()
    result.is_error = is_error
    result.content = [MagicMock(text=text)]
    session.call_tool = AsyncMock(return_value=result)
    session.initialize = AsyncMock()
    return session


def _run(session, **kwargs):
    with patch("chatbot.storage.client.stdio_client", _fake_stdio):
        with patch("chatbot.storage.client.ClientSession") as MockCS:
            MockCS.return_value.__aenter__ = AsyncMock(return_value=session)
            MockCS.return_value.__aexit__ = AsyncMock(return_value=False)
            asyncio.run(ReservationStorageClient().write_record(**kwargs))
    return session


def test_client_calls_correct_tool_with_args():
    session = _run(_session_mock(), **VALID)
    session.call_tool.assert_called_once_with(
        "write_reservation_record",
        {
            "name": "Alice Smith",
            "car_number": "ABC123",
            "reservation_period": "2026-08-15 10:00 → 2026-08-16 10:00",
            "approval_time": "2026-08-12 14:30",
        },
    )


def test_is_error_response_raises_runtime_error():
    session = _session_mock(is_error=True, text="error: name must not be empty")
    with pytest.raises(RuntimeError, match="MCP storage error"):
        _run(session, **VALID)


def test_client_passes_all_field_values_unchanged():
    session = _run(_session_mock(), **VALID)
    passed = session.call_tool.call_args[0][1]
    assert passed["name"] == "Alice Smith"
    assert passed["car_number"] == "ABC123"
    assert passed["reservation_period"] == "2026-08-15 10:00 → 2026-08-16 10:00"
    assert passed["approval_time"] == "2026-08-12 14:30"
