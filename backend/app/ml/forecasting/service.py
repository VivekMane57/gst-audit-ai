"""
backend/app/ml/forecasting/service.py
Time-series forecasting for upcoming GST quarterly tax liability
"""
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from app.db.supabase_client import get_supabase_async
import logging

logger = logging.getLogger(__name__)


class LiabilityForecastService:
    def forecast_liability(self, historical_records: list[dict], periods_ahead: int = 3) -> list[dict]:
        if not historical_records or len(historical_records) < 3:
            # Cold-start synthetic baseline if insufficient history
            baseline_val = 125000.0
            last_date = datetime.now()
            forecasts = []
            for i in range(1, periods_ahead + 1):
                target_date = last_date + timedelta(days=30 * i)
                pred = baseline_val * (1.0 + (0.03 * i))
                forecasts.append({
                    "target_period": target_date.strftime("%Y-%m-01"),
                    "forecasted_liability": round(pred, 2),
                    "lower_bound": round(pred * 0.90, 2),
                    "upper_bound": round(pred * 1.12, 2)
                })
            return forecasts

        df = pd.DataFrame(historical_records)
        df["filing_month"] = pd.to_datetime(df["filing_month"])
        df = df.sort_values("filing_month")
        y = df["net_tax_payable"].astype(float).values

        # Linear trend + moving variance estimation
        x = np.arange(len(y))
        slope, intercept = np.polyfit(x, y, 1)
        std_dev = float(np.std(y)) if len(y) > 1 else y[0] * 0.1

        last_date = df["filing_month"].iloc[-1]
        forecasts = []

        for i in range(1, periods_ahead + 1):
            future_step = len(y) + i - 1
            pred = float(slope * future_step + intercept)
            pred = max(0.0, pred)

            target_date = last_date + pd.DateOffset(months=i)
            forecasts.append({
                "target_period": target_date.strftime("%Y-%m-01"),
                "forecasted_liability": round(pred, 2),
                "lower_bound": round(max(0.0, pred - (1.645 * std_dev)), 2),
                "upper_bound": round(pred + (1.645 * std_dev), 2)
            })

        return forecasts


forecast_service = LiabilityForecastService()