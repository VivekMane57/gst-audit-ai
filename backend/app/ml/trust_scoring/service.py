import os
import pickle
import numpy as np
import pandas as pd
import xgboost as xgb
import shap
from app.db.supabase_client import get_supabase
import logging

logger = logging.getLogger(__name__)

FEATURE_NAMES = [
    "filing_frequency_ratio",
    "avg_filing_delay_days",
    "gstr_mismatch_count",
    "hsn_consistency_score",
    "historical_flag_count"
]

MODEL_DIR = os.path.join(os.path.dirname(__file__), "artifacts")
MODEL_FILE = os.path.join(MODEL_DIR, "supplier_trust_xgb.json")


class SupplierTrustService:
    def __init__(self):
        self.model = None
        self.explainer = None
        os.makedirs(MODEL_DIR, exist_ok=True)
        self._load_or_train_baseline()

    def _train_baseline(self):
        """Generates baseline weights when cold-starting without historical runs."""
        logger.info("Training initial baseline Supplier Trust XGBoost model...")
        # Baseline synthetic range reflecting CA domain heuristics
        np.random.seed(42)
        n = 500
        data = {
            "filing_frequency_ratio": np.random.uniform(0.5, 1.0, n),
            "avg_filing_delay_days": np.random.exponential(5, n),
            "gstr_mismatch_count": np.random.poisson(2, n),
            "hsn_consistency_score": np.random.uniform(0.6, 1.0, n),
            "historical_flag_count": np.random.poisson(1, n),
        }
        df = pd.DataFrame(data)
        # Synthetic target: Higher mismatches/delays reduce trust score
        score = (
            df["filing_frequency_ratio"] * 35
            - df["avg_filing_delay_days"] * 1.8
            - df["gstr_mismatch_count"] * 5.5
            + df["hsn_consistency_score"] * 25
            - df["historical_flag_count"] * 4.0
            + 25
        )
        y = np.clip(score, 5.0, 99.0)

        model = xgb.XGBRegressor(
            n_estimators=100,
            max_depth=3,
            learning_rate=0.08,
            objective="reg:squarederror",
            random_state=42
        )
        model.fit(df[FEATURE_NAMES], y)
        model.save_model(MODEL_FILE)
        self.model = model
        self.explainer = shap.TreeExplainer(self.model)

    def _load_or_train_baseline(self):
        if os.path.exists(MODEL_FILE):
            try:
                self.model = xgb.XGBRegressor()
                self.model.load_model(MODEL_FILE)
                self.explainer = shap.TreeExplainer(self.model)
                logger.info("Loaded Supplier Trust XGBoost model artifact.")
            except Exception as e:
                logger.warning(f"Failed to load model file, retraining: {e}")
                self._train_baseline()
        else:
            self._train_baseline()

    def predict(self, feature_dict: dict) -> tuple[float, list[dict]]:
        df = pd.DataFrame([{k: float(feature_dict.get(k, 0.0)) for k in FEATURE_NAMES}])
        pred = float(self.model.predict(df)[0])
        score = float(np.clip(pred, 0.0, 100.0))

        # Calculate SHAP explainability
        shap_values = self.explainer(df)
        contributions = shap_values.values[0]

        factors = []
        for name, impact in zip(FEATURE_NAMES, contributions):
            factors.append({
                "feature": name,
                "impact": round(float(impact), 2),
                "direction": "positive" if impact > 0 else "negative"
            })

        # Sort top 3 drivers by absolute magnitude
        factors.sort(key=lambda x: abs(x["impact"]), reverse=True)
        return round(score, 2), factors[:3]


trust_service = SupplierTrustService()