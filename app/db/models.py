from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    ForeignKey,
    Boolean,
    DateTime,
    func,
    JSON,
)
from sqlalchemy.orm import declarative_base, relationship
import enum

Base = declarative_base()


class Ticket(Base):
    __tablename__ = "tickets"
    id = Column(Integer, primary_key=True, index=True)
    subject = Column(Text)
    body = Column(Text)
    category = Column(String(50), nullable=True)  # Made nullable
    priority = Column(String(20), nullable=True)  # Made nullable
    language = Column(String(10), nullable=True)  # Made nullable
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    responses = relationship("Response", back_populates="ticket")


class Response(Base):
    __tablename__ = "responses"
    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id"))
    generated_response = Column(Text)
    reviewed = Column(Boolean, default=False)
    sent = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    ticket = relationship("Ticket", back_populates="responses")
    status = Column(String(20), nullable=True)


class LogLevel(str, enum.Enum):  # This enum is fine here or in logging_config.py
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class Log(Base):
    __tablename__ = "logs"
    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id"), nullable=True)
    # 'event_type' can be used for specific, categorized events if you wish.
    # If record.getMessage() is the main content, it goes into 'message'.
    event_type = Column(String(50), nullable=True)
    message = Column(Text)  # For record.getMessage()
    level = Column(String(20))  # For record.levelname
    details = Column(JSON, nullable=True)  # NEW: For structured details
    created_at = Column(DateTime(timezone=True), server_default=func.now())