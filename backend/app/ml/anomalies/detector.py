"""
backend/app/ml/anomalies/detector.py
Unsupervised Isolation Forest for GST fraud/circular trading patterns
"""
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from app.db.supabase_client import get_supabase_async
import logging

logger = logging.getLogger(__name__)

FEATURE_COLS = [
    "taxable_value",
    "itc_availed",
    "invoice_frequency_per_day",
    "tax_to_turnover_ratio",
    "buyer_seller_circular_rank"
]


class AnomalyDetectorService:
    def __init__(self, contamination: float = 0.05):
        self.contamination = contamination
        self.model = IsolationForest(
            n_estimators=100,
            contamination=self.contamination,
            random_state=42
        )
        self._fitted = False

    def _fit_baseline(self):
        # Synthetic baseline representing normal GST invoice profiles
        np.random.seed(42)
        n = 300
        normal_data = {
            "taxable_value": np.random.exponential(scale=50000, size=n),
            "itc_availed": np.random.exponential(scale=9000, size=n),
            "invoice_frequency_per_day": np.random.poisson(lam=3, size=n),
            "tax_to_turnover_ratio": np.random.uniform(0.05, 0.18, n),
            "buyer_seller_circular_rank": np.random.uniform(0.0, 0.3, n)
        }
        df = pd.DataFrame(normal_data)
        self.model.fit(df[FEATURE_COLS])
        self._fitted = True

    def scan_transactions(self, transactions: list[dict]) -> list[dict]:
        if not self._fitted:
            self._fit_baseline()

        if not transactions:
            return []

        df = pd.DataFrame(transactions)
        for col in FEATURE_COLS:
            if col not in df.columns:
                df[col] = 0.0

        X = df[FEATURE_COLS].fillna(0.0)

        # Isolation forest scores: lower values represent stronger anomalies
        raw_scores = self.model.score_samples(X)
        preds = self.model.predict(X)

        # Invert and normalize to 0.0 (clean) -> 1.0 (extreme anomaly)
        norm_scores = (raw_scores.max() - raw_scores) / (raw_scores.max() - raw_scores.min() + 1e-8)

        flagged_anomalies = []
        for idx, pred in enumerate(preds):
            score = float(norm_scores[idx])
            row = df.iloc[idx]
            reasons = []

            if row["itc_availed"] > (row["taxable_value"] * 0.28):
                reasons.append("ITC claim exceeds statutory 28% ceiling of taxable invoice value.")
            if row["buyer_seller_circular_rank"] > 0.70:
                reasons.append("High topological loop index indicates potential circular trading network.")
            if row["invoice_frequency_per_day"] > 25:
                reasons.append("Abnormal spike in daily transactional invoicing volume.")

            if pred == -1 or score >= 0.65:
                if not reasons:
                    reasons.append("Multivariate statistical variance outside standard audit boundaries.")

                flagged_anomalies.append({
                    "transaction_id": str(row.get("transaction_id", f"tx-{idx+1}")),
                    "client_id": str(row.get("client_id", "00000000-0000-0000-0000-000000000000")),
                    "anomaly_score": round(score, 4),
                    "flagged_reasons": reasons
                })

        return flagged_anomalies


anomaly_engine = AnomalyDetectorService()