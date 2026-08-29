"""
models/audit.py
---------------
Audit request/response schemas.

Changes from previous version:
  - AuditResponse: added notice_probability, top_risk_reasons,
    estimated_penalty_exposure, issue_summary, if_fixed_risk_drop
  - NoticeOutput: new model for structured notice predictor output
  - IssueSummary: severity counts in one clean model
  - All new fields Optional — backward compatible
"""
from pydantic import BaseModel, Field
from typing import Optional, Literal, List, Dict
from app.models.issue import Issue, Severity


class AuditRequest(BaseModel):
    client_gstin: str
    our_gstin:    str
    period:       str
    language:     Literal["en", "hi", "mr"] = "en"


class ITCSummary(BaseModel):
    eligible: float = 0.0
    at_risk:  float = 0.0
    blocked:  float = 0.0
    total:    float = 0.0


class IssueSummary(BaseModel):
    """Severity breakdown — single source of truth."""
    total:    int = 0
    critical: int = 0
    high:     int = 0
    medium:   int = 0
    low:      int = 0

    @classmethod
    def from_issues(cls, issues: List[Issue]) -> "IssueSummary":
        return cls(
            total    = len(issues),
            critical = sum(1 for i in issues if i.severity == Severity.CRITICAL),
            high     = sum(1 for i in issues if i.severity == Severity.HIGH),
            medium   = sum(1 for i in issues if i.severity == Severity.MEDIUM),
            low      = sum(1 for i in issues if i.severity == Severity.LOW),
        )


class WhatIfResult(BaseModel):
    """What-if analysis result."""
    current_probability: int
    new_probability:     int
    reduction:           float
    reduction_percent:   float
    current_risk_level:  str
    new_risk_level:      str
    fixes_count:         int


class NoticeOutput(BaseModel):
    """
    Structured notice predictor output.
    Embedded in AuditResponse — used by frontend, email, PDF.
    """
    probability:              int                   # 0-100
    risk_level:               str                   # LOW/MEDIUM/HIGH/VERY_HIGH
    risk_message:             str
    top_risk_reasons:         List[str] = []        # Top 3 human-readable reasons
    estimated_penalty_exposure: float = 0.0         # Total rupee exposure
    if_fixed_risk_drop:       Optional[WhatIfResult] = None
    possible_notices:         List[Dict] = []
    recommendations:          List[Dict] = []
    risk_areas:               List[Dict] = []


class AuditResponse(BaseModel):
    """POST /audit response — single source of truth."""
    audit_id:             str
    client_gstin_masked:  str
    period:               str
    language:             str

    # Score
    compliance_score:      int
    risk_level:            str
    risk_level_translated: str

    # Invoices + Issues
    total_invoices: int
    issues:         List[Issue]

    # Issue summary — derived, never re-calculated separately
    issue_summary:  Optional[IssueSummary] = None

    # Legacy severity counts — kept for backward compat
    critical_count: int = 0
    high_count:     int = 0
    medium_count:   int = 0
    low_count:      int = 0

    # ITC
    itc_summary: ITCSummary

    # Notice predictor output (NEW — optional for backward compat)
    notice_output: NoticeOutput = Field(default_factory=lambda: NoticeOutput(
    probability=0,
    risk_level="LOW",
    risk_message="No risk detected",
    top_risk_reasons=[],
    estimated_penalty_exposure=0.0,
    possible_notices=[],
    recommendations=[],
    risk_areas=[]
))

    # Report
    pdf_url:    Optional[str] = None
    created_at: str

    def get_issue_summary(self) -> IssueSummary:
        """
        Always derive from actual issues — never from stale counts.
        This prevents the "No issues found" contradiction bug.
        """
        if self.issues:
            return IssueSummary.from_issues(self.issues)
        # Fallback to stored summary
        if self.issue_summary:
            return self.issue_summary
        # Last resort — reconstruct from legacy counts
        return IssueSummary(
            total    = self.critical_count + self.high_count + self.medium_count + self.low_count,
            critical = self.critical_count,
            high     = self.high_count,
            medium   = self.medium_count,
            low      = self.low_count,
        )

    def has_issues(self) -> bool:
        """Source of truth: are there any issues?"""
        return len(self.issues) > 0 or self.get_issue_summary().total > 0


class AuditListItem(BaseModel):
    audit_id:    str
    client_name: str
    gstin_masked: str
    period:      str
    score:       int
    risk_level:  str
    itc_at_risk: float
    created_at:  str