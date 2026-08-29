"""
app/services/ocr_scanner.py  (MODIFIED — backward-compatible)

Public API is UNCHANGED — same signatures as before:

  scan_image_to_invoices(image_bytes, filename, invoice_type, our_gstin, period) → list[Invoice]
  extract_invoice_from_image(image_bytes, languages) → Dict
  scan_multiple_images(image_files, languages) → List[Dict]

Internally delegates to new OCR module. Tesseract stays as last-resort fallback.
Feature flags:
  USE_OCR_ROUTER=false (default) — transparent pass-through, same as before
  USE_OCR_ROUTER=true            — smart language routing
  ENABLE_AWS_TEXTRACT=true       — adds Textract for English
"""
from __future__ import annotations

import io
import logging
import os
import re
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# ── Tesseract (optional, same as before) ──────────────────────────────────
try:
    import pytesseract
    from PIL import Image, ImageEnhance
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False
    logger.warning("pytesseract/Pillow not installed. Tesseract fallback disabled.")

# ── New OCR module ─────────────────────────────────────────────────────────
from app.services.ocr import OCRLanguage, OCRProvider, OCRResult, OCRRouter

# ── Language map: str → OCRLanguage ───────────────────────────────────────
_LANG_MAP = {
    "en":  OCRLanguage.ENGLISH,
    "hi":  OCRLanguage.HINDI,
    "mr":  OCRLanguage.MARATHI,
    "eng": OCRLanguage.ENGLISH,
    "hin": OCRLanguage.HINDI,
    "mar": OCRLanguage.MARATHI,
}

# ── Keep existing regex constants (used by extract_invoice_from_image) ────
GSTIN_RE    = re.compile(r'\b(\d{2}[A-Za-z]{5}\d{4}[A-Za-z][A-Za-z\d][Zz][A-Za-z\d])\b')
INVOICE_RE  = re.compile(r'(?:Invoice\s*(?:No|Number|#)?\.?\s*[:;]?\s*)([A-Za-z0-9/\-_]+)', re.IGNORECASE)
INV_RE2     = re.compile(r'(?:INV|BILL|VCH|RCP)[\-/]?\d{2,}[\-/]?\d{2,}', re.IGNORECASE)
DATE_RE     = re.compile(r'\b(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})\b')
DATE_RE2    = re.compile(r'\b(\d{1,2}[\-\s](?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[\-\s]\d{4})\b', re.IGNORECASE)
SUBTOTAL_RE = re.compile(r'(?:Subtotal|Sub\s*Total|Taxable\s*Value|Net\s*Amount)[\s:₹Rs.]*([0-9,]+\.?\d*)', re.IGNORECASE)
TOTAL_RE    = re.compile(r'(?:Total\s*Amount|Grand\s*Total|Invoice\s*Total)[\s:₹Rs.]*([0-9,]+\.?\d*)', re.IGNORECASE)
CGST_RE     = re.compile(r'CGST[\s:@₹Rs.%0-9]*?([0-9,]+\.?\d*)\s*$', re.IGNORECASE | re.MULTILINE)
SGST_RE     = re.compile(r'(?:SGST|UTGST)[\s:@₹Rs.%0-9]*?([0-9,]+\.?\d*)\s*$', re.IGNORECASE | re.MULTILINE)
IGST_RE     = re.compile(r'IGST[\s:@₹Rs.%0-9]*?([0-9,]+\.?\d*)\s*$', re.IGNORECASE | re.MULTILINE)
HSN_RE      = re.compile(r'HSN|SAC', re.IGNORECASE)
PARTY_RE    = re.compile(r'(?:Bill\s*To|Sold\s*To|Buyer|Ship\s*To|Recipient)\s*[:\n]\s*(.+)', re.IGNORECASE)


def _clean_amount(text: str) -> float:
    try:
        return float(re.sub(r'[^\d.]', '', text.replace(',', '')))
    except (ValueError, TypeError):
        return 0.0


