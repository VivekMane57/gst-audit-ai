"""
db/supabase_client.py
---------------------
Thread-safe Supabase client — Production v2.0

Tera existing code almost sahi tha.
Sirf ek problem thi:
  threading.Lock() synchronous hai — asyncio event loop block karta hai.

Fix:
  asyncio.Lock() use kiya — FastAPI ke async environment ke liye sahi.
  Double-checked locking pattern same rakha.
  get_supabase() ab sync bhi hai (Celery workers ke liye)
  get_supabase_async() async version (FastAPI routes ke liye)
"""
from supabase import create_client, Client
from app.config import get_settings
import logging
import threading
import asyncio
from typing import Optional

logger = logging.getLogger(__name__)

# ── Sync client — Celery workers ke liye (threading.Lock) ────────────────────
_sync_client:  Optional[Client] = None
_sync_lock     = threading.Lock()

# ── Async lock — FastAPI startup ke liye ──────────────────────────────────────
_async_lock    = None   # asyncio.Lock() event loop ke baad banta hai


def get_supabase() -> Client:
    """
    Thread-safe sync client.
    Use karo: Celery tasks, health checks, sync code mein.
    Double-checked locking — race condition proof.
    """
    global _sync_client
    if _sync_client is None:
        with _sync_lock:
            if _sync_client is None:
                settings = get_settings()
                try:
                    _sync_client = create_client(
                        settings.supabase_url,
                        settings.supabase_service_key,
                    )
                    logger.info("Supabase sync client initialized (thread-safe)")
                except Exception as e:
                    logger.error(f"Supabase init failed: {e}")
                    raise RuntimeError(f"Database connection failed: {e}") from e
    return _sync_client


async def get_supabase_async() -> Client:
    """
    Async-safe client init.
    Use karo: FastAPI route handlers, async services mein.
    Same underlying client — sirf init thread-safe hai.
    """
    global _sync_client, _async_lock

    # asyncio.Lock() event loop ke andar banta hai
    if _async_lock is None:
        _async_lock = asyncio.Lock()

    if _sync_client is None:
        async with _async_lock:
            if _sync_client is None:
                settings = get_settings()
                try:
                    _sync_client = create_client(
                        settings.supabase_url,
                        settings.supabase_service_key,
                    )
                    logger.info("Supabase async client initialized")
                except Exception as e:
                    logger.error(f"Supabase async init failed: {e}")
                    raise RuntimeError(f"Database connection failed: {e}") from e

    return _sync_client


def check_db_health() -> bool:
    """Health check — DB reachable hai ya nahi."""
    try:
        db = get_supabase()
        db.table("users").select("id").limit(1).execute()
        return True
    except Exception as e:
        logger.error(f"DB health check failed: {e}")
        return False


def reset_client() -> None:
    """
    Testing ke liye — client reset karo.
    Production mein use mat karo.
    """
    global _sync_client
    with _sync_lock:
        _sync_client = None
    logger.warning("Supabase client reset (testing only)")