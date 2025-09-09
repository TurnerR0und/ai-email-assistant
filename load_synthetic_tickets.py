# load_synthetic_tickets.py  (minimal skeleton)
import asyncio
import json
import argparse
import pathlib
import aiofiles
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import Ticket
from app.db.database import AsyncSessionLocal


 # your helpers

async def load_chunk(session: AsyncSession, rows):
    session.add_all([Ticket(**row) for row in rows])
    await session.commit()

async def main(path: pathlib.Path, chunk: int = 200):
    async with AsyncSessionLocal() as session:
        buf = []
        async with aiofiles.open(path) as f:
            async for line in f:
                buf.append(json.loads(line))
                if len(buf) == chunk:
                    await load_chunk(session, buf)
                    buf.clear()
        if buf:
            await load_chunk(session, buf)

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--file", required=True)
    p.add_argument("--chunk", type=int, default=200)
    args = p.parse_args()
    asyncio.run(main(pathlib.Path(args.file), args.chunk))
