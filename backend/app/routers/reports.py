# """
# routers/reports.py
# ------------------
# GET /reports        — All audits for this CA (with client_name joined)
# GET /reports/{id}   — Single audit detail
# GET /reports/{id}/pdf — Download PDF
# """
# from fastapi import APIRouter, Header, HTTPException
# from fastapi.responses import StreamingResponse
# from app.db.supabase_client import get_supabase
# from app.services.report_generator import generate_pdf
# from app.models.audit import AuditResponse, ITCSummary
# from app.models.issue import Issue
# import io
# import logging

# logger = logging.getLogger(__name__)
# router = APIRouter(prefix="/reports", tags=["reports"])


# def _get_ca_id(x_user_id: str | None) -> str:
#     if not x_user_id:
#         raise HTTPException(status_code=401, detail="Unauthorized")
#     return x_user_id


# def _build_audit_response(row: dict, lang: str = "en") -> AuditResponse:
#     """DB row dict → AuditResponse object."""
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
#     ca_id    = _get_ca_id(x_user_id)
#     supabase = get_supabase()

#     try:
#         res = (
#             supabase.table("audit_reports")
#             .select(
#                 "id, period, compliance_score, risk_level, "
#                 "total_invoices_scanned, itc_summary, itc_at_risk, "
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


