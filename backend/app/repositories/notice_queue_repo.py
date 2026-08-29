"""
repositories/notice_queue_repo.py
----------------------------------
Data access for notice risk queue.
Reads from existing audit_reports table — no new table needed.

Query strategy:
  - Get latest audit per client (subquery pattern via Python groupby)
  - Returns only fields needed for queue — efficient
"""
from __future__ import annotations
import logging
from supabase import Client

logger = logging.getLogger(__name__)

# Fields needed for queue — don't fetch issues_json (large, not needed for queue)
QUEUE_SELECT = (
    "id, client_id, client_name, client_gstin_masked, period, "
    "compliance_score, notice_probability, notice_risk_level, "
    "itc_at_risk, critical_count, high_count, medium_count, low_count, "
    "estimated_penalty_exposure, top_risk_reasons, notice_simulation, "
    "created_at"
)


class NoticeQueueRepository:
    def __init__(self, db: Client):
        self.db = db

    def fetch_latest_audits_per_client(
        self,
        ca_id: str,
        limit: int = 100,
    ) -> list[dict]:
        """
        Fetch the latest audit for each client.

        Strategy: fetch recent audits sorted by date DESC,
        then deduplicate by client_id in Python (keeps latest).
        This avoids complex SQL while staying efficient for
        up to ~1000 clients (typical CA firm).
        """
        try:
            res = (
                self.db.table("audit_reports")
                .select(QUEUE_SELECT)
                .eq("ca_id", ca_id)
                .order("created_at", desc=True)
                .limit(limit * 3)   # fetch more, deduplicate in Python
                .execute()
            )
            rows = res.data or []

            # Deduplicate — keep latest per client_id
            seen_clients: set = set()
            latest: list[dict] = []
            for row in rows:
                cid = row.get("client_id") or row["id"]   # fallback to audit_id if no client
                if cid not in seen_clients:
                    seen_clients.add(cid)
                    latest.append(row)
                if len(latest) >= limit:
                    break

            return latest

        except Exception as e:
            logger.error(f"fetch_latest_audits_per_client error: {e}")
            return []

    def fetch_by_risk_level(
        self,
        ca_id:      str,
        risk_level: str,
        limit:      int = 50,
    ) -> list[dict]:
        """Fetch audits by specific notice risk level."""
        try:
            res = (
                self.db.table("audit_reports")
                .select(QUEUE_SELECT)
                .eq("ca_id", ca_id)
                .eq("notice_risk_level", risk_level)
                .order("notice_probability", desc=True)
                .limit(limit)
                .execute()
            )
            return res.data or []
        except Exception as e:
            logger.error(f"fetch_by_risk_level error: {e}")
            return []

    def fetch_high_risk_this_month(
        self,
        ca_id:    str,
        min_prob: int = 50,
    ) -> list[dict]:
        """
        Fetch high-risk audits created this month.
        Used for monthly recheck scheduler output.
        """
        try:
            from datetime import datetime
            month_start = datetime.now().replace(day=1, hour=0, minute=0, second=0).isoformat()
            res = (
                self.db.table("audit_reports")
                .select(QUEUE_SELECT)
                .eq("ca_id", ca_id)
                .gte("notice_probability", min_prob)
                .gte("created_at", month_start)
                .order("notice_probability", desc=True)
                .limit(100)
                .execute()
            )
            return res.data or []
        except Exception as e:
            logger.error(f"fetch_high_risk_this_month error: {e}")
            return []

    def count_by_risk_level(self, ca_id: str) -> dict[str, int]:
        """Count audits by notice risk level — for dashboard stats."""
        try:
            res = (
                self.db.table("audit_reports")
                .select("notice_risk_level")
                .eq("ca_id", ca_id)
                .execute()
            )
            counts = {"VERY_HIGH": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
            for row in (res.data or []):
                lvl = row.get("notice_risk_level") or "LOW"
                counts[lvl] = counts.get(lvl, 0) + 1
            return counts
        except Exception as e:
            logger.error(f"count_by_risk_level error: {e}")
            return {}