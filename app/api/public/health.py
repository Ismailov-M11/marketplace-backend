from fastapi import APIRouter
from sqlalchemy import text

from app.api.deps import DB

router = APIRouter()


@router.get("/health")
async def health():
    """Basic liveness check — no DB required. Used by Railway healthcheck."""
    return {"status": "ok"}


@router.get("/health/db")
async def health_db(db: DB):
    """Deep health check including DB connection."""
    await db.execute(text("SELECT 1"))
    return {"status": "ok", "database": "ok"}
