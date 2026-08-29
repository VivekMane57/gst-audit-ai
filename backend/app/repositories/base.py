# """
# repositories/base.py
# --------------------
# Minimal Supabase repository base.
# Matches your existing repo style (sync Supabase client, .execute() pattern).
# No magic — just shared error handling and logging.
# """
# from __future__ import annotations
# import logging
# from typing import Optional, Any
# from supabase import Client


# class SupabaseRepository:
#     """
#     Thin base. Provides:
#       - self.db
#       - self.logger
#       - _execute() with consistent error wrapping
#     Not an ORM. Not a unit-of-work. Just a clean base.
#     """

#     def __init__(self, db: Client, table_name: str):
#         self.db    = db
#         self.table = table_name
#         self.logger = logging.getLogger(self.__class__.__name__)

#     def _execute(self, query: Any, context: str = "") -> list[dict]:
#         """
#         Execute a Supabase query and return rows.
#         Raises RuntimeError on DB errors — caller decides how to handle.
#         """
#         try:
#             res = query.execute()
#             return res.data or []
#         except Exception as e:
#             self.logger.error(f"DB error [{self.table}]{f' [{context}]' if context else ''}: {e}")
#             raise RuntimeError(f"Database error on {self.table}: {e}") from e

#     def _execute_single(self, query: Any, context: str = "") -> Optional[dict]:
#         rows = self._execute(query, context)
#         return rows[0] if rows else None


# """
# repositories/rule_repository.py
# ---------------------------------
# CRUD + active rule fetching for compliance_rules table.
# Engine calls get_active_rules() — the hot path.
# Admin API calls the rest.
# """
# from __future__ import annotations
# import logging
# from datetime import date
# from typing import Optional
# from supabase import Client

# from app.repositories.base import SupabaseRepository
# from app.models.rule import (
#     ComplianceRuleDB,
#     ComplianceRuleCreate,
#     ComplianceRuleUpdate,
#     ActiveRuleView,
# )

# logger = logging.getLogger(__name__)

# _RULE_SELECT = (
#     "id, rule_code, title, description, category, severity, "
#     "condition_type, condition_config, law_code, plain_explanation, "
#     "penalty_formula_type, penalty_formula_config, "
#     "notice_risk_weight, notice_risk_max, "
#     "is_active, version, effective_from, effective_to, "
#     "created_by, created_at, updated_at"
# )


# class RuleRepository(SupabaseRepository):

#     def __init__(self, db: Client):
#         super().__init__(db, "compliance_rules")

#     # ── Engine hot path ───────────────────────────────────────

#     def get_active_rules(
#         self,
#         category:   Optional[str] = None,
#         as_of_date: Optional[date] = None,
#     ) -> list[ActiveRuleView]:
#         """
#         Fetch all active, currently-effective rules.
#         Called by rule_engine_service on every audit run.

#         as_of_date defaults to today — rules outside effective window excluded.
#         """
#         today = as_of_date or date.today()
#         today_str = today.isoformat()

#         query = (
#             self.db.table(self.table)
#             .select(_RULE_SELECT)
#             .eq("is_active", True)
#             # effective_from <= today OR effective_from IS NULL
#             .or_(f"effective_from.is.null,effective_from.lte.{today_str}")
#             # effective_to >= today OR effective_to IS NULL
#             .or_(f"effective_to.is.null,effective_to.gte.{today_str}")
#         )

#         if category:
#             query = query.eq("category", category)

#         rows = self._execute(query, "get_active_rules")

#         rules = []
#         for row in rows:
#             try:
#                 db_obj = ComplianceRuleDB(**row)
#                 rules.append(ActiveRuleView.from_db(db_obj))
#             except Exception as e:
#                 logger.warning(f"Rule parse error rule_code={row.get('rule_code')}: {e}")
#         return rules

#     def get_rule_weights_map(self) -> dict[str, dict]:
#         """
#         Returns dict compatible with notice_simulator.ISSUE_WEIGHTS format.
#         Used for backward-compatible migration path.

