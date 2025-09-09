import os
import pytest
from httpx import AsyncClient, ASGITransport


@pytest.mark.asyncio
async def test_health_endpoints():
    # Configure to use SQLite and mock AI before importing app
    os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test.db")
    os.environ.setdefault("APP_MOCK_AI", "1")

    from app.main import app  # import after env setup

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.get("/health/")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"
        assert data["db"] in {"up", "down"}

        r2 = await ac.get("/health/ml")
        assert r2.status_code == 200
        ml = r2.json()
        # Ensure backend key present (mock)
        assert "backend" in ml
        assert "gpu_available" in ml
