"""
services/notice_risk_queue.py
------------------------------
Notice Risk Queue — prioritized list of high-risk clients/audits
for the dashboard "Action Required" view.

Design:
  - Reads from audit_reports table (existing)
  - No new DB table needed — queries existing data
  - Prioritizes by: notice_probability > amount_at_risk > critical count > recency
  - Repository pattern — DB access isolated in NoticeQueueRepository
  - Service contains business logic only

Usage:
    from app.services.notice_risk_queue import NoticeRiskQueueService
    from app.repositories.notice_queue_repo import NoticeQueueRepository
    from app.db.supabase_client import get_supabase

    repo    = NoticeQueueRepository(get_supabase())
    service = NoticeRiskQueueService(repo)
    queue   = service.get_queue(ca_id="user_xxx", limit=20)
"""
from __future__ import annotations
import logging
from typing import Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


# ── Queue item schema ─────────────────────────────────────────
@dataclass
class QueueItem:
    """Single item in the notice risk queue."""
    audit_id:             str
    client_id:            Optional[str]
    client_name:          str
    client_gstin_masked:  str
    period:               str
    compliance_score:     int
    notice_probability:   int
    notice_risk_level:    str
    itc_at_risk:          float
    critical_count:       int
    high_count:           int
    unresolved_issue_count: int
    last_audit_date:      str
    top_reason:           str
    recommended_action:   str
    estimated_penalty:    float
    urgency_score:        float   # computed — used for sorting

    def to_dict(self) -> dict:
        return {
            "audit_id":               self.audit_id,
            "client_id":              self.client_id,
            "client_name":            self.client_name,
            "client_gstin_masked":    self.client_gstin_masked,
            "period":                 self.period,
            "compliance_score":       self.compliance_score,
            "notice_probability":     self.notice_probability,
            "notice_risk_level":      self.notice_risk_level,
            "itc_at_risk":            self.itc_at_risk,
            "critical_count":         self.critical_count,
            "high_count":             self.high_count,
            "unresolved_issue_count": self.unresolved_issue_count,
            "last_audit_date":        self.last_audit_date,
            "top_reason":             self.top_reason,
            "recommended_action":     self.recommended_action,
            "estimated_penalty":      self.estimated_penalty,
            "urgency_score":          round(self.urgency_score, 2),
        }


# ── Urgency score calculation ─────────────────────────────────
def _compute_urgency(
    notice_probability: int,
    itc_at_risk:        float,
    critical_count:     int,
    high_count:         int,
    compliance_score:   int,
) -> float:
    """
    Urgency score — higher = more urgent.
    Weights:
      - notice_probability: 50%
      - amount_at_risk (normalized): 25%
      - critical/high issues: 15%
      - compliance score (inverse): 10%
    """
    prob_score       = notice_probability * 0.50
    amount_score     = min(itc_at_risk / 100_000, 1.0) * 25          # normalize to 0-25
    issue_score      = min((critical_count * 3 + high_count * 1), 15) # max 15
    compliance_score_inv = ((100 - compliance_score) / 100) * 10     # inverse
    return round(prob_score + amount_score + issue_score + compliance_score_inv, 2)


# ── Recommended action generator ─────────────────────────────
def _recommended_action(
    notice_probability: int,
    critical_count:     int,
    itc_at_risk:        float,
) -> str:
    if notice_probability >= 70:
        return "URGENT: File corrections immediately. Notice likely within 3-6 months."
    if notice_probability >= 50:
        return "HIGH PRIORITY: Fix critical issues this week to reduce notice risk."
    if critical_count > 0:
        return f"Fix {critical_count} critical issue(s) before next filing."
    if itc_at_risk > 50_000:
        return f"Review ITC claims — ₹{itc_at_risk:,.0f} at risk. Do not claim until resolved."
    return "Monitor and fix flagged issues before next return filing."


