"""
routers/admin/laws_router.py
-----------------------------
Admin router: law_catalog CRUD.
"""
from fastapi import APIRouter, Depends, HTTPException, Header, Query
from typing import Optional
import logging

from app.db.supabase_client import get_supabase
from app.repositories.law_repository import LawRepository
from app.models.law import LawCatalogCreate, LawCatalogUpdate
from app.config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/laws", tags=["admin-laws"])


def _get_law_repo() -> LawRepository:
    return LawRepository(get_supabase())


def _assert_admin(x_admin_key: Optional[str] = Header(default=None)) -> None:
    settings = get_settings()
    admin_key = getattr(settings, "admin_api_key", None)
    if admin_key and x_admin_key != admin_key:
        raise HTTPException(status_code=403, detail="Admin access required")


@router.get("")
async def list_laws(
    active_only: bool       = Query(default=True),
    _:    None              = Depends(_assert_admin),
    repo: LawRepository     = Depends(_get_law_repo),
):
    laws = repo.list_all(active_only=active_only)
    return {"laws": [l.model_dump() for l in laws], "total": len(laws)}


@router.post("", status_code=201)
async def create_law(
    payload: LawCatalogCreate,
    _:    None          = Depends(_assert_admin),
    repo: LawRepository = Depends(_get_law_repo),
):
    existing = repo.get_by_code(payload.law_code)
    if existing:
        raise HTTPException(status_code=409, detail=f"Law '{payload.law_code}' already exists")
    law = repo.create(payload)
    return {"law": law.model_dump(), "message": "Law created"}


@router.patch("/{law_id}")
async def update_law(
    law_id:  str,
    payload: LawCatalogUpdate,
    _:    None          = Depends(_assert_admin),
    repo: LawRepository = Depends(_get_law_repo),
):
    updated = repo.update(law_id, payload)
    if not updated:
        raise HTTPException(status_code=404, detail="Law not found")
    return {"law": updated.model_dump(), "message": "Law updated"}