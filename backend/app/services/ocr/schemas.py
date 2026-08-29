"""
app/services/ocr/schemas.py
Normalized Pydantic schema for OCR results — aligned with actual Invoice model.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, validator


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class OCRProvider(str, Enum):
    GOOGLE_VISION = "google_vision"
    AWS_TEXTRACT  = "aws_textract"
    TESSERACT     = "tesseract"
    MOCK          = "mock"


class OCRConfidence(str, Enum):
    HIGH   = "high"    # > 0.85
    MEDIUM = "medium"  # 0.60 – 0.85
    LOW    = "low"     # < 0.60


class OCRLanguage(str, Enum):
    ENGLISH = "en"
    HINDI   = "hi"
    MARATHI = "mr"
    AUTO    = "auto"


# ---------------------------------------------------------------------------
# Building-block models
# ---------------------------------------------------------------------------

class OCRTableCell(BaseModel):
    text:       str
    row_index:  int
    col_index:  int
    row_span:   int   = 1
    col_span:   int   = 1
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    is_header:  bool  = False


class OCRTable(BaseModel):
    rows:  int
    cols:  int
    cells: List[OCRTableCell] = Field(default_factory=list)

    def to_dict_list(self) -> List[Dict[str, Any]]:
        """Convert table to list-of-dicts keyed by header row."""
        if not self.cells:
            return []
        headers = {
            c.col_index: c.text
            for c in self.cells
            if c.is_header and c.row_index == 0
        }
        if not headers:
            headers = {c.col_index: c.text for c in self.cells if c.row_index == 0}
        rows_data: Dict[int, Dict[str, str]] = {}
        for cell in self.cells:
            if cell.row_index == 0:
                continue
            row = rows_data.setdefault(cell.row_index, {})
            row[headers.get(cell.col_index, f"col_{cell.col_index}")] = cell.text
        return list(rows_data.values())


class OCRKeyValue(BaseModel):
    key:        str
    value:      str
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


# ---------------------------------------------------------------------------
# Extracted invoice fields — matches Invoice model field names exactly
# ---------------------------------------------------------------------------

class ExtractedInvoiceFields(BaseModel):
    """
    Fields map 1:1 to Invoice model fields in app/models/invoice.py.
    Safe to unpack directly: Invoice(**extracted.to_invoice_kwargs(...))
    """
    invoice_number: Optional[str]  = None
    invoice_date:   Optional[date] = None
    party_name:     Optional[str]  = None
    party_gstin:    Optional[str]  = None
    taxable_value:  float          = 0.0
    igst:           float          = 0.0
    cgst:           float          = 0.0
    sgst:           float          = 0.0
    hsn_code:       Optional[str]  = None
    irn:            Optional[str]  = None

    # Extra fields not in Invoice but useful for display
    total_amount:   float          = 0.0
    our_gstin_hint: Optional[str]  = None   # second GSTIN found (may be our own)

    def to_invoice_kwargs(
        self,
        invoice_type: str  = "purchase",
        our_gstin:    str  = "",
        period:       Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Return dict ready to pass to Invoice(**kwargs).
        Only includes fields that Invoice model accepts.
        """
        return {
            "invoice_number": self.invoice_number or "",
            "invoice_date":   self.invoice_date,
            "party_name":     self.party_name,
            "party_gstin":    self.party_gstin,
            "taxable_value":  self.taxable_value,
            "igst":           self.igst,
            "cgst":           self.cgst,
            "sgst":           self.sgst,
            "hsn_code":       self.hsn_code,
            "irn":            self.irn,
            "our_gstin":      our_gstin,
            "period":         period,
        }


# ---------------------------------------------------------------------------
# Top-level OCR result
# ---------------------------------------------------------------------------

class OCRResult(BaseModel):
    """
    Unified result returned by every engine.
    ocr_scanner.py only consumes this model.
    """
    provider:     OCRProvider
    raw_text:     str  = ""

    # Structured outputs (provider-dependent)
    tables:       List[OCRTable]    = Field(default_factory=list)
    key_values:   List[OCRKeyValue] = Field(default_factory=list)

    # Extracted invoice semantics
    extracted:    ExtractedInvoiceFields = Field(default_factory=ExtractedInvoiceFields)

    # Quality signals
    overall_confidence: float        = Field(default=0.0, ge=0.0, le=1.0)
    confidence_label:   OCRConfidence = OCRConfidence.LOW
    language_detected:  Optional[str] = None

    # Error / warning info
    success:       bool              = True
    error_message: Optional[str]     = None
    warnings:      List[str]         = Field(default_factory=list)

    # Provider metadata (Textract job ID, Vision request ID, etc.)
    provider_metadata: Dict[str, Any] = Field(default_factory=dict)

    @validator("confidence_label", always=True, pre=False)
    def _set_confidence_label(cls, v, values):  # noqa: N805
        score = values.get("overall_confidence", 0.0)
        if score >= 0.85:
            return OCRConfidence.HIGH
        if score >= 0.60:
            return OCRConfidence.MEDIUM
        return OCRConfidence.LOW

    @classmethod
    def failure(
        cls,
        provider: OCRProvider,
        error:    str,
        *,
        warnings: Optional[List[str]] = None,
    ) -> "OCRResult":
        return cls(
            provider=provider,
            success=False,
            error_message=error,
            warnings=warnings or [],
        )

    def is_usable(self, min_confidence: float = 0.50) -> bool:
        return self.success and self.overall_confidence >= min_confidence