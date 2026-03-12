"""
tests/test_day1.py
------------------
Day 1 ka code test karo.
Run: pytest tests/test_day1.py -v
"""
import pytest
from app.utils.gstin_validator import validate_gstin, mask_gstin
from app.utils.state_codes import is_interstate, is_export, get_state_name
from app.utils.translations import get_text
from app.services.score_calculator import (
    calculate_score, get_risk_level, count_by_severity
)
from app.models.issue import Issue, Severity, IssueType


# ── GSTIN Validator Tests ─────────────────────────────────────────────────────

class TestGSTINValidator:

    def test_valid_maharashtra_gstin(self):
        result = validate_gstin("27AABCS1234R1Z5")
        assert result.is_valid is True
        assert result.state_code == "27"
        assert result.state_name == "Maharashtra"

    def test_valid_karnataka_gstin(self):
        result = validate_gstin("29AABCS1234R1Z5")
        assert result.is_valid is True
        assert result.state_code == "29"

    def test_empty_gstin(self):
        result = validate_gstin("")
        assert result.is_valid is False
        assert "empty" in result.error.lower()

    def test_short_gstin(self):
        result = validate_gstin("27AABCS1234")
        assert result.is_valid is False
        assert "15" in result.error

    def test_invalid_state_code(self):
        result = validate_gstin("99AABCS1234R1Z5")
        # 99 = export, should be invalid as regular GSTIN
        # Note: 99 is valid state code for export
        # Test with truly invalid code
        result2 = validate_gstin("00AABCS1234R1Z5")
        assert result2.is_valid is False

    def test_lowercase_gstin_normalized(self):
        result = validate_gstin("27aabcs1234r1z5")
        assert result.is_valid is True   # uppercase ho jaana chahiye

    def test_mask_gstin(self):
        masked = mask_gstin("27AABCS1234R1Z5")
        assert masked == "27**********1Z5"
        assert len(masked) == 15


# ── State Code Tests ──────────────────────────────────────────────────────────

class TestStateCodes:

    def test_interstate_different_states(self):
        # Maharashtra → Karnataka
        assert is_interstate("27AABCS1234R1Z5", "29XYZAB1234C1Z5") is True

    def test_intrastate_same_state(self):
        # Maharashtra → Maharashtra
        assert is_interstate("27AABCS1234R1Z5", "27XYZAB1234C1Z5") is False

    def test_export_detection(self):
        assert is_export("99AABCS1234R1Z5") is True
        assert is_export("27AABCS1234R1Z5") is False

    def test_state_name_maharashtra(self):
        assert get_state_name("27") == "Maharashtra"

    def test_state_name_unknown(self):
        assert get_state_name("00") == "Unknown State"


# ── Translations Tests ────────────────────────────────────────────────────────

class TestTranslations:

    def test_english_translation(self):
        text = get_text("risk_low", "en")
        assert text == "LOW RISK"

    def test_hindi_translation(self):
        text = get_text("risk_low", "hi")
        assert text == "कम जोखिम"

    def test_marathi_translation(self):
        text = get_text("risk_low", "mr")
        assert text == "कमी धोका"

    def test_missing_key_returns_key(self):
        text = get_text("nonexistent_key", "en")
        assert text == "nonexistent_key"

    def test_english_fallback(self):
        text = get_text("risk_high", "en")
        assert text == "HIGH RISK"


# ── Score Calculator Tests ────────────────────────────────────────────────────

def make_issue(severity: Severity) -> Issue:
    return Issue(
        issue_type=IssueType.TAX_TYPE_MISMATCH,
        severity=severity,
        invoice_number="TEST-001",
        problem_en="Test problem",
        problem_hi="टेस्ट समस्या",
        problem_mr="चाचणी समस्या",
        legal_ref="Test Section",
        fix_steps=["Fix step 1"],
    )


class TestScoreCalculator:

    def test_perfect_score_no_issues(self):
        assert calculate_score([]) == 100

    def test_one_critical_issue(self):
        issues = [make_issue(Severity.CRITICAL)]
        assert calculate_score(issues) == 80

    def test_three_critical_issues(self):
        issues = [make_issue(Severity.CRITICAL)] * 3
        assert calculate_score(issues) == 40   # 100 - 60

    def test_minimum_score_is_zero(self):
        issues = [make_issue(Severity.CRITICAL)] * 10
        assert calculate_score(issues) == 0    # not negative

    def test_risk_level_low(self):
        assert get_risk_level(85) == "LOW"

    def test_risk_level_medium(self):
        assert get_risk_level(65) == "MEDIUM"

    def test_risk_level_high(self):
        assert get_risk_level(45) == "HIGH"

    def test_risk_level_critical(self):
        assert get_risk_level(20) == "CRITICAL"

    def test_count_by_severity(self):
        issues = [
            make_issue(Severity.CRITICAL),
            make_issue(Severity.CRITICAL),
            make_issue(Severity.HIGH),
        ]
        counts = count_by_severity(issues)
        assert counts[Severity.CRITICAL] == 2
        assert counts[Severity.HIGH] == 1
        assert counts[Severity.MEDIUM] == 0