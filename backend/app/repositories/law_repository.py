"""
repositories/law_repository.py
--------------------------------
CRUD for law_catalog table.
"""
from __future__ import annotations
from typing import Optional
from supabase import Client

from app.repositories.base import SupabaseRepository
from app.models.law import LawCatalogDB, LawCatalogCreate, LawCatalogUpdate

_LAW_SELECT = (
    "id, law_code, act_name, section, short_text, "
    "official_source_url, reviewed_on, is_active, created_at, updated_at"
)


class LawRepository(SupabaseRepository):

    def __init__(self, db: Client):
        super().__init__(db, "law_catalog")

    def get_by_code(self, law_code: str) -> Optional[LawCatalogDB]:
        row = self._execute_single(
            self.db.table(self.table).select(_LAW_SELECT)
            .eq("law_code", law_code.upper()).limit(1),
            "get_by_code"
        )
        return LawCatalogDB(**row) if row else None

    def list_all(self, active_only: bool = True) -> list[LawCatalogDB]:
        query = self.db.table(self.table).select(_LAW_SELECT)
        if active_only:
            query = query.eq("is_active", True)
        query = query.order("act_name").order("section")
        rows  = self._execute(query, "list_all")
        return [LawCatalogDB(**r) for r in rows]

    def create(self, payload: LawCatalogCreate) -> LawCatalogDB:
        data = payload.model_dump(exclude_none=False)
        if data.get("reviewed_on"):
            data["reviewed_on"] = data["reviewed_on"].isoformat()
        row = self._execute_single(
            self.db.table(self.table).insert(data).select(_LAW_SELECT),
            "create"
        )
        if not row:
            raise RuntimeError("Law insert returned no row")
        self._log_law_change("created", row["id"], None, row)
        return LawCatalogDB(**row)

    def update(self, law_id: str, payload: LawCatalogUpdate) -> Optional[LawCatalogDB]:
        data = payload.model_dump(exclude_none=True)
        if data.get("reviewed_on"):
            data["reviewed_on"] = data["reviewed_on"].isoformat()
        row = self._execute_single(
            self.db.table(self.table).update(data).eq("id", law_id).select(_LAW_SELECT),
            "update"
        )
        return LawCatalogDB(**row) if row else None

    def bulk_upsert_for_seeding(self, laws: list[LawCatalogCreate]) -> int:
        """Used by seed scripts. Upsert on law_code."""
        records = []
        for law in laws:
            data = law.model_dump(exclude_none=False)
            if data.get("reviewed_on"):
                data["reviewed_on"] = data["reviewed_on"].isoformat()
            records.append(data)
        if not records:
            return 0
        self.db.table(self.table).upsert(records, on_conflict="law_code").execute()
        return len(records)

    def _log_law_change(self, action: str, entity_id: str, before, after) -> None:
        try:
            self.db.table("rule_audit_log").insert({
                "entity_type":  "law_catalog",
                "entity_id":    str(entity_id),
                "action":       action,
                "before_state": before,
                "after_state":  after,
            }).execute()
        except Exception as e:
            self.logger.warning(f"Law audit log failed: {e}")