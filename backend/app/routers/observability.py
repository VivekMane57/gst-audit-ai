"""
backend/app/routers/observability.py
Telemetry dashboard endpoint
"""
from fastapi import APIRouter
from app.telemetry.tracker import telemetry_collector

router = APIRouter(prefix="/api/v1/observability", tags=["Observability & Telemetry"])


@router.get("/metrics")
async def get_system_telemetry():
    return telemetry_collector.get_metrics_summary()