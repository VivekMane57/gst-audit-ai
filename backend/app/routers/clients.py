# """
# routers/clients.py
# ------------------
# GET  /clients         — All clients with last_score + last_audit_at
# POST /clients         — Add new client
# GET  /clients/{id}    — Single client detail
# DELETE /clients/{id}  — Delete client
# """
# from fastapi import APIRouter, Header, HTTPException
# from pydantic import BaseModel
# from typing import Optional
# from app.db.supabase_client import get_supabase
# from app.utils.gstin_validator import validate_gstin
# import logging

# logger = logging.getLogger(__name__)
# router = APIRouter(prefix="/clients", tags=["clients"])


# class AddClientRequest(BaseModel):
#     business_name: str
#     gstin:         str
#     sector:        Optional[str] = None


# def _get_ca_id(x_user_id: str | None) -> str:
#     if not x_user_id:
#         raise HTTPException(status_code=401, detail="Unauthorized")
#     return x_user_id


# # ── GET /clients ───────────────────────────────────────────────
# @router.get("")
# async def get_clients(x_user_id: str | None = Header(default=None)):
#     ca_id    = _get_ca_id(x_user_id)
#     supabase = get_supabase()

#     try:
#         # Fetch all clients for this CA
#         clients_res = (
#             supabase.table("clients")
#             .select("id, business_name, gstin_masked, sector, created_at")
#             .eq("ca_id", ca_id)
#             .order("business_name")
#             .execute()
#         )
#         clients = clients_res.data or []

#         if not clients:
#             return {"clients": [], "total": 0}

#         # For each client — get their latest audit score
#         client_ids = [c["id"] for c in clients]

#         audits_res = (
#             supabase.table("audit_reports")
#             .select("client_id, compliance_score, created_at")
#             .eq("ca_id", ca_id)
#             .in_("client_id", client_ids)
#             .order("created_at", desc=True)
#             .execute()
#         )

#         # Build a map: client_id → latest audit
#         latest_audit: dict = {}
#         for audit in (audits_res.data or []):
#             cid = audit["client_id"]
#             if cid not in latest_audit:   # already sorted desc — first = latest
#                 latest_audit[cid] = {
#                     "last_score":    audit["compliance_score"],
#                     "last_audit_at": audit["created_at"],
#                 }

#         # Merge
#         result = []
#         for c in clients:
#             audit_info = latest_audit.get(c["id"], {})
#             result.append({
#                 **c,
#                 "last_score":    audit_info.get("last_score"),
#                 "last_audit_at": audit_info.get("last_audit_at"),
#             })

#         return {"clients": result, "total": len(result)}

#     except Exception as e:
#         logger.error(f"get_clients error: {e}")
#         raise HTTPException(status_code=500, detail=str(e))


# # ── POST /clients ──────────────────────────────────────────────
# @router.post("")
# async def add_client(
#     body: AddClientRequest,
#     x_user_id: str | None = Header(default=None),
# ):
#     ca_id = _get_ca_id(x_user_id)

#     # Validate GSTIN
#     gstin = body.gstin.upper().strip()
#     result = validate_gstin(gstin)
#     if not result.is_valid:
#         raise HTTPException(
#             status_code=422,
#             detail=f"Invalid GSTIN: {result.error}"
#         )

#     # Mask GSTIN — show only first 2 + last 3 chars
#     gstin_masked = f"{gstin[:2]}{'*' * 10}{gstin[-3:]}"

#     supabase = get_supabase()
#     try:
#         res = (
#             supabase.table("clients")
#             .insert({
#                 "ca_id":         ca_id,
#                 "business_name": body.business_name.strip(),
#                 "gstin":         gstin,            # encrypted ideally
#                 "gstin_masked":  gstin_masked,
#                 "sector":        body.sector or None,
#             })
#             .execute()
#         )

#         if not res.data:
#             raise HTTPException(status_code=500, detail="Failed to create client")

#         return {"client": res.data[0], "message": "Client added successfully"}

#     except HTTPException:
#         raise
#     except Exception as e:
#         logger.error(f"add_client error: {e}")
#         # Check duplicate GSTIN
#         if "duplicate" in str(e).lower() or "unique" in str(e).lower():
#             raise HTTPException(status_code=409, detail="Client with this GSTIN already exists")
#         raise HTTPException(status_code=500, detail=str(e))


# # ── GET /clients/{id} ─────────────────────────────────────────
# @router.get("/{client_id}")
# async def get_client(
#     client_id: str,
#     x_user_id: str | None = Header(default=None),
# ):
#     ca_id    = _get_ca_id(x_user_id)
#     supabase = get_supabase()

#     try:
#         client_res = (
#             supabase.table("clients")
#             .select("*")
#             .eq("id", client_id)
#             .eq("ca_id", ca_id)
#             .limit(1)
#             .execute()
#         )

#         if not client_res.data:
#             raise HTTPException(status_code=404, detail="Client not found")

#         client = client_res.data[0]

#         # Get all audits for this client
#         audits_res = (
#             supabase.table("audit_reports")
#             .select("id, period, compliance_score, risk_level, created_at, itc_summary")
#             .eq("client_id", client_id)
#             .eq("ca_id", ca_id)
#             .order("created_at", desc=True)
#             .execute()
#         )