#         Format: {"rule_code": {"weight": 8.0, "max": 15.0, "category": "itc"}}
#         """
#         rules = self.get_active_rules()
#         return {
#             r.rule_code.lower(): {
#                 "weight":   r.notice_risk_weight,
#                 "max":      r.notice_risk_max,
#                 "category": r.category,
#             }
#             for r in rules
#         }

#     # ── Admin CRUD ────────────────────────────────────────────

#     def get_by_id(self, rule_id: str) -> Optional[ComplianceRuleDB]:
#         row = self._execute_single(
#             self.db.table(self.table).select(_RULE_SELECT).eq("id", rule_id).limit(1),
#             "get_by_id"
#         )
#         return ComplianceRuleDB(**row) if row else None

#     def get_by_code(self, rule_code: str) -> Optional[ComplianceRuleDB]:
#         row = self._execute_single(
#             self.db.table(self.table).select(_RULE_SELECT)
#             .eq("rule_code", rule_code.upper()).limit(1),
#             "get_by_code"
#         )
#         return ComplianceRuleDB(**row) if row else None

#     def list_all(
#         self,
#         active_only: bool = False,
#         category:    Optional[str] = None,
#         limit:       int = 200,
#         offset:      int = 0,
#     ) -> list[ComplianceRuleDB]:
#         query = self.db.table(self.table).select(_RULE_SELECT)
#         if active_only:
#             query = query.eq("is_active", True)
#         if category:
#             query = query.eq("category", category)
#         query = query.order("category").order("rule_code").range(offset, offset + limit - 1)
#         rows = self._execute(query, "list_all")
#         return [ComplianceRuleDB(**r) for r in rows]

#     def create(self, payload: ComplianceRuleCreate) -> ComplianceRuleDB:
#         data = payload.model_dump(exclude_none=False)
#         # Serialize date objects for Supabase
#         for k in ("effective_from", "effective_to"):
#             if data.get(k):
#                 data[k] = data[k].isoformat()
#         # Serialize enums
#         for k in ("category", "severity", "penalty_formula_type"):
#             if hasattr(data.get(k), "value"):
#                 data[k] = data[k].value

#         row = self._execute_single(
#             self.db.table(self.table).insert(data).select(_RULE_SELECT),
#             "create"
#         )
#         if not row:
#             raise RuntimeError("Rule insert returned no row")
#         self._log_change("created", row["id"], None, row)
#         return ComplianceRuleDB(**row)

#     def update(self, rule_id: str, payload: ComplianceRuleUpdate) -> Optional[ComplianceRuleDB]:
#         before = self.get_by_id(rule_id)
#         if not before:
#             return None

#         data = payload.model_dump(exclude_none=True)
#         # Serialize
#         for k in ("effective_from", "effective_to"):
#             if data.get(k):
#                 data[k] = data[k].isoformat()
#         for k in ("severity", "penalty_formula_type"):
#             if hasattr(data.get(k), "value"):
#                 data[k] = data[k].value

#         row = self._execute_single(
#             self.db.table(self.table).update(data).eq("id", rule_id).select(_RULE_SELECT),
#             "update"
#         )
#         if row:
#             self._log_change("updated", rule_id, before.model_dump(), row)
#             return ComplianceRuleDB(**row)
#         return None

#     def set_active(self, rule_id: str, active: bool) -> Optional[ComplianceRuleDB]:
#         action = "reactivated" if active else "deactivated"
#         before = self.get_by_id(rule_id)
#         if not before:
#             return None

#         row = self._execute_single(
#             self.db.table(self.table)
#             .update({"is_active": active})
#             .eq("id", rule_id)
#             .select(_RULE_SELECT),
#             "set_active"
#         )
#         if row:
#             self._log_change(action, rule_id, before.model_dump(), row)
#             return ComplianceRuleDB(**row)
#         return None

#     def count_active(self) -> int:
#         try:
#             res = (
#                 self.db.table(self.table)
#                 .select("id", count="exact")
#                 .eq("is_active", True)
#                 .execute()
#             )
#             return res.count or 0
#         except Exception:
#             return 0

#     # ── Audit log helper ──────────────────────────────────────

