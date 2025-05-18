from fastapi import FastAPI
from app.routers import tickets  # Import as a package

app = FastAPI()
app.include_router(tickets.router, prefix="/tickets", tags=["tickets"])
