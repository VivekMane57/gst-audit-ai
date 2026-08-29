"""
workers/audit_tasks.py  (Fixed)
---------------------------------
Fix from previous version:
  1. PDF was built with issues=[] — now uses result["issues"] properly
  2. issue_summary used for email instead of re-counting
  3. notice_sim enriched fields (top_risk_reasons, estimated_penalty) 
     passed to email functions
  4. Task result includes issue_summary for frontend polling
"""
from __future__ import annotations
import logging
import os
from typing import Optional

from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


def _valid_email(email: str | None) -> str | None:
    if not email:
        return None
    e = email.strip()
    if "@" not in e or "@placeholder" in e or "auditai.app" in e or "example.com" in e:
        return None
    return e


@celery_app.task(
    bind=True,
    name="audit.run",
    max_retries=2,
    default_retry_delay=30,
    soft_time_limit=120,
    time_limit=180,
)
def run_audit_task(
    self,
    *,
    sales_path:        Optional[str] = None,
    sales_filename:    Optional[str] = None,
    purchase_path:     Optional[str] = None,
    purchase_filename: Optional[str] = None,
    extra_paths:       list[tuple[str, str]] = [],
    our_gstin:         str,
    period:            str,
    language:          str           = "en",
    sector:            Optional[str] = None,
    client_id:         Optional[str] = None,
    filing_delays:     int           = 0,
    turnover_cr:       float         = 1.0,
    previous_notices:  int           = 0,
    user_uuid:         str           = "",
    ca_id:             str           = "",
    ca_email:          Optional[str] = None,
    ca_name:           str           = "CA",
) -> dict:
    task_id            = self.request.id
    temp_files_cleanup = []

    logger.info(f"[TASK:{task_id}] Audit started | gstin={our_gstin[:6]}*** period={period}")

    try:
        # ── Step 1: Read files ────────────────────────────────
        sales_bytes    = None
        purchase_bytes = None
        extra_files    = []

        if sales_path and os.path.exists(sales_path):
            with open(sales_path, "rb") as f: sales_bytes = f.read()
            temp_files_cleanup.append(sales_path)

        if purchase_path and os.path.exists(purchase_path):
            with open(purchase_path, "rb") as f: purchase_bytes = f.read()
            temp_files_cleanup.append(purchase_path)

        for path, fname in (extra_paths or []):
            if os.path.exists(path):
                with open(path, "rb") as f: extra_files.append((f.read(), fname))
                temp_files_cleanup.append(path)

        # ── Step 2: Run audit service ─────────────────────────
        from app.db.supabase_client import get_supabase
        from app.repositories.audit_repo import AuditRepository
        from app.repositories.client_repo import ClientRepository
        from app.core.dependencies import AuditDeps
        from app.services.audit_service import AuditService

        db   = get_supabase()
        deps = AuditDeps(
            audit_repo  = AuditRepository(db),
            client_repo = ClientRepository(db),
            user_uuid   = user_uuid,
            ca_id       = ca_id,
            ca_email    = ca_email,
            ca_name     = ca_name,
        )
        service = AuditService(deps)
        result  = service.run(
            sales_bytes       = sales_bytes,
            sales_filename    = sales_filename,
            purchase_bytes    = purchase_bytes,
            purchase_filename = purchase_filename,
            extra_files       = extra_files,
            our_gstin         = our_gstin,
            period            = period,
            language          = language,
            sector            = sector,
            client_id         = client_id,
            filing_delays     = filing_delays,
            turnover_cr       = turnover_cr,
            previous_notices  = previous_notices,
        )

        audit_id = result.get("audit_id", task_id)
        logger.info(f"[TASK:{task_id}] Audit complete | audit_id={audit_id}")

        # ── Step 3: Update task status ────────────────────────
        try:
            db.table("audit_tasks").update({
                "status":       "completed",
                "audit_id":     audit_id,
                "completed_at": "now()",
            }).eq("task_id", task_id).execute()
        except Exception as db_err:
            logger.warning(f"[TASK:{task_id}] Status update failed (non-fatal): {db_err}")

        # ── Step 4: Generate PDF ──────────────────────────────
        # FIX: use actual issues from result, not empty list
        pdf_bytes    = None
        client_name  = result.get("client_name") or "Client"
        issue_summary = result.get("issue_summary") or {}

        try:
            from app.services.report_generator import generate_pdf
            from app.models.audit import AuditResponse, ITCSummary, IssueSummary
            from app.models.issue import Issue

            # Reconstruct Issue objects from structured dicts
            raw_issues = result.get("issues") or []
            issues_objs = []
            for raw in raw_issues:
                try:
                    issues_objs.append(Issue(**{
                        k: v for k, v in raw.items()
                        if k in Issue.__fields__
                    }))
                except Exception:
                    pass   # skip malformed issues — don't fail PDF

            summary = IssueSummary(
                total    = issue_summary.get("total", len(issues_objs)),
                critical = issue_summary.get("critical", result.get("critical_count", 0)),
                high     = issue_summary.get("high",     result.get("high_count", 0)),
                medium   = issue_summary.get("medium",   result.get("medium_count", 0)),
                low      = issue_summary.get("low",      result.get("low_count", 0)),
            )

            audit_obj = AuditResponse(
                audit_id              = audit_id,
                client_gstin_masked   = result.get("client_gstin_masked", ""),
                period                = period,
                compliance_score      = result.get("compliance_score", 0),
                risk_level            = result.get("risk_level", "UNKNOWN"),
                risk_level_translated = result.get("risk_level", "UNKNOWN"),
                total_invoices        = result.get("total_invoices", 0),
                itc_summary           = ITCSummary(
                    at_risk  = result.get("itc_at_risk", 0),
                    blocked  = 0,
                    total    = result.get("itc_at_risk", 0),
                ),
                issues         = issues_objs,   # ← FIXED: actual issues, not []
                issue_summary  = summary,
                critical_count = summary.critical,
                high_count     = summary.high,
                medium_count   = summary.medium,
                low_count      = summary.low,
                language       = language,
                created_at     = str(__import__("datetime").datetime.utcnow().isoformat()),
            )

            pdf_bytes = generate_pdf(audit_obj, ca_name=ca_name, client_name=client_name, lang=language)
            logger.info(f"[TASK:{task_id}] PDF generated: {len(pdf_bytes)} bytes | issues in PDF: {len(issues_objs)}")

        except Exception as pdf_err:
            logger.error(f"[TASK:{task_id}] PDF failed: {pdf_err}", exc_info=True)

        # ── Step 5: Get CA + Client emails ────────────────────
        valid_ca_email = _valid_email(ca_email)
        client_email   = None

        if not valid_ca_email:
            try:
                user_res = db.table("users").select("email, full_name").eq("clerk_id", ca_id).limit(1).execute()
                if user_res.data:
                    valid_ca_email = _valid_email(user_res.data[0].get("email"))
                    ca_name        = user_res.data[0].get("full_name") or ca_name
            except Exception as ue:
                logger.warning(f"[TASK:{task_id}] CA email fetch failed: {ue}")

        if client_id:
            try:
                client_res = db.table("clients").select("email, business_name").eq("id", client_id).eq("ca_id", ca_id).limit(1).execute()
                if client_res.data:
                    client_name  = client_res.data[0].get("business_name") or client_name
                    client_email = _valid_email(client_res.data[0].get("email"))
            except Exception as ce:
                logger.warning(f"[TASK:{task_id}] Client fetch failed: {ce}")

        # ── Step 6: Send Emails ───────────────────────────────
        from app.services.email_service import send_audit_complete_to_ca, send_high_risk_alert

        notice_sim   = result.get("notice_simulation") or {}
        score        = result.get("compliance_score", 0)
        risk_level   = result.get("risk_level", "UNKNOWN")
        notice_prob  = notice_sim.get("probability", 0)
        itc_at_risk  = float(result.get("itc_at_risk", 0))

        # Use issue_summary — not re-counting from stale data
        total_issues   = issue_summary.get("total", 0)
        critical_count = issue_summary.get("critical", result.get("critical_count", 0))

        top_risk_reasons           = notice_sim.get("top_risk_reasons", []) or result.get("top_risk_reasons", [])
        estimated_penalty_exposure = notice_sim.get("estimated_penalty_exposure", 0) or result.get("estimated_penalty_exposure", 0)

        email_params = dict(
            ca_name        = ca_name,
            client_name    = client_name,
            client_gstin   = our_gstin,
            period         = period,
            score          = score,
            risk_level     = risk_level,
            issues_count   = total_issues,
            critical_count = critical_count,
            itc_at_risk    = itc_at_risk,
            notice_prob    = notice_prob,
            audit_id       = audit_id,
            pdf_content    = pdf_bytes,
            top_risk_reasons           = top_risk_reasons,
            estimated_penalty_exposure = float(estimated_penalty_exposure),
        )

        if valid_ca_email:
            sent_ca = send_audit_complete_to_ca(ca_email=valid_ca_email, is_client=False, **email_params)
            logger.info(f"[TASK:{task_id}] CA email {'✅' if sent_ca else '❌'} → {valid_ca_email}")

        if client_email and client_email != valid_ca_email:
            sent_client = send_audit_complete_to_ca(ca_email=client_email, is_client=True, **email_params)
            logger.info(f"[TASK:{task_id}] Client email {'✅' if sent_client else '❌'} → {client_email}")

        if notice_prob >= 50 and valid_ca_email:
            critical_issues = [i for i in result.get("issues", []) if (i.get("severity") or "").upper() == "CRITICAL"]
            send_high_risk_alert(
                ca_email    = valid_ca_email,
                ca_name     = ca_name,
                client_name = client_name,
                score       = score,
                notice_prob = notice_prob,
                issues      = critical_issues,
                top_risk_reasons           = top_risk_reasons,
                estimated_penalty_exposure = float(estimated_penalty_exposure),
            )

        return result

    except Exception as exc:
        logger.error(f"[TASK:{task_id}] FAILED: {exc}", exc_info=True)
        try:
            from app.db.supabase_client import get_supabase
            get_supabase().table("audit_tasks").update({
                "status": "failed",
                "error":  str(exc)[:500],
            }).eq("task_id", task_id).execute()
        except Exception:
            pass
        try:
            raise self.retry(exc=exc, countdown=30)
        except self.MaxRetriesExceededError:
            return {"error": str(exc), "status": "failed", "task_id": task_id}

    finally:
        for path in temp_files_cleanup:
            try:
                if os.path.exists(path): os.unlink(path)
            except Exception as e:
                logger.warning(f"[TASK:{task_id}] Cleanup failed {path}: {e}")