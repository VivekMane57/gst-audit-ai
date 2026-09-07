import numpy as np
import pandas as pd
from scipy import stats
from app.db.supabase_client import get_supabase_async
import logging

logger = logging.getLogger(__name__)

MONITORED_FEATURES = [
    "filing_frequency_ratio",
    "avg_filing_delay_days",
    "gstr_mismatch_count",
    "hsn_consistency_score",
    "historical_flag_count"
]


async def evaluate_feature_drift(p_value_threshold: float = 0.05, drift_share_threshold: float = 0.40) -> dict:
    """
    Runs two-sample Kolmogorov-Smirnov test between baseline reference data 
    and recent inference feature distributions.
    """
    supabase = await get_supabase_async()

    # 1. Fetch recent live inferences
    recent_records = supabase.table("supplier_features")\
        .select("*")\
        .order("updated_at", desc=True)\
        .limit(500)\
        .execute().data or []

    # Cold start fallback if live traffic is minimal
    if len(recent_records) < 15:
        return {
            "status": "skipped",
            "message": "Insufficient live samples for statistical drift test (minimum 15 required)."
        }

    current_df = pd.DataFrame(recent_records)

    # 2. Reference distribution baseline parameters
    reference_baselines = {
        "filing_frequency_ratio": (0.85, 0.10),
        "avg_filing_delay_days": (3.5, 2.0),
        "gstr_mismatch_count": (1.0, 1.2),
        "hsn_consistency_score": (0.90, 0.08),
        "historical_flag_count": (0.5, 0.7)
    }

    drifted_features = []
    np.random.seed(42)

    for feat in MONITORED_FEATURES:
        if feat not in current_df.columns:
            continue
        curr_vals = current_df[feat].astype(float).dropna().values
        mean_b, std_b = reference_baselines.get(feat, (0.0, 1.0))
        ref_vals = np.random.normal(loc=mean_b, scale=std_b, size=len(curr_vals))

        # Kolmogorov-Smirnov 2-sample test
        ks_stat, p_val = stats.ks_2samp(ref_vals, curr_vals)
        if p_val < p_value_threshold:
            drifted_features.append({
                "feature": feat,
                "ks_statistic": round(float(ks_stat), 4),
                "p_value": round(float(p_val), 5)
            })

    drift_share = len(drifted_features) / len(MONITORED_FEATURES)
    is_dataset_drifted = drift_share >= drift_share_threshold
    action_taken = "trigger_retraining_alert" if is_dataset_drifted else "none"

    # 3. Save snapshot to Supabase
    supabase.table("model_drift_logs").insert({
        "model_name": "SupplierTrustScoreXGB",
        "dataset_drift": is_dataset_drifted,
        "drift_share": round(drift_share, 4),
        "drifted_features": drifted_features,
        "action_taken": action_taken
    }).execute()

    if is_dataset_drifted:
        logger.warning(f"⚠️ Model Data Drift Detected! Drifted ratio: {drift_share:.2%}")

    return {
        "dataset_drift": is_dataset_drifted,
        "drift_share": round(drift_share, 4),
        "drifted_features": drifted_features,
        "action_taken": action_taken
    }