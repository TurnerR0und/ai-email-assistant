"""Logging configuration with async DB sink.

This module installs standard stderr logging and an optional async DB writer
that consumes records from an asyncio.Queue to avoid blocking the event loop.
"""

import logging
import asyncio
from logging.handlers import RotatingFileHandler
from typing import Optional

from app.db.database import AsyncSessionLocal
from app.db.models import Log
from prometheus_client import Gauge


class AsyncDBQueueHandler(logging.Handler):
    """Non-blocking handler that pushes log records to an asyncio.Queue."""

    def __init__(self, queue: asyncio.Queue):
        super().__init__()
        self.queue = queue

    def emit(self, record: logging.LogRecord):
        try:
            payload = {
                "level": record.levelname,
                "message": record.getMessage(),
                "details": {
                    "pathname": record.pathname,
                    "lineno": record.lineno,
                    "funcName": record.funcName,
                    "module": record.module,
                    "name": record.name,
                },
            }
            # Optional extras if present
            for key in ("ticket_id", "event_type"):
                if hasattr(record, key):
                    payload[key] = getattr(record, key)
            # Try put_nowait; drop on full queue to avoid backpressure
            self.queue.put_nowait(payload)
        except Exception:
            self.handleError(record)


LOG_QUEUE_DEPTH = Gauge(
    "log_queue_depth",
    "Depth of the async log queue"
)


async def log_writer(queue: asyncio.Queue):
    """Async consumer that persists log records to the DB."""
    while True:
        item = await queue.get()
        if item is None:  # shutdown sentinel
            try:
                LOG_QUEUE_DEPTH.set(0)
            except Exception:
                pass
            queue.task_done()
            break
        try:
            async with AsyncSessionLocal() as session:
                session.add(Log(**item))
                await session.commit()
        except Exception:
            # Intentionally avoid logging here to prevent recursion loops
            pass
        finally:
            try:
                LOG_QUEUE_DEPTH.set(queue.qsize())
            except Exception:
                pass
            queue.task_done()


def setup_logging(queue: Optional[asyncio.Queue] = None) -> None:
    root = logging.getLogger()
    root.setLevel(logging.WARNING)

    # stderr handler
    stderr_handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s [%(name)s:%(funcName)s:%(lineno)d] %(message)s"
    )
    stderr_handler.setFormatter(formatter)
    if not any(isinstance(h, logging.StreamHandler) for h in root.handlers):
        root.addHandler(stderr_handler)

    # optional rotating file example (kept commented)
    # file_handler = RotatingFileHandler("logs/app.log", maxBytes=10_000_000, backupCount=5)
    # file_handler.setFormatter(formatter)
    # root.addHandler(file_handler)

    # Async DB sink via queue
    if queue is not None and not any(isinstance(h, AsyncDBQueueHandler) for h in root.handlers):
        db_handler = AsyncDBQueueHandler(queue)
        db_handler.setLevel(logging.WARNING)
        root.addHandler(db_handler)

__all__ = ["setup_logging", "log_writer", "AsyncDBQueueHandler"]
