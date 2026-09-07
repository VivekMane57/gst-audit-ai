from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.ml.trust_scoring.service import trust_service
from app.db.supabase_client import get_supabase_async
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/suppliers", tags=["Suppliers"])


class TopFactor(BaseModel):
    feature: str
    impact: float
    direction: str


class TrustScoreResponse(BaseModel):
    supplier_id: str
    score: float
    top_factors: list[TopFactor]


@router.get("/{supplier_id}/trust-score", response_model=TrustScoreResponse)
async def get_supplier_trust_score(supplier_id: str):
    try:
        supabase = await get_supabase_async()
        
        # 1. Fetch live metrics from Supabase
        res = supabase.table("supplier_features")\
            .select("*")\
            .eq("supplier_id", supplier_id)\
            .order("updated_at", desc=True)\
            .limit(1)\
            .execute()

        # If supplier is new/untracked, provide standard default features
        if not res.data:
            features = {
                "filing_frequency_ratio": 0.95,
                "avg_filing_delay_days": 2.0,
                "gstr_mismatch_count": 0,
                "hsn_consistency_score": 1.0,
                "historical_flag_count": 0
            }
        else:
            features = res.data[0]

        # 2. Run Model + SHAP inference
        score, top_factors = trust_service.predict(features)

        # 3. Store snapshot
        supabase.table("supplier_trust_scores").insert({
            "supplier_id": supplier_id,
            "trust_score": score,
            "top_factors": top_factors,
            "model_version": "v1-xgb"
        }).execute()

        return TrustScoreResponse(
            supplier_id=supplier_id,
            score=score,
            top_factors=top_factors
        )

    except Exception as e:
        logger.error(f"Error evaluating supplier {supplier_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to calculate supplier trust score")