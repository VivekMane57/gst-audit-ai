"""
routers/hsn.py
--------------
GET  /hsn/lookup/{code}    — Get HSN info + correct rate
GET  /hsn/search?q=...     — Search HSN codes
POST /hsn/validate          — Validate HSN rate
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
from app.services.hsn_validator import get_hsn_info, validate_hsn_rate, search_hsn
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/hsn", tags=["hsn"])


class ValidateRequest(BaseModel):
    hsn_code: str
    applied_rate: float
    taxable_value: Optional[float] = 0.0


# ── GET /hsn/lookup/{code} ────────────────────────────────────
@router.get("/lookup/{hsn_code}")
async def lookup_hsn(hsn_code: str):
    """HSN code ka info return karo — rate, description, category."""
    info = get_hsn_info(hsn_code)
    if not info:
        raise HTTPException(status_code=404, detail=f"HSN code {hsn_code} not found")
    return info


# ── GET /hsn/search?q=laptop ─────────────────────────────────
@router.get("/search")
async def search_hsn_codes(
    q: str = Query(..., min_length=2, description="Search query"),
    limit: int = Query(default=20, le=50),
):
    """HSN codes search by code or description."""
    results = search_hsn(q, limit)
    return {"results": results, "total": len(results), "query": q}


# ── POST /hsn/validate ───────────────────────────────────────
@router.post("/validate")
async def validate_hsn(body: ValidateRequest):
    """HSN code ke against applied rate validate karo."""
    result = validate_hsn_rate(
        hsn_code=body.hsn_code,
        applied_rate=body.applied_rate,
        taxable_value=body.taxable_value,
    )
    return result