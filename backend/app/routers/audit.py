# """
# routers/audit.py
# ----------------
# Complete Integrated Router:
# 1. Multi-file Parsing (Sales/Purchase/Extra) — smart type detection
# 2. Audit Engine & Sector Specific Checks
# 3. Notice Simulation & Scoring
# 4. PDF Report Generation                      ← Added from File 1
# 5. Email with PDF Attachment                   ← Added from File 1
# """
# from fastapi import APIRouter, UploadFile, File, Form, Header, HTTPException
# from typing import Optional, List
# import logging
# import uuid

# from app.db.supabase_client import get_supabase
# from app.services.file_router import parse_any_file, get_supported_formats
# from app.services.audit_engine import run_all_checks
# from app.services.sector_checks import run_sector_checks
# from app.services.score_calculator import calculate_score, ScoreResult
# from app.services.notice_simulator import run_notice_simulation
# from app.services.email_service import send_audit_complete_to_ca, send_high_risk_alert
# from app.services.report_generator import generate_pdf          # <- Added
# from app.models.audit import AuditResponse, ITCSummary          # <- Added
# from app.utils.auth import get_user_uuid

# logger = logging.getLogger(__name__)
# router = APIRouter(prefix="/audit", tags=["audit"])

# VALID_SECTORS = {
#     "healthcare", "retail", "manufacturing",
#     "it_services", "real_estate", "restaurant", "export_import"
# }


# def _safe_issue_amount(issue) -> float:
#     for attr in ("taxable_value", "amount", "taxable_amount", "itc_at_risk"):
#         val = getattr(issue, attr, None)
#         if val is not None and val != 0:
#             return float(val)
#     return 0.0


# def _get_real_email(email: Optional[str]) -> Optional[str]:
#     """Email valid hai — placeholder/empty nahi."""
#     if not email:
#         return None
#     email = email.strip()
#     if "@placeholder" in email or "auditai.app" in email or "@" not in email:
#         return None
#     return email


# # -- GET /audit/formats ----------------------------------------
# @router.get("/formats")
# async def supported_formats():
#     return get_supported_formats()


# # -- POST /audit -----------------------------------------------
# @router.post("")
# async def run_audit(
#     sales_file:       UploadFile       = File(None),
#     purchase_file:    UploadFile       = File(None),
#     extra_files:      List[UploadFile] = File(None),
#     our_gstin:        str              = Form(...),
#     period:           str              = Form(...),
#     language:         str              = Form(default="en"),
#     sector:           Optional[str]    = Form(default=None),
#     client_id:        Optional[str]    = Form(default=None),
#     x_user_id:        Optional[str]    = Header(default=None),
#     x_user_email:     Optional[str]    = Header(default=None),
#     x_user_name:      Optional[str]    = Header(default=None),
#     filing_delays:    int              = Form(default=0),
#     turnover_cr:      float            = Form(default=1.0),
#     previous_notices: int              = Form(default=0),
# ):
#     if not x_user_id:
#         raise HTTPException(status_code=401, detail="Unauthorized")
#     if sector and sector not in VALID_SECTORS:
#         raise HTTPException(status_code=422, detail=f"Invalid sector: {sector}")
#     if language not in ("en", "hi", "mr"):
#         language = "en"

#     has_sales    = sales_file    and sales_file.filename
#     has_purchase = purchase_file and purchase_file.filename
#     has_extra    = extra_files   and any(f.filename for f in extra_files)

#     if not has_sales and not has_purchase and not has_extra:
#         raise HTTPException(status_code=400, detail="At least one file is required")

#     try:
#         supabase  = get_supabase()
#         user_uuid = get_user_uuid(
#             supabase, x_user_id,
#             email=x_user_email,
#             full_name=x_user_name,
#         )

#         all_invoices = []
#         files_parsed = 0
#         parse_errors = []

