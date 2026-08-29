"""
routers/notice_queue.py
------------------------
GET /api/notice-queue          — Prioritized list of high-risk clients
GET /api/notice-queue/summary  — Dashboard stats (counts by risk level)

Change from previous version:
  - prefix changed from "/notice-queue" to "/api/notice-queue"
    so frontend calls to "/api/notice-queue" work correctly.

Thin router — delegates to NoticeRiskQueueService.
Auth: x-user-id header (Clerk).
"""
from fastapi import APIRouter, Header, HTTPException, Query
from typing import Optional
import logging

from app.db.supabase_client import get_supabase
from app.utils.auth import get_user_uuid
from app.repositories.notice_queue_repo import NoticeQueueRepository
from app.services.notice_risk_queue import NoticeRiskQueueService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/notice-queue", tags=["notice-queue"])   # <- prefix fixed


def _get_ca_id(x_user_id: Optional[str]) -> str:
    if not x_user_id:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return x_user_id


@router.get("")
async def get_notice_risk_queue(
    min_prob:     int           = Query(default=0,    ge=0, le=100),
    limit:        int           = Query(default=50,   ge=1, le=200),
    risk_level:   Optional[str] = Query(default=None, description="LOW / MEDIUM / HIGH / VERY_HIGH"),
    x_user_id:    Optional[str] = Header(default=None),
    x_user_email: Optional[str] = Header(default=None),
    x_user_name:  Optional[str] = Header(default=None),
):
    """
    Prioritized notice risk queue for CA's clients.
    Sorted by urgency: notice_probability + itc_at_risk + critical issues + compliance score.
    Frontend: "Action Required" dashboard widget.
    """
    ca_id = _get_ca_id(x_user_id)
    db    = get_supabase()

    try:
        get_user_uuid(db, ca_id, email=x_user_email, full_name=x_user_name)
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))

    valid_levels = {"LOW", "MEDIUM", "HIGH", "VERY_HIGH"}
    if risk_level:
        risk_level = risk_level.upper()
        if risk_level not in valid_levels:
            raise HTTPException(
                status_code=422,
                detail=f"Invalid risk_level '{risk_level}'. Use: {', '.join(valid_levels)}"
            )

    try:
        repo    = NoticeQueueRepository(db)
        service = NoticeRiskQueueService(repo)
        queue   = service.get_queue(
            ca_id      = ca_id,
            min_prob   = min_prob,
            limit      = limit,
            risk_level = risk_level,
        )
        return {
            "queue":  queue,
            "total":  len(queue),
            "filter": {"min_prob": min_prob, "risk_level": risk_level},
        }
    except Exception as e:
        logger.error(f"get_notice_risk_queue error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/summary")
async def get_notice_queue_summary(
    x_user_id:    Optional[str] = Header(default=None),
    x_user_email: Optional[str] = Header(default=None),
    x_user_name:  Optional[str] = Header(default=None),
):
    """
    Dashboard stats: counts by risk level + total ITC + penalty exposure.
    Frontend: stat cards (Penalty Exposure, High Risk count).
    """
    ca_id = _get_ca_id(x_user_id)
    db    = get_supabase()

    try:
        get_user_uuid(db, ca_id, email=x_user_email, full_name=x_user_name)
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))

    try:
        repo    = NoticeQueueRepository(db)
        service = NoticeRiskQueueService(repo)
        return service.get_summary(ca_id)
    except Exception as e:
        logger.error(f"get_notice_queue_summary error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))