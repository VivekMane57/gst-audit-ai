"""
routers/admin/thresholds_router.py
------------------------------------
Admin router: risk_thresholds CRUD.
"""
from fastapi import APIRouter, Depends, HTTPException, Header, Query
from typing import Optional
import logging

from app.db.supabase_client import get_supabase
from app.repositories.threshold_repository import ThresholdRepository
from app.models.threshold import RiskThresholdCreate, RiskThresholdUpdate
from app.config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/thresholds", tags=["admin-thresholds"])


def _get_threshold_repo() -> ThresholdRepository:
    return ThresholdRepository(get_supabase())


def _assert_admin(x_admin_key: Optional[str] = Header(default=None)) -> None:
    settings = get_settings()
    admin_key = getattr(settings, "admin_api_key", None)
    if admin_key and x_admin_key != admin_key:
        raise HTTPException(status_code=403, detail="Admin access required")


@router.get("")
async def list_thresholds(
    _:    None                = Depends(_assert_admin),
    repo: ThresholdRepository = Depends(_get_threshold_repo),
):
    thresholds = repo.list_all()
    return {"thresholds": [t.model_dump() for t in thresholds]}


@router.post("", status_code=201)
async def create_threshold(
    payload: RiskThresholdCreate,
    _:    None                = Depends(_assert_admin),
    repo: ThresholdRepository = Depends(_get_threshold_repo),
):
    try:
        payload.validate_bands()
        threshold = repo.create(payload)
        return {"threshold": threshold.model_dump(), "message": "Threshold created"}
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.patch("/{threshold_id}")
async def update_threshold(
    threshold_id: str,
    payload:      RiskThresholdUpdate,
    _:    None                = Depends(_assert_admin),
    repo: ThresholdRepository = Depends(_get_threshold_repo),
):
    updated = repo.update(threshold_id, payload)
    if not updated:
        raise HTTPException(status_code=404, detail="Threshold not found")
    return {"threshold": updated.model_dump(), "message": "Threshold updated"}