#         # -- Parse sales file ------------------------------------
#         if has_sales:
#             try:
#                 sales_bytes    = await sales_file.read()
#                 sales_invoices = parse_any_file(
#                     sales_bytes,
#                     filename=sales_file.filename,
#                     invoice_type="sale",
#                     our_gstin=our_gstin,
#                     period=period,
#                 )
#                 all_invoices.extend(sales_invoices)
#                 files_parsed += 1
#                 logger.info(f"Sales file: {len(sales_invoices)} invoices from {sales_file.filename}")
#             except Exception as e:
#                 parse_errors.append(f"Sales file ({sales_file.filename}): {str(e)}")
#                 logger.warning(f"Sales file parse error: {e}")

#         # -- Parse purchase file ---------------------------------
#         if has_purchase:
#             try:
#                 purchase_bytes    = await purchase_file.read()
#                 purchase_invoices = parse_any_file(
#                     purchase_bytes,
#                     filename=purchase_file.filename,
#                     invoice_type="purchase",
#                     our_gstin=our_gstin,
#                     period=period,
#                 )
#                 all_invoices.extend(purchase_invoices)
#                 files_parsed += 1
#                 logger.info(f"Purchase file: {len(purchase_invoices)} invoices from {purchase_file.filename}")
#             except Exception as e:
#                 parse_errors.append(f"Purchase file ({purchase_file.filename}): {str(e)}")
#                 logger.warning(f"Purchase file parse error: {e}")

#         # -- Parse extra/bulk files (smart type detection) -------
#         if has_extra:
#             for f in extra_files:
#                 if not f.filename:
#                     continue
#                 try:
#                     f_bytes     = await f.read()
#                     fname_lower = f.filename.lower()
#                     if any(k in fname_lower for k in ["sale", "gstr1", "gstr-1", "outward"]):
#                         inv_type = "sale"
#                     elif any(k in fname_lower for k in ["purchase", "gstr2", "gstr-2", "inward", "2b"]):
#                         inv_type = "purchase"
#                     else:
#                         inv_type = "purchase"

#                     extra_invoices = parse_any_file(
#                         f_bytes,
#                         filename=f.filename,
#                         invoice_type=inv_type,
#                         our_gstin=our_gstin,
#                         period=period,
#                     )
#                     all_invoices.extend(extra_invoices)
#                     files_parsed += 1
#                     logger.info(f"Extra file ({inv_type}): {len(extra_invoices)} invoices from {f.filename}")
#                 except Exception as e:
#                     parse_errors.append(f"{f.filename}: {str(e)}")
#                     logger.warning(f"Extra file parse error ({f.filename}): {e}")

#         if not all_invoices:
#             error_detail = "No invoices could be extracted from uploaded files."
#             if parse_errors:
#                 error_detail += f" Errors: {'; '.join(parse_errors[:3])}"
#             raise HTTPException(status_code=422, detail=error_detail)

#         logger.info(f"Total: {len(all_invoices)} invoices from {files_parsed} files")

#         # -- 2. Audit Engine -------------------------------------
#         issues = run_all_checks(all_invoices, our_gstin=our_gstin, period=period)

#         if sector and sector in VALID_SECTORS:
#             issues.extend(run_sector_checks(all_invoices, sector=sector, our_gstin=our_gstin))

#         severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
#         issues.sort(key=lambda x: severity_order.get(x.severity.value, 99))

#         # -- 3. Scoring ------------------------------------------
#         score_result: ScoreResult = calculate_score(issues)

#         issues_json    = [issue.dict() for issue in issues]
#         itc_at_risk    = sum(i.itc_at_risk for i in issues)
#         itc_blocked    = sum(i.itc_at_risk for i in issues if i.issue_type.value == "gstr2b_missing")
#         critical_count = sum(1 for i in issues if i.severity.value == "CRITICAL")
#         high_count     = sum(1 for i in issues if i.severity.value == "HIGH")
#         medium_count   = sum(1 for i in issues if i.severity.value == "MEDIUM")
#         low_count      = sum(1 for i in issues if i.severity.value == "LOW")

#         # -- 4. Notice Simulation --------------------------------
#         notice_issues = [
#             {
#                 "type":       i.issue_type.value,
#                 "severity":   i.severity.value.lower(),
#                 "invoice":    i.invoice_number,
#                 "party":      i.party_name or "N/A",
#                 "amount":     _safe_issue_amount(i),
#                 "tax_impact": i.itc_at_risk or 0,
#             }
#             for i in issues
#         ]

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
#         logger.info(f"Notice simulation: {notice_sim['probability']}% ({notice_sim['risk_level']})")

