"""
models/audit.py
---------------
Audit request aur response ka schema.
FastAPI in models se automatically docs generate karta hai.
"""
from pydantic import BaseModel
from typing import Optional, Literal
from app.models.issue import Issue, Severity


class AuditRequest(BaseModel):
    """POST /audit ka body."""
    client_gstin: str
    our_gstin:    str
    period:       str                     # "2025-01"
    language:     Literal["en", "hi", "mr"] = "en"
    # File upload alag se aata hai — multipart form data mein


class ITCSummary(BaseModel):
    """ITC breakdown."""
    eligible:   float = 0.0
    at_risk:    float = 0.0
    blocked:    float = 0.0
    total:      float = 0.0


class AuditResponse(BaseModel):
    """POST /audit ka response."""
    audit_id:             str
    client_gstin_masked:  str
    period:               str
    language:             str

    # Score
    compliance_score:     int             # 0-100
    risk_level:           str             # LOW / MEDIUM / HIGH / CRITICAL
    risk_level_translated: str            # user ki language mein

    # Issues
    total_invoices:       int
    issues:               list[Issue]
    critical_count:       int
    high_count:           int
    medium_count:         int
    low_count:            int

    # ITC
    itc_summary:          ITCSummary

    # Report
    pdf_url:              Optional[str] = None
    created_at:           str


class AuditListItem(BaseModel):
    """Dashboard list mein ek audit ka summary."""
    audit_id:         str
    client_name:      str
    gstin_masked:     str
    period:           str
    score:            int
    risk_level:       str
    itc_at_risk:      float
    created_at:       str