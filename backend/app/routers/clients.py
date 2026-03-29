"""
routers/clients.py
------------------
GET    /clients         — All clients
POST   /clients         — Add new client + welcome email
GET    /clients/{id}    — Single client detail
PUT    /clients/{id}    — Update client + welcome email if new email
DELETE /clients/{id}    — Delete client
"""
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.db.supabase_client import get_supabase
from app.utils.gstin_validator import validate_gstin
from app.utils.auth import get_user_uuid
from app.config import get_settings
import logging
import threading
from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/clients", tags=["clients"])


def _get_fernet() -> Fernet:
    key = get_settings().encryption_key
    return Fernet(key.encode())

def encrypt_gstin(gstin: str) -> str:
    return _get_fernet().encrypt(gstin.encode()).decode()


class AddClientRequest(BaseModel):
    business_name:  str
    gstin:          str
    sector:         Optional[str] = None
    contact_person: Optional[str] = None
    phone:          Optional[str] = None
    email:          Optional[str] = None
    address:        Optional[str] = None

class UpdateClientRequest(BaseModel):
    business_name:  Optional[str] = None
    gstin:          Optional[str] = None
    sector:         Optional[str] = None
    contact_person: Optional[str] = None
    phone:          Optional[str] = None
    email:          Optional[str] = None
    address:        Optional[str] = None


def _get_ca_id(x_user_id: str | None) -> str:
    if not x_user_id:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return x_user_id

def _ensure_user(x_user_id: str, email: str = None, full_name: str = None) -> None:
    supabase = get_supabase()
    get_user_uuid(supabase, x_user_id, email=email, full_name=full_name)


def _send_welcome_email_bg(client_email, client_name, ca_name, ca_email, gstin_masked):
    """Background thread mein welcome email bhejo — API block na ho."""
    try:
        from app.services.email_service import send_client_welcome
        result = send_client_welcome(
            client_email=client_email,
            client_name=client_name,
            ca_name=ca_name,
            ca_email=ca_email,
            gstin_masked=gstin_masked,
        )
        if result:
            logger.info(f"Welcome email sent to client: {client_email}")
        else:
            logger.warning(f"Welcome email failed for: {client_email}")
    except Exception as e:
        logger.warning(f"Welcome email error: {e}")


def _get_ca_info(supabase, ca_id: str) -> tuple:
    """CA ka email aur name fetch karo users table se."""
    try:
        res = (
            supabase.table("users")
            .select("email, full_name")
            .eq("clerk_id", ca_id)
            .limit(1)
            .execute()
        )
        if res.data:
            return (
                res.data[0].get("email") or "",
                res.data[0].get("full_name") or "Your CA",
            )
    except Exception:
        pass
    return ("", "Your CA")


