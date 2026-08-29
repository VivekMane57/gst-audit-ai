"""
routers/admin/fix_steps_router.py
-----------------------------------
Admin router: rule_fix_steps CRUD.
"""
from fastapi import APIRouter, Depends, HTTPException, Header
from typing import Optional
import logging

from app.db.supabase_client import get_supabase
from app.repositories.fix_step_repository import FixStepRepository
from app.models.fix_step import RuleFixStepCreate, RuleFixStepUpdate
from app.config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/fix-steps", tags=["admin-fix-steps"])


def _get_fix_step_repo() -> FixStepRepository:
    return FixStepRepository(get_supabase())


def _assert_admin(x_admin_key: Optional[str] = Header(default=None)) -> None:
    settings = get_settings()
    admin_key = getattr(settings, "admin_api_key", None)
    if admin_key and x_admin_key != admin_key:
        raise HTTPException(status_code=403, detail="Admin access required")


@router.get("/{rule_code}")
async def get_fix_steps(
    rule_code: str,
    _:    None              = Depends(_assert_admin),
    repo: FixStepRepository = Depends(_get_fix_step_repo),
):
    bundle = repo.get_bundle(rule_code)
    return {"rule_code": rule_code, "steps": bundle.model_dump()}


@router.post("", status_code=201)
async def add_fix_step(
    payload: RuleFixStepCreate,
    _:    None              = Depends(_assert_admin),
    repo: FixStepRepository = Depends(_get_fix_step_repo),
):
    step = repo.add_step(payload)
    return {"step": step.model_dump(), "message": "Fix step added"}


@router.patch("/{step_id}")
async def update_fix_step(
    step_id: str,
    payload: RuleFixStepUpdate,
    _:    None              = Depends(_assert_admin),
    repo: FixStepRepository = Depends(_get_fix_step_repo),
):
    updated = repo.update_step(step_id, payload)
    if not updated:
        raise HTTPException(status_code=404, detail="Step not found")
    return {"step": updated.model_dump(), "message": "Step updated"}


@router.delete("/{step_id}")
async def delete_fix_step(
    step_id: str,
    _:    None              = Depends(_assert_admin),
    repo: FixStepRepository = Depends(_get_fix_step_repo),
):
    ok = repo.delete_step(step_id)
    if not ok:
        raise HTTPException(status_code=500, detail="Delete failed")
    return {"step_id": step_id, "message": "Step deleted"}


@router.post("/{rule_code}/reorder")
async def reorder_fix_steps(
    rule_code:        str,
    step_ids_ordered: list[str],
    _:    None              = Depends(_assert_admin),
    repo: FixStepRepository = Depends(_get_fix_step_repo),
):
    ok = repo.reorder_steps(rule_code, step_ids_ordered)
    if not ok:
        raise HTTPException(status_code=500, detail="Reorder failed")
    return {"rule_code": rule_code, "message": "Steps reordered"}