#     def _log_change(
#         self, action: str, entity_id: str,
#         before: Optional[dict], after: Optional[dict],
#         changed_by: Optional[str] = None,
#     ) -> None:
#         try:
#             self.db.table("rule_audit_log").insert({
#                 "entity_type": "compliance_rule",
#                 "entity_id":   str(entity_id),
#                 "action":      action,
#                 "changed_by":  changed_by,
#                 "before_state": before,
#                 "after_state":  after,
#             }).execute()
#         except Exception as e:
#             logger.warning(f"Audit log write failed (non-fatal): {e}")


# """
# repositories/law_repository.py
# --------------------------------
# """
# from app.models.rule import RuleCategory
# from app.models.law import LawCatalogDB, LawCatalogCreate, LawCatalogUpdate

# _LAW_SELECT = "id, law_code, act_name, section, short_text, official_source_url, reviewed_on, is_active, created_at, updated_at"


# class LawRepository(SupabaseRepository):

#     def __init__(self, db: Client):
#         super().__init__(db, "law_catalog")

#     def get_by_code(self, law_code: str) -> Optional[LawCatalogDB]:
#         row = self._execute_single(
#             self.db.table(self.table).select(_LAW_SELECT)
#             .eq("law_code", law_code.upper()).limit(1)
#         )
#         return LawCatalogDB(**row) if row else None

#     def list_all(self, active_only: bool = True) -> list[LawCatalogDB]:
#         query = self.db.table(self.table).select(_LAW_SELECT)
#         if active_only:
#             query = query.eq("is_active", True)
#         query = query.order("act_name").order("section")
#         rows = self._execute(query, "list_all")
#         return [LawCatalogDB(**r) for r in rows]

#     def create(self, payload: LawCatalogCreate) -> LawCatalogDB:
#         data = payload.model_dump(exclude_none=False)
#         if data.get("reviewed_on"):
#             data["reviewed_on"] = data["reviewed_on"].isoformat()
#         row = self._execute_single(
#             self.db.table(self.table).insert(data).select(_LAW_SELECT)
#         )
#         if not row:
#             raise RuntimeError("Law insert returned no row")
#         self._log_law_change("created", row["id"], None, row)
#         return LawCatalogDB(**row)

#     def update(self, law_id: str, payload: LawCatalogUpdate) -> Optional[LawCatalogDB]:
#         data = payload.model_dump(exclude_none=True)
#         if data.get("reviewed_on"):
#             data["reviewed_on"] = data["reviewed_on"].isoformat()
#         row = self._execute_single(
#             self.db.table(self.table).update(data).eq("id", law_id).select(_LAW_SELECT)
#         )
#         return LawCatalogDB(**row) if row else None

#     def bulk_upsert_for_seeding(self, laws: list[LawCatalogCreate]) -> int:
#         """
#         Used by seed scripts. Upsert on law_code.
#         Returns count of upserted rows.
#         """
#         records = []
#         for law in laws:
#             data = law.model_dump(exclude_none=False)
#             if data.get("reviewed_on"):
#                 data["reviewed_on"] = data["reviewed_on"].isoformat()
#             records.append(data)
#         if not records:
#             return 0
#         self.db.table(self.table).upsert(records, on_conflict="law_code").execute()
#         return len(records)

#     def _log_law_change(self, action, entity_id, before, after):
#         try:
#             self.db.table("rule_audit_log").insert({
#                 "entity_type": "law_catalog",
#                 "entity_id":   str(entity_id),
#                 "action":      action,
#                 "before_state": before,
#                 "after_state":  after,
#             }).execute()
#         except Exception as e:
#             self.logger.warning(f"Law audit log failed: {e}")


# """
# repositories/fix_step_repository.py
# -------------------------------------
# """
# from app.models.fix_step import RuleFixStepDB, RuleFixStepCreate, RuleFixStepUpdate, RuleFixStepsBundle

# _STEP_SELECT = "id, rule_code, step_order, step_text_en, step_text_hi, step_text_mr, created_at, updated_at"


# class FixStepRepository(SupabaseRepository):

#     def __init__(self, db: Client):
#         super().__init__(db, "rule_fix_steps")