# ── GET /clients ───────────────────────────────────────────────
@router.get("")
async def get_clients(
    x_user_id: str | None = Header(default=None),
    x_user_email: str | None = Header(default=None),
    x_user_name: str | None = Header(default=None),
):
    ca_id = _get_ca_id(x_user_id)
    _ensure_user(ca_id, email=x_user_email, full_name=x_user_name)
    supabase = get_supabase()

    try:
        clients_res = (
            supabase.table("clients")
            .select("id, business_name, gstin_masked, gstin_encrypted, sector, created_at, contact_person, phone, email, address, state_code")
            .eq("ca_id", ca_id)
            .order("business_name")
            .execute()
        )
        clients = clients_res.data or []
        if not clients:
            return {"clients": [], "total": 0}

        client_ids = [c["id"] for c in clients]
        audits_res = (
            supabase.table("audit_reports")
            .select("client_id, compliance_score, created_at")
            .eq("ca_id", ca_id)
            .in_("client_id", client_ids)
            .order("created_at", desc=True)
            .execute()
        )

        latest_audit: dict = {}
        for audit in (audits_res.data or []):
            cid = audit["client_id"]
            if cid not in latest_audit:
                latest_audit[cid] = {
                    "last_score": audit["compliance_score"],
                    "last_audit_at": audit["created_at"],
                }

        result = []
        for c in clients:
            audit_info = latest_audit.get(c["id"], {})
            c.pop("gstin_encrypted", None)
            result.append({**c, "last_score": audit_info.get("last_score"), "last_audit_at": audit_info.get("last_audit_at")})

        return {"clients": result, "total": len(result)}
    except Exception as e:
        logger.error(f"get_clients error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── POST /clients — Add + Welcome Email ───────────────────────
@router.post("")
async def add_client(
    body: AddClientRequest,
    x_user_id: str | None = Header(default=None),
    x_user_email: str | None = Header(default=None),
    x_user_name: str | None = Header(default=None),
):
    ca_id = _get_ca_id(x_user_id)
    _ensure_user(ca_id, email=x_user_email, full_name=x_user_name)

    gstin = body.gstin.upper().strip()
    result = validate_gstin(gstin)
    if not result.is_valid:
        raise HTTPException(status_code=422, detail=f"Invalid GSTIN: {result.error}")

    gstin_masked = f"{gstin[:2]}{'*' * 10}{gstin[-3:]}"
    gstin_encrypted = encrypt_gstin(gstin)
    state_code = gstin[:2]

    supabase = get_supabase()
    try:
        res = (
            supabase.table("clients")
            .insert({
                "ca_id": ca_id, "business_name": body.business_name.strip(),
                "gstin_encrypted": gstin_encrypted, "gstin_masked": gstin_masked,
                "state_code": state_code, "sector": body.sector or None,
                "contact_person": body.contact_person or None, "phone": body.phone or None,
                "email": body.email or None, "address": body.address or None,
            })
            .execute()
        )
        if not res.data:
            raise HTTPException(status_code=500, detail="Failed to create client")

        client_data = res.data[0]
        client_data.pop("gstin_encrypted", None)

        # ── Welcome email to client (background) ─────────────
        client_email = (body.email or "").strip()
        if client_email and "@" in client_email:
            ca_email, ca_name = _get_ca_info(supabase, ca_id)
            threading.Thread(
                target=_send_welcome_email_bg,
                args=(client_email, body.business_name.strip(), ca_name, ca_email, gstin_masked),
                daemon=True,
            ).start()
            logger.info(f"Welcome email queued for new client: {client_email}")

        return {"client": client_data, "message": "Client added successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"add_client error: {e}")
        if "duplicate" in str(e).lower() or "unique" in str(e).lower():
            raise HTTPException(status_code=409, detail="Client with this GSTIN already exists")
        raise HTTPException(status_code=500, detail=str(e))


# ── GET /clients/{id} ─────────────────────────────────────────
@router.get("/{client_id}")
async def get_client(
    client_id: str,
    x_user_id: str | None = Header(default=None),
    x_user_email: str | None = Header(default=None),
    x_user_name: str | None = Header(default=None),
):
    ca_id = _get_ca_id(x_user_id)
    _ensure_user(ca_id, email=x_user_email, full_name=x_user_name)
    supabase = get_supabase()

    try:
        client_res = (
            supabase.table("clients").select("*")
            .eq("id", client_id).eq("ca_id", ca_id).limit(1).execute()
        )
        if not client_res.data:
            raise HTTPException(status_code=404, detail="Client not found")

        client = client_res.data[0]
        client.pop("gstin_encrypted", None)

        audits_res = (
            supabase.table("audit_reports")
            .select("id, period, compliance_score, risk_level, created_at, itc_summary")
            .eq("client_id", client_id).eq("ca_id", ca_id)
            .order("created_at", desc=True).execute()
        )
        audits = audits_res.data or []

        return {
            **client,
            "last_score": audits[0]["compliance_score"] if audits else None,
            "last_audit_at": audits[0]["created_at"] if audits else None,
            "audit_history": audits, "total_audits": len(audits),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"get_client error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── PUT /clients/{id} — Update + Welcome Email if new email ───
@router.put("/{client_id}")
async def update_client(
    client_id: str,
    body: UpdateClientRequest,
    x_user_id: str | None = Header(default=None),
    x_user_email: str | None = Header(default=None),
    x_user_name: str | None = Header(default=None),
):
    ca_id = _get_ca_id(x_user_id)
    _ensure_user(ca_id, email=x_user_email, full_name=x_user_name)
    supabase = get_supabase()

    try:
        check = (
            supabase.table("clients").select("id, gstin_encrypted, email, business_name, gstin_masked")
            .eq("id", client_id).eq("ca_id", ca_id).limit(1).execute()
        )
        if not check.data:
            raise HTTPException(status_code=404, detail="Client not found")

        old_email = (check.data[0].get("email") or "").strip()
        old_name = check.data[0].get("business_name") or ""
        old_gstin_masked = check.data[0].get("gstin_masked") or ""

        update_data: dict = {}
        if body.business_name is not None:
            update_data["business_name"] = body.business_name.strip()
        if body.gstin is not None:
            gstin = body.gstin.upper().strip()
            result = validate_gstin(gstin)
            if not result.is_valid:
                raise HTTPException(status_code=422, detail=f"Invalid GSTIN: {result.error}")
            update_data["gstin_encrypted"] = encrypt_gstin(gstin)
            update_data["gstin_masked"] = f"{gstin[:2]}{'*' * 10}{gstin[-3:]}"
            update_data["state_code"] = gstin[:2]
        if body.sector is not None:
            update_data["sector"] = body.sector or None
        for field in ("contact_person", "phone", "email", "address"):
            val = getattr(body, field)
            if val is not None:
                update_data[field] = val or None

        if not update_data:
            raise HTTPException(status_code=400, detail="No fields to update")

        res = (
            supabase.table("clients").update(update_data)
            .eq("id", client_id).eq("ca_id", ca_id).execute()
        )
        if not res.data:
            raise HTTPException(status_code=500, detail="Update failed")

        client_data = res.data[0]
        client_data.pop("gstin_encrypted", None)

        # ── Welcome email if NEW email added ──────────────────
        new_email = (body.email or "").strip()
        if new_email and "@" in new_email and new_email != old_email:
            ca_email_val, ca_name_val = _get_ca_info(supabase, ca_id)
            client_name = body.business_name or old_name
            gstin_masked = update_data.get("gstin_masked") or old_gstin_masked
            threading.Thread(
                target=_send_welcome_email_bg,
                args=(new_email, client_name, ca_name_val, ca_email_val, gstin_masked),
                daemon=True,
            ).start()
            logger.info(f"Welcome email queued for updated client: {new_email}")

        logger.info(f"Client {client_id} updated: {list(update_data.keys())}")
        return {"client": client_data, "message": "Client updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"update_client error: {e}")
        if "duplicate" in str(e).lower() or "unique" in str(e).lower():
            raise HTTPException(status_code=409, detail="GSTIN already used by another client")
        raise HTTPException(status_code=500, detail=str(e))


# ── DELETE /clients/{id} ──────────────────────────────────────
@router.delete("/{client_id}")
async def delete_client(
    client_id: str,
    x_user_id: str | None = Header(default=None),
):
    ca_id = _get_ca_id(x_user_id)
    supabase = get_supabase()
    try:
        check = (
            supabase.table("clients").select("id")
            .eq("id", client_id).eq("ca_id", ca_id).limit(1).execute()
        )
        if not check.data:
            raise HTTPException(status_code=404, detail="Client not found")
        supabase.table("clients").delete().eq("id", client_id).execute()
        return {"message": "Client deleted", "id": client_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"delete_client error: {e}")
        raise HTTPException(status_code=500, detail=str(e))