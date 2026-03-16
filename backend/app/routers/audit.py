# """
# routers/audit.py
# ----------------
# POST /audit              — Run audit + notice simulation (saves to DB)
# GET  /audit/{id}         — Get single audit result
# POST /audit/{id}/notice  — Re-run notice simulation with custom params
# """
# from fastapi import APIRouter, UploadFile, File, Form, Header, HTTPException
# from typing import Optional
# from app.db.supabase_client import get_supabase
# from app.services.excel_parser import parse_from_bytes
# from app.services.audit_engine import run_all_checks
# from app.services.sector_checks import run_sector_checks
# from app.services.score_calculator import calculate_score, ScoreResult
# from app.services.notice_simulator import run_notice_simulation
# import logging
# import uuid

# logger = logging.getLogger(__name__)
# router = APIRouter(prefix="/audit", tags=["audit"])

# VALID_SECTORS = {
#     "healthcare", "retail", "manufacturing",
#     "it_services", "real_estate", "restaurant", "export_import"
# }


# def get_user_uuid(supabase, clerk_id: str) -> str:
#     """Clerk ID se users table mein UUID lookup karo."""
#     try:
#         res = (
#             supabase.table("users")
#             .select("id")
#             .eq("clerk_id", clerk_id)
#             .limit(1)
#             .execute()
#         )
#         if res.data:
#             return res.data[0]["id"]
#         raise HTTPException(
#             status_code=404,
#             detail="User not found. Please complete signup first."
#         )
#     except HTTPException:
#         raise
#     except Exception as e:
#         logger.error(f"get_user_uuid error: {e}")
#         raise HTTPException(status_code=500, detail="User lookup failed")


# def _safe_issue_amount(issue) -> float:
#     """Safely get amount from Issue object — handles different model field names."""
#     for attr in ("taxable_value", "amount", "taxable_amount", "itc_at_risk"):
#         val = getattr(issue, attr, None)
#         if val is not None and val != 0:
#             return float(val)
#     return 0.0


# # ── POST /audit ────────────────────────────────────────────────
# @router.post("")
# async def run_audit(
#     sales_file:    UploadFile = File(...),
#     purchase_file: UploadFile = File(...),
#     our_gstin:     str        = Form(...),
#     period:        str        = Form(...),
#     language:      str        = Form(default="en"),
#     sector:        Optional[str] = Form(default=None),
#     client_id:     Optional[str] = Form(default=None),
#     x_user_id:     Optional[str] = Header(default=None),
#     filing_delays:    int   = Form(default=0),
#     turnover_cr:      float = Form(default=1.0),
#     previous_notices: int   = Form(default=0),
# ):
#     if not x_user_id:
#         raise HTTPException(status_code=401, detail="Unauthorized")

#     if sector and sector not in VALID_SECTORS:
#         raise HTTPException(status_code=422, detail=f"Invalid sector: {sector}")

#     if language not in ("en", "hi", "mr"):
#         language = "en"

#     try:
#         supabase = get_supabase()

#         # ── Clerk ID → UUID lookup ─────────────────────────────
#         user_uuid = get_user_uuid(supabase, x_user_id)

#         # ── Parse Excel files ──────────────────────────────────
#         sales_bytes    = await sales_file.read()
#         purchase_bytes = await purchase_file.read()

#         sales_invoices    = parse_from_bytes(sales_bytes,    filename=sales_file.filename,    invoice_type="sale",     our_gstin=our_gstin, period=period)
#         purchase_invoices = parse_from_bytes(purchase_bytes, filename=purchase_file.filename, invoice_type="purchase", our_gstin=our_gstin, period=period)
#         all_invoices      = sales_invoices + purchase_invoices

#         logger.info(f"Parsed {len(sales_invoices)} sales + {len(purchase_invoices)} purchase invoices")

#         # ── Run audit checks ───────────────────────────────────
#         issues = run_all_checks(all_invoices, our_gstin=our_gstin, period=period)

#         if sector and sector in VALID_SECTORS:
#             sector_issues = run_sector_checks(all_invoices, sector=sector, our_gstin=our_gstin)
#             issues.extend(sector_issues)
#             severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
#             issues.sort(key=lambda x: severity_order.get(x.severity.value, 99))

#         # ── Calculate score ────────────────────────────────────
#         score_result: ScoreResult = calculate_score(issues)

