"""
utils/auth.py
-------------
Clerk ID se user UUID lookup.
Real email Clerk se aata hai via x-user-email header.
Auto-create user with real email. Update placeholder emails automatically.
"""
import uuid
import logging
from fastapi import HTTPException

logger = logging.getLogger(__name__)


def get_user_uuid(
    supabase,
    clerk_id: str,
    email: str = None,
    full_name: str = None,
) -> str:
    try:
        res = (
            supabase.table("users")
            .select("id, email, full_name")
            .eq("clerk_id", clerk_id)
            .limit(1)
            .execute()
        )

        if res.data:
            user = res.data[0]
            user_id = user["id"]
            current_email = user.get("email") or ""
            current_name = user.get("full_name") or ""

            # Update real email if current is placeholder
            needs_update = False
            update_data = {}

            if email and "auditai.app" not in email and "@placeholder" not in email:
                if not current_email or "auditai.app" in current_email or "@placeholder" in current_email:
                    update_data["email"] = email
                    needs_update = True

            if full_name and full_name != "User" and (not current_name or current_name == "User"):
                update_data["full_name"] = full_name
                needs_update = True

            if needs_update:
                try:
                    supabase.table("users").update(update_data).eq("id", user_id).execute()
                    logger.info(f"User email updated: {clerk_id} → {update_data.get('email', 'same')}")
                except Exception as e:
                    logger.warning(f"User update failed: {e}")

            return user_id

        # New user — save with real email
        new_id = str(uuid.uuid4())
        user_email = email if (email and "auditai.app" not in email and "@placeholder" not in email) else f"{clerk_id}@auditai.app"

        insert_data = {
            "id": new_id,
            "clerk_id": clerk_id,
            "email": user_email,
        }
        if full_name and full_name != "User":
            insert_data["full_name"] = full_name

        supabase.table("users").insert(insert_data).execute()
        logger.info(f"New user: {clerk_id} → email: {user_email}")
        return new_id

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"get_user_uuid error: {e}")
        raise HTTPException(status_code=500, detail="User lookup failed")