"""
app/services/ocr/google_vision.py
Google Cloud Vision OCR — same logic as existing ocr_scanner.py,
refactored into BaseOCREngine interface.

Preserves ALL existing regex patterns from ocr_scanner.py exactly.
"""
from __future__ import annotations

import base64
import logging
import os
import re
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import requests

from .base import BaseOCREngine
from .schemas import (
    ExtractedInvoiceFields,
    OCRKeyValue,
    OCRLanguage,
    OCRProvider,
    OCRResult,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Regex patterns — SAME as existing ocr_scanner.py
# ---------------------------------------------------------------------------

GSTIN_RE    = re.compile(r'\b(\d{2}[A-Za-z]{5}\d{4}[A-Za-z][A-Za-z\d][Zz][A-Za-z\d])\b')
INVOICE_RE  = re.compile(r'(?:Invoice\s*(?:No|Number|#)?\.?\s*[:;]?\s*)([A-Za-z0-9/\-_]+)', re.IGNORECASE)
INV_RE2     = re.compile(r'(?:INV|BILL|VCH|RCP)[\-/]?\d{2,}[\-/]?\d{2,}', re.IGNORECASE)
DATE_RE     = re.compile(r'\b(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})\b')
DATE_RE2    = re.compile(
    r'\b(\d{1,2}[\-\s](?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[\-\s]\d{4})\b',
    re.IGNORECASE,
)
SUBTOTAL_RE = re.compile(
    r'(?:Subtotal|Sub\s*Total|Taxable\s*Value|Net\s*Amount)[\s:₹Rs.]*([0-9,]+\.?\d*)',
    re.IGNORECASE,
)
TOTAL_RE    = re.compile(
    r'(?:Total\s*Amount|Grand\s*Total|Invoice\s*Total)[\s:₹Rs.]*([0-9,]+\.?\d*)',
    re.IGNORECASE,
)
CGST_RE     = re.compile(r'CGST[\s:@₹Rs.%0-9]*?([0-9,]+\.?\d*)\s*$', re.IGNORECASE | re.MULTILINE)
SGST_RE     = re.compile(r'(?:SGST|UTGST)[\s:@₹Rs.%0-9]*?([0-9,]+\.?\d*)\s*$', re.IGNORECASE | re.MULTILINE)
IGST_RE     = re.compile(r'IGST[\s:@₹Rs.%0-9]*?([0-9,]+\.?\d*)\s*$', re.IGNORECASE | re.MULTILINE)
HSN_RE      = re.compile(r'HSN|SAC', re.IGNORECASE)
PARTY_RE    = re.compile(r'(?:Bill\s*To|Sold\s*To|Buyer|Ship\s*To|Recipient)\s*[:\n]\s*(.+)', re.IGNORECASE)
IRN_RE      = re.compile(r'\b([a-f0-9]{64})\b', re.IGNORECASE)  # IRN is 64-char hex


def _clean_amount(text: str) -> float:
    try:
        return float(re.sub(r'[^\d.]', '', text.replace(',', '')))
    except (ValueError, TypeError):
        return 0.0


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

class GoogleVisionOCR(BaseOCREngine):
    """OCR engine backed by Google Cloud Vision DOCUMENT_TEXT_DETECTION."""

    def __init__(self, api_key: Optional[str] = None) -> None:
        self._api_key = api_key or os.getenv("GOOGLE_VISION_API_KEY", "")

    @property
    def provider(self) -> OCRProvider:
        return OCRProvider.GOOGLE_VISION

    @classmethod
    def is_available(cls) -> bool:
        return bool(os.getenv("GOOGLE_VISION_API_KEY", ""))

    def _run_ocr(
        self,
        image_source: Union[bytes, Path, str],
        language: OCRLanguage,
    ) -> OCRResult:
        image_bytes = self._to_bytes(image_source)
        if image_bytes is None:
            return OCRResult.failure(
                self.provider, f"Cannot read image from: {image_source}"
            )
        raw_response = self._call_api(image_bytes, language)
        if raw_response is None:
            return OCRResult.failure(self.provider, "Google Vision API call failed.")
        return self._parse_response(raw_response)

    # ------------------------------------------------------------------
    # API call — same as existing extract_text_google_vision()
    # ------------------------------------------------------------------

    def _call_api(self, image_bytes: bytes, language: OCRLanguage) -> Optional[Dict[str, Any]]:
        hints = self._language_hints(language)
        payload = {
            "requests": [{
                "image":        {"content": base64.b64encode(image_bytes).decode("utf-8")},
                "features":     [{"type": "DOCUMENT_TEXT_DETECTION", "maxResults": 1}],
                "imageContext": {"languageHints": hints},
            }]
        }
        try:
            resp = requests.post(
                f"https://vision.googleapis.com/v1/images:annotate?key={self._api_key}",
                json=payload,
                timeout=15,
            )
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as exc:
            logger.warning("Google Vision API error: %s", exc)
            return None

    # ------------------------------------------------------------------
    # Response parsing
    # ------------------------------------------------------------------

    def _parse_response(self, raw: Dict[str, Any]) -> OCRResult:
        try:
            response0 = raw.get("responses", [{}])[0]
        except IndexError:
            return OCRResult.failure(self.provider, "Empty responses from Vision API.")

        # API error check
        if "error" in response0:
            return OCRResult.failure(
                self.provider,
                f"Vision API error: {response0['error'].get('message', 'Unknown')}",
            )

        # Full text
        full_text = response0.get("fullTextAnnotation", {}).get("text", "")
        if not full_text:
            annotations = response0.get("textAnnotations", [])
            if annotations:
                full_text = annotations[0].get("description", "")

        if not full_text or len(full_text) < 20:
            return OCRResult.failure(self.provider, "No meaningful text detected.")

        # Confidence from page blocks
        pages     = response0.get("fullTextAnnotation", {}).get("pages", [])
        confidence = self._page_confidence(pages)

        # Language detection
        lang_detected = None
        if pages:
            langs = pages[0].get("property", {}).get("detectedLanguages", [])
            if langs:
                lang_detected = langs[0].get("languageCode")

        # Key-value pairs from colon-separated lines
        key_values = [
            OCRKeyValue(key=parts[0].strip(), value=parts[1].strip(), confidence=0.75)
            for line in full_text.splitlines()
            if ":" in line
            for parts in [line.split(":", 1)]
            if parts[0].strip() and parts[1].strip()
        ]

        extracted = self._extract_fields(full_text)

        return OCRResult(
            provider           = self.provider,
            raw_text           = full_text,
            key_values         = key_values,
            extracted          = extracted,
            overall_confidence = confidence,
            language_detected  = lang_detected,
            success            = True,
        )

    @staticmethod
    def _page_confidence(pages: List[Dict]) -> float:
        if not pages:
            return 0.5
        scores = [
            block.get("confidence", 0.0)
            for page in pages
            for block in page.get("blocks", [])
        ]
        return sum(scores) / len(scores) if scores else 0.5

    # ------------------------------------------------------------------
    # Field extraction — same logic as existing _parse_invoice_from_text()
    # ------------------------------------------------------------------

    @classmethod
    def _extract_fields(cls, text: str) -> ExtractedInvoiceFields:
        f = ExtractedInvoiceFields()

        # GSTINs — first = supplier/vendor, second = buyer
        gstins = [g.upper() for g in GSTIN_RE.findall(text)]
        if gstins:
            f.party_gstin    = gstins[0]
            if len(gstins) > 1:
                f.our_gstin_hint = gstins[1]

        # Invoice number
        m = INVOICE_RE.search(text)
        if m:
            f.invoice_number = m.group(1).strip()
        else:
            m2 = INV_RE2.search(text)
            if m2:
                f.invoice_number = m2.group(0).upper()

        # Date
        m = DATE_RE2.search(text) or DATE_RE.search(text)
        if m:
            f.invoice_date = cls._parse_date(m.group(1))

        # Taxable value / subtotal
        m = SUBTOTAL_RE.search(text)
        if m:
            f.taxable_value = _clean_amount(m.group(1))

        # Total amount
        m = TOTAL_RE.search(text)
        if m:
            f.total_amount = _clean_amount(m.group(1))

        taxable = f.taxable_value

        # CGST
        m = CGST_RE.search(text)
        if m:
            v = _clean_amount(m.group(1))
            if taxable == 0 or v < taxable:
                f.cgst = v

        # SGST
        m = SGST_RE.search(text)
        if m:
            v = _clean_amount(m.group(1))
            if taxable == 0 or v < taxable:
                f.sgst = v

        # IGST
        m = IGST_RE.search(text)
        if m:
            v = _clean_amount(m.group(1))
            if taxable == 0 or v < taxable:
                f.igst = v

        # Auto-calculate total if missing
        if f.total_amount == 0 and f.taxable_value > 0:
            f.total_amount = f.taxable_value + f.igst + f.cgst + f.sgst

        # HSN code
        lines = text.split('\n')
        for i, line in enumerate(lines):
            if HSN_RE.search(line):
                area  = '\n'.join(lines[max(0, i): i + 5])
                hsn8  = re.findall(r'\b(\d{8})\b', area)
                if hsn8:
                    f.hsn_code = hsn8[0]; break
                hsn4 = re.findall(r'\b(\d{4})\b', area)
                if hsn4:
                    f.hsn_code = hsn4[0]; break

        # Party name
        m = PARTY_RE.search(text)
        if m:
            name = m.group(1).strip().split('\n')[0].strip()
            if 3 < len(name) < 100:
                f.party_name = name

        # IRN
        m = IRN_RE.search(text)
        if m:
            f.irn = m.group(1)

        return f

    @staticmethod
    def _parse_date(date_str: str) -> Optional[date]:
        """Parse common Indian date formats to date object."""
        import re as _re
        from datetime import datetime
        formats = [
            "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y",
            "%d/%m/%y", "%d-%m-%y",
            "%d %b %Y", "%d-%b-%Y", "%d %B %Y",
            "%Y-%m-%d",
        ]
        clean = _re.sub(r'\s+', ' ', date_str.strip())
        for fmt in formats:
            try:
                return datetime.strptime(clean, fmt).date()
            except ValueError:
                continue
        return None