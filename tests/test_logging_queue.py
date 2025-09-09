import asyncio
import logging
import pytest
from sqlalchemy import select

from app.db.database import AsyncSessionLocal
from app.db.models import Log
from app.logging_config import log_writer, AsyncDBQueueHandler


@pytest.mark.asyncio
async def test_logging_queue_inserts_rows():
    # The os.environ calls are no longer needed here

    # Start the log writer task
    log_queue = asyncio.Queue()
    log_consumer = asyncio.create_task(log_writer(log_queue))

    logger = logging.getLogger("tests.logging")
    # Clear existing handlers and add a new one with the test queue
    if logger.hasHandlers():
        logger.handlers.clear()
    logger.addHandler(AsyncDBQueueHandler(log_queue))
    logger.setLevel(logging.WARNING)

    logger.warning("Test warning log for DB handler")

    # Wait for the queue to process the item
    await log_queue.join()

    # Shutdown the log writer and wait for it to finish
    await log_queue.put(None)
    await log_consumer

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Log).order_by(Log.id.desc()))
        rows = result.scalars().all()
        assert len(rows) >= 1
        assert rows[-1].level in {"WARNING", "ERROR", "INFO", "DEBUG", "CRITICAL"}