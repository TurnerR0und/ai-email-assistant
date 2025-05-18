# app/db/models.py

from sqlalchemy import Column, Integer, String, Text, ForeignKey, Boolean, DateTime, func
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class Ticket(Base):
    __tablename__ = "tickets"
    id = Column(Integer, primary_key=True, index=True)
    subject = Column(Text)
    body = Column(Text)
    category = Column(String(50))
    priority = Column(String(20))
    language = Column(String(10))
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

class Log(Base):
    __tablename__ = "logs"
    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id"), nullable=True)
    event_type = Column(String(50))
    message = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
