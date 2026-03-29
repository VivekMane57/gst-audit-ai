"""
repositories/audit_repo.py
--------------------------
All audit DB operations — ek jagah.
Router ya Service kabhi direct DB call nahi karega.

Rule: Yahan sirf Supabase calls. Zero business logic.
"""
from __future__ import annotations
import logging
from typing import Optional
from supabase import Client

logger = logging.getLogger(__name__)


class AuditRepository:
    def __init__(self, db: Client):
        self.db = db

    # ── Insert ────────────────────────────────────────────────
    def insert(self, record: dict) -> dict:
        """
        Audit record insert karo.
        Field-level retry: agar notice fields fail karein toh unhe hata ke retry.
        """
        try:
            res = self.db.table("audit_reports").insert(record).execute()
            return res.data[0] if res.data else record
        except Exception as first_err:
            logger.warning(f"Insert failed (attempt 1): {first_err}")
            # Notice fields hata ke retry
            safe_record = {
                k: v for k, v in record.items()
                if k not in ("notice_probability", "notice_risk_level", "notice_simulation")
            }
            try:
                res = self.db.table("audit_reports").insert(safe_record).execute()
                logger.info("Insert succeeded after removing notice fields")
                return res.data[0] if res.data else safe_record
            except Exception as retry_err:
                logger.error(f"Insert retry failed: {retry_err}", exc_info=True)
                raise RuntimeError(f"DB insert failed: {retry_err}") from retry_err

    # ── Fetch by ID ───────────────────────────────────────────
    def get_by_id(self, audit_id: str, user_uuid: str) -> Optional[dict]:
        try:
            res = (
                self.db.table("audit_reports")
                .select("*")
                .eq("id", audit_id)
                .eq("user_id", user_uuid)
                .limit(1)
                .execute()
            )
            return res.data[0] if res.data else None
        except Exception as e:
            logger.error(f"get_by_id error: {e}")
            raise

    # ── Fetch by CA ───────────────────────────────────────────
    def list_by_ca(self, ca_id: str, limit: int = 100) -> list[dict]:
        try:
            res = (
                self.db.table("audit_reports")
                .select(
                    "id, period, compliance_score, risk_level, "
                    "total_invoices_scanned, itc_summary, itc_at_risk, "
                    "issues_json, sector, language, created_at, client_id, "
                    "client_name, client_gstin_masked, "
                    "critical_count, high_count, medium_count, low_count"
                )
                .eq("ca_id", ca_id)
                .order("created_at", desc=True)
                .limit(limit)
                .execute()
            )
            return res.data or []
        except Exception as e:
            logger.error(f"list_by_ca error: {e}")
            raise

    # ── Update notice simulation ───────────────────────────────
    def update_notice_simulation(self, audit_id: str, notice_data: dict) -> None:
        try:
            self.db.table("audit_reports").update(notice_data).eq("id", audit_id).execute()
        except Exception as e:
            logger.warning(f"update_notice_simulation failed (non-fatal): {e}")

    # ── Fetch for PDF (by CA) ─────────────────────────────────
    def get_by_id_for_ca(self, audit_id: str, ca_id: str) -> Optional[dict]:
        try:
            res = (
                self.db.table("audit_reports")
                .select("*")
                .eq("id", audit_id)
                .eq("ca_id", ca_id)
                .limit(1)
                .execute()
            )
            return res.data[0] if res.data else None
        except Exception as e:
            logger.error(f"get_by_id_for_ca error: {e}")
            raise

    # ── Supplier data (all issues across audits) ───────────────
    def list_issues_for_suppliers(self, ca_id: str, limit: int = 200) -> list[dict]:
        try:
            res = (
                self.db.table("audit_reports")
                .select("id, issues_json, period, client_name, client_gstin_masked")
                .eq("ca_id", ca_id)
                .order("created_at", desc=True)
                .limit(limit)
                .execute()
            )
            return res.data or []
        except Exception as e:
            logger.error(f"list_issues_for_suppliers error: {e}")
            raise