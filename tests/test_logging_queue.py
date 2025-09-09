import os
import asyncio
import logging
import pytest
from sqlalchemy import select


@pytest.mark.asyncio
async def test_logging_queue_inserts_rows():
    os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test.db")
    os.environ.setdefault("APP_MOCK_AI", "1")

    from app.main import app
    from app.db.database import AsyncSessionLocal
    from app.db.models import Log

    logger = logging.getLogger("tests.logging")
    logger.warning("Test warning log for DB handler")

    # Wait for queue to drain
    await asyncio.wait_for(app.state.log_queue.join(), timeout=5)

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Log).order_by(Log.id.desc()))
        rows = result.scalars().all()
        assert len(rows) >= 1
        assert rows[-1].level in {"WARNING", "ERROR", "INFO", "DEBUG", "CRITICAL"}

