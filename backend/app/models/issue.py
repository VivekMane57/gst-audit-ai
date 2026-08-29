"""
models/issue.py
---------------
Enhanced Issue model — structured output with all fields needed for:
  - Structured issue engine
  - Notice risk contribution
  - Report/email/PDF consistency
  - Frontend display

Backward compatible — all new fields are Optional with defaults.
"""
from pydantic import BaseModel, Field
from enum import Enum
from typing import Optional, List


class Severity(str, Enum):
    CRITICAL = "CRITICAL"    # Penalty guaranteed — fix immediately
    HIGH     = "HIGH"        # ITC risk — fix soon
    MEDIUM   = "MEDIUM"      # Compliance risk — fix before filing
    LOW      = "LOW"         # Best practice — note it


class IssueCategory(str, Enum):
    ITC            = "itc"
    INVOICING      = "invoicing"
    GSTIN          = "gstin"
    RECONCILIATION = "reconciliation"
    HSN            = "hsn"
    FILING         = "filing"
    FRAUD          = "fraud"
    CLASSIFICATION = "classification"
    TAX_COMPUTATION = "tax_computation"
    SECTOR         = "sector"


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


# ── Issue type → category mapping (centralized) ───────────────
ISSUE_CATEGORY_MAP: dict[IssueType, IssueCategory] = {
    IssueType.INVALID_GSTIN:        IssueCategory.GSTIN,
    IssueType.TAX_TYPE_MISMATCH:    IssueCategory.TAX_COMPUTATION,
    IssueType.DUPLICATE_INVOICE:    IssueCategory.FRAUD,
    IssueType.GSTR2B_MISSING:       IssueCategory.ITC,
    IssueType.AMOUNT_MISMATCH:      IssueCategory.RECONCILIATION,
    IssueType.GSTR1_MISSING:        IssueCategory.FILING,
    IssueType.GSTR1_VS_3B_MISMATCH: IssueCategory.RECONCILIATION,
    IssueType.PAYMENT_180_DAYS:     IssueCategory.ITC,
    IssueType.HSN_MISMATCH:         IssueCategory.HSN,
    IssueType.EINVOICE_MISSING:     IssueCategory.INVOICING,
    IssueType.EXPORT_VALIDATION:    IssueCategory.INVOICING,
    IssueType.CIRCULAR_TRANSACTION: IssueCategory.FRAUD,
    IssueType.SECTOR_SPECIFIC:      IssueCategory.SECTOR,
}

# ── Issue type → human readable title (EN) ───────────────────
ISSUE_TITLE_MAP: dict[IssueType, str] = {
    IssueType.INVALID_GSTIN:        "Invalid GSTIN Detected",
    IssueType.TAX_TYPE_MISMATCH:    "Wrong Tax Type (IGST vs CGST+SGST)",
    IssueType.DUPLICATE_INVOICE:    "Duplicate Invoice Found",
    IssueType.GSTR2B_MISSING:       "Invoice Missing in GSTR-2B",
    IssueType.AMOUNT_MISMATCH:      "Tax Amount Mismatch (Books vs GSTR-2B)",
    IssueType.GSTR1_MISSING:        "Sale Invoice Not in GSTR-1",
    IssueType.GSTR1_VS_3B_MISMATCH: "GSTR-1 vs GSTR-3B Mismatch",
    IssueType.PAYMENT_180_DAYS:     "Payment Rule Violation (180 Days)",
    IssueType.HSN_MISMATCH:         "HSN Code Rate Mismatch",
    IssueType.EINVOICE_MISSING:     "E-Invoice IRN Missing",
    IssueType.EXPORT_VALIDATION:    "Export Invoice Validation Failed",
    IssueType.CIRCULAR_TRANSACTION: "Circular Transaction Detected",
    IssueType.SECTOR_SPECIFIC:      "Sector-Specific Compliance Issue",
}


class LegalReference(BaseModel):
    """Structured legal reference."""
    act_name:        str                 # "CGST Act 2017"
    section:         str                 # "Section 16(2)(aa)"
    short_legal_text: str               # One-line description


