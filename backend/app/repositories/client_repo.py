"""
repositories/client_repo.py
----------------------------
All client DB operations — ek jagah.
Router ya Service kabhi direct DB call nahi karega.

Rule: Yahan sirf Supabase calls. Zero business logic.
"""
from __future__ import annotations
import logging
from typing import Optional
from supabase import Client

logger = logging.getLogger(__name__)


class ClientRepository:
    def __init__(self, db: Client):
        self.db = db

    # ── List all clients for a CA ──────────────────────────────
    def list_by_ca(self, ca_id: str) -> list[dict]:
        try:
            res = (
                self.db.table("clients")
                .select(
                    "id, business_name, gstin_masked, gstin_encrypted, "
                    "sector, created_at, contact_person, phone, email, "
                    "address, state_code"
                )
                .eq("ca_id", ca_id)
                .order("business_name")
                .execute()
            )
            return res.data or []
        except Exception as e:
            logger.error(f"list_by_ca error: {e}")
            raise

    # ── Get single client ──────────────────────────────────────
    def get_by_id(self, client_id: str, ca_id: str) -> Optional[dict]:
        try:
            res = (
                self.db.table("clients")
                .select("*")
                .eq("id", client_id)
                .eq("ca_id", ca_id)
                .limit(1)
                .execute()
            )
            return res.data[0] if res.data else None
        except Exception as e:
            logger.error(f"get_by_id error: {e}")
            raise

    # ── Get client name only (for audit) ──────────────────────
    def get_name(self, client_id: str, ca_id: str) -> Optional[str]:
        try:
            res = (
                self.db.table("clients")
                .select("business_name")
                .eq("id", client_id)
                .eq("ca_id", ca_id)
                .limit(1)
                .execute()
            )
            return res.data[0]["business_name"] if res.data else None
        except Exception as e:
            logger.warning(f"get_name failed: {e}")
            return None

    # ── Get client email + contact (for audit email) ───────────
    def get_contact(self, client_id: str, ca_id: str) -> Optional[dict]:
        try:
            res = (
                self.db.table("clients")
                .select("email, business_name, contact_person")
                .eq("id", client_id)
                .eq("ca_id", ca_id)
                .limit(1)
                .execute()
            )
            return res.data[0] if res.data else None
        except Exception as e:
            logger.warning(f"get_contact failed: {e}")
            return None

    # ── Insert ────────────────────────────────────────────────
    def insert(self, data: dict) -> dict:
        try:
            res = self.db.table("clients").insert(data).execute()
            if not res.data:
                raise RuntimeError("Insert returned no data")
            return res.data[0]
        except Exception as e:
            logger.error(f"insert error: {e}")
            raise

    # ── Update ────────────────────────────────────────────────
    def update(self, client_id: str, ca_id: str, data: dict) -> dict:
        try:
            res = (
                self.db.table("clients")
                .update(data)
                .eq("id", client_id)
                .eq("ca_id", ca_id)
                .execute()
            )
            if not res.data:
                raise RuntimeError("Update returned no data")
            return res.data[0]
        except Exception as e:
            logger.error(f"update error: {e}")
            raise

    # ── Delete ────────────────────────────────────────────────
    def delete(self, client_id: str, ca_id: str) -> None:
        try:
            self.db.table("clients").delete().eq("id", client_id).execute()
        except Exception as e:
            logger.error(f"delete error: {e}")
            raise

    # ── Update last_score after audit ─────────────────────────
    def update_last_score(self, client_id: str, ca_id: str, score: int) -> None:
        try:
            self.db.table("clients").update({
                "last_score":    score,
                "last_audit_at": "now()",
            }).eq("id", client_id).eq("ca_id", ca_id).execute()
        except Exception as e:
            logger.warning(f"update_last_score failed (non-fatal): {e}")

    # ── Latest audit scores (for dashboard list) ──────────────
    def get_latest_audit_scores(self, ca_id: str, client_ids: list[str]) -> dict:
        """
        Returns {client_id: {last_score, last_audit_at}} dict.
        """
        if not client_ids:
            return {}
        try:
            res = (
                self.db.table("audit_reports")
                .select("client_id, compliance_score, created_at")
                .eq("ca_id", ca_id)
                .in_("client_id", client_ids)
                .order("created_at", desc=True)
                .execute()
            )
            result: dict = {}
            for audit in (res.data or []):
                cid = audit["client_id"]
                if cid not in result:
                    result[cid] = {
                        "last_score":    audit["compliance_score"],
                        "last_audit_at": audit["created_at"],
                    }
            return result
        except Exception as e:
            logger.warning(f"get_latest_audit_scores failed: {e}")
            return {}

    # ── Get audit history for a client ────────────────────────
    def get_audit_history(self, client_id: str, ca_id: str) -> list[dict]:
        try:
            res = (
                self.db.table("audit_reports")
                .select("id, period, compliance_score, risk_level, created_at, itc_summary")
                .eq("client_id", client_id)
                .eq("ca_id", ca_id)
                .order("created_at", desc=True)
                .execute()
            )
            return res.data or []
        except Exception as e:
            logger.warning(f"get_audit_history failed: {e}")
            return []