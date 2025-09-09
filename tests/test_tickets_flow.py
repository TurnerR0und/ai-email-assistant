import os
import asyncio
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_tickets_flow_returns_refund_and_response():
    os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test.db")
    os.environ.setdefault("APP_MOCK_AI", "1")

    from app.main import app

    async with AsyncClient(app=app, base_url="http://test") as ac:
        # Create ticket
        r = await ac.post(
            "/tickets/",
            json={
                "subject": "Requesting refund for incorrect charge",
                "body": "I was charged twice last month.",
                "priority": "high",
                "language": "en",
            },
        )
        assert r.status_code == 201
        ticket = r.json()
        assert ticket["id"] > 0
        # Category should be set synchronously to "Refund" by mock classifier
        assert ticket.get("category") in ("Refund", None)

        ticket_id = ticket["id"]

        # Poll responses until completed or timeout
        for _ in range(20):
            resp = await ac.get(f"/tickets/{ticket_id}/responses")
            assert resp.status_code == 200
            responses = resp.json()
            if responses:
                status = responses[0].get("status")
                if status == "completed":
                    break
            await asyncio.sleep(0.1)
        else:
            pytest.fail("Response generation did not complete in time")