# ═══════════════════════════════════════════════════════════════
#  MAIN PUBLIC API  (signature UNCHANGED)
# ═══════════════════════════════════════════════════════════════

def scan_image_to_invoices(
    image_bytes:  bytes,
    filename:     str,
    invoice_type: str = "purchase",
    our_gstin:    str = "",
    period:       str = "",
) -> list:
    """
    Scan image bytes and return Invoice model objects.
    Signature identical to existing code — drop-in replacement.
    """
    from app.models.invoice import Invoice, InvoiceType

    inv_type = InvoiceType.SALE if invoice_type in ("sale", "sales") else InvoiceType.PURCHASE

    # ── Detect language from filename or default to auto ──────
    ocr_language = _detect_language_from_filename(filename)

    # ── 1. Try OCR module engines ─────────────────────────────
    router = OCRRouter.build()
    result: Optional[OCRResult] = router.route(image_bytes, ocr_language)

    # ── 2. Tesseract fallback ─────────────────────────────────
    if result is None or not result.is_usable():
        logger.info("Falling back to Tesseract for %s", filename)
        raw = _tesseract_extract(image_bytes)
        if raw.get("ocr_confidence") == "failed":
            return []
        return _raw_dict_to_invoices(raw, inv_type, our_gstin, period, filename)

    # ── 3. OCRResult → Invoice ────────────────────────────────
    if not result.success:
        return []

    try:
        ext = result.extracted
        invoice = Invoice(
            invoice_type  = inv_type,
            invoice_number= ext.invoice_number or f"OCR-{filename[:10]}",
            our_gstin     = our_gstin,
            period        = period,
            party_name    = ext.party_name,
            party_gstin   = ext.party_gstin,
            taxable_value = ext.taxable_value,
            igst          = ext.igst,
            cgst          = ext.cgst,
            sgst          = ext.sgst,
            invoice_date  = ext.invoice_date,
            hsn_code      = ext.hsn_code,
            irn           = ext.irn,
        )
        return [invoice]
    except Exception as exc:
        logger.warning("Skip OCR invoice (%s): %s", filename, exc)
        return []


# ═══════════════════════════════════════════════════════════════
#  LEGACY API — kept for any code that calls these directly
# ═══════════════════════════════════════════════════════════════

def extract_invoice_from_image(image_bytes: bytes, languages: str = "eng") -> Dict:
    """Legacy function — still works. Returns raw dict (same shape as before)."""
    # Try new engine first
    lang = _LANG_MAP.get(languages, OCRLanguage.AUTO)
    router = OCRRouter.build()
    result = router.route(image_bytes, lang)

    if result and result.is_usable():
        return _ocr_result_to_raw_dict(result)

    # Fallback to Tesseract
    return _tesseract_extract(image_bytes)


def scan_multiple_images(image_files: List[tuple], languages: str = "eng") -> List[Dict]:
    """Scan multiple invoice images. Signature unchanged."""
    results = []
    for filename, file_bytes in image_files:
        try:
            invoice = extract_invoice_from_image(file_bytes, languages)
            invoice["source_file"] = filename
            results.append(invoice)
        except Exception as e:
            logger.warning("Failed to scan %s: %s", filename, e)
            results.append({
                "source_file":      filename,
                "error":            str(e),
                "ocr_confidence":   "failed",
            })
    return results


# ═══════════════════════════════════════════════════════════════
#  TESSERACT FALLBACK (preserved from original)
# ═══════════════════════════════════════════════════════════════

def extract_text_google_vision(image_bytes: bytes) -> str:
    """
    Direct Google Vision call — kept for backward compat.
    New code should use OCRRouter instead.
    """
    from app.services.ocr.google_vision import GoogleVisionOCR
    engine = GoogleVisionOCR()
    result = engine._call_api(image_bytes, OCRLanguage.AUTO)
    if result:
        responses = result.get("responses", [{}])
        return responses[0].get("fullTextAnnotation", {}).get("text", "") if responses else ""
    raise ValueError("Google Vision API call failed.")