#         # ── Prepare issues data ────────────────────────────────
#         issues_json    = [issue.dict() for issue in issues]
#         itc_at_risk    = sum(i.itc_at_risk for i in issues)
#         itc_blocked    = sum(
#             i.itc_at_risk for i in issues
#             if i.issue_type.value == "gstr2b_missing"
#         )
#         critical_count = sum(1 for i in issues if i.severity.value == "CRITICAL")
#         high_count     = sum(1 for i in issues if i.severity.value == "HIGH")
#         medium_count   = sum(1 for i in issues if i.severity.value == "MEDIUM")
#         low_count      = sum(1 for i in issues if i.severity.value == "LOW")

#         # ── Run Notice Simulator ───────────────────────────────
#         notice_issues = []
#         for issue in issues:
#             notice_issues.append({
#                 "type": issue.issue_type.value,
#                 "severity": issue.severity.value.lower(),
#                 "invoice": issue.invoice_number,
#                 "party": issue.party_name or "N/A",
#                 "amount": _safe_issue_amount(issue),
#                 "tax_impact": issue.itc_at_risk or 0,
#             })

#         notice_sim = run_notice_simulation(
#             issues=notice_issues,
#             compliance_score=score_result.score,
#             client_name="",
#             client_gstin=our_gstin,
#             lang=language,
#             filing_delays=filing_delays,
#             turnover_cr=turnover_cr,
#             previous_notices=previous_notices,
#         )

#         logger.info(
#             f"Notice simulation: {notice_sim['probability']}% "
#             f"({notice_sim['risk_level']})"
#         )

#         # ── Get client_name if client_id provided ──────────────
#         client_name = None
#         if client_id:
#             try:
#                 client_res = (
#                     supabase.table("clients")
#                     .select("business_name")
#                     .eq("id", client_id)
#                     .eq("ca_id", x_user_id)
#                     .limit(1)
#                     .execute()
#                 )
#                 if client_res.data:
#                     client_name = client_res.data[0]["business_name"]
#             except Exception as e:
#                 logger.warning(f"Could not fetch client name: {e}")

#         # ── Save to Supabase ───────────────────────────────────
#         audit_id     = str(uuid.uuid4())
#         gstin_masked = (
#             f"{our_gstin[:2]}{'*' * 10}{our_gstin[-3:]}"
#             if len(our_gstin) == 15 else our_gstin
#         )

#         audit_record = {
#             "id":                     audit_id,
#             "user_id":                user_uuid,
#             "ca_id":                  x_user_id,
#             "client_id":              client_id,
#             "client_name":            client_name,
#             "client_gstin_masked":    gstin_masked,
#             "period":                 period,
#             "language":               language,
#             "sector":                 sector,
#             "total_invoices_scanned": len(all_invoices),
#             "compliance_score":       score_result.score,
#             "risk_level":             score_result.risk_level,
#             "issues_json":            issues_json,
#             "itc_at_risk":            round(itc_at_risk, 2),
#             "itc_blocked":            round(itc_blocked, 2),
#             "itc_eligible":           0.0,
#             "itc_summary": {
#                 "at_risk":      round(itc_at_risk, 2),
#                 "blocked":      round(itc_blocked, 2),
#                 "total_impact": round(itc_at_risk + itc_blocked, 2),
#             },
#             "critical_count":         critical_count,
#             "high_count":             high_count,
#             "medium_count":           medium_count,
#             "low_count":              low_count,
#             "notice_probability":     notice_sim["probability"],
#             "notice_risk_level":      notice_sim["risk_level"],
#             "notice_simulation":      {
#                 "probability":       notice_sim["probability"],
#                 "risk_level":        notice_sim["risk_level"],
#                 "risk_message":      notice_sim["risk_message"],
#                 "risk_areas":        notice_sim["risk_areas"],
#                 "possible_notices":  notice_sim["possible_notices"],
#                 "what_if_fix_all":   notice_sim["what_if_fix_all"],
#                 "recommendations":   notice_sim["recommendations"][:5],
#             },
#         }

