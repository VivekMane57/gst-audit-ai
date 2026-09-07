from fastapi import APIRouter, HTTPException
from app.mlops.drift_monitor import evaluate_feature_drift
from app.db.supabase_client import get_supabase_async

router = APIRouter(prefix="/api/v1/mlops", tags=["MLOps & Monitoring"])


@router.post("/drift/check")
async def run_drift_check():
    try:
        result = await evaluate_feature_drift()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/drift/history")
async def get_drift_history(limit: int = 10):
    supabase = await get_supabase_async()
    res = supabase.table("model_drift_logs")\
        .select("*")\
        .order("checked_at", desc=True)\
        .limit(limit)\
        .execute()
    return {"logs": res.data or []}