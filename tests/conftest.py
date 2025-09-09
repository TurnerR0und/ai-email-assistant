import os
import sys
import asyncio
import pytest
from pathlib import Path

# Add project root to sys.path so 'import app' works
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# --- Environment Setup ---
# Set default environment variables for all tests
os.environ.setdefault("APP_MOCK_AI", "1")
os.environ.setdefault("DISABLE_OTEL", "1")
# Use an in-memory SQLite database for tests. This is faster and ensures
# that each test run starts with a clean, empty database.
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")


# --- Pytest Asyncio and Event Loop Setup ---
@pytest.fixture(scope="session")
def event_loop():
    """
    Creates a new asyncio event loop for the entire test session,
    preventing interference between tests.
    """
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# --- Database Fixture ---
@pytest.fixture(scope="session", autouse=True)
async def setup_database(event_loop):
    """
    An auto-running, session-scoped fixture that creates all database tables
    once before any tests run, and drops them all after all tests have completed.
    This is the definitive fix for the 'no such table' error.
    """
    from app.db.database import engine
    from app.db.models import Base

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Allow the tests to run
    yield

    # Drop all tables after the test session is over
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)