#         # -- 5. Client name --------------------------------------
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

#         # -- 6. DB Record ----------------------------------------
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
#             "critical_count":     critical_count,
#             "high_count":         high_count,
#             "medium_count":       medium_count,
#             "low_count":          low_count,
#             "notice_probability": notice_sim["probability"],
#             "notice_risk_level":  notice_sim["risk_level"],
#             "notice_simulation": {
#                 "probability":      notice_sim["probability"],
#                 "risk_level":       notice_sim["risk_level"],
#                 "risk_message":     notice_sim["risk_message"],
#                 "risk_areas":       notice_sim["risk_areas"],
#                 "possible_notices": notice_sim["possible_notices"],
#                 "what_if_fix_all":  notice_sim["what_if_fix_all"],
#                 "recommendations":  notice_sim["recommendations"][:5],
#             },
#         }

#         # Field-level retry logic
#         try:
#             supabase.table("audit_reports").insert(audit_record).execute()
#         except Exception as insert_err:
#             logger.warning(f"Insert failed with notice fields: {insert_err}")
#             for key in ["notice_probability", "notice_risk_level", "notice_simulation"]:
#                 audit_record.pop(key, None)
#             try:
#                 supabase.table("audit_reports").insert(audit_record).execute()
#             except Exception as retry_err:
#                 logger.error(f"Insert retry failed: {retry_err}", exc_info=True)
#                 raise HTTPException(status_code=500, detail=f"Failed to save: {str(retry_err)}")

#         # Update client last_score
#         if client_id:
#             try:
#                 supabase.table("clients").update({
#                     "last_score":    score_result.score,
#                     "last_audit_at": "now()",
#                 }).eq("id", client_id).eq("ca_id", x_user_id).execute()
#             except Exception:
#                 pass

#         # -- 7. PDF Generation -----------------------------------  <- Added
#         pdf_bytes = None
#         try:
#             audit_obj = AuditResponse(
#                 audit_id=audit_id,
#                 client_gstin_masked=gstin_masked,
#                 period=period,
#                 compliance_score=score_result.score,
#                 risk_level=score_result.risk_level,
#                 risk_level_translated=score_result.risk_level,
#                 total_invoices=len(all_invoices),
#                 itc_summary=ITCSummary(
#                     at_risk=itc_at_risk,
#                     blocked=itc_blocked,
#                     total=itc_at_risk + itc_blocked,
#                 ),
#                 issues=issues,
#                 language=language,
#                 critical_count=critical_count,
#                 high_count=high_count,
#                 medium_count=medium_count,
#                 low_count=low_count,
#                 created_at=str(__import__("datetime").datetime.utcnow().isoformat()),
#             )
#             pdf_bytes = generate_pdf(
#                 audit_obj,
#                 ca_name=x_user_name or "CA",
#                 client_name=client_name or "Client",
#                 lang=language,
#             )
#             logger.info(f"PDF generated: {len(pdf_bytes)} bytes" if pdf_bytes else "PDF returned empty")
#         except Exception as pdf_err:
#             logger.error(f"PDF generation failed (non-fatal): {pdf_err}", exc_info=True)
#             # pdf_bytes stays None — audit still succeeds

#         # -- 8. Email Alerts -------------------------------------
#         try:
#             ca_email = _get_real_email(x_user_email)
#             ca_name  = x_user_name or "CA"

#             # DB fallback if header email missing
#             if not ca_email:
#                 try:
#                     user_res = (
#                         supabase.table("users")
#                         .select("email, full_name")
#                         .eq("clerk_id", x_user_id)
#                         .limit(1)
#                         .execute()
#                     )
#                     if user_res.data:
#                         ca_email = _get_real_email(user_res.data[0].get("email"))
#                         ca_name  = user_res.data[0].get("full_name") or "CA"
#                 except Exception as ue:
#                     logger.warning(f"Could not fetch user email from DB: {ue}")

