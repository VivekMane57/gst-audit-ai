"""
repositories/fix_step_repository.py
-------------------------------------
CRUD for rule_fix_steps table.
"""
from __future__ import annotations
from typing import Optional
from supabase import Client

from app.repositories.base import SupabaseRepository
from app.models.fix_step import (
    RuleFixStepDB,
    RuleFixStepCreate,
    RuleFixStepUpdate,
    RuleFixStepsBundle,
)

_STEP_SELECT = (
    "id, rule_code, step_order, step_text_en, "
    "step_text_hi, step_text_mr, created_at, updated_at"
)


class FixStepRepository(SupabaseRepository):

    def __init__(self, db: Client):
        super().__init__(db, "rule_fix_steps")

    def get_steps_for_rule(self, rule_code: str) -> list[RuleFixStepDB]:
        rows = self._execute(
            self.db.table(self.table).select(_STEP_SELECT)
            .eq("rule_code", rule_code.upper())
            .order("step_order"),
            "get_steps_for_rule"
        )
        return [RuleFixStepDB(**r) for r in rows]

    def get_bundle(self, rule_code: str) -> RuleFixStepsBundle:
        steps = self.get_steps_for_rule(rule_code)
        return RuleFixStepsBundle(
            rule_code = rule_code,
            en        = [s.step_text_en for s in steps],
            hi        = [s.step_text_hi or s.step_text_en for s in steps],
            mr        = [s.step_text_mr or s.step_text_en for s in steps],
        )

    def get_bundles_for_rules(self, rule_codes: list[str]) -> dict[str, RuleFixStepsBundle]:
        """Batch fetch — one query for multiple rules."""
        if not rule_codes:
            return {}
        upper_codes = [c.upper() for c in rule_codes]
        rows = self._execute(
            self.db.table(self.table).select(_STEP_SELECT)
            .in_("rule_code", upper_codes)
            .order("rule_code").order("step_order"),
            "get_bundles_for_rules"
        )

        bundles: dict[str, dict] = {}
        for row in rows:
            rc = row["rule_code"]
            if rc not in bundles:
                bundles[rc] = {"en": [], "hi": [], "mr": []}
            bundles[rc]["en"].append(row["step_text_en"])
            bundles[rc]["hi"].append(row["step_text_hi"] or row["step_text_en"])
            bundles[rc]["mr"].append(row["step_text_mr"] or row["step_text_en"])

        return {
            rc: RuleFixStepsBundle(rule_code=rc, **data)
            for rc, data in bundles.items()
        }

    def add_step(self, payload: RuleFixStepCreate) -> RuleFixStepDB:
        data = payload.model_dump()
        data["rule_code"] = data["rule_code"].upper()
        row = self._execute_single(
            self.db.table(self.table).insert(data).select(_STEP_SELECT),
            "add_step"
        )
        if not row:
            raise RuntimeError("Fix step insert returned no row")
        return RuleFixStepDB(**row)

    def update_step(self, step_id: str, payload: RuleFixStepUpdate) -> Optional[RuleFixStepDB]:
        data = payload.model_dump(exclude_none=True)
        row  = self._execute_single(
            self.db.table(self.table).update(data).eq("id", step_id).select(_STEP_SELECT),
            "update_step"
        )
        return RuleFixStepDB(**row) if row else None

    def delete_step(self, step_id: str) -> bool:
        try:
            self.db.table(self.table).delete().eq("id", step_id).execute()
            return True
        except Exception as e:
            self.logger.error(f"delete_step failed: {e}")
            return False

    def reorder_steps(self, rule_code: str, step_ids_ordered: list[str]) -> bool:
        try:
            for idx, step_id in enumerate(step_ids_ordered, start=1):
                self.db.table(self.table).update({"step_order": idx}) \
                    .eq("id", step_id) \
                    .eq("rule_code", rule_code.upper()) \
                    .execute()
            return True
        except Exception as e:
            self.logger.error(f"reorder_steps failed: {e}")
            return False