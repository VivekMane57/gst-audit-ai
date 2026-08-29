"""
repositories/threshold_repository.py
--------------------------------------
CRUD for risk_thresholds table.
get_default() MUST never raise — it's in the audit critical path.
"""
from __future__ import annotations
from typing import Optional
from supabase import Client

from app.repositories.base import SupabaseRepository
from app.models.threshold import (
    RiskThresholdDB,
    RiskThresholdCreate,
    RiskThresholdUpdate,
    DEFAULT_THRESHOLD_FALLBACK,
)

_THRESHOLD_SELECT = (
    "id, profile_name, low_max, medium_max, "
    "high_max, critical_min, is_default, created_at, updated_at"
)


class ThresholdRepository(SupabaseRepository):

    def __init__(self, db: Client):
        super().__init__(db, "risk_thresholds")

    def get_default(self) -> RiskThresholdDB:
        """
        Returns default threshold profile.
        Falls back to hardcoded default if DB unavailable.
        NEVER raises — audit critical path.
        """
        try:
            row = self._execute_single(
                self.db.table(self.table).select(_THRESHOLD_SELECT)
                .eq("is_default", True).limit(1),
                "get_default"
            )
            if row:
                return RiskThresholdDB(**row)
        except Exception as e:
            self.logger.error(f"get_default failed — using hardcoded fallback: {e}")

        # Hardcoded fallback — matches migration seed values
        return RiskThresholdDB(
            id           = "00000000-0000-0000-0000-000000000000",
            profile_name = DEFAULT_THRESHOLD_FALLBACK.profile_name,
            low_max      = DEFAULT_THRESHOLD_FALLBACK.low_max,
            medium_max   = DEFAULT_THRESHOLD_FALLBACK.medium_max,
            high_max     = DEFAULT_THRESHOLD_FALLBACK.high_max,
            critical_min = DEFAULT_THRESHOLD_FALLBACK.critical_min,
            is_default   = True,
        )

    def list_all(self) -> list[RiskThresholdDB]:
        rows = self._execute(
            self.db.table(self.table).select(_THRESHOLD_SELECT).order("profile_name"),
            "list_all"
        )
        return [RiskThresholdDB(**r) for r in rows]

    def create(self, payload: RiskThresholdCreate) -> RiskThresholdDB:
        payload.validate_bands()
        data = payload.model_dump()
        row  = self._execute_single(
            self.db.table(self.table).insert(data).select(_THRESHOLD_SELECT),
            "create"
        )
        if not row:
            raise RuntimeError("Threshold insert returned no row")
        self._log_threshold_change("created", row["id"], None, row)
        return RiskThresholdDB(**row)

    def update(self, threshold_id: str, payload: RiskThresholdUpdate) -> Optional[RiskThresholdDB]:
        data = payload.model_dump(exclude_none=True)
        if data.get("is_default") is True:
            self._clear_other_defaults(threshold_id)

        row = self._execute_single(
            self.db.table(self.table).update(data).eq("id", threshold_id).select(_THRESHOLD_SELECT),
            "update"
        )
        if row:
            self._log_threshold_change("updated", threshold_id, None, row)
            return RiskThresholdDB(**row)
        return None

    def _clear_other_defaults(self, except_id: str) -> None:
        try:
            self.db.table(self.table) \
                .update({"is_default": False}) \
                .neq("id", except_id) \
                .eq("is_default", True) \
                .execute()
        except Exception as e:
            self.logger.warning(f"_clear_other_defaults failed: {e}")

    def _log_threshold_change(self, action: str, entity_id: str, before, after) -> None:
        try:
            self.db.table("rule_audit_log").insert({
                "entity_type":  "risk_threshold",
                "entity_id":    str(entity_id),
                "action":       action,
                "before_state": before,
                "after_state":  after,
            }).execute()
        except Exception as e:
            self.logger.warning(f"Threshold audit log failed: {e}")