#             logger.info(
#                 f"Email debug -> ca_email={ca_email!r} | "
#                 f"x_user_email={x_user_email!r} | "
#                 f"notice_prob={notice_sim.get('probability', 0)}"
#             )

#             # CA audit complete email — pdf_bytes attached         <- Added
#             if ca_email:
#                 sent = send_audit_complete_to_ca(
#                     ca_email=ca_email,
#                     ca_name=ca_name,
#                     client_name=client_name or "Client",
#                     client_gstin=our_gstin,
#                     period=period or "",
#                     score=score_result.score,
#                     risk_level=score_result.risk_level,
#                     issues_count=len(issues),
#                     critical_count=critical_count,
#                     itc_at_risk=float(itc_at_risk),
#                     notice_prob=notice_sim.get("probability", 0),
#                     audit_id=audit_id,
#                     pdf_content=pdf_bytes,                  # <- PDF attached here
#                 )
#                 logger.info(f"CA email {'sent' if sent else 'failed'} -> {ca_email}")
#             else:
#                 logger.warning("CA email skipped — no valid email found")

#             # High risk alert
#             if ca_email and notice_sim.get("probability", 0) >= 50:
#                 sent_alert = send_high_risk_alert(
#                     ca_email=ca_email,
#                     ca_name=ca_name,
#                     client_name=client_name or "Client",
#                     score=score_result.score,
#                     notice_prob=notice_sim.get("probability", 0),
#                     issues=[i.dict() for i in issues if i.severity.value == "CRITICAL"],
#                 )
#                 logger.info(f"High risk alert {'sent' if sent_alert else 'failed'} -> {ca_email}")

#             # Client email                                         <- File 2 feature
#             if client_id:
#                 try:
#                     client_email_res = (
#                         supabase.table("clients")
#                         .select("email, business_name, contact_person")
#                         .eq("id", client_id)
#                         .eq("ca_id", x_user_id)
#                         .limit(1)
#                         .execute()
#                     )
#                     if client_email_res.data:
#                         raw_client_email = client_email_res.data[0].get("email")
#                         client_email     = _get_real_email(raw_client_email)
#                         client_contact   = (
#                             client_email_res.data[0].get("contact_person")
#                             or client_name
#                             or "Sir/Madam"
#                         )

#                         if client_email and client_email != ca_email:
#                             sent_client = send_audit_complete_to_ca(
#                                 ca_email=client_email,
#                                 ca_name=client_contact,
#                                 client_name=client_name or "Your Business",
#                                 client_gstin=our_gstin,
#                                 period=period or "",
#                                 score=score_result.score,
#                                 risk_level=score_result.risk_level,
#                                 issues_count=len(issues),
#                                 critical_count=critical_count,
#                                 itc_at_risk=float(itc_at_risk),
#                                 notice_prob=notice_sim.get("probability", 0),
#                                 audit_id=audit_id,
#                                 pdf_content=pdf_bytes,      # <- PDF to client too
#                             )
#                             logger.info(f"Client email {'sent' if sent_client else 'failed'} -> {client_email}")
#                 except Exception as client_email_err:
#                     logger.warning(f"Client email skipped: {client_email_err}")

#         except Exception as email_err:
#             logger.warning(f"Email alerts skipped: {email_err}", exc_info=True)

#         # -- 9. Return Response ----------------------------------
#         return {
#             "audit_id":          audit_id,
#             "compliance_score":  score_result.score,
#             "risk_level":        score_result.risk_level,
#             "total_invoices":    len(all_invoices),
#             "files_parsed":      files_parsed,
#             "parse_errors":      parse_errors[:5] if parse_errors else [],
#             "issues":            issues_json,
#             "itc_at_risk":       itc_at_risk,
#             "critical_count":    critical_count,
#             "high_count":        high_count,
#             "medium_count":      medium_count,
#             "low_count":         low_count,
#             "notice_simulation": notice_sim,
#             "pdf_generated":     pdf_bytes is not None,
#             "message":           "Audit complete",
#         }

