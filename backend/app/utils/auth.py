"""
utils/auth.py
"""
import uuid
import logging
from fastapi import HTTPException
from app.db.supabase_client import get_supabase

logger = logging.getLogger(__name__)


def get_user_uuid(supabase, clerk_id: str) -> str:
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

        # Auto-create with ALL required NOT NULL fields
        new_id = str(uuid.uuid4())
        supabase.table("users").insert({
            "id": new_id,
            "clerk_id": clerk_id,
            "email": f"{clerk_id}@auditai.app",
            "is_sso_user": False,
            "is_anonymous": False,
        }).execute()

        logger.info(f"Auto-created user: {clerk_id} → {new_id}")
        return new_id

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"get_user_uuid error: {e}")
        raise HTTPException(status_code=500, detail="User lookup failed")