#         audits = audits_res.data or []

#         return {
#             **client,
#             "last_score":    audits[0]["compliance_score"] if audits else None,
#             "last_audit_at": audits[0]["created_at"]       if audits else None,
#             "audit_history": audits,
#             "total_audits":  len(audits),
#         }

#     except HTTPException:
#         raise
#     except Exception as e:
#         logger.error(f"get_client error: {e}")
#         raise HTTPException(status_code=500, detail=str(e))


# # ── DELETE /clients/{id} ──────────────────────────────────────
# @router.delete("/{client_id}")
# async def delete_client(
#     client_id: str,
#     x_user_id: str | None = Header(default=None),
# ):
#     ca_id    = _get_ca_id(x_user_id)
#     supabase = get_supabase()

#     try:
#         # Verify ownership first
#         check = (
#             supabase.table("clients")
#             .select("id")
#             .eq("id", client_id)
#             .eq("ca_id", ca_id)
#             .limit(1)
#             .execute()
#         )

#         if not check.data:
#             raise HTTPException(status_code=404, detail="Client not found")

#         supabase.table("clients").delete().eq("id", client_id).execute()

#         return {"message": "Client deleted", "id": client_id}

#     except HTTPException:
#         raise
#     except Exception as e:
#         logger.error(f"delete_client error: {e}")
#         raise HTTPException(status_code=500, detail=str(e))



"""
routers/clients.py
------------------
GET  /clients         — All clients with last_score + last_audit_at
POST /clients         — Add new client
GET  /clients/{id}    — Single client detail
DELETE /clients/{id}  — Delete client
"""
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.db.supabase_client import get_supabase
from app.utils.gstin_validator import validate_gstin
from app.utils.auth import get_user_uuid
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/clients", tags=["clients"])


class AddClientRequest(BaseModel):
    business_name: str
    gstin:         str
    sector:        Optional[str] = None


def _get_ca_id(x_user_id: str | None) -> str:
    if not x_user_id:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return x_user_id


def _ensure_user(x_user_id: str) -> None:
    """Ensure user exists in DB — auto-create if not."""
    supabase = get_supabase()
    get_user_uuid(supabase, x_user_id)


# ── GET /clients ───────────────────────────────────────────────
@router.get("")
async def get_clients(x_user_id: str | None = Header(default=None)):
    ca_id = _get_ca_id(x_user_id)
    _ensure_user(ca_id)
    supabase = get_supabase()

    try:
        clients_res = (
            supabase.table("clients")
            .select("id, business_name, gstin_masked, sector, created_at")
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
                    "last_score":    audit["compliance_score"],
                    "last_audit_at": audit["created_at"],
                }

        result = []
        for c in clients:
            audit_info = latest_audit.get(c["id"], {})
            result.append({
                **c,
                "last_score":    audit_info.get("last_score"),
                "last_audit_at": audit_info.get("last_audit_at"),
            })

        return {"clients": result, "total": len(result)}

    except Exception as e:
        logger.error(f"get_clients error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── POST /clients ──────────────────────────────────────────────
@router.post("")
async def add_client(
    body: AddClientRequest,
    x_user_id: str | None = Header(default=None),
):
    ca_id = _get_ca_id(x_user_id)
    _ensure_user(ca_id)

    gstin = body.gstin.upper().strip()
    result = validate_gstin(gstin)
    if not result.is_valid:
        raise HTTPException(status_code=422, detail=f"Invalid GSTIN: {result.error}")

    gstin_masked = f"{gstin[:2]}{'*' * 10}{gstin[-3:]}"

    supabase = get_supabase()
    try:
        res = (
            supabase.table("clients")
            .insert({
                "ca_id":         ca_id,
                "business_name": body.business_name.strip(),
                "gstin":         gstin,
                "gstin_masked":  gstin_masked,
                "sector":        body.sector or None,
            })
            .execute()
        )

        if not res.data:
            raise HTTPException(status_code=500, detail="Failed to create client")

        return {"client": res.data[0], "message": "Client added successfully"}

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
):
    ca_id = _get_ca_id(x_user_id)
    supabase = get_supabase()

    try:
        client_res = (
            supabase.table("clients")
            .select("*")
            .eq("id", client_id)
            .eq("ca_id", ca_id)
            .limit(1)
            .execute()
        )

        if not client_res.data:
            raise HTTPException(status_code=404, detail="Client not found")

        client = client_res.data[0]

        audits_res = (
            supabase.table("audit_reports")
            .select("id, period, compliance_score, risk_level, created_at, itc_summary")
            .eq("client_id", client_id)
            .eq("ca_id", ca_id)
            .order("created_at", desc=True)
            .execute()
        )

        audits = audits_res.data or []

        return {
            **client,
            "last_score":    audits[0]["compliance_score"] if audits else None,
            "last_audit_at": audits[0]["created_at"]       if audits else None,
            "audit_history": audits,
            "total_audits":  len(audits),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"get_client error: {e}")
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
            supabase.table("clients")
            .select("id")
            .eq("id", client_id)
            .eq("ca_id", ca_id)
            .limit(1)
            .execute()
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