#     except HTTPException:
#         raise
#     except Exception as e:
#         logger.error(f"run_audit error: {e}", exc_info=True)
#         raise HTTPException(status_code=500, detail=f"Audit failed: {str(e)}")


# # -- GET /audit/{id} -------------------------------------------
# @router.get("/{audit_id}")
# async def get_audit(
#     audit_id:     str,
#     x_user_id:    Optional[str] = Header(default=None),
#     x_user_email: Optional[str] = Header(default=None),
#     x_user_name:  Optional[str] = Header(default=None),
# ):
#     if not x_user_id:
#         raise HTTPException(status_code=401, detail="Unauthorized")

#     supabase  = get_supabase()
#     user_uuid = get_user_uuid(
#         supabase, x_user_id,
#         email=x_user_email,
#         full_name=x_user_name,
#     )

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


# # -- POST /audit/{id}/notice -----------------------------------
# @router.post("/{audit_id}/notice")
# async def rerun_notice_simulation(
#     audit_id:         str,
#     filing_delays:    int   = Form(default=0),
#     turnover_cr:      float = Form(default=1.0),
#     previous_notices: int   = Form(default=0),
#     language:         str   = Form(default="en"),
#     x_user_id:        Optional[str] = Header(default=None),
#     x_user_email:     Optional[str] = Header(default=None),
#     x_user_name:      Optional[str] = Header(default=None),
# ):
#     if not x_user_id:
#         raise HTTPException(status_code=401, detail="Unauthorized")

#     supabase  = get_supabase()
#     user_uuid = get_user_uuid(
#         supabase, x_user_id,
#         email=x_user_email,
#         full_name=x_user_name,
#     )

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

#         row         = res.data[0]
#         issues_json = row.get("issues_json", [])

#         notice_issues = [
#             {
#                 "type":       issue.get("issue_type", "unknown"),
#                 "severity":   issue.get("severity", "medium").lower(),
#                 "invoice":    issue.get("invoice_number", "N/A"),
#                 "party":      issue.get("party_name", "N/A"),
#                 "amount":     issue.get("itc_at_risk", 0),
#                 "tax_impact": issue.get("itc_at_risk", 0),
#             }
#             for issue in issues_json
#         ]

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
#                 "notice_simulation": {
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
#             "audit_id":          audit_id,
#             "notice_simulation": notice_sim,
#             "message":           "Notice simulation updated",
#         }
#     except HTTPException:
#         raise
#     except Exception as e:
#         logger.error(f"rerun_notice error: {e}", exc_info=True)
#         raise HTTPException(status_code=500, detail=str(e))

"""
routers/audit.py
----------------
Same as existing — sirf 2 fixes:
1. get_audit() mein "undefined" UUID guard
2. get_task_status() mein audit_id clearly return karta hai
"""
from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from typing import Optional, List
import logging
import tempfile
import os

from app.core.dependencies import AuditDeps, get_audit_deps

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/audit", tags=["audit"])

VALID_SECTORS = {
    "healthcare", "retail", "manufacturing",
    "it_services", "real_estate", "restaurant", "export_import"
}

MAX_FILE_SIZE = 25 * 1024 * 1024  # 25MB
CHUNK_SIZE    = 1 * 1024 * 1024   # 1MB


async def _save_to_temp(upload: UploadFile) -> tuple[str, int]:
    total  = 0
    suffix = os.path.splitext(upload.filename)[1] or ".tmp"
    fd, path = tempfile.mkstemp(suffix=suffix)
    try:
        with os.fdopen(fd, "wb") as tmp:
            while True:
                chunk = await upload.read(CHUNK_SIZE)
                if not chunk:
                    break
                total += len(chunk)
                if total > MAX_FILE_SIZE:
                    os.unlink(path)
                    raise HTTPException(
                        status_code=413,
                        detail=f"{upload.filename}: File too large. Max 25MB allowed."
                    )
                tmp.write(chunk)
    except HTTPException:
        raise
    except Exception as e:
        if os.path.exists(path):
            os.unlink(path)
        raise HTTPException(status_code=422, detail=f"File read failed: {e}")
    return path, total


# ── GET /audit/formats ────────────────────────────────────────
@router.get("/formats")
async def supported_formats():
    from app.services.file_router import get_supported_formats
    return get_supported_formats()