# ── Queue service ─────────────────────────────────────────────
class NoticeRiskQueueService:
    """
    Business logic for notice risk queue.
    Reads existing audit_reports — no new DB table.
    """

    def __init__(self, repo: "NoticeQueueRepository"):
        self.repo = repo

    def get_queue(
        self,
        ca_id:        str,
        min_prob:     int   = 0,      # Only show audits with probability >= this
        limit:        int   = 50,
        risk_level:   Optional[str] = None,  # Filter: LOW/MEDIUM/HIGH/VERY_HIGH
    ) -> list[dict]:
        """
        Get prioritized notice risk queue for a CA.
        Returns list sorted by urgency_score descending.
        """
        rows = self.repo.fetch_latest_audits_per_client(ca_id, limit=limit * 2)

        items: list[QueueItem] = []
        for row in rows:
            prob          = int(row.get("notice_probability") or 0)
            notice_level  = row.get("notice_risk_level") or "LOW"

            # Filters
            if prob < min_prob:
                continue
            if risk_level and notice_level != risk_level:
                continue

            itc_at_risk    = float(row.get("itc_at_risk") or 0)
            critical_count = int(row.get("critical_count") or 0)
            high_count     = int(row.get("high_count") or 0)
            medium_count   = int(row.get("medium_count") or 0)
            score          = int(row.get("compliance_score") or 100)

            # top_reason: from notice_simulation or fallback
            notice_sim    = row.get("notice_simulation") or {}
            top_reasons   = notice_sim.get("top_risk_reasons") or row.get("top_risk_reasons") or []
            top_reason    = top_reasons[0] if top_reasons else _default_reason(notice_level)

            estimated_penalty = float(
                notice_sim.get("estimated_penalty_exposure") or
                row.get("estimated_penalty_exposure") or 0
            )

            urgency = _compute_urgency(prob, itc_at_risk, critical_count, high_count, score)

            items.append(QueueItem(
                audit_id             = row["id"],
                client_id            = row.get("client_id"),
                client_name          = row.get("client_name") or "Unknown Client",
                client_gstin_masked  = row.get("client_gstin_masked") or "**********",
                period               = row.get("period") or "",
                compliance_score     = score,
                notice_probability   = prob,
                notice_risk_level    = notice_level,
                itc_at_risk          = itc_at_risk,
                critical_count       = critical_count,
                high_count           = high_count,
                unresolved_issue_count = critical_count + high_count + medium_count,
                last_audit_date      = row.get("created_at") or "",
                top_reason           = top_reason,
                recommended_action   = _recommended_action(prob, critical_count, itc_at_risk),
                estimated_penalty    = estimated_penalty,
                urgency_score        = urgency,
            ))

        # Sort by urgency descending
        items.sort(key=lambda x: x.urgency_score, reverse=True)

        return [item.to_dict() for item in items[:limit]]

    def get_summary(self, ca_id: str) -> dict:
        """
        Dashboard summary stats for notice risk queue.
        Returns total counts by risk level + total exposure.
        """
        rows = self.repo.fetch_latest_audits_per_client(ca_id, limit=200)
        total           = len(rows)
        very_high       = sum(1 for r in rows if (r.get("notice_risk_level") or "") == "VERY_HIGH")
        high            = sum(1 for r in rows if (r.get("notice_risk_level") or "") == "HIGH")
        medium          = sum(1 for r in rows if (r.get("notice_risk_level") or "") == "MEDIUM")
        low             = sum(1 for r in rows if (r.get("notice_risk_level") or "") == "LOW")
        total_itc       = sum(float(r.get("itc_at_risk") or 0) for r in rows)
        total_penalty   = sum(
            float((r.get("notice_simulation") or {}).get("estimated_penalty_exposure") or
                  r.get("estimated_penalty_exposure") or 0)
            for r in rows
        )
        avg_prob = (
            sum(int(r.get("notice_probability") or 0) for r in rows) / total
            if total > 0 else 0
        )

        return {
            "total_clients_audited": total,
            "by_risk_level": {
                "very_high": very_high,
                "high":      high,
                "medium":    medium,
                "low":       low,
            },
            "total_itc_at_risk":           round(total_itc, 2),
            "total_estimated_penalty":     round(total_penalty, 2),
            "average_notice_probability":  round(avg_prob, 1),
            "clients_needing_action":      very_high + high,
        }


def _default_reason(risk_level: str) -> str:
    return {
        "VERY_HIGH": "Multiple critical compliance issues detected",
        "HIGH":      "Significant ITC or reconciliation issues found",
        "MEDIUM":    "Some compliance gaps need attention",
        "LOW":       "Minor issues — good compliance overall",
    }.get(risk_level, "Compliance review recommended")