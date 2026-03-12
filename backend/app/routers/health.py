"""
routers/health.py
-----------------
/health endpoint — UptimeRobot ye check karta hai.
DB connection, version, timestamp return karo.
"""
from fastapi import APIRouter
from datetime import datetime, timezone
from app.db.supabase_client import check_db_health
from app.config import get_settings

router = APIRouter()


@router.get("/health")
async def health_check():
    settings = get_settings()
    db_ok = check_db_health()

    return {
        "status":    "healthy" if db_ok else "degraded",
        "app":       settings.app_name,
        "version":   settings.app_version,
        "database":  "connected" if db_ok else "error",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }