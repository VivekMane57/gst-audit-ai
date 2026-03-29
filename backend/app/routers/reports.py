# """
# routers/reports.py
# ------------------
# GET /reports              — All audits for this CA (with client_name joined)
# GET /reports/{id}         — Single audit detail
# GET /reports/{id}/pdf     — Download PDF
# GET /reports/suppliers    — Supplier trust scores extracted from all audits
# """
# from fastapi import APIRouter, Header, HTTPException
# from fastapi.responses import StreamingResponse
# from app.db.supabase_client import get_supabase
# from app.services.report_generator import generate_pdf
# from app.models.audit import AuditResponse, ITCSummary
# from app.models.issue import Issue
# from app.utils.auth import get_user_uuid
# import io
# import logging

# logger = logging.getLogger(__name__)
# router = APIRouter(prefix="/reports", tags=["reports"])


# def _get_ca_id(x_user_id: str | None) -> str:
#     if not x_user_id:
#         raise HTTPException(status_code=401, detail="Unauthorized")
#     return x_user_id


# def _ensure_user(x_user_id: str) -> None:
#     supabase = get_supabase()
#     get_user_uuid(supabase, x_user_id)


# def _build_audit_response(row: dict, lang: str = "en") -> AuditResponse:
#     from app.services.score_calculator import get_risk_level_translated

#     itc_raw = row.get("itc_summary") or {}
#     issues  = [Issue(**i) for i in (row.get("issues_json") or [])]

#     at_risk = float(itc_raw.get("at_risk",      row.get("itc_at_risk",  0) or 0))
#     blocked = float(itc_raw.get("blocked",       row.get("itc_blocked",  0) or 0))
#     total   = float(itc_raw.get("total_impact",  at_risk + blocked))

#     score      = row.get("compliance_score", 0) or 0
#     risk_level = row.get("risk_level", "HIGH") or "HIGH"

#     return AuditResponse(
#         audit_id              = row["id"],
#         client_gstin_masked   = row.get("client_gstin_masked") or "",
#         period                = row.get("period") or "",
#         language              = lang,
#         compliance_score      = score,
#         risk_level            = risk_level,
#         risk_level_translated = get_risk_level_translated(score, lang),
#         total_invoices        = row.get("total_invoices_scanned") or row.get("total_invoices") or 0,
#         issues                = issues,
#         critical_count        = row.get("critical_count") or sum(1 for i in issues if i.severity.value == "CRITICAL"),
#         high_count            = row.get("high_count")     or sum(1 for i in issues if i.severity.value == "HIGH"),
#         medium_count          = row.get("medium_count")   or sum(1 for i in issues if i.severity.value == "MEDIUM"),
#         low_count             = row.get("low_count")      or sum(1 for i in issues if i.severity.value == "LOW"),
#         itc_summary           = ITCSummary(
#             at_risk  = at_risk,
#             blocked  = blocked,
#             total    = total,
#             eligible = float(row.get("itc_eligible") or 0),
#         ),
#         pdf_url    = row.get("pdf_url"),
#         created_at = row.get("created_at") or "",
#     )


# # ── GET /reports ───────────────────────────────────────────────
# @router.get("")
# async def get_all_reports(x_user_id: str | None = Header(default=None)):
#     ca_id = _get_ca_id(x_user_id)
#     _ensure_user(ca_id)
#     supabase = get_supabase()

#     try:
#         res = (
#             supabase.table("audit_reports")
#             .select(
#                 "id, period, compliance_score, risk_level, "
#                 "total_invoices_scanned, itc_summary, itc_at_risk, "
#                 "issues_json, "
#                 "sector, language, created_at, client_id, "
#                 "client_name, client_gstin_masked, "
#                 "critical_count, high_count, medium_count, low_count"
#             )
#             .eq("ca_id", ca_id)
#             .order("created_at", desc=True)
#             .limit(100)
#             .execute()
#         )

#         reports = []
#         for row in (res.data or []):
#             itc_raw   = row.get("itc_summary") or {}
#             at_risk   = itc_raw.get("at_risk") or row.get("itc_at_risk") or 0
#             reports.append({
#                 "id":               row["id"],
#                 "period":           row.get("period"),
#                 "compliance_score": row.get("compliance_score", 0),
#                 "risk_level":       row.get("risk_level"),
#                 "total_invoices":   row.get("total_invoices_scanned") or 0,
#                 "itc_summary":      itc_raw,
#                 "itc_at_risk":      at_risk,
#                 "issues_json":      row.get("issues_json") or [],
#                 "sector":           row.get("sector"),
#                 "language":         row.get("language", "en"),
#                 "created_at":       row.get("created_at"),
#                 "client_id":        row.get("client_id"),
#                 "client_name":      row.get("client_name") or "Audit",
#                 "client_gstin_masked": row.get("client_gstin_masked"),
#                 "critical_count":   row.get("critical_count", 0),
#                 "high_count":       row.get("high_count", 0),
#                 "medium_count":     row.get("medium_count", 0),
#                 "low_count":        row.get("low_count", 0),
#             })

#         return {"reports": reports, "total": len(reports)}

#     except Exception as e:
#         logger.error(f"get_all_reports error: {e}", exc_info=True)
#         raise HTTPException(status_code=500, detail=str(e))


# # ── GET /reports/suppliers — Supplier Trust Scores ─────────────
# @router.get("/suppliers")
# async def get_supplier_trust_scores(x_user_id: str | None = Header(default=None)):
#     """
#     All audit reports se supplier data extract karke trust scores return karo.
#     Frontend Suppliers page isko directly call kar sakta hai.
#     """
#     ca_id = _get_ca_id(x_user_id)
#     _ensure_user(ca_id)
#     supabase = get_supabase()

#     try:
#         res = (
#             supabase.table("audit_reports")
#             .select("id, issues_json, period, client_name, client_gstin_masked")
#             .eq("ca_id", ca_id)
#             .order("created_at", desc=True)
#             .limit(200)
#             .execute()
#         )

#         # Extract suppliers from all audit issues
#         supplier_map: dict = {}

#         for report in (res.data or []):
#             issues = report.get("issues_json") or []
#             for issue in issues:
#                 # Identify supplier by GSTIN or party name
#                 gstin = (issue.get("party_gstin") or "").upper().strip()
#                 name  = issue.get("party_name") or ""
#                 key   = gstin if len(gstin) >= 15 else name or issue.get("invoice_number", "UNKNOWN")

#                 if not key or key == "UNKNOWN":
#                     continue

#                 if key not in supplier_map:
#                     supplier_map[key] = {
#                         "gstin":           gstin if len(gstin) >= 15 else "N/A",
#                         "gstin_masked":    f"{gstin[:2]}{'*' * 10}{gstin[-3:]}" if len(gstin) >= 15 else "N/A",
#                         "name":            name or key,
#                         "state_code":      gstin[:2] if len(gstin) >= 2 else "??",
#                         "total_invoices":  0,
#                         "total_amount":    0,
#                         "total_tax":       0,
#                         "trust_score":     100,
#                         "risk_level":      "LOW",
#                         "in_gstr2b":       True,
#                         "amount_mismatch": False,
#                         "invalid_gstin":   False,
#                         "issues":          [],
#                         "audits":          [],
#                     }

#                 supplier = supplier_map[key]
#                 supplier["total_invoices"] += 1
#                 supplier["total_amount"]   += float(issue.get("taxable_value") or issue.get("itc_at_risk") or 0)
#                 supplier["total_tax"]      += float(issue.get("itc_at_risk") or 0)

#                 # Track which audits this supplier appeared in
#                 audit_id = report.get("id")
#                 if audit_id and audit_id not in supplier["audits"]:
#                     supplier["audits"].append(audit_id)

#                 # Add issue detail
#                 supplier["issues"].append({
#                     "type":        issue.get("issue_type") or issue.get("type") or "unknown",
#                     "severity":    (issue.get("severity") or "medium").lower(),
#                     "description": issue.get("description") or issue.get("message") or "",
#                     "invoice":     issue.get("invoice_number") or "",
#                     "amount":      float(issue.get("itc_at_risk") or 0),
#                     "period":      report.get("period") or "",
#                     "fix_steps":   issue.get("fix_steps") or issue.get("fix") or "",
#                 })

#                 # Score deductions based on severity
#                 severity = (issue.get("severity") or "").lower()
#                 if severity == "critical":
#                     supplier["trust_score"] -= 25
#                 elif severity == "high":
#                     supplier["trust_score"] -= 15
#                 elif severity == "medium":
#                     supplier["trust_score"] -= 8
#                 else:
#                     supplier["trust_score"] -= 3

#                 # Flag specific issue types
#                 issue_type = (issue.get("issue_type") or issue.get("type") or "").lower()
#                 if "gstr2b" in issue_type or "missing" in issue_type or "not_in_2b" in issue_type:
#                     supplier["in_gstr2b"] = False
#                 if "mismatch" in issue_type or "amount" in issue_type:
#                     supplier["amount_mismatch"] = True
#                 if "invalid" in issue_type or "gstin" in issue_type:
#                     supplier["invalid_gstin"] = True

#         # Normalize scores and assign risk levels
#         suppliers = []
#         for s in supplier_map.values():
#             s["trust_score"] = max(0, min(100, s["trust_score"]))
#             if s["trust_score"] >= 70:
#                 s["risk_level"] = "LOW"
#             elif s["trust_score"] >= 40:
#                 s["risk_level"] = "MEDIUM"
#             else:
#                 s["risk_level"] = "HIGH"

#             # Recommendation text
#             if s["trust_score"] < 40:
#                 s["recommendation"] = f"⚠️ Contact {s['name']} immediately. ITC ₹{s['total_tax']:,.0f} at risk. Consider switching supplier."
#             elif s["trust_score"] < 70:
#                 s["recommendation"] = f"🔍 Monitor {s['name']} closely. Verify invoice amounts and follow up on discrepancies."
#             else:
#                 s["recommendation"] = f"✅ {s['name']} is filing correctly. Continue regular monitoring."

#             s["total_audits"] = len(s.get("audits", []))
#             s.pop("audits", None)  # Don't send audit IDs to frontend
#             suppliers.append(s)

#         # Sort by trust score ascending (worst first)
#         suppliers.sort(key=lambda x: x["trust_score"])

#         # Stats
#         high_risk   = sum(1 for s in suppliers if s["risk_level"] == "HIGH")
#         medium_risk = sum(1 for s in suppliers if s["risk_level"] == "MEDIUM")
#         low_risk    = sum(1 for s in suppliers if s["risk_level"] == "LOW")
#         total_itc   = sum(s["total_tax"] for s in suppliers)

#         return {
#             "suppliers": suppliers,
#             "total":     len(suppliers),
#             "stats": {
#                 "high_risk":      high_risk,
#                 "medium_risk":    medium_risk,
#                 "low_risk":       low_risk,
#                 "total_itc_risk": total_itc,
#             },
#         }

#     except Exception as e:
#         logger.error(f"get_supplier_trust_scores error: {e}", exc_info=True)
#         raise HTTPException(status_code=500, detail=str(e))


# # ── GET /reports/{id} ─────────────────────────────────────────
# @router.get("/{report_id}")
# async def get_report(
#     report_id: str,
#     lang: str  = "en",
#     x_user_id: str | None = Header(default=None),
# ):
#     ca_id = _get_ca_id(x_user_id)
#     _ensure_user(ca_id)
#     supabase = get_supabase()

#     try:
#         res = (
#             supabase.table("audit_reports")
#             .select("*")
#             .eq("id", report_id)
#             .eq("ca_id", ca_id)
#             .limit(1)
#             .execute()
#         )

#         if not res.data:
#             raise HTTPException(status_code=404, detail="Report not found")

#         row = res.data[0]
#         return {
#             **row,
#             "total_invoices":      row.get("total_invoices_scanned") or row.get("total_invoices") or 0,
#             "client_name":         row.get("client_name") or "Audit",
#             "client_gstin_masked": row.get("client_gstin_masked") or "",
#         }

#     except HTTPException:
#         raise
#     except Exception as e:
#         logger.error(f"get_report error: {e}", exc_info=True)
#         raise HTTPException(status_code=500, detail=str(e))


# # ── GET /reports/{id}/pdf ─────────────────────────────────────
# @router.get("/{report_id}/pdf")
# async def download_pdf(
#     report_id: str,
#     lang: str  = "en",
#     x_user_id: str | None = Header(default=None),
# ):
#     ca_id = _get_ca_id(x_user_id)
#     supabase = get_supabase()

#     try:
#         res = (
#             supabase.table("audit_reports")
#             .select("*")
#             .eq("id", report_id)
#             .eq("ca_id", ca_id)
#             .limit(1)
#             .execute()
#         )

#         if not res.data:
#             raise HTTPException(status_code=404, detail="Report not found")

#         row         = res.data[0]
#         client_name = row.get("client_name") or "Client"

#         audit_obj = _build_audit_response(row, lang=lang)

#         pdf_bytes = generate_pdf(
#             audit_obj,
#             client_name = client_name,
#             lang        = lang,
#         )

#         return StreamingResponse(
#             io.BytesIO(pdf_bytes),
#             media_type="application/pdf",
#             headers={
#                 "Content-Disposition": (
#                     f'attachment; filename="GST_Audit_{row.get("period", report_id[:8])}.pdf"'
#                 )
#             },
#         )

#     except HTTPException:
#         raise
#     except Exception as e:
#         logger.error(f"download_pdf error: {e}", exc_info=True)
#         raise HTTPException(status_code=500, detail=str(e))


"""
routers/reports.py  (Clean Architecture version)
-------------------------------------------------
Thin router — sirf HTTP in/out.
DB calls → AuditRepository mein.
PDF logic → report_generator service mein.
"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
import io
import logging

from app.core.dependencies import ReportDeps, get_report_deps
from app.services.report_generator import generate_pdf
from app.models.audit import AuditResponse, ITCSummary
from app.models.issue import Issue

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/reports", tags=["reports"])


# ── GET /reports ──────────────────────────────────────────────
@router.get("")
async def get_all_reports(deps: ReportDeps = Depends(get_report_deps)):
    try:
        rows = deps.audit_repo.list_by_ca(deps.ca_id)
        reports = []
        for row in rows:
            itc_raw = row.get("itc_summary") or {}
            reports.append({
                "id":                  row["id"],
                "period":              row.get("period"),
                "compliance_score":    row.get("compliance_score", 0),
                "risk_level":          row.get("risk_level"),
                "total_invoices":      row.get("total_invoices_scanned") or 0,
                "itc_summary":         itc_raw,
                "itc_at_risk":         itc_raw.get("at_risk") or row.get("itc_at_risk") or 0,
                "issues_json":         row.get("issues_json") or [],
                "sector":              row.get("sector"),
                "language":            row.get("language", "en"),
                "created_at":          row.get("created_at"),
                "client_id":           row.get("client_id"),
                "client_name":         row.get("client_name") or "Audit",
                "client_gstin_masked": row.get("client_gstin_masked"),
                "critical_count":      row.get("critical_count", 0),
                "high_count":          row.get("high_count", 0),
                "medium_count":        row.get("medium_count", 0),
                "low_count":           row.get("low_count", 0),
            })
        return {"reports": reports, "total": len(reports)}
    except Exception as e:
        logger.error(f"get_all_reports error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ── GET /reports/suppliers ────────────────────────────────────
@router.get("/suppliers")
async def get_supplier_trust_scores(deps: ReportDeps = Depends(get_report_deps)):
    try:
        rows    = deps.audit_repo.list_issues_for_suppliers(deps.ca_id)
        return _build_supplier_report(rows)
    except Exception as e:
        logger.error(f"get_supplier_trust_scores error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ── GET /reports/{id} ─────────────────────────────────────────
@router.get("/{report_id}")
async def get_report(
    report_id: str,
    deps: ReportDeps = Depends(get_report_deps),
):
    row = deps.audit_repo.get_by_id_for_ca(report_id, deps.ca_id)
    if not row:
        raise HTTPException(status_code=404, detail="Report not found")
    return {
        **row,
        "total_invoices":      row.get("total_invoices_scanned") or 0,
        "client_name":         row.get("client_name") or "Audit",
        "client_gstin_masked": row.get("client_gstin_masked") or "",
    }


# ── GET /reports/{id}/pdf ─────────────────────────────────────
@router.get("/{report_id}/pdf")
async def download_pdf(
    report_id: str,
    lang: str  = "en",
    deps: ReportDeps = Depends(get_report_deps),
):
    row = deps.audit_repo.get_by_id_for_ca(report_id, deps.ca_id)
    if not row:
        raise HTTPException(status_code=404, detail="Report not found")

    try:
        audit_obj = _build_audit_response(row, lang)
        pdf_bytes = generate_pdf(
            audit_obj,
            client_name = row.get("client_name") or "Client",
            lang        = lang,
        )
        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type = "application/pdf",
            headers    = {
                "Content-Disposition": (
                    f'attachment; filename="GST_Audit_{row.get("period", report_id[:8])}.pdf"'
                )
            },
        )
    except Exception as e:
        logger.error(f"download_pdf error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ── Helpers ───────────────────────────────────────────────────

def _build_audit_response(row: dict, lang: str = "en") -> AuditResponse:
    from app.services.score_calculator import get_risk_level_translated
    itc_raw = row.get("itc_summary") or {}
    issues  = [Issue(**i) for i in (row.get("issues_json") or [])]
    at_risk = float(itc_raw.get("at_risk",     row.get("itc_at_risk", 0) or 0))
    blocked = float(itc_raw.get("blocked",      row.get("itc_blocked", 0) or 0))
    total   = float(itc_raw.get("total_impact", at_risk + blocked))
    score   = row.get("compliance_score", 0) or 0
    risk    = row.get("risk_level", "HIGH") or "HIGH"

    return AuditResponse(
        audit_id              = row["id"],
        client_gstin_masked   = row.get("client_gstin_masked") or "",
        period                = row.get("period") or "",
        language              = lang,
        compliance_score      = score,
        risk_level            = risk,
        risk_level_translated = get_risk_level_translated(score, lang),
        total_invoices        = row.get("total_invoices_scanned") or 0,
        issues                = issues,
        critical_count        = row.get("critical_count") or sum(1 for i in issues if i.severity.value == "CRITICAL"),
        high_count            = row.get("high_count")     or sum(1 for i in issues if i.severity.value == "HIGH"),
        medium_count          = row.get("medium_count")   or sum(1 for i in issues if i.severity.value == "MEDIUM"),
        low_count             = row.get("low_count")      or sum(1 for i in issues if i.severity.value == "LOW"),
        itc_summary           = ITCSummary(at_risk=at_risk, blocked=blocked, total=total,
                                           eligible=float(row.get("itc_eligible") or 0)),
        pdf_url               = row.get("pdf_url"),
        created_at            = row.get("created_at") or "",
    )


def _build_supplier_report(rows: list[dict]) -> dict:
    supplier_map: dict = {}

    for report in rows:
        for issue in (report.get("issues_json") or []):
            gstin = (issue.get("party_gstin") or "").upper().strip()
            name  = issue.get("party_name") or ""
            key   = gstin if len(gstin) >= 15 else name or issue.get("invoice_number", "UNKNOWN")
            if not key or key == "UNKNOWN":
                continue

            if key not in supplier_map:
                supplier_map[key] = {
                    "gstin":           gstin if len(gstin) >= 15 else "N/A",
                    "gstin_masked":    f"{gstin[:2]}{'*' * 10}{gstin[-3:]}" if len(gstin) >= 15 else "N/A",
                    "name":            name or key,
                    "state_code":      gstin[:2] if len(gstin) >= 2 else "??",
                    "total_invoices":  0,
                    "total_amount":    0,
                    "total_tax":       0,
                    "trust_score":     100,
                    "risk_level":      "LOW",
                    "in_gstr2b":       True,
                    "amount_mismatch": False,
                    "invalid_gstin":   False,
                    "issues":          [],
                    "audits":          [],
                }

            s = supplier_map[key]
            s["total_invoices"] += 1
            s["total_amount"]   += float(issue.get("taxable_value") or issue.get("itc_at_risk") or 0)
            s["total_tax"]      += float(issue.get("itc_at_risk") or 0)

            audit_id = report.get("id")
            if audit_id and audit_id not in s["audits"]:
                s["audits"].append(audit_id)

            s["issues"].append({
                "type":        issue.get("issue_type") or "unknown",
                "severity":    (issue.get("severity") or "medium").lower(),
                "description": issue.get("description") or "",
                "invoice":     issue.get("invoice_number") or "",
                "amount":      float(issue.get("itc_at_risk") or 0),
                "period":      report.get("period") or "",
                "fix_steps":   issue.get("fix_steps") or "",
            })

            severity = (issue.get("severity") or "").lower()
            deduction = {"critical": 25, "high": 15, "medium": 8}.get(severity, 3)
            s["trust_score"] -= deduction

            issue_type = (issue.get("issue_type") or "").lower()
            if "gstr2b" in issue_type or "missing" in issue_type:
                s["in_gstr2b"] = False
            if "mismatch" in issue_type or "amount" in issue_type:
                s["amount_mismatch"] = True
            if "invalid" in issue_type or "gstin" in issue_type:
                s["invalid_gstin"] = True

    suppliers = []
    for s in supplier_map.values():
        s["trust_score"] = max(0, min(100, s["trust_score"]))
        s["risk_level"]  = "LOW" if s["trust_score"] >= 70 else "MEDIUM" if s["trust_score"] >= 40 else "HIGH"
        if s["trust_score"] < 40:
            s["recommendation"] = f"⚠️ Contact {s['name']} immediately. ITC ₹{s['total_tax']:,.0f} at risk."
        elif s["trust_score"] < 70:
            s["recommendation"] = f"🔍 Monitor {s['name']} closely. Follow up on discrepancies."
        else:
            s["recommendation"] = f"✅ {s['name']} is filing correctly."
        s["total_audits"] = len(s.get("audits", []))
        s.pop("audits", None)
        suppliers.append(s)

    suppliers.sort(key=lambda x: x["trust_score"])
    return {
        "suppliers": suppliers,
        "total":     len(suppliers),
        "stats": {
            "high_risk":      sum(1 for s in suppliers if s["risk_level"] == "HIGH"),
            "medium_risk":    sum(1 for s in suppliers if s["risk_level"] == "MEDIUM"),
            "low_risk":       sum(1 for s in suppliers if s["risk_level"] == "LOW"),
            "total_itc_risk": sum(s["total_tax"] for s in suppliers),
        },
    }