# ── GET /audit/status/{task_id} ───────────────────────────────
@router.get("/status/{task_id}")
async def get_task_status(task_id: str):
    """
    Celery task status poll karo.
    Frontend 3 sec interval pe ye call kare.
    Response includes audit_id when completed.
    """
    # Guard — invalid task_id
    if not task_id or task_id in ("undefined", "null") or len(task_id) < 8:
        raise HTTPException(status_code=400, detail="Invalid task ID")

    try:
        from app.workers.celery_app import celery_app
        task = celery_app.AsyncResult(task_id)

        if task.state == "PENDING":
            return {
                "task_id": task_id,
                "status":  "pending",
                "progress": 0,
            }

        if task.state == "STARTED":
            return {
                "task_id": task_id,
                "status":  "processing",
                "progress": 30,
            }

        if task.state == "SUCCESS":
            result   = task.result or {}
            audit_id = result.get("audit_id") if isinstance(result, dict) else None
            return {
                "task_id":  task_id,
                "status":   "completed",
                "progress": 100,
                "audit_id": audit_id,          # ← Frontend yahi use karta hai
                "result":   result,
            }

        if task.state == "FAILURE":
            return {
                "task_id": task_id,
                "status":  "failed",
                "error":   str(task.info),
            }

        # RETRY, REVOKED, etc.
        return {
            "task_id": task_id,
            "status":  task.state.lower(),
            "progress": 10,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"get_task_status error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ── POST /audit ───────────────────────────────────────────────
@router.post("")
async def run_audit(
    sales_file:       UploadFile       = File(None),
    purchase_file:    UploadFile       = File(None),
    extra_files:      List[UploadFile] = File(None),
    our_gstin:        str              = Form(...),
    period:           str              = Form(...),
    language:         str              = Form(default="en"),
    sector:           Optional[str]    = Form(default=None),
    client_id:        Optional[str]    = Form(default=None),
    filing_delays:    int              = Form(default=0),
    turnover_cr:      float            = Form(default=1.0),
    previous_notices: int              = Form(default=0),
    deps:             AuditDeps        = Depends(get_audit_deps),
):
    if sector and sector not in VALID_SECTORS:
        raise HTTPException(status_code=422, detail=f"Invalid sector: {sector}")
    if language not in ("en", "hi", "mr"):
        language = "en"

    has_files = (
        (sales_file    and sales_file.filename)    or
        (purchase_file and purchase_file.filename) or
        (extra_files   and any(f.filename for f in extra_files))
    )
    if not has_files:
        raise HTTPException(status_code=400, detail="At least one file is required")

    # Save to temp disk
    sales_path    = None
    purchase_path = None
    extra_paths   = []

    if sales_file and sales_file.filename:
        sales_path, sz = await _save_to_temp(sales_file)
        logger.info(f"Sales saved: {sz/1024:.1f}KB")

    if purchase_file and purchase_file.filename:
        purchase_path, sz = await _save_to_temp(purchase_file)
        logger.info(f"Purchase saved: {sz/1024:.1f}KB")

    if extra_files:
        for f in extra_files:
            if f.filename:
                path, sz = await _save_to_temp(f)
                extra_paths.append((path, f.filename))

    # Try Celery background task
    try:
        from app.workers.audit_tasks import run_audit_task

        task = run_audit_task.delay(
            sales_path        = sales_path,
            sales_filename    = sales_file.filename if sales_path else None,
            purchase_path     = purchase_path,
            purchase_filename = purchase_file.filename if purchase_path else None,
            extra_paths       = extra_paths,
            our_gstin         = our_gstin,
            period            = period,
            language          = language,
            sector            = sector,
            client_id         = client_id,
            filing_delays     = filing_delays,
            turnover_cr       = turnover_cr,
            previous_notices  = previous_notices,
            user_uuid         = deps.user_uuid,
            ca_id             = deps.ca_id,
            ca_email          = deps.ca_email,
            ca_name           = deps.ca_name,
        )

        logger.info(f"Audit task queued: {task.id}")
        return {
            "task_id":  task.id,
            "status":   "queued",
            "message":  "Audit started in background.",
            "poll_url": f"/audit/status/{task.id}",
        }

    except Exception as celery_err:
        # Fallback: sync run
        logger.warning(f"Celery unavailable ({celery_err}) — sync fallback")

        sales_bytes     = None
        purchase_bytes  = None
        extra_file_data = []

        if sales_path and os.path.exists(sales_path):
            with open(sales_path, "rb") as f:
                sales_bytes = f.read()
            os.unlink(sales_path)

        if purchase_path and os.path.exists(purchase_path):
            with open(purchase_path, "rb") as f:
                purchase_bytes = f.read()
            os.unlink(purchase_path)

        for path, fname in extra_paths:
            if os.path.exists(path):
                with open(path, "rb") as f:
                    extra_file_data.append((f.read(), fname))
                os.unlink(path)

        from app.services.audit_service import AuditService
        service = AuditService(deps)
        result  = service.run(
            sales_bytes       = sales_bytes,
            sales_filename    = sales_file.filename if sales_bytes else None,
            purchase_bytes    = purchase_bytes,
            purchase_filename = purchase_file.filename if purchase_bytes else None,
            extra_files       = extra_file_data,
            our_gstin         = our_gstin,
            period            = period,
            language          = language,
            sector            = sector,
            client_id         = client_id,
            filing_delays     = filing_delays,
            turnover_cr       = turnover_cr,
            previous_notices  = previous_notices,
        )
        result["status"] = "completed"
        return result


# ── GET /audit/{audit_id} ─────────────────────────────────────
@router.get("/{audit_id}")
async def get_audit(
    audit_id: str,
    deps:     AuditDeps = Depends(get_audit_deps),
):
    # ── Guard: "undefined" string se protect karo ─────────────
    if not audit_id or audit_id in ("undefined", "null") or len(audit_id) < 8:
        raise HTTPException(
            status_code=400,
            detail="Invalid audit ID. Please run a new audit."
        )

    row = deps.audit_repo.get_by_id(audit_id, deps.user_uuid)
    if not row:
        raise HTTPException(status_code=404, detail="Audit not found")

    return {
        **row,
        "total_invoices":      row.get("total_invoices_scanned"),
        "client_name":         row.get("client_name") or "Audit",
        "client_gstin_masked": row.get("client_gstin_masked"),
    }


# ── POST /audit/{audit_id}/notice ─────────────────────────────
@router.post("/{audit_id}/notice")
async def rerun_notice_simulation(
    audit_id:         str,
    filing_delays:    int   = Form(default=0),
    turnover_cr:      float = Form(default=1.0),
    previous_notices: int   = Form(default=0),
    language:         str   = Form(default="en"),
    deps:             AuditDeps = Depends(get_audit_deps),
):
    if not audit_id or audit_id in ("undefined", "null") or len(audit_id) < 8:
        raise HTTPException(status_code=400, detail="Invalid audit ID")

    row = deps.audit_repo.get_by_id(audit_id, deps.user_uuid)
    if not row:
        raise HTTPException(status_code=404, detail="Audit not found")

    from app.services.notice_simulator import run_notice_simulation

    notice_sim = run_notice_simulation(
        issues=[
            {
                "type":       i.get("issue_type", "unknown"),
                "severity":   i.get("severity", "medium").lower(),
                "invoice":    i.get("invoice_number", "N/A"),
                "party":      i.get("party_name", "N/A"),
                "amount":     i.get("itc_at_risk", 0),
                "tax_impact": i.get("itc_at_risk", 0),
            }
            for i in (row.get("issues_json", []))
        ],
        compliance_score = row.get("compliance_score", 50),
        client_name      = row.get("client_name", ""),
        client_gstin     = row.get("client_gstin_masked", ""),
        lang             = language,
        filing_delays    = filing_delays,
        turnover_cr      = turnover_cr,
        previous_notices = previous_notices,
    )

    deps.audit_repo.update_notice_simulation(audit_id, {
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
    })

    return {"audit_id": audit_id, "notice_simulation": notice_sim, "message": "Updated"}