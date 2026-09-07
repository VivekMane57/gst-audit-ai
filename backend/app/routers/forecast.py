"""
backend/app/routers/forecast.py
Endpoint for GST cash flow planning and upcoming liability prediction
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from app.ml.forecasting.service import forecast_service
from app.db.supabase_client import get_supabase_async
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/forecast", tags=["Cashflow & Liability Forecasting"])


class ForecastPeriod(BaseModel):
    target_period: str
    forecasted_liability: float
    lower_bound: float
    upper_bound: float


class ForecastResponse(BaseModel):
    client_id: str
    periods_ahead: int
    quarterly_forecast: list[ForecastPeriod]


@router.get("/liability/{client_id}", response_model=ForecastResponse)
async def get_client_liability_forecast(
    client_id: str,
    periods: int = Query(3, ge=1, le=12)
):
    try:
        supabase = await get_supabase_async()
        res = supabase.table("client_gst_filings")\
            .select("filing_month, net_tax_payable")\
            .eq("client_id", client_id)\
            .order("filing_month", desc=False)\
            .execute()

        forecasts = forecast_service.forecast_liability(
            historical_records=res.data or [],
            periods_ahead=periods
        )

        return ForecastResponse(
            client_id=client_id,
            periods_ahead=periods,
            quarterly_forecast=forecasts
        )
    except Exception as e:
        logger.error(f"Failed to generate forecast for {client_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))