#         try:
#             supabase.table("audit_reports").insert(audit_record).execute()
#         except Exception as insert_err:
#             logger.warning(f"Insert failed with notice fields: {insert_err}")
#             for key in ["notice_probability", "notice_risk_level", "notice_simulation"]:
#                 audit_record.pop(key, None)
#             try:
#                 supabase.table("audit_reports").insert(audit_record).execute()
#                 logger.info("Insert succeeded without notice columns")
#             except Exception as retry_err:
#                 logger.error(f"Insert retry also failed: {retry_err}", exc_info=True)
#                 raise HTTPException(
#                     status_code=500,
#                     detail=f"Failed to save audit: {str(retry_err)}"
#                 )

#         # ── Update client last_score ───────────────────────────
#         if client_id:
#             try:
#                 supabase.table("clients").update({
#                     "last_score":    score_result.score,
#                     "last_audit_at": "now()",
#                 }).eq("id", client_id).eq("ca_id", x_user_id).execute()
#             except Exception as e:
#                 logger.warning(f"Could not update client last_score: {e}")

#         # ── Return result ──────────────────────────────────────
#         return {
#             "audit_id":         audit_id,
#             "compliance_score": score_result.score,
#             "risk_level":       score_result.risk_level,
#             "total_invoices":   len(all_invoices),
#             "issues":           issues_json,
#             "itc_at_risk":      itc_at_risk,
#             "critical_count":   critical_count,
#             "high_count":       high_count,
#             "medium_count":     medium_count,
#             "low_count":        low_count,
#             "notice_simulation": notice_sim,
#             "message":          "Audit complete",
#         }

#     except HTTPException:
#         raise
#     except Exception as e:
#         logger.error(f"run_audit error: {e}", exc_info=True)
#         raise HTTPException(status_code=500, detail=f"Audit failed: {str(e)}")


# # ── GET /audit/{id} ────────────────────────────────────────────
# @router.get("/{audit_id}")
# async def get_audit(
#     audit_id:  str,
#     x_user_id: Optional[str] = Header(default=None),
# ):
#     if not x_user_id:
#         raise HTTPException(status_code=401, detail="Unauthorized")

#     supabase  = get_supabase()
#     user_uuid = get_user_uuid(supabase, x_user_id)

#     try:
#         res = (
#             supabase.table("audit_reports")
#             .select("*")
#             .eq("id", audit_id)
#             .eq("user_id", user_uuid)
#             .limit(1)
#             .execute()
#         )

#         if not res.data:
#             raise HTTPException(status_code=404, detail="Audit not found")

#         row = res.data[0]
#         return {
#             **row,
#             "total_invoices":      row.get("total_invoices_scanned"),
#             "client_name":         row.get("client_name") or "Audit",
#             "client_gstin_masked": row.get("client_gstin_masked"),
#         }

#     except HTTPException:
#         raise
#     except Exception as e:
#         logger.error(f"get_audit error: {e}")
#         raise HTTPException(status_code=500, detail=str(e))


# # ── POST /audit/{id}/notice ───────────────────────────────────
# @router.post("/{audit_id}/notice")
# async def rerun_notice_simulation(
#     audit_id:         str,
#     filing_delays:    int   = Form(default=0),
#     turnover_cr:      float = Form(default=1.0),
#     previous_notices: int   = Form(default=0),
#     language:         str   = Form(default="en"),
#     x_user_id:        Optional[str] = Header(default=None),
# ):
#     if not x_user_id:
#         raise HTTPException(status_code=401, detail="Unauthorized")

#     supabase  = get_supabase()
#     user_uuid = get_user_uuid(supabase, x_user_id)

#     try:
#         res = (
#             supabase.table("audit_reports")
#             .select("*")
#             .eq("id", audit_id)
#             .eq("user_id", user_uuid)
#             .limit(1)
#             .execute()
#         )

#         if not res.data:
#             raise HTTPException(status_code=404, detail="Audit not found")

#         row = res.data[0]
#         issues_json = row.get("issues_json", [])

#         notice_issues = []
#         for issue in issues_json:
#             notice_issues.append({
#                 "type": issue.get("issue_type", "unknown"),
#                 "severity": issue.get("severity", "medium").lower(),
#                 "invoice": issue.get("invoice_number", "N/A"),
#                 "party": issue.get("party_name", "N/A"),
#                 "amount": issue.get("itc_at_risk", 0),
#                 "tax_impact": issue.get("itc_at_risk", 0),
#             })

