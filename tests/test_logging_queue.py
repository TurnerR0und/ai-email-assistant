import asyncio
import logging
import pytest
from sqlalchemy import select

from app.db.database import AsyncSessionLocal
from app.db.models import Log
from app.logging_config import log_writer, AsyncDBQueueHandler


@pytest.mark.asyncio
async def test_logging_queue_inserts_rows():
    # Start the log writer task to consume from the queue
    log_queue = asyncio.Queue()
    log_consumer = asyncio.create_task(log_writer(log_queue))

    # Configure a logger to use our async handler
    logger = logging.getLogger("tests.logging_integration")
    if logger.hasHandlers():
        logger.handlers.clear()
    logger.addHandler(AsyncDBQueueHandler(log_queue))
    logger.setLevel(logging.WARNING)

    # --- Act ---
    # Emit a log message
    logger.warning("Test warning log for DB handler")

    # Wait for the async log_writer to process the item from the queue
    await log_queue.join()

    # --- Assert ---
    # Gracefully shut down the log writer
    await log_queue.put(None)
    await log_consumer

    # Check that the log was actually written to the database
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Log).order_by(Log.id.desc()))
        rows = result.scalars().all()
        assert len(rows) >= 1
        assert rows[0].level == "WARNING"
        assert "Test warning log for DB handler" in rows[0].message