class Issue(BaseModel):
    """
    Single audit issue — fully structured.
    All new fields are Optional for backward compatibility.
    """
    # ── Core fields (existing) ────────────────────────────────
    issue_type:     IssueType
    severity:       Severity
    invoice_number: str
    party_name:     Optional[str]   = None
    party_gstin:    Optional[str]   = None
    amount:         Optional[float] = None

    # ── Problem description — all 3 languages ─────────────────
    problem_en: str
    problem_hi: str
    problem_mr: str

    # ── Legal reference (legacy string — kept for compat) ─────
    legal_ref:    str
    penalty_risk: Optional[str] = None

    # ── Fix steps — all 3 languages ───────────────────────────
    fix_steps_en: List[str] = []
    fix_steps_hi: List[str] = []
    fix_steps_mr: List[str] = []

    # ── ITC impact ────────────────────────────────────────────
    itc_at_risk: float = 0.0

    # ── NEW: Structured fields (all Optional — backward compat) ──

    # Human-readable title (auto-derived if not set)
    title: Optional[str] = None

    # Structured legal reference (richer than legacy string)
    legal_reference: Optional[LegalReference] = None

    # Issue category for grouping/filtering
    category: Optional[IssueCategory] = None

    # How much this issue contributes to notice probability (0-35)
    notice_risk_impact: Optional[float] = None

    # Documents CA should gather to defend this issue
    evidence_required: Optional[List[str]] = None

    # Estimated penalty in rupees (numeric — for total exposure calc)
    estimated_penalty: Optional[float] = None

    # ── Computed helpers ──────────────────────────────────────
    def get_title(self) -> str:
        """Return title — from field or auto-derive from issue_type."""
        if self.title:
            return self.title
        return ISSUE_TITLE_MAP.get(self.issue_type, self.issue_type.value.replace("_", " ").title())

    def get_category(self) -> IssueCategory:
        """Return category — from field or auto-derive."""
        if self.category:
            return self.category
        return ISSUE_CATEGORY_MAP.get(self.issue_type, IssueCategory.FILING)

    def get_problem(self, lang: str = "en") -> str:
        if lang == "hi": return self.problem_hi or self.problem_en
        if lang == "mr": return self.problem_mr or self.problem_en
        return self.problem_en

    def get_fix_steps(self, lang: str = "en") -> List[str]:
        if lang == "hi": return self.fix_steps_hi or self.fix_steps_en
        if lang == "mr": return self.fix_steps_mr or self.fix_steps_en
        return self.fix_steps_en

    # Backward compat
    @property
    def fix_steps(self) -> List[str]:
        return self.fix_steps_en

    def to_notice_sim_dict(self) -> dict:
        """
        Convert to dict format expected by notice_simulator.
        Centralizes this conversion — no more scattered dicts.
        """
        return {
            "type":       self.issue_type.value,
            "severity":   self.severity.value.lower(),
            "invoice":    self.invoice_number,
            "party":      self.party_name or "N/A",
            "amount":     float(self.amount or 0),
            "tax_impact": float(self.itc_at_risk or 0),
        }

    def to_structured_dict(self, lang: str = "en") -> dict:
        """
        Full structured output for API response / frontend.
        This is the source of truth for all issue displays.
        """
        return {
            "issue_type":        self.issue_type.value,
            "title":             self.get_title(),
            "severity":          self.severity.value,
            "category":          self.get_category().value,
            "invoice_number":    self.invoice_number,
            "party_name":        self.party_name,
            "party_gstin":       self.party_gstin,
            "amount":            self.amount,
            "itc_at_risk":       self.itc_at_risk,
            "estimated_penalty": self.estimated_penalty,
            "notice_risk_impact": self.notice_risk_impact,
            # Language-aware fields
            "problem":           self.get_problem(lang),
            "problem_en":        self.problem_en,
            "problem_hi":        self.problem_hi,
            "problem_mr":        self.problem_mr,
            "fix_steps":         self.get_fix_steps(lang),
            "fix_steps_en":      self.fix_steps_en,
            "fix_steps_hi":      self.fix_steps_hi,
            "fix_steps_mr":      self.fix_steps_mr,
            "legal_ref":         self.legal_ref,
            "legal_reference":   self.legal_reference.dict() if self.legal_reference else None,
            "penalty_risk":      self.penalty_risk,
            "evidence_required": self.evidence_required or [],
        }