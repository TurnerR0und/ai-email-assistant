import os
import asyncio
import pytest


@pytest.fixture(scope="session", autouse=True)
def configure_env():
    # Ensure tests use SQLite and mocked AI
    os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test.db")
    os.environ.setdefault("APP_MOCK_AI", "1")
    os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")
    return True


@pytest.fixture(scope="session")
def anyio_backend():
    # httpx/pytest-asyncio interop
    return "asyncio"


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session", autouse=True)
def create_db_schema(configure_env):
    # Create tables once for SQLite
    from app.db.database import engine
    from app.db.models import Base

    async def _create():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    asyncio.get_event_loop().run_until_complete(_create())

