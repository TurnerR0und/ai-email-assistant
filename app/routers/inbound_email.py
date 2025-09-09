# In app/routers/inbound_email.py

import hashlib
import hmac
import os
from typing import List, Optional

from fastapi import (APIRouter, BackgroundTasks, Depends, Header, HTTPException,
                     Request, status)
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import AsyncSessionLocal
from app.db.models import Ticket
from app.routers.tickets import draft_and_store_response
from app.schemas import TicketOut

# --- ADDED IMPORTS ---
from app.services.classifier import classify_ticket


router = APIRouter()


# Pydantic models for the incoming email payload
class Attachment(BaseModel):
    filename: Optional[str] = None
    contentType: Optional[str] = None
    data: Optional[str] = None


class EmailPayload(BaseModel):
    to: str
    from_: str = Field(..., alias='from')
    subject: str
    date: str
    text: str
    html: Optional[str] = None
    attachments: List[Attachment] = []


async def get_session() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session


# Dependency to verify the HMAC signature
async def verify_signature(request: Request, x_signature: str = Header(...)):
    shared_secret = os.getenv("CLOUDFLARE_WORKER_SHARED_SECRET")
    if not shared_secret:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="CLOUDFLARE_WORKER_SHARED_SECRET is not set",
        )

    body = await request.body()
    expected_signature = hmac.new(
        shared_secret.encode(), body, hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(expected_signature, x_signature):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid signature"
        )


@router.post(
    "/inbound",
    status_code=status.HTTP_201_CREATED,
    response_model=TicketOut,
    dependencies=[Depends(verify_signature)],
)
async def receive_inbound_email(
    payload: EmailPayload,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
):
    """
    Receives an inbound email from the Cloudflare worker, verifies the signature,
    and creates a new ticket.
    """
    ticket_in = {"subject": payload.subject, "body": payload.text}
    db_ticket = Ticket(**ticket_in)
    session.add(db_ticket)
    await session.commit()
    await session.refresh(db_ticket)

    # --- ADDED CLASSIFICATION LOGIC ---
    # Classify the ticket synchronously and save the category
    try:
        category = await classify_ticket(db_ticket.subject, db_ticket.body)
        db_ticket.category = category
        await session.commit()
        await session.refresh(db_ticket)
    except Exception as e:
        # If classification fails, log it but don't crash the request
        print(f"Error during classification for ticket {db_ticket.id}: {e}")
    # --- END OF ADDED LOGIC ---


    # Start response generation in the background
    background_tasks.add_task(
        draft_and_store_response, db_ticket.id, AsyncSessionLocal
    )

    return db_ticket