#         notice_sim = run_notice_simulation(
#             issues=notice_issues,
#             compliance_score=row.get("compliance_score", 50),
#             client_name=row.get("client_name", ""),
#             client_gstin=row.get("client_gstin_masked", ""),
#             lang=language,
#             filing_delays=filing_delays,
#             turnover_cr=turnover_cr,
#             previous_notices=previous_notices,
#         )

#         try:
#             supabase.table("audit_reports").update({
#                 "notice_probability": notice_sim["probability"],
#                 "notice_risk_level":  notice_sim["risk_level"],
#                 "notice_simulation":  {
#                     "probability":      notice_sim["probability"],
#                     "risk_level":       notice_sim["risk_level"],
#                     "risk_message":     notice_sim["risk_message"],
#                     "risk_areas":       notice_sim["risk_areas"],
#                     "possible_notices": notice_sim["possible_notices"],
#                     "what_if_fix_all":  notice_sim["what_if_fix_all"],
#                     "recommendations":  notice_sim["recommendations"][:5],
#                 },
#             }).eq("id", audit_id).execute()
#         except Exception as update_err:
#             logger.warning(f"Could not update notice data: {update_err}")

#         return {
#             "audit_id": audit_id,
#             "notice_simulation": notice_sim,
#             "message": "Notice simulation updated",
#         }

#     except HTTPException:
#         raise
#     except Exception as e:
#         logger.error(f"rerun_notice error: {e}", exc_info=True)
#         raise HTTPException(status_code=500, detail=str(e))


"""
routers/audit.py
----------------
POST /audit              — Run audit + notice simulation (saves to DB)
GET  /audit/{id}         — Get single audit result
POST /audit/{id}/notice  — Re-run notice simulation with custom params
"""
from fastapi import APIRouter, UploadFile, File, Form, Header, HTTPException
from typing import Optional
from app.db.supabase_client import get_supabase
from app.services.excel_parser import parse_from_bytes
from app.services.audit_engine import run_all_checks
from app.services.sector_checks import run_sector_checks
from app.services.score_calculator import calculate_score, ScoreResult
from app.services.notice_simulator import run_notice_simulation
from app.utils.auth import get_user_uuid
import logging
import uuid

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/audit", tags=["audit"])

VALID_SECTORS = {
    "healthcare", "retail", "manufacturing",
    "it_services", "real_estate", "restaurant", "export_import"
}


def _safe_issue_amount(issue) -> float:
    for attr in ("taxable_value", "amount", "taxable_amount", "itc_at_risk"):
        val = getattr(issue, attr, None)
        if val is not None and val != 0:
            return float(val)
    return 0.0


