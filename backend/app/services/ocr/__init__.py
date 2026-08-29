"""app/services/ocr/__init__.py"""
from .schemas import (
    ExtractedInvoiceFields, OCRConfidence, OCRKeyValue,
    OCRLanguage, OCRProvider, OCRResult, OCRTable, OCRTableCell,
)
from .base   import BaseOCREngine
from .router import OCRRouter, USE_OCR_ROUTER, ENABLE_AWS_TEXTRACT

__all__ = [
    "ExtractedInvoiceFields", "OCRConfidence", "OCRKeyValue",
    "OCRLanguage", "OCRProvider", "OCRResult", "OCRTable", "OCRTableCell",
    "BaseOCREngine", "OCRRouter", "USE_OCR_ROUTER", "ENABLE_AWS_TEXTRACT",
]