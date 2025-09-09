import os
import asyncio
import logging
import pytest
from sqlalchemy import select

from app.main import app
from app.db.database import AsyncSessionLocal
from app.db.models import Log
from app.logging_config import log_writer


@pytest.mark.asyncio
async def test_logging_queue_inserts_rows():
    os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test.db")
    os.environ.setdefault("APP_MOCK_AI", "1")

    # Start the log writer task
    log_queue = asyncio.Queue()
    log_consumer = asyncio.create_task(log_writer(log_queue))

    logger = logging.getLogger("tests.logging")
    # Clear existing handlers and add a new one with the test queue
    logger.handlers.clear()
    from app.logging_config import AsyncDBQueueHandler

    logger.addHandler(AsyncDBQueueHandler(log_queue))
    logger.setLevel(logging.WARNING)

    logger.warning("Test warning log for DB handler")

    # Wait for the queue to drain
    await log_queue.join()

    # Shutdown the log writer and wait for it to finish
    await log_queue.put(None)
    await log_consumer

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Log).order_by(Log.id.desc()))
        rows = result.scalars().all()
        assert len(rows) >= 1
        assert rows[-1].level in {"WARNING", "ERROR", "INFO", "DEBUG", "CRITICAL"}