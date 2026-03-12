"""
models/invoice.py
-----------------
Excel se parse hone ke baad har invoice ka model.
Sale invoice aur purchase invoice dono yahi model use karte hain.
"""
from pydantic import BaseModel, field_validator
from typing import Optional
from datetime import date
from enum import Enum


class InvoiceType(str, Enum):
    SALE     = "sale"
    PURCHASE = "purchase"


class TaxType(str, Enum):
    IGST      = "IGST"
    CGST_SGST = "CGST_SGST"
    EXEMPT    = "EXEMPT"
    UNKNOWN   = "UNKNOWN"


class Invoice(BaseModel):
    """Single invoice — sale ya purchase."""
    invoice_type:   InvoiceType
    invoice_number: str
    party_name:     Optional[str] = None
    party_gstin:    Optional[str] = None
    our_gstin:      Optional[str] = None      # seller ka GSTIN (sales) / buyer ka (purchase)
    taxable_value:  float = 0.0
    igst:           float = 0.0
    cgst:           float = 0.0
    sgst:           float = 0.0
    invoice_date:   Optional[date] = None
    period:         Optional[str] = None      # "2025-01"
    hsn_code:       Optional[str] = None
    irn:            Optional[str] = None      # E-invoice reference
    payment_date:   Optional[date] = None
    is_in_gstr1:    Optional[bool] = None     # Sales: GSTR-1 mein hai?
    is_in_gstr2b:   Optional[bool] = None     # Purchase: GSTR-2B mein hai?
    gstr2b_amount:  Optional[float] = None    # GSTR-2B mein amount

    @property
    def total_tax(self) -> float:
        return self.igst + self.cgst + self.sgst

    @property
    def tax_type(self) -> TaxType:
        if self.igst > 0 and self.cgst == 0:
            return TaxType.IGST
        if self.cgst > 0 and self.igst == 0:
            return TaxType.CGST_SGST
        if self.total_tax == 0:
            return TaxType.EXEMPT
        return TaxType.UNKNOWN

    @field_validator("invoice_number")
    @classmethod
    def strip_invoice_number(cls, v: str) -> str:
        return v.strip().upper()

    @field_validator("party_gstin", "our_gstin", mode="before")
    @classmethod
    def uppercase_gstin(cls, v):
        if v and isinstance(v, str):
            return v.strip().upper()
        return v