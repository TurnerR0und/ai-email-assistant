from pydantic import BaseModel, ConfigDict
from datetime import datetime


class TicketIn(BaseModel):
    subject: str
    body: str
    # Add more fields if your Ticket model has them


class TicketOut(TicketIn):
    id: int
    category: str | None

    model_config = ConfigDict(from_attributes=True)


class ResponseOut(BaseModel):
    id: int
    ticket_id: int
    generated_response: str
    reviewed: bool
    sent: bool
    status: str | None
    created_at: datetime  # from typing import datetime

    model_config = ConfigDict(from_attributes=True)