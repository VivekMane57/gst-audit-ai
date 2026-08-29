"""
repositories/rule_repository.py
---------------------------------
CRUD + active rule fetching for compliance_rules table.
"""
from __future__ import annotations
import logging
from datetime import date
from typing import Optional
from supabase import Client

from app.repositories.base import SupabaseRepository
from app.models.rule import (
    ComplianceRuleDB,
    ComplianceRuleCreate,
    ComplianceRuleUpdate,
    ActiveRuleView,
)

logger = logging.getLogger(__name__)

_RULE_SELECT = (
    "id, rule_code, title, description, category, severity, "
    "condition_type, condition_config, law_code, plain_explanation, "
    "penalty_formula_type, penalty_formula_config, "
    "notice_risk_weight, notice_risk_max, "
    "is_active, version, effective_from, effective_to, "
    "created_by, created_at, updated_at"
)


class RuleRepository(SupabaseRepository):

    def __init__(self, db: Client):
        super().__init__(db, "compliance_rules")

    # ── Engine hot path ───────────────────────────────────────

    def get_active_rules(
        self,
        category:   Optional[str] = None,
        as_of_date: Optional[date] = None,
    ) -> list[ActiveRuleView]:
        today     = as_of_date or date.today()
        today_str = today.isoformat()

        query = (
            self.db.table(self.table)
            .select(_RULE_SELECT)
            .eq("is_active", True)
            .or_(f"effective_from.is.null,effective_from.lte.{today_str}")
            .or_(f"effective_to.is.null,effective_to.gte.{today_str}")
        )
        if category:
            query = query.eq("category", category)

        rows  = self._execute(query, "get_active_rules")
        rules = []
        for row in rows:
            try:
                db_obj = ComplianceRuleDB(**row)
                rules.append(ActiveRuleView.from_db(db_obj))
            except Exception as e:
                logger.warning(f"Rule parse error rule_code={row.get('rule_code')}: {e}")
        return rules

    def get_rule_weights_map(self) -> dict[str, dict]:
        """Returns dict compatible with notice_simulator.ISSUE_WEIGHTS format."""
        rules = self.get_active_rules()
        return {
            r.rule_code.lower(): {
                "weight":   r.notice_risk_weight,
                "max":      r.notice_risk_max,
                "category": r.category,
            }
            for r in rules
        }

    # ── Admin CRUD ────────────────────────────────────────────

    def get_by_id(self, rule_id: str) -> Optional[ComplianceRuleDB]:
        row = self._execute_single(
            self.db.table(self.table).select(_RULE_SELECT).eq("id", rule_id).limit(1),
            "get_by_id"
        )
        return ComplianceRuleDB(**row) if row else None

    def get_by_code(self, rule_code: str) -> Optional[ComplianceRuleDB]:
        row = self._execute_single(
            self.db.table(self.table).select(_RULE_SELECT)
            .eq("rule_code", rule_code.upper()).limit(1),
            "get_by_code"
        )
        return ComplianceRuleDB(**row) if row else None

    def list_all(
        self,
        active_only: bool = False,
        category:    Optional[str] = None,
        limit:       int = 200,
        offset:      int = 0,
    ) -> list[ComplianceRuleDB]:
        query = self.db.table(self.table).select(_RULE_SELECT)
        if active_only:
            query = query.eq("is_active", True)
        if category:
            query = query.eq("category", category)
        query = query.order("category").order("rule_code").range(offset, offset + limit - 1)
        rows  = self._execute(query, "list_all")
        return [ComplianceRuleDB(**r) for r in rows]

    def create(self, payload: ComplianceRuleCreate) -> ComplianceRuleDB:
        data = payload.model_dump(exclude_none=False)
        for k in ("effective_from", "effective_to"):
            if data.get(k):
                data[k] = data[k].isoformat()
        for k in ("category", "severity", "penalty_formula_type"):
            if hasattr(data.get(k), "value"):
                data[k] = data[k].value

        row = self._execute_single(
            self.db.table(self.table).insert(data).select(_RULE_SELECT),
            "create"
        )
        if not row:
            raise RuntimeError("Rule insert returned no row")
        self._log_change("created", row["id"], None, row)
        return ComplianceRuleDB(**row)

    def update(self, rule_id: str, payload: ComplianceRuleUpdate) -> Optional[ComplianceRuleDB]:
        before = self.get_by_id(rule_id)
        if not before:
            return None

        data = payload.model_dump(exclude_none=True)
        for k in ("effective_from", "effective_to"):
            if data.get(k):
                data[k] = data[k].isoformat()
        for k in ("severity", "penalty_formula_type"):
            if hasattr(data.get(k), "value"):
                data[k] = data[k].value

        row = self._execute_single(
            self.db.table(self.table).update(data).eq("id", rule_id).select(_RULE_SELECT),
            "update"
        )
        if row:
            self._log_change("updated", rule_id, before.model_dump(), row)
            return ComplianceRuleDB(**row)
        return None

    def set_active(self, rule_id: str, active: bool) -> Optional[ComplianceRuleDB]:
        action = "reactivated" if active else "deactivated"
        before = self.get_by_id(rule_id)
        if not before:
            return None

        row = self._execute_single(
            self.db.table(self.table)
            .update({"is_active": active})
            .eq("id", rule_id)
            .select(_RULE_SELECT),
            "set_active"
        )
        if row:
            self._log_change(action, rule_id, before.model_dump(), row)
            return ComplianceRuleDB(**row)
        return None

    def count_active(self) -> int:
        try:
            res = (
                self.db.table(self.table)
                .select("id", count="exact")
                .eq("is_active", True)
                .execute()
            )
            return res.count or 0
        except Exception:
            return 0

    def _log_change(
        self, action: str, entity_id: str,
        before: Optional[dict], after: Optional[dict],
        changed_by: Optional[str] = None,
    ) -> None:
        try:
            self.db.table("rule_audit_log").insert({
                "entity_type":  "compliance_rule",
                "entity_id":    str(entity_id),
                "action":       action,
                "changed_by":   changed_by,
                "before_state": before,
                "after_state":  after,
            }).execute()
        except Exception as e:
            logger.warning(f"Audit log write failed (non-fatal): {e}")