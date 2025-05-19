# app/logging_config.py
import logging
from logging.handlers import RotatingFileHandler
from app.db.database import AsyncSessionLocal
from app.db.models import Log, LogLevel

class DBHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.session = AsyncSessionLocal()

    def emit(self, record: logging.LogRecord):
        log_entry = Log(
            level=LogLevel(record.levelname),
            event=record.getMessage(),
            details={"pathname": record.pathname, "lineno": record.lineno}
        )
        self.session.add(log_entry)
        self.session.commit()

def setup_logging():
    root = logging.getLogger()
    root.setLevel(logging.INFO)

    # stderr handler
    stderr_handler = logging.StreamHandler()
    stderr_handler.setFormatter(logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s: %(message)s"
    ))
    root.addHandler(stderr_handler)

    # rotating file (optional)
    file_handler = RotatingFileHandler("logs/app.log", maxBytes=1e7, backupCount=5)
    file_handler.setFormatter(stderr_handler.formatter)
    root.addHandler(file_handler)

    # DB handler
    db_handler = DBHandler()
    db_handler.setLevel(logging.WARNING)  # only WARNING+ go to DB
    root.addHandler(db_handler)