def extract_text_tesseract(image_bytes: bytes) -> str:
    """Direct Tesseract call — kept for backward compat."""
    if not TESSERACT_AVAILABLE:
        raise ValueError("Tesseract not available")
    img  = Image.open(io.BytesIO(image_bytes))
    proc = _preprocess(img)
    text = pytesseract.image_to_string(proc, lang="eng", config='--psm 6 --oem 3')
    if not GSTIN_RE.search(text) and not re.search(r'\d{3,}', text):
        text_multi = pytesseract.image_to_string(proc, lang="eng+hin+mar", config='--psm 6 --oem 3')
        if len(text_multi) > len(text):
            text = text_multi
    return text


def extract_text_from_image(image_bytes: bytes) -> str:
    """Google Vision first, Tesseract fallback — kept for backward compat."""
    api_key = os.getenv("GOOGLE_VISION_API_KEY", "")
    if api_key:
        try:
            text = extract_text_google_vision(image_bytes)
            if text and len(text) > 20:
                return text
        except Exception as e:
            logger.warning("Google Vision failed → Tesseract: %s", e)
    if TESSERACT_AVAILABLE:
        return extract_text_tesseract(image_bytes)
    raise ValueError("No OCR engine available.")


# ═══════════════════════════════════════════════════════════════
#  INTERNAL HELPERS
# ═══════════════════════════════════════════════════════════════

def _detect_language_from_filename(filename: str) -> OCRLanguage:
    """Infer language hint from filename convention."""
    fname = filename.lower()
    if any(k in fname for k in ("_mr", "_marathi", "-mr-")):
        return OCRLanguage.MARATHI
    if any(k in fname for k in ("_hi", "_hindi", "-hi-")):
        return OCRLanguage.HINDI
    return OCRLanguage.AUTO


def _preprocess(image: "Image.Image") -> "Image.Image":
    """Tesseract preprocessing — same as original."""
    img = image.convert('L')
    w, h = img.size
    if w < 1200:
        img = img.resize((int(w * 1200 / w), int(h * 1200 / w)), Image.LANCZOS)
    img = ImageEnhance.Contrast(img).enhance(1.8)
    img = ImageEnhance.Sharpness(img).enhance(2.0)
    img = img.point(lambda x: 255 if x > 150 else 0)
    return img


def _tesseract_extract(image_bytes: bytes) -> Dict:
    """
    Run Tesseract and return raw dict — same shape as original
    _parse_invoice_from_text() output.
    """
    if not TESSERACT_AVAILABLE:
        return {"ocr_confidence": "failed", "error": "Tesseract not available"}

    try:
        text = extract_text_tesseract(image_bytes)
        return _parse_invoice_from_text(text, source="tesseract_fallback")
    except Exception as exc:
        logger.warning("Tesseract failed: %s", exc)
        return {"ocr_confidence": "failed", "error": str(exc)}


