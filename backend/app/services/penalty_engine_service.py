"""
services/penalty_engine_service.py
------------------------------------
Generic penalty formula handlers.

WHAT IS HARDCODED (intentional):
  - formula handler functions (fixed_amount, percentage, etc.)
  - dispatch table mapping formula_type → handler

WHAT COMES FROM DB:
  - formula_type (which handler to use)
  - formula_config (rate, cap, min_amount, etc.)
  - global penalty_config overrides (interest rate, etc.)

Usage:
    engine = PenaltyEngineService(db)
    exposure = engine.calculate(
        formula_type   = "percentage_of_amount",
        formula_config = {"rate": 0.18, "cap": 500000},
        base_amount    = 100000,
    )
    # → 18000.0
"""
from __future__ import annotations
import logging
from typing import Optional
from supabase import Client

logger = logging.getLogger(__name__)

# ── Hardcoded fallback rates (matches migration seed) ────────
# These are overridden by penalty_configs table when DB is available.
_FALLBACK_CONFIGS: dict[str, float] = {
    "gst_interest_rate":          0.18,
    "fraud_penalty_multiplier":   2.0,
    "late_fee_per_day_cgst":      100.0,
    "late_fee_per_day_sgst":      100.0,
    "itc_penalty_rate":           1.0,
    "tax_mismatch_interest_rate": 0.18,
}


class PenaltyEngineService:
    """
    Stateless penalty calculator.
    Formula logic is code. Formula params come from DB (or fallback dict).
    """

    def __init__(self, db: Optional[Client] = None):
        self._db               = db
        self._config_cache: dict[str, float] = {}
        self._cache_loaded     = False

    # ── Public API ────────────────────────────────────────────

    def calculate(
        self,
        formula_type:   str,
        formula_config: dict,
        base_amount:    float,
        invoice_count:  int = 1,
        days_overdue:   int = 0,
    ) -> float:
        """
        Calculate penalty exposure in INR.
        Returns 0.0 for no_penalty or unknown formula types.
        Never raises — penalty calc failure should not fail audit.
        """
        try:
            handler = self._FORMULA_HANDLERS.get(formula_type)
            if handler is None:
                logger.warning(f"Unknown penalty formula_type: {formula_type!r}")
                return 0.0
            return round(
                handler(self, formula_config, base_amount, invoice_count, days_overdue),
                2
            )
        except Exception as e:
            logger.error(f"Penalty calc error formula_type={formula_type}: {e}")
            return 0.0

    def calculate_from_rule(
        self,
        rule,             # ActiveRuleView
        base_amount: float,
        invoice_count: int = 1,
        days_overdue:  int = 0,
    ) -> float:
        """Convenience wrapper — takes ActiveRuleView directly."""
        return self.calculate(
            formula_type   = rule.penalty_formula_type,
            formula_config = rule.penalty_formula_config,
            base_amount    = base_amount,
            invoice_count  = invoice_count,
            days_overdue   = days_overdue,
        )

    def get_global_rate(self, config_key: str, fallback: float = 0.0) -> float:
        """
        Fetch global penalty config rate from DB (cached per service instance).
        Falls back to hardcoded dict if DB unavailable.
        """
        if not self._cache_loaded:
            self._load_config_cache()
        return self._config_cache.get(config_key, _FALLBACK_CONFIGS.get(config_key, fallback))

    # ── Formula handlers (hardcoded) ──────────────────────────

    def _formula_no_penalty(self, config: dict, base: float, count: int, days: int) -> float:
        return 0.0

    def _formula_fixed_amount(self, config: dict, base: float, count: int, days: int) -> float:
        """
        Fixed amount per invoice.
        config: {"amount": 10000, "currency": "INR"}
        """
        amount = float(config.get("amount", 0))
        return amount * max(count, 1)

    def _formula_percentage(self, config: dict, base: float, count: int, days: int) -> float:
        """
        Percentage of base amount.
        config: {"rate": 0.18, "cap": 500000, "min_amount": 1000}
        """
        rate       = float(config.get("rate", 0))
        cap        = config.get("cap")
        min_amount = config.get("min_amount", 0)
        result     = base * rate
        if cap is not None:
            result = min(result, float(cap))
        result = max(result, float(min_amount))
        return result

    def _formula_tax_plus_interest(self, config: dict, base: float, count: int, days: int) -> float:
        """
        Tax demand + interest component.
        config: {"tax_rate": 0.18, "interest_rate": 0.18, "interest_period_days": 365}
        Typically: ITC reversal = base amount; interest on that for period.
        """
        tax_rate     = float(config.get("tax_rate",     self.get_global_rate("gst_interest_rate", 0.18)))
        int_rate     = float(config.get("interest_rate", self.get_global_rate("tax_mismatch_interest_rate", 0.18)))
        period_days  = int(config.get("interest_period_days", 365))
        # Simple interest on tax amount for given period
        tax_amount   = base * tax_rate
        interest     = tax_amount * int_rate * (period_days / 365)
        return tax_amount + interest

    def _formula_late_fee_per_day(self, config: dict, base: float, count: int, days: int) -> float:
        """
        Late fee per day of delay.
        config: {"amount_per_day": 100, "max_days": 180}
        Uses days_overdue param if > 0, else defaults to max_days.
        """
        per_day  = float(config.get("amount_per_day", self.get_global_rate("late_fee_per_day_cgst", 100)))
        max_days = int(config.get("max_days", 180))
        actual_days = min(days if days > 0 else max_days, max_days)
        # CGST + SGST = 2x late fee
        return per_day * 2 * actual_days

    def _formula_custom_note(self, config: dict, base: float, count: int, days: int) -> float:
        """
        Custom exposure — returns 0 (note only, no numeric calc).
        Note text surfaced in rule.plain_explanation.
        """
        return 0.0

    _FORMULA_HANDLERS = {
        "no_penalty":               _formula_no_penalty,
        "fixed_amount":             _formula_fixed_amount,
        "percentage_of_amount":     _formula_percentage,
        "tax_plus_interest_percent": _formula_tax_plus_interest,
        "late_fee_per_day":         _formula_late_fee_per_day,
        "custom_exposure_note":     _formula_custom_note,
    }

    # ── Config cache ──────────────────────────────────────────

    def _load_config_cache(self) -> None:
        """Load penalty_configs table into memory. One-time per instance."""
        if not self._db:
            self._cache_loaded = True
            return
        try:
            res = (
                self._db.table("penalty_configs")
                .select("config_key, config_value")
                .eq("is_active", True)
                .execute()
            )
            for row in (res.data or []):
                key = row["config_key"]
                val = row["config_value"]
                # config_value is JSONB — extract numeric value
                if isinstance(val, dict):
                    numeric = val.get("rate") or val.get("amount") or val.get("multiplier")
                    if numeric is not None:
                        self._config_cache[key] = float(numeric)
            logger.debug(f"Penalty config cache loaded: {len(self._config_cache)} keys")
        except Exception as e:
            logger.warning(f"Penalty config load failed — using hardcoded fallback: {e}")
        finally:
            self._cache_loaded = True


