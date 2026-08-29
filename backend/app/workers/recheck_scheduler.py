"""
workers/recheck_scheduler.py
------------------------------
Monthly notice risk recheck scheduler.

Fix: Removed circular import — celery_app imported via shared instance.
"""
from __future__ import annotations
import logging
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)

# ── Import celery_app AFTER it is fully initialized ───────────
# Using shared_task avoids circular import issue entirely
from celery import shared_task


@shared_task(
    name            = "recheck.monthly_notice_risk",
    bind            = True,
    max_retries     = 1,
    soft_time_limit = 300,
    time_limit      = 360,
)
def run_monthly_recheck(self) -> dict:
    """
    Monthly task: recalculate notice risk for all active clients.

    Flow:
      1. Fetch all CAs with recent audit activity
      2. For each CA → fetch latest audit per client
      3. Rerun notice_simulator on existing issues_json
      4. Save recheck result to audit_recheks table
      5. If risk increased → alert CA

    Idempotent: skips clients already rechecked this month.
    """
    task_id   = self.request.id
    now       = datetime.now(timezone.utc)
    month_key = now.strftime("%Y-%m")

    logger.info(f"[RECHECK:{task_id}] Monthly recheck started | month={month_key}")

    try:
        from app.db.supabase_client import get_supabase
        db = get_supabase()

        # Step 1: All CAs with recent audit activity
        ca_res = (
            db.table("audit_reports")
            .select("ca_id")
            .order("created_at", desc=True)
            .limit(500)
            .execute()
        )
        ca_ids = list(set(r["ca_id"] for r in (ca_res.data or []) if r.get("ca_id")))
        logger.info(f"[RECHECK:{task_id}] CAs to process: {len(ca_ids)}")

        total_processed = total_skipped = total_alerted = 0

        for ca_id in ca_ids:
            try:
                p, s, a = _recheck_ca(db, ca_id, month_key, task_id)
                total_processed += p
                total_skipped   += s
                total_alerted   += a
            except Exception as ca_err:
                logger.error(f"[RECHECK:{task_id}] CA {ca_id[:8]}*** failed: {ca_err}")

        result = {
            "month":             month_key,
            "cas_processed":     len(ca_ids),
            "clients_processed": total_processed,
            "clients_skipped":   total_skipped,
            "alerts_sent":       total_alerted,
            "completed_at":      now.isoformat(),
        }
        logger.info(f"[RECHECK:{task_id}] Complete: {result}")
        return result

    except Exception as exc:
        logger.error(f"[RECHECK:{task_id}] Fatal: {exc}", exc_info=True)
        try:
            raise self.retry(exc=exc, countdown=3600)
        except self.MaxRetriesExceededError:
            return {"error": str(exc), "status": "failed"}


def _recheck_ca(db, ca_id: str, month_key: str, task_id: str) -> tuple[int, int, int]:
    from app.services.notice_simulator import run_notice_simulation

    res = (
        db.table("audit_reports")
        .select(
            "id, client_id, client_name, client_gstin_masked, period, "
            "compliance_score, issues_json, notice_probability, notice_risk_level, "
            "itc_at_risk, ca_id"
        )
        .eq("ca_id", ca_id)
        .order("created_at", desc=True)
        .limit(200)
        .execute()
    )

    # Deduplicate — latest per client
    seen: set = set()
    latest_per_client: list[dict] = []
    for row in (res.data or []):
        cid = row.get("client_id") or row["id"]
        if cid not in seen:
            seen.add(cid)
            latest_per_client.append(row)

    processed = skipped = alerted = 0

    for audit_row in latest_per_client:
        audit_id  = audit_row["id"]
        client_id = audit_row.get("client_id")

        if _already_rechecked(db, audit_id, month_key):
            skipped += 1
            continue

        issues_json   = audit_row.get("issues_json") or []
        score         = int(audit_row.get("compliance_score") or 100)
        notice_issues = _issues_to_sim_format(issues_json)

        try:
            notice_sim = run_notice_simulation(
                issues           = notice_issues,
                compliance_score = score,
                client_name      = audit_row.get("client_name") or "",
                client_gstin     = audit_row.get("client_gstin_masked") or "",
                lang             = "en",
            )
        except Exception as sim_err:
            logger.warning(f"[RECHECK:{task_id}] Sim failed for {audit_id}: {sim_err}")
            continue

        _save_recheck(db, audit_id, ca_id, client_id, month_key, notice_sim)
        processed += 1

        prev_prob = int(audit_row.get("notice_probability") or 0)
        new_prob  = notice_sim["probability"]
        if new_prob >= 50 and (new_prob - prev_prob) >= 10:
            _send_recheck_alert(db, ca_id, audit_row, notice_sim, task_id)
            alerted += 1

    return processed, skipped, alerted


