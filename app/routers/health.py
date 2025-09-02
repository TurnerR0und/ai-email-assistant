from fastapi import APIRouter
from sqlalchemy import text
from app.db.database import AsyncSessionLocal

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/")
async def health_root():
    db_status = "down"
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        db_status = "up"
    except Exception:
        db_status = "down"
    return {"status": "ok", "db": db_status}


@router.get("/ml")
async def health_ml():
    gpu = False
    gpu_count = 0
    try:
        import torch  # type: ignore
        gpu = torch.cuda.is_available()
        gpu_count = torch.cuda.device_count() if gpu else 0
    except Exception:
        gpu = False
        gpu_count = 0
    return {"gpu_available": gpu, "gpu_count": gpu_count}

