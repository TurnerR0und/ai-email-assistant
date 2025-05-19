# app/db/database.py

import os
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Load .env for local development if DATABASE_URL is not set,
# but environment variables from Docker Compose will take precedence.
load_dotenv()

# Prioritize DATABASE_URL from the environment (which is set by Docker Compose)
DATABASE_URL_ENV = os.getenv("DATABASE_URL")

if DATABASE_URL_ENV:
    DATABASE_URL = DATABASE_URL_ENV
else:
    # Fallback to constructing from individual parts
    # (useful for local development without Docker or if DATABASE_URL is not set)
    DB_USER = os.getenv("POSTGRES_USER")
    DB_PASSWORD = os.getenv("POSTGRES_PASSWORD")
    DB_HOST = os.getenv("POSTGRES_HOST", "localhost") # For non-Docker, this might be localhost
    DB_PORT = os.getenv("POSTGRES_PORT", "5432")
    DB_NAME = os.getenv("POSTGRES_DB")

    if not all([DB_USER, DB_PASSWORD, DB_HOST, DB_NAME]):
        raise ValueError("Database connection details are not fully configured. "
                         "Set DATABASE_URL or POSTGRES_USER, POSTGRES_PASSWORD, "
                         "POSTGRES_HOST, POSTGRES_DB environment variables.")

    DATABASE_URL = (
        f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    )

engine = create_async_engine(DATABASE_URL, echo=True) # Set echo=False in production
AsyncSessionLocal = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)