def _issues_to_sim_format(issues_json: list[dict]) -> list[dict]:
    result = []
    for i in issues_json:
        result.append({
            "type":       i.get("issue_type") or i.get("type") or "unknown",
            "severity":   (i.get("severity") or "medium").lower(),
            "invoice":    i.get("invoice_number") or i.get("invoice") or "N/A",
            "party":      i.get("party_name") or "N/A",
            "amount":     float(i.get("amount") or 0),
            "tax_impact": float(i.get("itc_at_risk") or i.get("tax_impact") or 0),
        })
    return result


def _already_rechecked(db, audit_id: str, month_key: str) -> bool:
    try:
        res = (
            db.table("audit_recheks")
            .select("id")
            .eq("audit_id", audit_id)
            .eq("month_key", month_key)
            .limit(1)
            .execute()
        )
        return bool(res.data)
    except Exception:
        return False


def _save_recheck(
    db,
    audit_id:   str,
    ca_id:      str,
    client_id:  Optional[str],
    month_key:  str,
    notice_sim: dict,
) -> None:
    try:
        db.table("audit_recheks").insert({
            "audit_id":           audit_id,
            "ca_id":              ca_id,
            "client_id":          client_id,
            "month_key":          month_key,
            "notice_probability": notice_sim["probability"],
            "notice_risk_level":  notice_sim["risk_level"],
            "top_risk_reasons":   notice_sim.get("top_risk_reasons", []),
            "estimated_penalty":  notice_sim.get("estimated_penalty_exposure", 0),
            "issue_summary":      notice_sim.get("issue_summary", {}),
            "recheck_data": {
                "probability":      notice_sim["probability"],
                "risk_level":       notice_sim["risk_level"],
                "risk_message":     notice_sim["risk_message"],
                "top_risk_reasons": notice_sim.get("top_risk_reasons", []),
            },
        }).execute()
    except Exception as e:
        logger.warning(f"_save_recheck failed for {audit_id}: {e}")


def _send_recheck_alert(
    db, ca_id: str, audit_row: dict, notice_sim: dict, task_id: str
) -> None:
    try:
        user_res = (
            db.table("users")
            .select("email, full_name")
            .eq("clerk_id", ca_id)
            .limit(1)
            .execute()
        )
        if not user_res.data:
            return
        ca_email = user_res.data[0].get("email")
        ca_name  = user_res.data[0].get("full_name") or "CA"
        if not ca_email or "@placeholder" in ca_email or "auditai.app" in ca_email:
            return

        from app.services.email_service import send_high_risk_alert
        send_high_risk_alert(
            ca_email                   = ca_email,
            ca_name                    = ca_name,
            client_name                = audit_row.get("client_name") or "Client",
            score                      = int(audit_row.get("compliance_score") or 0),
            notice_prob                = notice_sim["probability"],
            issues                     = [],
            top_risk_reasons           = notice_sim.get("top_risk_reasons", []),
            estimated_penalty_exposure = notice_sim.get("estimated_penalty_exposure", 0),
        )
        logger.info(f"[RECHECK:{task_id}] Alert sent → {ca_email}")
    except Exception as e:
        logger.warning(f"_send_recheck_alert failed: {e}")