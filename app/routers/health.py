from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.database import engine

router = APIRouter()


@router.get("", description="Health check")
async def health():
    from datetime import datetime
    return {"status": "ok", "version": "1.0.0", "uptime_seconds": 0, "timestamp": datetime.utcnow().isoformat()}


@router.get("/ready", description="Readiness check")
async def ready():
    try:
        async with engine.connect() as conn:
            await conn.execute("SELECT 1")
        return {"status": "ready", "database": "connected"}
    except Exception:
        return JSONResponse(status_code=503, content={"status": "not ready", "database": "unreachable"})
