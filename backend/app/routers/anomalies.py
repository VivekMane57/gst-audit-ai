from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from app.ml.anomalies.detector import anomaly_engine
from app.db.supabase_client import get_supabase_async
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/anomalies", tags=["Anomaly & Fraud Detection"])


class TransactionItem(BaseModel):
    transaction_id: str | None = None
    client_id: str
    taxable_value: float
    itc_availed: float
    invoice_frequency_per_day: float
    tax_to_turnover_ratio: float
    buyer_seller_circular_rank: float


class AnomalyScanRequest(BaseModel):
    transactions: list[TransactionItem]


@router.post("/scan")
async def scan_for_anomalies(payload: AnomalyScanRequest):
    try:
        tx_data = [item.model_dump() for item in payload.transactions]
        anomalies = anomaly_engine.scan_transactions(tx_data)

        # Store detected anomalies to Supabase review queue
        if anomalies:
            supabase = await get_supabase_async()
            records = [{
                "client_id": a["client_id"],
                "anomaly_score": a["anomaly_score"],
                "flagged_reasons": a["flagged_reasons"],
                "status": "pending_review"
            } for a in anomalies]
            supabase.table("audit_anomalies").insert(records).execute()

        return {
            "total_scanned": len(payload.transactions),
            "flagged_count": len(anomalies),
            "anomalies": anomalies
        }
    except Exception as e:
        logger.error(f"Anomaly scanning failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("")
async def get_anomaly_queue(threshold: float = Query(0.60, ge=0.0, le=1.0), limit: int = 50):
    supabase = await get_supabase_async()
    res = supabase.table("audit_anomalies")\
        .select("*")\
        .gte("anomaly_score", threshold)\
        .eq("status", "pending_review")\
        .order("anomaly_score", desc=True)\
        .limit(limit)\
        .execute()
    return {"count": len(res.data or []), "review_queue": res.data or []}