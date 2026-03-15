"""
models/issue.py
---------------
Audit issue data model.
Each problem becomes one Issue object.
Fix steps are language-aware — EN / HI / MR.
"""
from pydantic import BaseModel
from enum import Enum
from typing import Optional


class Severity(str, Enum):
    CRITICAL = "CRITICAL"    # Penalty guaranteed — fix immediately
    HIGH     = "HIGH"        # ITC risk — fix soon
    MEDIUM   = "MEDIUM"      # Compliance risk — fix before filing
    LOW      = "LOW"         # Best practice — note it


class IssueType(str, Enum):
    INVALID_GSTIN        = "invalid_gstin"
    TAX_TYPE_MISMATCH    = "tax_type_mismatch"
    DUPLICATE_INVOICE    = "duplicate_invoice"
    GSTR2B_MISSING       = "gstr2b_missing"
    AMOUNT_MISMATCH      = "amount_mismatch"
    GSTR1_MISSING        = "gstr1_missing"
    GSTR1_VS_3B_MISMATCH = "gstr1_vs_3b_mismatch"
    PAYMENT_180_DAYS     = "payment_180_days"
    HSN_MISMATCH         = "hsn_mismatch"
    EINVOICE_MISSING     = "einvoice_missing"
    EXPORT_VALIDATION    = "export_validation"
    CIRCULAR_TRANSACTION = "circular_transaction"
    SECTOR_SPECIFIC      = "sector_specific"


class Issue(BaseModel):
    """Single audit issue."""
    issue_type:     IssueType
    severity:       Severity
    invoice_number: str
    party_name:     Optional[str]   = None
    party_gstin:    Optional[str]   = None
    amount:         Optional[float] = None

    # Problem description — all 3 languages
    problem_en: str
    problem_hi: str
    problem_mr: str

    # Legal reference
    legal_ref:    str
    penalty_risk: Optional[str] = None

    # Fix steps — all 3 languages (only relevant steps for this issue)
    fix_steps_en: list[str] = []
    fix_steps_hi: list[str] = []
    fix_steps_mr: list[str] = []

    # ITC impact
    itc_at_risk: float = 0.0

    # ── Helpers ────────────────────────────────────────────────
    def get_problem(self, lang: str = "en") -> str:
        """Return problem in requested language."""
        if lang == "hi": return self.problem_hi
        if lang == "mr": return self.problem_mr
        return self.problem_en

    def get_fix_steps(self, lang: str = "en") -> list[str]:
        """Return fix steps in requested language. Falls back to EN."""
        if lang == "hi": return self.fix_steps_hi or self.fix_steps_en
        if lang == "mr": return self.fix_steps_mr or self.fix_steps_en
        return self.fix_steps_en

    # Backward compatibility — old code used fix_steps directly
    @property
    def fix_steps(self) -> list[str]:
        return self.fix_steps_en