#     def get_steps_for_rule(self, rule_code: str) -> list[RuleFixStepDB]:
#         rows = self._execute(
#             self.db.table(self.table).select(_STEP_SELECT)
#             .eq("rule_code", rule_code.upper())
#             .order("step_order"),
#             "get_steps_for_rule"
#         )
#         return [RuleFixStepDB(**r) for r in rows]

#     def get_bundle(self, rule_code: str) -> RuleFixStepsBundle:
#         """Returns RuleFixStepsBundle — engine-ready, language-keyed."""
#         steps = self.get_steps_for_rule(rule_code)
#         return RuleFixStepsBundle(
#             rule_code = rule_code,
#             en        = [s.step_text_en for s in steps],
#             hi        = [s.step_text_hi or s.step_text_en for s in steps],
#             mr        = [s.step_text_mr or s.step_text_en for s in steps],
#         )

#     def get_bundles_for_rules(self, rule_codes: list[str]) -> dict[str, RuleFixStepsBundle]:
#         """
#         Batch fetch — one query for multiple rules.
#         Returns {rule_code: RuleFixStepsBundle}
#         """
#         if not rule_codes:
#             return {}
#         upper_codes = [c.upper() for c in rule_codes]
#         rows = self._execute(
#             self.db.table(self.table).select(_STEP_SELECT)
#             .in_("rule_code", upper_codes)
#             .order("rule_code").order("step_order"),
#             "get_bundles_for_rules"
#         )

#         bundles: dict[str, dict] = {}
#         for row in rows:
#             rc = row["rule_code"]
#             if rc not in bundles:
#                 bundles[rc] = {"en": [], "hi": [], "mr": []}
#             bundles[rc]["en"].append(row["step_text_en"])
#             bundles[rc]["hi"].append(row["step_text_hi"] or row["step_text_en"])
#             bundles[rc]["mr"].append(row["step_text_mr"] or row["step_text_en"])

#         return {
#             rc: RuleFixStepsBundle(rule_code=rc, **data)
#             for rc, data in bundles.items()
#         }

#     def add_step(self, payload: RuleFixStepCreate) -> RuleFixStepDB:
#         data = payload.model_dump()
#         data["rule_code"] = data["rule_code"].upper()
#         row = self._execute_single(
#             self.db.table(self.table).insert(data).select(_STEP_SELECT)
#         )
#         if not row:
#             raise RuntimeError("Fix step insert returned no row")
#         return RuleFixStepDB(**row)

#     def update_step(self, step_id: str, payload: RuleFixStepUpdate) -> Optional[RuleFixStepDB]:
#         data = payload.model_dump(exclude_none=True)
#         row = self._execute_single(
#             self.db.table(self.table).update(data).eq("id", step_id).select(_STEP_SELECT)
#         )
#         return RuleFixStepDB(**row) if row else None

#     def delete_step(self, step_id: str) -> bool:
#         try:
#             self.db.table(self.table).delete().eq("id", step_id).execute()
#             return True
#         except Exception as e:
#             self.logger.error(f"delete_step failed: {e}")
#             return False

#     def reorder_steps(self, rule_code: str, step_ids_ordered: list[str]) -> bool:
#         """
#         Reorder steps by providing step IDs in desired order.
#         Updates step_order to match position in list.
#         """
#         try:
#             for idx, step_id in enumerate(step_ids_ordered, start=1):
#                 self.db.table(self.table).update({"step_order": idx}).eq("id", step_id).eq("rule_code", rule_code.upper()).execute()
#             return True
#         except Exception as e:
#             self.logger.error(f"reorder_steps failed: {e}")
#             return False


# """
# repositories/threshold_repository.py
# --------------------------------------
# """
# from app.models.threshold import RiskThresholdDB, RiskThresholdCreate, RiskThresholdUpdate, DEFAULT_THRESHOLD_FALLBACK

# _THRESHOLD_SELECT = "id, profile_name, low_max, medium_max, high_max, critical_min, is_default, created_at, updated_at"


# class ThresholdRepository(SupabaseRepository):

#     def __init__(self, db: Client):
#         super().__init__(db, "risk_thresholds")

