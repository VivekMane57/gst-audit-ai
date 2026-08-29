"""
routers/admin/rules_router.py
------------------------------
Admin router: compliance_rules CRUD.
Thin router — all logic in RuleRepository.
"""
from fastapi import APIRouter, Depends, HTTPException, Header, Query
from typing import Optional
import logging

from app.db.supabase_client import get_supabase
from app.repositories.rule_repository import RuleRepository
from app.models.rule import ComplianceRuleCreate, ComplianceRuleUpdate
from app.config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/rules", tags=["admin-rules"])


def _get_rule_repo() -> RuleRepository:
    return RuleRepository(get_supabase())


def _assert_admin(x_admin_key: Optional[str] = Header(default=None)) -> None:
    settings = get_settings()
    admin_key = getattr(settings, "admin_api_key", None)
    if admin_key and x_admin_key != admin_key:
        raise HTTPException(status_code=403, detail="Admin access required")


@router.get("")
async def list_rules(
    active_only: bool          = Query(default=False),
    category:    Optional[str] = Query(default=None),
    limit:       int           = Query(default=50, le=200),
    offset:      int           = Query(default=0),
    _:           None          = Depends(_assert_admin),
    repo:        RuleRepository = Depends(_get_rule_repo),
):
    rules = repo.list_all(active_only=active_only, category=category, limit=limit, offset=offset)
    return {
        "rules": [r.model_dump() for r in rules],
        "total": len(rules),
        "active_count": repo.count_active(),
    }


@router.post("", status_code=201)
async def create_rule(
    payload: ComplianceRuleCreate,
    _:    None           = Depends(_assert_admin),
    repo: RuleRepository = Depends(_get_rule_repo),
):
    existing = repo.get_by_code(payload.rule_code)
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Rule '{payload.rule_code}' already exists. Use PATCH /admin/rules/{existing.id}."
        )
    try:
        rule = repo.create(payload)
        return {"rule": rule.model_dump(), "message": "Rule created"}
    except Exception as e:
        logger.error(f"create_rule failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{rule_id}")
async def get_rule(
    rule_id: str,
    _:    None           = Depends(_assert_admin),
    repo: RuleRepository = Depends(_get_rule_repo),
):
    rule = repo.get_by_id(rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    return rule.model_dump()


@router.patch("/{rule_id}")
async def update_rule(
    rule_id: str,
    payload: ComplianceRuleUpdate,
    _:    None           = Depends(_assert_admin),
    repo: RuleRepository = Depends(_get_rule_repo),
):
    if not repo.get_by_id(rule_id):
        raise HTTPException(status_code=404, detail="Rule not found")
    updated = repo.update(rule_id, payload)
    if not updated:
        raise HTTPException(status_code=500, detail="Update failed")
    return {"rule": updated.model_dump(), "message": "Rule updated"}


@router.post("/{rule_id}/activate")
async def activate_rule(
    rule_id: str,
    _:    None           = Depends(_assert_admin),
    repo: RuleRepository = Depends(_get_rule_repo),
):
    updated = repo.set_active(rule_id, True)
    if not updated:
        raise HTTPException(status_code=404, detail="Rule not found")
    return {"rule_id": rule_id, "is_active": True, "message": "Rule activated"}


@router.post("/{rule_id}/deactivate")
async def deactivate_rule(
    rule_id: str,
    _:    None           = Depends(_assert_admin),
    repo: RuleRepository = Depends(_get_rule_repo),
):
    updated = repo.set_active(rule_id, False)
    if not updated:
        raise HTTPException(status_code=404, detail="Rule not found")
    return {"rule_id": rule_id, "is_active": False, "message": "Rule deactivated"}


@router.get("/active/weights")
async def get_active_weights(
    _:    None           = Depends(_assert_admin),
    repo: RuleRepository = Depends(_get_rule_repo),
):
    return {
        "weights_map": repo.get_rule_weights_map(),
        "count":       repo.count_active(),
    }