@router.post("")
async def run_audit(
    sales_file:    UploadFile = File(...),
    purchase_file: UploadFile = File(...),
    our_gstin:     str        = Form(...),
    period:        str        = Form(...),
    language:      str        = Form(default="en"),
    sector:        Optional[str] = Form(default=None),
    client_id:     Optional[str] = Form(default=None),
    x_user_id:     Optional[str] = Header(default=None),
    filing_delays:    int   = Form(default=0),
    turnover_cr:      float = Form(default=1.0),
    previous_notices: int   = Form(default=0),
):
    if not x_user_id:
        raise HTTPException(status_code=401, detail="Unauthorized")
    if sector and sector not in VALID_SECTORS:
        raise HTTPException(status_code=422, detail=f"Invalid sector: {sector}")
    if language not in ("en", "hi", "mr"):
        language = "en"

    try:
        supabase = get_supabase()
        user_uuid = get_user_uuid(supabase, x_user_id)

        sales_bytes    = await sales_file.read()
        purchase_bytes = await purchase_file.read()

        sales_invoices    = parse_from_bytes(sales_bytes,    filename=sales_file.filename,    invoice_type="sale",     our_gstin=our_gstin, period=period)
        purchase_invoices = parse_from_bytes(purchase_bytes, filename=purchase_file.filename, invoice_type="purchase", our_gstin=our_gstin, period=period)
        all_invoices      = sales_invoices + purchase_invoices

        logger.info(f"Parsed {len(sales_invoices)} sales + {len(purchase_invoices)} purchase invoices")

        issues = run_all_checks(all_invoices, our_gstin=our_gstin, period=period)

        if sector and sector in VALID_SECTORS:
            sector_issues = run_sector_checks(all_invoices, sector=sector, our_gstin=our_gstin)
            issues.extend(sector_issues)
            severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
            issues.sort(key=lambda x: severity_order.get(x.severity.value, 99))

        score_result: ScoreResult = calculate_score(issues)

        issues_json    = [issue.dict() for issue in issues]
        itc_at_risk    = sum(i.itc_at_risk for i in issues)
        itc_blocked    = sum(i.itc_at_risk for i in issues if i.issue_type.value == "gstr2b_missing")
        critical_count = sum(1 for i in issues if i.severity.value == "CRITICAL")
        high_count     = sum(1 for i in issues if i.severity.value == "HIGH")
        medium_count   = sum(1 for i in issues if i.severity.value == "MEDIUM")
        low_count      = sum(1 for i in issues if i.severity.value == "LOW")

        notice_issues = []
        for issue in issues:
            notice_issues.append({
                "type": issue.issue_type.value,
                "severity": issue.severity.value.lower(),
                "invoice": issue.invoice_number,
                "party": issue.party_name or "N/A",
                "amount": _safe_issue_amount(issue),
                "tax_impact": issue.itc_at_risk or 0,
            })

        notice_sim = run_notice_simulation(
            issues=notice_issues,
            compliance_score=score_result.score,
            client_name="",
            client_gstin=our_gstin,
            lang=language,
            filing_delays=filing_delays,
            turnover_cr=turnover_cr,
            previous_notices=previous_notices,
        )

        logger.info(f"Notice simulation: {notice_sim['probability']}% ({notice_sim['risk_level']})")

        client_name = None
        if client_id:
            try:
                client_res = (
                    supabase.table("clients")
                    .select("business_name")
                    .eq("id", client_id)
                    .eq("ca_id", x_user_id)
                    .limit(1)
                    .execute()
                )
                if client_res.data:
                    client_name = client_res.data[0]["business_name"]
            except Exception as e:
                logger.warning(f"Could not fetch client name: {e}")

        audit_id = str(uuid.uuid4())
        gstin_masked = (
            f"{our_gstin[:2]}{'*' * 10}{our_gstin[-3:]}"
            if len(our_gstin) == 15 else our_gstin
        )

        audit_record = {
            "id":                     audit_id,
            "user_id":                user_uuid,
            "ca_id":                  x_user_id,
            "client_id":              client_id,
            "client_name":            client_name,
            "client_gstin_masked":    gstin_masked,
            "period":                 period,
            "language":               language,
            "sector":                 sector,
            "total_invoices_scanned": len(all_invoices),
            "compliance_score":       score_result.score,
            "risk_level":             score_result.risk_level,
            "issues_json":            issues_json,
            "itc_at_risk":            round(itc_at_risk, 2),
            "itc_blocked":            round(itc_blocked, 2),
            "itc_eligible":           0.0,
            "itc_summary": {
                "at_risk":      round(itc_at_risk, 2),
                "blocked":      round(itc_blocked, 2),
                "total_impact": round(itc_at_risk + itc_blocked, 2),
            },
            "critical_count": critical_count,
            "high_count":     high_count,
            "medium_count":   medium_count,
            "low_count":      low_count,
            "notice_probability": notice_sim["probability"],
            "notice_risk_level":  notice_sim["risk_level"],
            "notice_simulation": {
                "probability":      notice_sim["probability"],
                "risk_level":       notice_sim["risk_level"],
                "risk_message":     notice_sim["risk_message"],
                "risk_areas":       notice_sim["risk_areas"],
                "possible_notices": notice_sim["possible_notices"],
                "what_if_fix_all":  notice_sim["what_if_fix_all"],
                "recommendations":  notice_sim["recommendations"][:5],
            },
        }

        try:
            supabase.table("audit_reports").insert(audit_record).execute()
        except Exception as insert_err:
            logger.warning(f"Insert failed with notice fields: {insert_err}")
            for key in ["notice_probability", "notice_risk_level", "notice_simulation"]:
                audit_record.pop(key, None)
            try:
                supabase.table("audit_reports").insert(audit_record).execute()
                logger.info("Insert succeeded without notice columns")
            except Exception as retry_err:
                logger.error(f"Insert retry also failed: {retry_err}", exc_info=True)
                raise HTTPException(status_code=500, detail=f"Failed to save audit: {str(retry_err)}")

        if client_id:
            try:
                supabase.table("clients").update({
                    "last_score":    score_result.score,
                    "last_audit_at": "now()",
                }).eq("id", client_id).eq("ca_id", x_user_id).execute()
            except Exception as e:
                logger.warning(f"Could not update client last_score: {e}")

        return {
            "audit_id":         audit_id,
            "compliance_score": score_result.score,
            "risk_level":       score_result.risk_level,
            "total_invoices":   len(all_invoices),
            "issues":           issues_json,
            "itc_at_risk":      itc_at_risk,
            "critical_count":   critical_count,
            "high_count":       high_count,
            "medium_count":     medium_count,
            "low_count":        low_count,
            "notice_simulation": notice_sim,
            "message":          "Audit complete",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"run_audit error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Audit failed: {str(e)}")


