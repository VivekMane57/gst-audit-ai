"""
utils/auth.py
-------------
Common auth functions — auto-create user if not exists.
Import this in all routers instead of writing get_user_uuid locally.
"""
import uuid
import logging
from fastapi import HTTPException
from app.db.supabase_client import get_supabase

logger = logging.getLogger(__name__)


def get_user_uuid(supabase, clerk_id: str) -> str:
    """
    Clerk ID se UUID lookup karo.
    Agar user nahi mila toh AUTO-CREATE karo.
    """
    try:
        res = (
            supabase.table("users")
            .select("id")
            .eq("clerk_id", clerk_id)
            .limit(1)
            .execute()
        )
        if res.data:
            return res.data[0]["id"]

        # User nahi mila — auto-create
        new_id = str(uuid.uuid4())
        supabase.table("users").insert({
            "id": new_id,
            "clerk_id": clerk_id,
        }).execute()

        logger.info(f"Auto-created user: {clerk_id} → {new_id}")
        return new_id

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"get_user_uuid error: {e}")
        raise HTTPException(status_code=500, detail="User lookup failed")


def require_auth(x_user_id: str | None) -> str:
    """Validate x_user_id header exists."""
    if not x_user_id:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return x_user_id