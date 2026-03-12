"""
services/score_calculator.py
-----------------------------
Compliance score 0-100 calculate karo.
Issues ki severity se score ghatta hai.
"""
from app.models.issue import Issue, Severity
from app.utils.translations import get_text
from typing import Literal


SEVERITY_DEDUCTIONS = {
    Severity.CRITICAL: 20,
    Severity.HIGH:     10,
    Severity.MEDIUM:    5,
    Severity.LOW:       2,
}


def calculate_score(issues: list[Issue]) -> int:
    """
    100 se shuru karo, har issue ke hisaab se points ghatao.
    Minimum 0.
    """
    score = 100
    for issue in issues:
        score -= SEVERITY_DEDUCTIONS.get(issue.severity, 0)
    return max(0, score)


def get_risk_level(score: int) -> str:
    """Score se risk level."""
    if score >= 80:
        return "LOW"
    elif score >= 60:
        return "MEDIUM"
    elif score >= 40:
        return "HIGH"
    else:
        return "CRITICAL"


def get_risk_level_translated(
    score: int,
    lang: Literal["en", "hi", "mr"] = "en"
) -> str:
    risk = get_risk_level(score)
    key_map = {
        "LOW":      "risk_low",
        "MEDIUM":   "risk_medium",
        "HIGH":     "risk_high",
        "CRITICAL": "risk_critical",
    }
    return get_text(key_map[risk], lang)


def calculate_itc_summary(issues: list[Issue]) -> dict:
    """
    ITC breakdown calculate karo:
    - at_risk: Supplier ne file nahi ki / mismatch
    - blocked: Ineligible category (food, personal use)
    - eligible: Safe ITC
    """
    itc_at_risk = sum(i.itc_at_risk for i in issues)
    return {
        "at_risk": round(itc_at_risk, 2),
        "blocked": 0.0,                     # L3 mein add hoga
        "eligible": 0.0,                    # Excel se calculate hoga
        "total": round(itc_at_risk, 2),
    }


def count_by_severity(issues: list[Issue]) -> dict:
    counts = {s: 0 for s in Severity}
    for issue in issues:
        counts[issue.severity] += 1
    return counts