"""
services/notice_risk_service.py
---------------------------------
DB-driven notice risk scoring engine.

This is the bridge between the new rule engine and
the existing notice_simulator.py.

Phase 1 (USE_DB_RULES=False):
  - Returns ISSUE_WEIGHTS dict enhanced with DB overrides where available
  - notice_simulator.py uses this via get_weights_map()

Phase 2 (USE_DB_RULES=True):
  - Full DB-driven scoring replaces hardcoded ISSUE_WEIGHTS
  - Same output format — notice_simulator.py needs no change

Design: Output format matches notice_simulator.ISSUE_WEIGHTS exactly.
        This means zero changes to notice_simulator.py during migration.
"""
from __future__ import annotations
import logging
from typing import Optional

from app.repositories.rule_repository import RuleRepository
from app.repositories.threshold_repository import ThresholdRepository
from app.models.threshold import RiskThresholdDB

logger = logging.getLogger(__name__)

# ── Hardcoded fallback weights (from existing notice_simulator.py) ──
# These are used when USE_DB_RULES=False or DB fetch fails.
# Must stay in sync with notice_simulator.ISSUE_WEIGHTS until cutover.
_HARDCODED_WEIGHTS: dict[str, dict] = {
    "gstin_invalid":        {"weight": 8,  "max": 15, "category": "registration"},
    "invalid_gstin":        {"weight": 8,  "max": 15, "category": "registration"},
    "tax_type_mismatch":    {"weight": 12, "max": 20, "category": "tax_computation"},
    "gstr1_missing":        {"weight": 10, "max": 18, "category": "filing"},
    "gstr2b_missing":       {"weight": 6,  "max": 12, "category": "itc"},
    "amount_mismatch":      {"weight": 8,  "max": 15, "category": "reconciliation"},
    "duplicate_invoice":    {"weight": 15, "max": 25, "category": "fraud"},
    "circular_trade":       {"weight": 25, "max": 35, "category": "fraud"},
    "circular_transaction": {"weight": 25, "max": 35, "category": "fraud"},
    "filing_delay":         {"weight": 5,  "max": 10, "category": "filing"},
    "rate_mismatch":        {"weight": 7,  "max": 12, "category": "tax_computation"},
    "hsn_mismatch":         {"weight": 4,  "max": 8,  "category": "classification"},
    "rcm_not_paid":         {"weight": 10, "max": 18, "category": "tax_computation"},
    "itc_overclaimed":      {"weight": 18, "max": 30, "category": "itc"},
    "r1_vs_3b_mismatch":    {"weight": 14, "max": 22, "category": "reconciliation"},
    "gstr1_vs_3b_mismatch": {"weight": 14, "max": 22, "category": "reconciliation"},
    "gstr9_not_filed":      {"weight": 8,  "max": 15, "category": "filing"},
    "eway_bill_missing":    {"weight": 6,  "max": 10, "category": "logistics"},
    "payment_180_days":     {"weight": 8,  "max": 14, "category": "itc"},
    "einvoice_missing":     {"weight": 5,  "max": 10, "category": "invoicing"},
    "export_validation":    {"weight": 7,  "max": 12, "category": "invoicing"},
    "sector_specific":      {"weight": 5,  "max": 10, "category": "filing"},
}


