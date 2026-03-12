"""
models/issue.py
---------------
Audit issue ka data model.
Har ek problem ek Issue object ban jaati hai.
"""
from pydantic import BaseModel
from enum import Enum
from typing import Optional


class Severity(str, Enum):
    CRITICAL = "CRITICAL"    # Penalty guaranteed — turant fix karo
    HIGH     = "HIGH"        # ITC risk — jaldi fix karo
    MEDIUM   = "MEDIUM"      # Compliance risk — filing se pehle fix karo
    LOW      = "LOW"         # Best practice — note karo


class IssueType(str, Enum):
    INVALID_GSTIN           = "invalid_gstin"
    TAX_TYPE_MISMATCH       = "tax_type_mismatch"
    DUPLICATE_INVOICE       = "duplicate_invoice"
    GSTR2B_MISSING          = "gstr2b_missing"
    AMOUNT_MISMATCH         = "amount_mismatch"
    GSTR1_MISSING           = "gstr1_missing"
    GSTR1_VS_3B_MISMATCH    = "gstr1_vs_3b_mismatch"
    PAYMENT_180_DAYS        = "payment_180_days"
    HSN_MISMATCH            = "hsn_mismatch"
    EINVOICE_MISSING        = "einvoice_missing"
    EXPORT_VALIDATION       = "export_validation"
    CIRCULAR_TRANSACTION    = "circular_transaction"


class Issue(BaseModel):
    """Single audit issue."""
    issue_type:     IssueType
    severity:       Severity
    invoice_number: str
    party_name:     Optional[str] = None
    party_gstin:    Optional[str] = None
    amount:         Optional[float] = None

    # Multi-language descriptions
    problem_en:     str
    problem_hi:     str
    problem_mr:     str

    # Legal reference
    legal_ref:      str           # e.g. "IGST Act Section 8(2)"
    penalty_risk:   Optional[str] = None

    # Fix steps (always English — CA will translate verbally)
    fix_steps:      list[str]

    # ITC impact
    itc_at_risk:    float = 0.0

    def get_problem(self, lang: str = "en") -> str:
        mapping = {"en": self.problem_en, "hi": self.problem_hi, "mr": self.problem_mr}
        return mapping.get(lang, self.problem_en)