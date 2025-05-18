from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from typing import AsyncGenerator
from app.db.database import AsyncSessionLocal
from app.db.models import Ticket, Response  
from app import schemas
from sqlalchemy import select, insert
from app.services.classifier import classify_ticket
from app.db.models import Ticket, Response
from app.services.response_gen import generate_response

router = APIRouter()

# Dependency: get DB session for each request
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session

# Dependency: get DB session for each request
async def draft_and_store_response(ticket_id: int, session_maker):
    async with session_maker() as session:
        ticket = await session.get(Ticket, ticket_id)
        if not ticket:
            return  # Ticket not found, silently exit or log as needed

        try:
            # Generate the AI-powered response
            response_text = await generate_response(
                ticket.subject, ticket.body, ticket.category or "Other"
            )
            status = "completed"
        except Exception as e:
            response_text = f"Response generation failed: {str(e)}"
            status = "failed"
            # Optionally log the traceback or error here

        # Store response in DB
        resp = Response(
            ticket_id=ticket_id,
            generated_response=response_text,
            reviewed=False,
            sent=False,
            status=status
        )
        session.add(resp)
        await session.commit()




async def classify_and_update_ticket(ticket_id: int, session_maker):
    async with session_maker() as session:
        ticket = await session.get(Ticket, ticket_id)
        if ticket is not None:
            category = await classify_ticket(ticket.subject, ticket.body)
            ticket.category = category
            await session.commit()


from fastapi import BackgroundTasks

@router.post("/", status_code=201, response_model=schemas.TicketOut)
async def create_ticket(
    ticket: schemas.TicketIn,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session)
):
    db_ticket = Ticket(**ticket.model_dump())
    session.add(db_ticket)
    await session.commit()
    await session.refresh(db_ticket)

    # Start classifier in background
    background_tasks.add_task(
        classify_and_update_ticket, db_ticket.id, AsyncSessionLocal
    )

    return db_ticket


@router.get("/", response_model=list[schemas.TicketOut])
async def list_tickets(limit: int = 50, offset: int = 0, session: AsyncSession = Depends(get_session)):
    result = await session.execute(
        select(Ticket).offset(offset).limit(limit)
    )
    tickets = result.scalars().all()
    return tickets

@router.get("/{ticket_id}", response_model=schemas.TicketOut)
async def get_ticket(ticket_id: int, session: AsyncSession = Depends(get_session)):
    ticket = await session.get(Ticket, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket

@router.post("/{ticket_id}/respond", status_code=202)
async def respond_to_ticket(
    ticket_id: int,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
):
    # Ensure ticket exists
    ticket = await session.get(Ticket, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found")

    # Schedule the background response generation
    background_tasks.add_task(draft_and_store_response, ticket_id, AsyncSessionLocal)

    return {"detail": "Response is being drafted in the background."}

@router.get("/{ticket_id}/responses", response_model=list[schemas.ResponseOut])
async def get_ticket_responses(ticket_id: int, session: AsyncSession = Depends(get_session)):
    result = await session.execute(
        select(Response).where(Response.ticket_id == ticket_id)
    )
    responses = result.scalars().all()
    return responses

