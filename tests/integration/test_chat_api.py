"""Integration tests for the FastAPI chat endpoint — require the full stack."""
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.integration


@pytest.fixture
async def client():
    from chatbot.api.main import app

    async with AsyncClient(app=app, base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_health_returns_ok(client):
    """GET /health returns status ok."""
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_chat_returns_response(client):
    """POST /chat with a valid question returns 200 with a non-empty response."""
    resp = await client.post(
        "/chat", json={"message": "Where is the parking located?"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "response" in data
    assert len(data["response"]) > 0
    assert "session_id" in data
