"""
workers/audit_tasks.py
-----------------------
Audit complete → CA ko email + Client ko email + High risk alert
"""
from __future__ import annotations
import logging
import os
from typing import Optional

from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


def _valid_email(email: str | None) -> str | None:
    """Return email only if valid."""
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
    sales_path: Optional[str] = None,
    sales_filename: Optional[str] = None,
    purchase_path: Optional[str] = None,
    purchase_filename: Optional[str] = None,
    extra_paths: list[tuple[str, str]] = [],
    our_gstin: str,
    period: str,
    language: str = "en",
    sector: Optional[str] = None,
    client_id: Optional[str] = None,
    filing_delays: int = 0,
    turnover_cr: float = 1.0,
    previous_notices: int = 0,
    user_uuid: str = "",
    ca_id: str = "",
    ca_email: Optional[str] = None,
    ca_name: str = "CA",
) -> dict:
    task_id = self.request.id
    temp_files_cleanup = []

    logger.info(
        f"[TASK:{task_id}] Audit started | "
        f"gstin={our_gstin[:6]}*** period={period} user={user_uuid[:8]}***"
    )

    try:
        # ── Step 1: Read files ────────────────────────────────
        sales_bytes = None
        purchase_bytes = None
        extra_files = []

        if sales_path and os.path.exists(sales_path):
            with open(sales_path, "rb") as f:
                sales_bytes = f.read()
            temp_files_cleanup.append(sales_path)
            logger.info(f"[TASK:{task_id}] Sales file read: {sales_filename}")

        if purchase_path and os.path.exists(purchase_path):
            with open(purchase_path, "rb") as f:
                purchase_bytes = f.read()
            temp_files_cleanup.append(purchase_path)
            logger.info(f"[TASK:{task_id}] Purchase file read: {purchase_filename}")

        for path, fname in (extra_paths or []):
            if os.path.exists(path):
                with open(path, "rb") as f:
                    extra_files.append((f.read(), fname))
                temp_files_cleanup.append(path)

        # ── Step 2: Run audit service ─────────────────────────
        from app.db.supabase_client import get_supabase
        from app.repositories.audit_repo import AuditRepository
        from app.repositories.client_repo import ClientRepository
        from app.core.dependencies import AuditDeps
        from app.services.audit_service import AuditService

        db = get_supabase()
        deps = AuditDeps(
            audit_repo=AuditRepository(db),
            client_repo=ClientRepository(db),
            user_uuid=user_uuid,
            ca_id=ca_id,
            ca_email=ca_email,
            ca_name=ca_name,
        )

        service = AuditService(deps)
        result = service.run(
            sales_bytes=sales_bytes,
            sales_filename=sales_filename,
            purchase_bytes=purchase_bytes,
            purchase_filename=purchase_filename,
            extra_files=extra_files,
            our_gstin=our_gstin,
            period=period,
            language=language,
            sector=sector,
            client_id=client_id,
            filing_delays=filing_delays,
            turnover_cr=turnover_cr,
            previous_notices=previous_notices,
        )

        audit_id = result.get("audit_id", task_id)
        logger.info(f"[TASK:{task_id}] Audit complete | audit_id={audit_id}")

        # ── Step 3: Update task status ────────────────────────
        try:
            db.table("audit_tasks").update({
                "status": "completed",
                "audit_id": audit_id,
                "completed_at": "now()",
            }).eq("task_id", task_id).execute()
        except Exception as db_err:
            logger.warning(f"[TASK:{task_id}] Status update failed (non-fatal): {db_err}")

        # ── Step 4: Fetch client info (name + email) ──────────
        client_name = result.get("client_name") or "Client"
        client_email = None

        if client_id:
            try:
                logger.info(f"[TASK:{task_id}] Fetching client email for client_id={client_id}")
                client_res = (
                    db.table("clients")
                    .select("email, business_name, contact_person")
                    .eq("id", client_id)
                    .eq("ca_id", ca_id)
                    .limit(1)
                    .execute()
                )
                if client_res.data:
                    raw_email = client_res.data[0].get("email")
                    client_name = client_res.data[0].get("business_name") or client_name
                    client_email = _valid_email(raw_email)
                    logger.info(
                        f"[TASK:{task_id}] Client DB email: raw='{raw_email}' → valid='{client_email}' | name={client_name}"
                    )
                else:
                    logger.warning(f"[TASK:{task_id}] Client not found in DB: {client_id}")
            except Exception as ce:
                logger.error(f"[TASK:{task_id}] Client fetch failed: {ce}")
        else:
            logger.info(f"[TASK:{task_id}] No client_id provided — client email skipped")

        # ── Step 5: Generate PDF ──────────────────────────────
        pdf_bytes = None
        try:
            from app.services.report_generator import generate_pdf
            from app.models.audit import AuditResponse, ITCSummary

            audit_obj = AuditResponse(
                audit_id=audit_id,
                client_gstin_masked=result.get("client_gstin_masked", ""),
                period=period,
                compliance_score=result.get("compliance_score", 0),
                risk_level=result.get("risk_level", "UNKNOWN"),
                risk_level_translated=result.get("risk_level", "UNKNOWN"),
                total_invoices=result.get("total_invoices", 0),
                itc_summary=ITCSummary(
                    at_risk=result.get("itc_at_risk", 0),
                    blocked=0,
                    total=result.get("itc_at_risk", 0),
                ),
                issues=[],
                language=language,
                critical_count=result.get("critical_count", 0),
                high_count=result.get("high_count", 0),
                medium_count=result.get("medium_count", 0),
                low_count=result.get("low_count", 0),
                created_at=str(__import__("datetime").datetime.utcnow().isoformat()),
            )
            pdf_bytes = generate_pdf(
                audit_obj,
                ca_name=ca_name or "CA",
                client_name=client_name,
                lang=language,
            )
            logger.info(f"[TASK:{task_id}] PDF generated: {len(pdf_bytes)} bytes")
        except Exception as pdf_err:
            logger.error(f"[TASK:{task_id}] PDF generation failed: {pdf_err}")

        # ── Step 6: Send Emails ───────────────────────────────
        from app.services.email_service import (
            send_audit_complete_to_ca,
            send_high_risk_alert,
        )

        score = result.get("compliance_score", 0)
        risk_level = result.get("risk_level", "UNKNOWN")
        issues_count = len(result.get("issues", []))
        critical_count = result.get("critical_count", 0)
        itc_at_risk = float(result.get("itc_at_risk", 0))
        notice_prob = result.get("notice_simulation", {}).get("probability", 0)

        # Get CA email (from header or DB)
        valid_ca_email = _valid_email(ca_email)
        if not valid_ca_email:
            try:
                user_res = (
                    db.table("users")
                    .select("email, full_name")
                    .eq("clerk_id", ca_id)
                    .limit(1)
                    .execute()
                )
                if user_res.data:
                    valid_ca_email = _valid_email(user_res.data[0].get("email"))
                    ca_name = user_res.data[0].get("full_name") or ca_name
            except Exception as ue:
                logger.warning(f"[TASK:{task_id}] CA email fetch failed: {ue}")

        logger.info(
            f"[TASK:{task_id}] Email targets: CA={valid_ca_email} | Client={client_email}"
        )

        # Common email params
        email_params = dict(
            ca_name=ca_name,
            client_name=client_name,
            client_gstin=our_gstin,
            period=period,
            score=score,
            risk_level=risk_level,
            issues_count=issues_count,
            critical_count=critical_count,
            itc_at_risk=itc_at_risk,
            notice_prob=notice_prob,
            audit_id=audit_id,
            pdf_content=pdf_bytes,
        )

        # ── 6a. CA ko email ──────────────────────────────────
        if valid_ca_email:
            sent_ca = send_audit_complete_to_ca(
                ca_email=valid_ca_email,
                is_client=False,
                **email_params,
            )
            logger.info(f"[TASK:{task_id}] CA email {'sent ✅' if sent_ca else 'FAILED ❌'} → {valid_ca_email}")
        else:
            logger.warning(f"[TASK:{task_id}] CA email SKIPPED — no valid email found")

        # ── 6b. Client ko email ──────────────────────────────
        if client_email:
            if client_email != valid_ca_email:
                sent_client = send_audit_complete_to_ca(
                    ca_email=client_email,
                    is_client=True,
                    **email_params,
                )
                logger.info(f"[TASK:{task_id}] Client email {'sent ✅' if sent_client else 'FAILED ❌'} → {client_email}")
            else:
                logger.info(f"[TASK:{task_id}] Client email SKIPPED — same as CA email ({client_email})")
        else:
            logger.warning(
                f"[TASK:{task_id}] Client email SKIPPED — no valid email in DB. "
                f"Client '{client_name}' needs email in Clients page."
            )

        # ── 6c. High risk alert (50%+) ──────────────────────
        if notice_prob >= 50 and valid_ca_email:
            sent_alert = send_high_risk_alert(
                ca_email=valid_ca_email,
                ca_name=ca_name,
                client_name=client_name,
                score=score,
                notice_prob=notice_prob,
                issues=[i for i in result.get("issues", []) if i.get("severity") == "CRITICAL"],
            )
            logger.info(f"[TASK:{task_id}] High risk alert {'sent ✅' if sent_alert else 'FAILED ❌'} → {valid_ca_email}")

        return result

    except Exception as exc:
        logger.error(f"[TASK:{task_id}] FAILED: {exc}", exc_info=True)
        try:
            from app.db.supabase_client import get_supabase
            get_supabase().table("audit_tasks").update({
                "status": "failed",
                "error": str(exc)[:500],
            }).eq("task_id", task_id).execute()
        except Exception:
            pass
        try:
            raise self.retry(exc=exc, countdown=30)
        except self.MaxRetriesExceededError:
            logger.error(f"[TASK:{task_id}] Max retries exceeded.")
            return {"error": str(exc), "status": "failed", "task_id": task_id}

    finally:
        for path in temp_files_cleanup:
            try:
                if os.path.exists(path):
                    os.unlink(path)
            except Exception as e:
                logger.warning(f"[TASK:{task_id}] Cleanup failed {path}: {e}")