@router.get("/{audit_id}")
async def get_audit(
    audit_id:  str,
    x_user_id: Optional[str] = Header(default=None),
):
    if not x_user_id:
        raise HTTPException(status_code=401, detail="Unauthorized")

    supabase  = get_supabase()
    user_uuid = get_user_uuid(supabase, x_user_id)

    try:
        res = (
            supabase.table("audit_reports")
            .select("*")
            .eq("id", audit_id)
            .eq("user_id", user_uuid)
            .limit(1)
            .execute()
        )
        if not res.data:
            raise HTTPException(status_code=404, detail="Audit not found")

        row = res.data[0]
        return {
            **row,
            "total_invoices":      row.get("total_invoices_scanned"),
            "client_name":         row.get("client_name") or "Audit",
            "client_gstin_masked": row.get("client_gstin_masked"),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"get_audit error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{audit_id}/notice")
async def rerun_notice_simulation(
    audit_id:         str,
    filing_delays:    int   = Form(default=0),
    turnover_cr:      float = Form(default=1.0),
    previous_notices: int   = Form(default=0),
    language:         str   = Form(default="en"),
    x_user_id:        Optional[str] = Header(default=None),
):
    if not x_user_id:
        raise HTTPException(status_code=401, detail="Unauthorized")

    supabase  = get_supabase()
    user_uuid = get_user_uuid(supabase, x_user_id)

    try:
        res = (
            supabase.table("audit_reports")
            .select("*")
            .eq("id", audit_id)
            .eq("user_id", user_uuid)
            .limit(1)
            .execute()
        )
        if not res.data:
            raise HTTPException(status_code=404, detail="Audit not found")

        row = res.data[0]
        issues_json = row.get("issues_json", [])

        notice_issues = []
        for issue in issues_json:
            notice_issues.append({
                "type": issue.get("issue_type", "unknown"),
                "severity": issue.get("severity", "medium").lower(),
                "invoice": issue.get("invoice_number", "N/A"),
                "party": issue.get("party_name", "N/A"),
                "amount": issue.get("itc_at_risk", 0),
                "tax_impact": issue.get("itc_at_risk", 0),
            })

        notice_sim = run_notice_simulation(
            issues=notice_issues,
            compliance_score=row.get("compliance_score", 50),
            client_name=row.get("client_name", ""),
            client_gstin=row.get("client_gstin_masked", ""),
            lang=language,
            filing_delays=filing_delays,
            turnover_cr=turnover_cr,
            previous_notices=previous_notices,
        )

        try:
            supabase.table("audit_reports").update({
                "notice_probability": notice_sim["probability"],
                "notice_risk_level":  notice_sim["risk_level"],
                "notice_simulation": {
                    "probability":      notice_sim["probability"],
                    "risk_level":       notice_sim["risk_level"],
                    "risk_message":     notice_sim["risk_message"],
                    "risk_areas":       notice_sim["risk_areas"],
                    "possible_notices": notice_sim["possible_notices"],
                    "what_if_fix_all":  notice_sim["what_if_fix_all"],
                    "recommendations":  notice_sim["recommendations"][:5],
                },
            }).eq("id", audit_id).execute()
        except Exception as update_err:
            logger.warning(f"Could not update notice data: {update_err}")

        return {
            "audit_id": audit_id,
            "notice_simulation": notice_sim,
            "message": "Notice simulation updated",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"rerun_notice error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))