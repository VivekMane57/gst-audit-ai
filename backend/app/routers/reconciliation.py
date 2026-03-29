"""
routers/reconciliation.py
--------------------------
POST /reconcile   — Run GSTR-2B vs Purchase Register reconciliation
GET  /reconcile/{id} — Get saved reconciliation result
"""
from fastapi import APIRouter, UploadFile, File, Form, Header, HTTPException
from typing import Optional, List
import logging
import uuid

from app.db.supabase_client import get_supabase
from app.services.file_router import parse_any_file
from app.services.reconciliation_service import reconcile, result_to_json
from app.utils.auth import get_user_uuid

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/reconcile", tags=["reconciliation"])


# ── POST /reconcile ───────────────────────────────────────────
@router.post("")
async def run_reconciliation(
    purchase_file:    UploadFile            = File(...),   # Purchase register
    gstr2b_file:      UploadFile            = File(...),   # GSTR-2B Excel/JSON
    our_gstin:        str                   = Form(...),
    period:           str                   = Form(...),
    language:         str                   = Form(default="en"),
    client_id:        Optional[str]         = Form(default=None),
    amount_tolerance: float                 = Form(default=1.0),
    x_user_id:        Optional[str]         = Header(default=None),
    x_user_email:     Optional[str]         = Header(default=None),
    x_user_name:      Optional[str]         = Header(default=None),
):
    if not x_user_id:
        raise HTTPException(status_code=401, detail="Unauthorized")
    if language not in ("en", "hi", "mr"):
        language = "en"

    try:
        supabase  = get_supabase()
        user_uuid = get_user_uuid(
            supabase, x_user_id,
            email=x_user_email,
            full_name=x_user_name,
        )

        all_invoices = []
        parse_errors = []

        # ── Parse Purchase Register ───────────────────────────
        try:
            purchase_bytes = await purchase_file.read()
            purchase_invs  = parse_any_file(
                purchase_bytes,
                filename=purchase_file.filename,
                invoice_type="purchase",
                our_gstin=our_gstin,
                period=period,
            )
            # Mark as books invoices (not from GSTR-2B)
            for inv in purchase_invs:
                if inv.is_in_gstr2b is None:
                    inv.is_in_gstr2b = False
            all_invoices.extend(purchase_invs)
            logger.info(f"Purchase register: {len(purchase_invs)} invoices")
        except Exception as e:
            parse_errors.append(f"Purchase file: {str(e)}")
            logger.error(f"Purchase parse error: {e}")

        # ── Parse GSTR-2B File ────────────────────────────────
        try:
            gstr2b_bytes = await gstr2b_file.read()
            gstr2b_invs  = parse_any_file(
                gstr2b_bytes,
                filename=gstr2b_file.filename,
                invoice_type="purchase",
                our_gstin=our_gstin,
                period=period,
            )
            # Mark all as GSTR-2B invoices
            for inv in gstr2b_invs:
                inv.is_in_gstr2b = True
            all_invoices.extend(gstr2b_invs)
            logger.info(f"GSTR-2B: {len(gstr2b_invs)} invoices")
        except Exception as e:
            parse_errors.append(f"GSTR-2B file: {str(e)}")
            logger.error(f"GSTR-2B parse error: {e}")

        if not all_invoices:
            raise HTTPException(
                status_code=422,
                detail=f"No invoices extracted. Errors: {'; '.join(parse_errors)}",
            )

        # ── Run Reconciliation ────────────────────────────────
        result     = reconcile(all_invoices, our_gstin=our_gstin, period=period, amount_tolerance=amount_tolerance)
        result_json = result_to_json(result)

        # ── Save to DB ────────────────────────────────────────
        recon_id = str(uuid.uuid4())
        try:
            supabase.table("reconciliation_reports").insert({
                "id":           recon_id,
                "user_id":      user_uuid,
                "ca_id":        x_user_id,
                "client_id":    client_id,
                "our_gstin":    our_gstin,
                "period":       period,
                "language":     language,
                "result_json":  result_json,
                "risk_level":   result.risk_level,
                "total_tax_loss": result.total_tax_loss,
                "missing_count":  result.missing_count,
                "mismatch_count": result.mismatch_count,
                "matched_count":  result.matched_count,
            }).execute()
        except Exception as db_err:
            # DB save fail hone se response fail nahi hoga
            logger.warning(f"DB save failed (non-fatal): {db_err}")

        return {
            "reconciliation_id": recon_id,
            "parse_errors":      parse_errors,
            **result_json,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Reconciliation error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Reconciliation failed: {str(e)}")


# ── GET /reconcile/{id} ───────────────────────────────────────
@router.get("/{recon_id}")
async def get_reconciliation(
    recon_id:     str,
    x_user_id:    Optional[str] = Header(default=None),
    x_user_email: Optional[str] = Header(default=None),
    x_user_name:  Optional[str] = Header(default=None),
):
    if not x_user_id:
        raise HTTPException(status_code=401, detail="Unauthorized")

    supabase  = get_supabase()
    user_uuid = get_user_uuid(
        supabase, x_user_id,
        email=x_user_email,
        full_name=x_user_name,
    )

    try:
        res = (
            supabase.table("reconciliation_reports")
            .select("*")
            .eq("id", recon_id)
            .eq("user_id", user_uuid)
            .limit(1)
            .execute()
        )
        if not res.data:
            raise HTTPException(status_code=404, detail="Reconciliation not found")
        return res.data[0]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"get_reconciliation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))