# app/logging_config.py
import logging
from logging.handlers import RotatingFileHandler
from app.db.database import AsyncSessionLocal # Assuming this provides an async session
from app.db.models import Log, LogLevel # LogLevel enum from models.py

class DBHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        # Note: Creating AsyncSessionLocal() here and committing synchronously in emit()
        # is problematic in a fully async app. This needs a proper async logging setup
        # (e.g., queue + dedicated writer task) for production.
        # For now, we're focusing on fixing the TypeError and then the model loading.

    def emit(self, record: logging.LogRecord):
        try:
            # Use the string representation of the log level
            log_level_str = record.levelname

            # Prepare data for the Log model
            log_entry_data = {
                "level": log_level_str,
                "message": record.getMessage(), # Main log message
                "details": {"pathname": record.pathname, "lineno": record.lineno, "funcName": record.funcName},
                # You can add these if you pass them as 'extra' to the logger
                # "ticket_id": getattr(record, 'ticket_id', None), 
                # "event_type": getattr(record, 'event_type', None), 
            }
            
            # --- TEMPORARY: SKIP ACTUAL DB WRITE TO ISOLATE MODEL LOADING ---
            # The actual database write from a logging handler in an async app
            # needs careful implementation to avoid blocking.
            # We'll print to confirm data preparation, then let other handlers work.
            # print(f"DBHandler (SKIPPING DB WRITE FOR NOW): Would log: {log_entry_data}")

            # Example of how it *might* look if it were async-safe (conceptual)
            # async def do_save():
            #     async with AsyncSessionLocal() as session:
            #         async with session.begin():
            #             log_entry = Log(**log_entry_data)
            #             session.add(log_entry)
            # import asyncio
            # try:
            #     loop = asyncio.get_event_loop()
            #     if loop.is_running():
            #         asyncio.create_task(do_save())
            #     else:
            #         # This path is problematic from a sync handler
            #         print("DBHandler: Event loop not running, cannot schedule async log save.")
            # except RuntimeError: # No event loop
            #     print("DBHandler: No event loop, cannot schedule async log save.")
            # --- END TEMPORARY ---

        except Exception as e:
            # print(f"Error in DBHandler during log preparation: {e}") # For debugging the handler itself
            self.handleError(record) # Default error handling

def setup_logging():
    root = logging.getLogger()
    # Set to WARNING to see your custom logs from classifier.py more easily during this test
    root.setLevel(logging.WARNING) 

    # stderr handler
    stderr_handler = logging.StreamHandler()
    # Added funcName and lineno to formatter for more context
    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s [%(name)s:%(funcName)s:%(lineno)d] %(message)s"
    )
    stderr_handler.setFormatter(formatter)
    if not root.hasHandlers() or not any(isinstance(h, logging.StreamHandler) for h in root.handlers):
        root.addHandler(stderr_handler)


    # rotating file (optional - ensure 'logs' directory exists)
    # import os
    # if not os.path.exists("logs"):
    #     os.makedirs("logs")
    # file_handler = RotatingFileHandler("logs/app.log", maxBytes=1e7, backupCount=5)
    # file_handler.setFormatter(formatter)
    # root.addHandler(file_handler)

    # DB handler
    # --- TEMPORARILY COMMENTING OUT DB HANDLER ADDITION ---
    # This is to ensure that any issues with async DB writes from the sync logging path
    # do not interfere with diagnosing the Transformers model loading issue.
    # Once the model loading is stable, this DBHandler's async interaction needs
    # to be properly implemented (e.g., using a queue).
    #
    # db_handler = DBHandler()
    # db_handler.setLevel(logging.WARNING)  # only WARNING+ go to DB
    # root.addHandler(db_handler)
    # --- END TEMPORARY COMMENT ---
