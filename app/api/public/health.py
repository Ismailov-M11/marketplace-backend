from fastapi import APIRouter
from sqlalchemy import text

from app.api.deps import DB

router = APIRouter()


@router.get("/health")
async def health(db: DB):
    await db.execute(text("SELECT 1"))
    return {"status": "ok", "database": "ok"}