class NoticeRiskService:
    """
    Provides risk weights and threshold for notice probability computation.
    Integrates with existing notice_simulator.py via get_weights_map().
    """

    def __init__(
        self,
        rule_repo:      RuleRepository,
        threshold_repo: ThresholdRepository,
        use_db_rules:   bool = False,   # From settings.use_db_rules
    ):
        self._rule_repo      = rule_repo
        self._threshold_repo = threshold_repo
        self._use_db_rules   = use_db_rules

    # ── Public API ────────────────────────────────────────────

    def get_weights_map(self) -> dict[str, dict]:
        """
        Returns weights dict in notice_simulator.ISSUE_WEIGHTS format.
        Drop-in replacement for the hardcoded dict.

        When USE_DB_RULES=False:
          Returns hardcoded dict with DB overrides merged on top.
          Safe — DB failure still works via fallback.

        When USE_DB_RULES=True:
          Returns DB-only dict. DB failure returns hardcoded fallback
          with a warning log.
        """
        if self._use_db_rules:
            return self._get_db_weights()
        return self._get_merged_weights()

    def get_threshold(self) -> RiskThresholdDB:
        """
        Returns active risk threshold.
        Always returns a valid threshold — never raises.
        """
        return self._threshold_repo.get_default()

    def classify_probability(self, probability: int) -> str:
        """
        Map probability (0-100) to risk label using DB threshold.
        Returns LOW | MEDIUM | HIGH | VERY_HIGH
        """
        threshold = self.get_threshold()
        return threshold.classify(probability)

    def compute_risk_breakdown(
        self,
        issues: list[dict],
        weights_map: Optional[dict] = None,
    ) -> dict[str, float]:
        """
        Compute per-category risk score breakdown.
        Compatible with notice_simulator.calculate_notice_probability() output.

        issues: list of dicts with 'type' and 'severity' keys
        weights_map: pass pre-fetched map to avoid double DB call
        """
        if weights_map is None:
            weights_map = self.get_weights_map()

        category_scores: dict[str, float] = {}
        sev_multipliers = {"critical": 1.5, "high": 1.0, "medium": 0.6, "low": 0.3}

        for issue in issues:
            issue_type  = issue.get("type", "unknown")
            severity    = (issue.get("severity") or "medium").lower()
            weight_info = weights_map.get(issue_type, {"weight": 5, "max": 10, "category": "filing"})
            sev_mult    = sev_multipliers.get(severity, 0.5)
            contribution = min(
                float(weight_info["weight"]) * sev_mult,
                float(weight_info["max"])
            )
            cat = weight_info.get("category", "filing")
            category_scores[cat] = category_scores.get(cat, 0.0) + contribution

        return category_scores

    # ── Internal ──────────────────────────────────────────────

    def _get_db_weights(self) -> dict[str, dict]:
        """DB-only weights. Fails back to hardcoded on error."""
        try:
            db_map = self._rule_repo.get_rule_weights_map()
            if db_map:
                return db_map
            logger.warning("DB weights empty — falling back to hardcoded")
        except Exception as e:
            logger.error(f"DB weights fetch failed — using hardcoded fallback: {e}")
        return _HARDCODED_WEIGHTS.copy()

    def _get_merged_weights(self) -> dict[str, dict]:
        """
        Hardcoded dict + DB overrides merged.
        DB overrides win on conflict (allows incremental migration).
        DB failure is silently ignored — hardcoded dict used as-is.
        """
        result = _HARDCODED_WEIGHTS.copy()
        try:
            db_map = self._rule_repo.get_rule_weights_map()
            # Merge: DB overrides hardcoded for matching rule codes
            result.update(db_map)
            if db_map:
                logger.debug(f"Merged {len(db_map)} DB rule weights over hardcoded dict")
        except Exception as e:
            logger.debug(f"DB weights merge skipped (using hardcoded only): {e}")
        return result