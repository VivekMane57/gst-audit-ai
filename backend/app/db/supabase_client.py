"""
supabase_client.py
------------------
Supabase connection — singleton pattern.
Service role key use karo — RLS bypass hoti hai server-side.
User isolation Python code mein enforce karo (user_id filter).
"""
from supabase import create_client, Client
from app.config import get_settings
import logging

logger = logging.getLogger(__name__)

_client: Client | None = None


def get_supabase() -> Client:
    """
    Singleton Supabase client.
    Har request pe naya client nahi banta — performance ke liye.
    """
    global _client
    if _client is None:
        settings = get_settings()
        try:
            _client = create_client(
                settings.supabase_url,
                settings.supabase_service_key,   # service role — backend only
            )
            logger.info("Supabase client initialized")
        except Exception as e:
            logger.error(f"Supabase init failed: {e}")
            raise RuntimeError(f"Database connection failed: {e}") from e
    return _client


def check_db_health() -> bool:
    """Health check — returns True if DB is reachable."""
    try:
        db = get_supabase()
        db.table("users").select("id").limit(1).execute()
        return True
    except Exception as e:
        logger.error(f"DB health check failed: {e}")
        return False