#     def get_default(self) -> RiskThresholdDB:
#         """
#         Returns default threshold profile.
#         Falls back to hardcoded default if DB unavailable.
#         This method MUST never raise — it's in the audit critical path.
#         """
#         try:
#             row = self._execute_single(
#                 self.db.table(self.table).select(_THRESHOLD_SELECT)
#                 .eq("is_default", True).limit(1)
#             )
#             if row:
#                 return RiskThresholdDB(**row)
#         except Exception as e:
#             self.logger.error(f"get_default threshold failed — using hardcoded fallback: {e}")

#         # Hardcoded fallback — matches migration seed values
#         return RiskThresholdDB(
#             id           = "00000000-0000-0000-0000-000000000000",
#             profile_name = DEFAULT_THRESHOLD_FALLBACK.profile_name,
#             low_max      = DEFAULT_THRESHOLD_FALLBACK.low_max,
#             medium_max   = DEFAULT_THRESHOLD_FALLBACK.medium_max,
#             high_max     = DEFAULT_THRESHOLD_FALLBACK.high_max,
#             critical_min = DEFAULT_THRESHOLD_FALLBACK.critical_min,
#             is_default   = True,
#         )

#     def list_all(self) -> list[RiskThresholdDB]:
#         rows = self._execute(
#             self.db.table(self.table).select(_THRESHOLD_SELECT).order("profile_name")
#         )
#         return [RiskThresholdDB(**r) for r in rows]

#     def create(self, payload: RiskThresholdCreate) -> RiskThresholdDB:
#         payload.validate_bands()
#         data = payload.model_dump()
#         row = self._execute_single(
#             self.db.table(self.table).insert(data).select(_THRESHOLD_SELECT)
#         )
#         if not row:
#             raise RuntimeError("Threshold insert returned no row")
#         self._log_threshold_change("created", row["id"], None, row)
#         return RiskThresholdDB(**row)

#     def update(self, threshold_id: str, payload: RiskThresholdUpdate) -> Optional[RiskThresholdDB]:
#         data = payload.model_dump(exclude_none=True)
#         # If setting as default, clear other defaults first
#         if data.get("is_default") is True:
#             self._clear_other_defaults(threshold_id)

#         row = self._execute_single(
#             self.db.table(self.table).update(data).eq("id", threshold_id).select(_THRESHOLD_SELECT)
#         )
#         if row:
#             self._log_threshold_change("updated", threshold_id, None, row)
#             return RiskThresholdDB(**row)
#         return None

#     def _clear_other_defaults(self, except_id: str) -> None:
#         try:
#             self.db.table(self.table).update({"is_default": False}).neq("id", except_id).eq("is_default", True).execute()
#         except Exception as e:
#             self.logger.warning(f"_clear_other_defaults failed: {e}")

#     def _log_threshold_change(self, action, entity_id, before, after):
#         try:
#             self.db.table("rule_audit_log").insert({
#                 "entity_type": "risk_threshold",
#                 "entity_id":   str(entity_id),
#                 "action":      action,
#                 "before_state": before,
#                 "after_state":  after,
#             }).execute()
#         except Exception as e:
#             self.logger.warning(f"Threshold audit log failed: {e}")




"""
repositories/base.py
--------------------
Minimal Supabase repository base.
Matches existing repo style (sync Supabase client, .execute() pattern).
"""
from __future__ import annotations
import logging
from typing import Optional, Any
from supabase import Client


class SupabaseRepository:
    """
    Thin base. Provides:
      - self.db
      - self.logger
      - _execute() with consistent error wrapping
    """

    def __init__(self, db: Client, table_name: str):
        self.db     = db
        self.table  = table_name
        self.logger = logging.getLogger(self.__class__.__name__)

    def _execute(self, query: Any, context: str = "") -> list[dict]:
        """Execute a Supabase query and return rows."""
        try:
            res = query.execute()
            return res.data or []
        except Exception as e:
            self.logger.error(
                f"DB error [{self.table}]{f' [{context}]' if context else ''}: {e}"
            )
            raise RuntimeError(f"Database error on {self.table}: {e}") from e

    def _execute_single(self, query: Any, context: str = "") -> Optional[dict]:
        rows = self._execute(query, context)
        return rows[0] if rows else None