# app/routers/tickets.py
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from typing import AsyncGenerator # Ensure this is imported if not already
from app.db.database import AsyncSessionLocal
from app.db.models import Ticket, Response  
from app import schemas
from sqlalchemy import select # Ensure select is imported
from app.services.classifier import classify_ticket, get_model_info
from app.services.response_gen import generate_response
import logging # Added for logging
import traceback # Added for full traceback
import time
from opentelemetry import trace

logger = logging.getLogger(__name__)
router = APIRouter()

async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session

async def draft_and_store_response(ticket_id: int, session_maker):
    logger.warning(f"Background task 'draft_and_store_response' started for ticket_id: {ticket_id}")
    async with session_maker() as session:
        try:
            ticket = await session.get(Ticket, ticket_id)
            if not ticket:
                logger.error(f"Ticket {ticket_id} not found in background task 'draft_and_store_response'.")
                return

            logger.warning(f"Generating OpenAI response for ticket {ticket_id} - Subject: {ticket.subject[:30]}...")
            # Pass the category if it's available, otherwise "Other" or None.
            # The classification task might not have completed yet.
            # generate_response should handle a None category if necessary.
            category_for_response = ticket.category if ticket.category else "Other"
            response_text = await generate_response(
                ticket.subject, ticket.body, category_for_response
            )
            
            if "Error:" in response_text: # Check if generate_response itself returned an error string
                current_status = "failed"
                logger.error(f"Response generation for ticket {ticket_id} indicated failure: {response_text}")
            else:
                current_status = "completed"
                logger.warning(f"Response generation for ticket {ticket_id} completed.")

        except Exception as e:
            logger.error(f"EXCEPTION in draft_and_store_response for ticket {ticket_id}: {e}")
            traceback.print_exc() 
            response_text = f"Response generation failed due to an unexpected error: {str(e)}"
            current_status = "failed"
        
        logger.warning(f"Attempting to store response for ticket {ticket_id} with status: {current_status}")
        try:
            resp = Response(
                ticket_id=ticket_id,
                generated_response=response_text,
                reviewed=False,
                sent=False,
                status=current_status
            )
            session.add(resp)
            await session.commit()
            await session.refresh(resp)
            logger.warning(f"Response for ticket {ticket_id} stored successfully with ID: {resp.id}")
        except Exception as e_db:
            logger.error(f"EXCEPTION storing response for ticket {ticket_id} to DB: {e_db}")
            traceback.print_exc()
            await session.rollback()


async def classify_and_update_ticket(ticket_id: int, session_maker):
    logger.warning(f"Background task 'classify_and_update_ticket' started for ticket_id: {ticket_id}")
    async with session_maker() as session:
        try:
            ticket = await session.get(Ticket, ticket_id)
            if ticket is not None:
                logger.warning(f"Classifying ticket {ticket_id} - Subject: {ticket.subject[:30]}...")
                category = await classify_ticket(ticket.subject, ticket.body)
                # setattr avoids Pylance Column typing confusion
                setattr(ticket, "category", category)
                await session.commit()
                logger.warning(f"Ticket {ticket_id} category updated to: {category}")
            else:
                logger.error(f"Ticket {ticket_id} not found in classify_and_update_ticket task.")
        except Exception as e:
            logger.error(f"EXCEPTION in classify_and_update_ticket for ticket {ticket_id}: {e}")
            traceback.print_exc()
            await session.rollback()


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=schemas.TicketOut)
async def create_ticket(
    ticket_in: schemas.TicketIn,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session)
):
    logger.warning(f"Creating ticket with subject: {ticket_in.subject[:30]}...")
    db_ticket = Ticket(**ticket_in.model_dump())
    session.add(db_ticket)
    try:
        await session.commit()
    except Exception as e:
        # On first run in certain CI flows, tables may not be initialized yet.
        # Attempt to initialize schema and retry once.
        from sqlalchemy.exc import OperationalError
        if isinstance(e, OperationalError) and "no such table" in str(e).lower():
            await session.rollback()
            try:
                from app.db.database import engine
                from app.db.models import Base
                async with engine.begin() as conn:
                    await conn.run_sync(Base.metadata.create_all)
                session.add(db_ticket)
                await session.commit()
            except Exception:
                await session.rollback()
                raise
        else:
            await session.rollback()
            raise
    await session.refresh(db_ticket)
    logger.warning(f"Ticket {db_ticket.id} created. Classifying and scheduling background tasks.")

    # Classify synchronously to capture span attributes and set category immediately
    tracer = trace.get_tracer(__name__)
    info = get_model_info()
    start = time.perf_counter()
    label = "Unknown"
    try:
        label = await classify_ticket(ticket_in.subject, ticket_in.body)
        setattr(db_ticket, "category", label)
        await session.commit()
    finally:
        latency_ms = int((time.perf_counter() - start) * 1000)
        with tracer.start_as_current_span("tickets.create") as span:
            span.set_attribute("classifier.backend", info.get("backend", "unknown"))
            span.set_attribute("classifier.model", info.get("model", "unknown"))
            span.set_attribute("classifier.device", info.get("device", "cpu"))
            span.set_attribute("latency_ms", latency_ms)
            span.set_attribute("label", label)
    
    # Start response generation in background, in parallel
    background_tasks.add_task(
        draft_and_store_response, db_ticket.id, AsyncSessionLocal # <<<--- THIS LINE IS ADDED/ENSURED
    )

    return db_ticket


@router.get("/", response_model=list[schemas.TicketOut])
async def list_tickets(limit: int = 50, offset: int = 0, session: AsyncSession = Depends(get_session)):
    result = await session.execute(
        select(Ticket).order_by(Ticket.id.desc()).offset(offset).limit(limit) # Added order_by
    )
    tickets = result.scalars().all()
    return tickets

@router.get("/{ticket_id}", response_model=schemas.TicketOut)
async def get_ticket(ticket_id: int, session: AsyncSession = Depends(get_session)):
    ticket = await session.get(Ticket, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")
    return ticket

# This endpoint can still be useful for manually re-triggering a response if needed,
# or if you decide to remove automatic generation from create_ticket later.
@router.post("/{ticket_id}/respond", status_code=status.HTTP_202_ACCEPTED)
async def respond_to_ticket(
    ticket_id: int,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
):
    logger.warning(f"Received request to MANUALLY respond to ticket_id: {ticket_id}")
    ticket = await session.get(Ticket, ticket_id)
    if ticket is None:
        logger.error(f"Manual respond request: Ticket {ticket_id} not found.")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")

    logger.warning(f"Scheduling 'draft_and_store_response' for ticket {ticket_id} (manual trigger).")
    background_tasks.add_task(draft_and_store_response, ticket_id, AsyncSessionLocal)

    return {"message": "Response generation has been re-initiated in the background."}

@router.get("/{ticket_id}/responses", response_model=list[schemas.ResponseOut])
async def get_ticket_responses(ticket_id: int, session: AsyncSession = Depends(get_session)):
    result = await session.execute(
        select(Response).where(Response.ticket_id == ticket_id).order_by(Response.created_at.desc()) # Added order_by
    )
    responses = result.scalars().all()
    return responses
