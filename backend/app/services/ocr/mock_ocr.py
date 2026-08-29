"""
app/services/ocr/mock_ocr.py
Mock OCR engine for tests — fixtures match actual Invoice model fields.
"""
from __future__ import annotations
from datetime import date
from typing import Optional
from .base import BaseOCREngine
from .schemas import ExtractedInvoiceFields, OCRKeyValue, OCRLanguage, OCRProvider, OCRResult, OCRTable, OCRTableCell

_FIXTURES: dict[str, OCRResult] = {}

def _build():
    # English GST invoice
    _FIXTURES["gst_invoice_en"] = OCRResult(
        provider=OCRProvider.MOCK,
        raw_text=(
            "TAX INVOICE\nInvoice No: INV-2024-001\nDate: 15/01/2024\n"
            "Supplier: Acme Supplies Pvt Ltd\nGSTIN: 27AABCU9603R1ZX\n"
            "Bill To: XYZ Corp\nBuyer GSTIN: 29GGGGG1314R9Z6\n"
            "Taxable Value: 10000.00\nCGST @ 9%: 900.00\nSGST @ 9%: 900.00\n"
            "Grand Total: 11800.00\nHSN: 8471"
        ),
        tables=[
            OCRTable(rows=2, cols=4, cells=[
                OCRTableCell(text="Description", row_index=0, col_index=0, is_header=True),
                OCRTableCell(text="HSN",         row_index=0, col_index=1, is_header=True),
                OCRTableCell(text="Qty",         row_index=0, col_index=2, is_header=True),
                OCRTableCell(text="Amount",      row_index=0, col_index=3, is_header=True),
                OCRTableCell(text="Widget A",    row_index=1, col_index=0),
                OCRTableCell(text="8471",        row_index=1, col_index=1),
                OCRTableCell(text="10",          row_index=1, col_index=2),
                OCRTableCell(text="10000.00",    row_index=1, col_index=3),
            ])
        ],
        key_values=[
            OCRKeyValue(key="Invoice No",   value="INV-2024-001",    confidence=0.97),
            OCRKeyValue(key="GSTIN",        value="27AABCU9603R1ZX", confidence=0.96),
            OCRKeyValue(key="Grand Total",  value="11800.00",        confidence=0.98),
        ],
        extracted=ExtractedInvoiceFields(
            invoice_number = "INV-2024-001",
            invoice_date   = date(2024, 1, 15),
            party_name     = "Acme Supplies Pvt Ltd",
            party_gstin    = "27AABCU9603R1ZX",
            our_gstin_hint = "29GGGGG1314R9Z6",
            taxable_value  = 10000.0,
            cgst           = 900.0,
            sgst           = 900.0,
            total_amount   = 11800.0,
            hsn_code       = "8471",
        ),
        overall_confidence = 0.97,
        language_detected  = "en",
        success            = True,
    )

    # Marathi invoice
    _FIXTURES["marathi_invoice"] = OCRResult(
        provider=OCRProvider.MOCK,
        raw_text="कर चलन\nचलन क्र.: INV-MR-001\nदिनांक: 20/01/2024\nएकूण रक्कम: ₹5900.00",
        extracted=ExtractedInvoiceFields(
            invoice_number = "INV-MR-001",
            invoice_date   = date(2024, 1, 20),
            total_amount   = 5900.0,
        ),
        overall_confidence = 0.80,
        language_detected  = "mr",
        success            = True,
    )

    _FIXTURES["low_confidence"] = OCRResult(
        provider=OCRProvider.MOCK,
        raw_text="??? illegible ???",
        overall_confidence=0.30,
        success=True,
        warnings=["Low confidence — rescan recommended."],
    )

    _FIXTURES["api_failure"] = OCRResult.failure(
        OCRProvider.MOCK, "Simulated API failure."
    )

_build()


class MockOCR(BaseOCREngine):
    def __init__(self, fixture: Optional[str] = None, result: Optional[OCRResult] = None):
        self._fixture = fixture
        self._custom  = result

    @property
    def provider(self) -> OCRProvider:
        return OCRProvider.MOCK

    @classmethod
    def is_available(cls) -> bool:
        return True

    def _run_ocr(self, image_source, language: OCRLanguage) -> OCRResult:
        if self._custom:
            return self._custom
        if self._fixture:
            r = _FIXTURES.get(self._fixture)
            if r is None:
                raise ValueError(f"Unknown fixture '{self._fixture}'. Available: {list(_FIXTURES)}")
            return r
        return OCRResult(provider=self.provider, raw_text="Mock text", overall_confidence=0.90, success=True)

    @classmethod
    def from_fixture(cls, name: str) -> "MockOCR":
        return cls(fixture=name)

    @classmethod
    def always_fail(cls, msg: str = "Mock failure") -> "MockOCR":
        return cls(result=OCRResult.failure(OCRProvider.MOCK, msg))

    @classmethod
    def low_confidence(cls) -> "MockOCR":
        return cls(fixture="low_confidence")