def _parse_invoice_from_text(text: str, source: str = "image_ocr") -> Dict:
    """Exact copy of original _parse_invoice_from_text() — unchanged."""
    invoice = {
        "invoice_number": None, "date": None, "party_name": None,
        "party_gstin": None, "taxable_value": 0.0, "igst": 0.0,
        "cgst": 0.0, "sgst": 0.0, "total_amount": 0.0,
        "hsn_code": None, "ocr_text": text[:1500],
        "ocr_confidence": "low", "source": source,
    }
    gstins = [g.upper() for g in GSTIN_RE.findall(text)]
    if gstins:
        invoice["party_gstin"] = gstins[0]

    m = INVOICE_RE.search(text)
    invoice["invoice_number"] = m.group(1).strip() if m else (
        INV_RE2.search(text).group(0).upper() if INV_RE2.search(text) else None
    )
    m = DATE_RE2.search(text) or DATE_RE.search(text)
    if m:
        invoice["date"] = m.group(1)

    m = SUBTOTAL_RE.search(text)
    if m:
        invoice["taxable_value"] = _clean_amount(m.group(1))

    m = TOTAL_RE.search(text)
    if m:
        invoice["total_amount"] = _clean_amount(m.group(1))

    taxable = invoice["taxable_value"]
    for regex, key in [(CGST_RE, "cgst"), (SGST_RE, "sgst"), (IGST_RE, "igst")]:
        m = regex.search(text)
        if m:
            v = _clean_amount(m.group(1))
            if taxable == 0 or v < taxable:
                invoice[key] = v

    if invoice["total_amount"] == 0 and invoice["taxable_value"] > 0:
        invoice["total_amount"] = (
            invoice["taxable_value"] + invoice["igst"]
            + invoice["cgst"] + invoice["sgst"]
        )

    lines = text.split('\n')
    for i, line in enumerate(lines):
        if HSN_RE.search(line):
            area = '\n'.join(lines[max(0, i): i + 5])
            hsn8 = re.findall(r'\b(\d{8})\b', area)
            if hsn8:
                invoice["hsn_code"] = hsn8[0]; break
            hsn4 = re.findall(r'\b(\d{4})\b', area)
            if hsn4:
                invoice["hsn_code"] = hsn4[0]; break

    m = PARTY_RE.search(text)
    if m:
        name = m.group(1).strip().split('\n')[0].strip()
        if 3 < len(name) < 100:
            invoice["party_name"] = name

    fields_ok = sum(1 for v in [
        invoice["invoice_number"],
        invoice["party_gstin"],
        invoice["taxable_value"] > 0,
        invoice["date"],
        (invoice["cgst"] > 0 or invoice["igst"] > 0 or invoice["sgst"] > 0),
    ] if v)
    invoice["ocr_confidence"] = "high" if fields_ok >= 4 else "medium" if fields_ok >= 2 else "low"
    return invoice


def _raw_dict_to_invoices(
    raw:          Dict,
    inv_type:     "InvoiceType",
    our_gstin:    str,
    period:       str,
    filename:     str,
) -> list:
    """Convert raw dict (Tesseract output) to Invoice objects."""
    from app.models.invoice import Invoice
    if raw.get("ocr_confidence") == "failed":
        return []
    try:
        invoice = Invoice(
            invoice_type  = inv_type,
            invoice_number= raw.get("invoice_number") or f"OCR-{filename[:10]}",
            our_gstin     = our_gstin,
            period        = period,
            party_name    = raw.get("party_name"),
            party_gstin   = raw.get("party_gstin"),
            taxable_value = raw.get("taxable_value", 0),
            igst          = raw.get("igst", 0),
            cgst          = raw.get("cgst", 0),
            sgst          = raw.get("sgst", 0),
            invoice_date  = None,
            hsn_code      = raw.get("hsn_code"),
        )
        return [invoice]
    except Exception as exc:
        logger.warning("Skip OCR invoice: %s", exc)
        return []


def _ocr_result_to_raw_dict(result: OCRResult) -> Dict:
    """Convert OCRResult → legacy raw dict shape (for extract_invoice_from_image)."""
    ext = result.extracted
    confidence_map = {"high": "high", "medium": "medium", "low": "low"}
    return {
        "invoice_number":  ext.invoice_number,
        "date":            str(ext.invoice_date) if ext.invoice_date else None,
        "party_name":      ext.party_name,
        "party_gstin":     ext.party_gstin,
        "taxable_value":   ext.taxable_value,
        "igst":            ext.igst,
        "cgst":            ext.cgst,
        "sgst":            ext.sgst,
        "total_amount":    ext.total_amount,
        "hsn_code":        ext.hsn_code,
        "ocr_text":        result.raw_text[:1500],
        "ocr_confidence":  result.confidence_label.value,
        "source":          f"ocr_module:{result.provider.value}",
    }