# # ── GET /reports/{id} ─────────────────────────────────────────
# @router.get("/{report_id}")
# async def get_report(
#     report_id: str,
#     lang: str  = "en",
#     x_user_id: str | None = Header(default=None),
# ):
#     ca_id    = _get_ca_id(x_user_id)
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
#     ca_id    = _get_ca_id(x_user_id)
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
routers/reports.py
------------------
GET /reports        — All audits for this CA (with client_name joined)
GET /reports/{id}   — Single audit detail
GET /reports/{id}/pdf — Download PDF
"""
from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import StreamingResponse
from app.db.supabase_client import get_supabase
from app.services.report_generator import generate_pdf
from app.models.audit import AuditResponse, ITCSummary
from app.models.issue import Issue
from app.utils.auth import get_user_uuid
import io
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/reports", tags=["reports"])


def _get_ca_id(x_user_id: str | None) -> str:
    if not x_user_id:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return x_user_id


def _ensure_user(x_user_id: str) -> None:
    """Ensure user exists in DB — auto-create if not."""
    supabase = get_supabase()
    get_user_uuid(supabase, x_user_id)


def _build_audit_response(row: dict, lang: str = "en") -> AuditResponse:
    from app.services.score_calculator import get_risk_level_translated

    itc_raw = row.get("itc_summary") or {}
    issues  = [Issue(**i) for i in (row.get("issues_json") or [])]

    at_risk = float(itc_raw.get("at_risk",      row.get("itc_at_risk",  0) or 0))
    blocked = float(itc_raw.get("blocked",       row.get("itc_blocked",  0) or 0))
    total   = float(itc_raw.get("total_impact",  at_risk + blocked))

    score      = row.get("compliance_score", 0) or 0
    risk_level = row.get("risk_level", "HIGH") or "HIGH"

    return AuditResponse(
        audit_id              = row["id"],
        client_gstin_masked   = row.get("client_gstin_masked") or "",
        period                = row.get("period") or "",
        language              = lang,
        compliance_score      = score,
        risk_level            = risk_level,
        risk_level_translated = get_risk_level_translated(score, lang),
        total_invoices        = row.get("total_invoices_scanned") or row.get("total_invoices") or 0,
        issues                = issues,
        critical_count        = row.get("critical_count") or sum(1 for i in issues if i.severity.value == "CRITICAL"),
        high_count            = row.get("high_count")     or sum(1 for i in issues if i.severity.value == "HIGH"),
        medium_count          = row.get("medium_count")   or sum(1 for i in issues if i.severity.value == "MEDIUM"),
        low_count             = row.get("low_count")      or sum(1 for i in issues if i.severity.value == "LOW"),
        itc_summary           = ITCSummary(
            at_risk  = at_risk,
            blocked  = blocked,
            total    = total,
            eligible = float(row.get("itc_eligible") or 0),
        ),
        pdf_url    = row.get("pdf_url"),
        created_at = row.get("created_at") or "",
    )


# ── GET /reports ───────────────────────────────────────────────
@router.get("")
async def get_all_reports(x_user_id: str | None = Header(default=None)):
    ca_id = _get_ca_id(x_user_id)
    _ensure_user(ca_id)
    supabase = get_supabase()

    try:
        res = (
            supabase.table("audit_reports")
            .select(
                "id, period, compliance_score, risk_level, "
                "total_invoices_scanned, itc_summary, itc_at_risk, "
                "sector, language, created_at, client_id, "
                "client_name, client_gstin_masked, "
                "critical_count, high_count, medium_count, low_count"
            )
            .eq("ca_id", ca_id)
            .order("created_at", desc=True)
            .limit(100)
            .execute()
        )

        reports = []
        for row in (res.data or []):
            itc_raw   = row.get("itc_summary") or {}
            at_risk   = itc_raw.get("at_risk") or row.get("itc_at_risk") or 0
            reports.append({
                "id":               row["id"],
                "period":           row.get("period"),
                "compliance_score": row.get("compliance_score", 0),
                "risk_level":       row.get("risk_level"),
                "total_invoices":   row.get("total_invoices_scanned") or 0,
                "itc_summary":      itc_raw,
                "itc_at_risk":      at_risk,
                "sector":           row.get("sector"),
                "language":         row.get("language", "en"),
                "created_at":       row.get("created_at"),
                "client_id":        row.get("client_id"),
                "client_name":      row.get("client_name") or "Audit",
                "client_gstin_masked": row.get("client_gstin_masked"),
                "critical_count":   row.get("critical_count", 0),
                "high_count":       row.get("high_count", 0),
                "medium_count":     row.get("medium_count", 0),
                "low_count":        row.get("low_count", 0),
            })

        return {"reports": reports, "total": len(reports)}

    except Exception as e:
        logger.error(f"get_all_reports error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ── GET /reports/{id} ─────────────────────────────────────────
@router.get("/{report_id}")
async def get_report(
    report_id: str,
    lang: str  = "en",
    x_user_id: str | None = Header(default=None),
):
    ca_id = _get_ca_id(x_user_id)
    _ensure_user(ca_id)
    supabase = get_supabase()

    try:
        res = (
            supabase.table("audit_reports")
            .select("*")
            .eq("id", report_id)
            .eq("ca_id", ca_id)
            .limit(1)
            .execute()
        )

        if not res.data:
            raise HTTPException(status_code=404, detail="Report not found")

        row = res.data[0]
        return {
            **row,
            "total_invoices":      row.get("total_invoices_scanned") or row.get("total_invoices") or 0,
            "client_name":         row.get("client_name") or "Audit",
            "client_gstin_masked": row.get("client_gstin_masked") or "",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"get_report error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ── GET /reports/{id}/pdf ─────────────────────────────────────
@router.get("/{report_id}/pdf")
async def download_pdf(
    report_id: str,
    lang: str  = "en",
    x_user_id: str | None = Header(default=None),
):
    ca_id = _get_ca_id(x_user_id)
    supabase = get_supabase()

    try:
        res = (
            supabase.table("audit_reports")
            .select("*")
            .eq("id", report_id)
            .eq("ca_id", ca_id)
            .limit(1)
            .execute()
        )

        if not res.data:
            raise HTTPException(status_code=404, detail="Report not found")

        row         = res.data[0]
        client_name = row.get("client_name") or "Client"

        audit_obj = _build_audit_response(row, lang=lang)

        pdf_bytes = generate_pdf(
            audit_obj,
            client_name = client_name,
            lang        = lang,
        )

        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={
                "Content-Disposition": (
                    f'attachment; filename="GST_Audit_{row.get("period", report_id[:8])}.pdf"'
                )
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"download_pdf error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))