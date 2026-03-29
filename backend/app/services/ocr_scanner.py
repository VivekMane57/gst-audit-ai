"""
ocr_scanner.py — Extract invoice data from images
===================================================
Location: app/services/ocr_scanner.py

Priority:
  1. Google Cloud Vision API (95%+ accuracy)
  2. Tesseract OCR (fallback — works offline)

Setup:
  .env mein: GOOGLE_VISION_API_KEY=AIzaSy...
  pip install pytesseract Pillow requests
"""

import re
import io
import os
import base64
import logging
import requests
from typing import Dict, List

logger = logging.getLogger(__name__)

try:
    import pytesseract
    from PIL import Image, ImageEnhance
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False
    logger.warning("pytesseract/Pillow not installed. Tesseract fallback disabled.")

GOOGLE_VISION_API_KEY = os.getenv("GOOGLE_VISION_API_KEY", "")
GOOGLE_VISION_URL = "https://vision.googleapis.com/v1/images:annotate"


# ═══════════════════════════════════════════════════════════════
#  REGEX PATTERNS
# ═══════════════════════════════════════════════════════════════

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
#  GOOGLE CLOUD VISION API
# ═══════════════════════════════════════════════════════════════

def extract_text_google_vision(image_bytes: bytes) -> str:
    """Call Google Vision API — returns full OCR text."""
    if not GOOGLE_VISION_API_KEY:
        raise ValueError("GOOGLE_VISION_API_KEY not configured")

    payload = {
        "requests": [{
            "image": {"content": base64.b64encode(image_bytes).decode("utf-8")},
            "features": [{"type": "DOCUMENT_TEXT_DETECTION", "maxResults": 1}],
            "imageContext": {"languageHints": ["en", "hi", "mr"]}
        }]
    }

    resp = requests.post(
        f"{GOOGLE_VISION_URL}?key={GOOGLE_VISION_API_KEY}",
        json=payload,
        timeout=15
    )
    resp.raise_for_status()
    data = resp.json()

    responses = data.get("responses", [])
    if not responses:
        raise ValueError("Empty response from Google Vision")

    # DOCUMENT_TEXT_DETECTION result
    full_text = responses[0].get("fullTextAnnotation", {}).get("text", "")

    # Fallback to textAnnotations
    if not full_text:
        annotations = responses[0].get("textAnnotations", [])
        if annotations:
            full_text = annotations[0].get("description", "")

    # Check for API error
    if not full_text:
        err = responses[0].get("error", {})
        if err:
            raise ValueError(f"Vision API error: {err.get('message', 'Unknown')}")

    logger.info(f"Google Vision: {len(full_text)} chars extracted")
    return full_text


# ═══════════════════════════════════════════════════════════════
#  TESSERACT OCR — FALLBACK
# ═══════════════════════════════════════════════════════════════

def _preprocess(image: "Image.Image") -> "Image.Image":
    img = image.convert('L')
    w, h = img.size
    if w < 1200:
        img = img.resize((int(w * 1200 / w), int(h * 1200 / w)), Image.LANCZOS)
    img = ImageEnhance.Contrast(img).enhance(1.8)
    img = ImageEnhance.Sharpness(img).enhance(2.0)
    img = img.point(lambda x: 255 if x > 150 else 0)
    return img


def extract_text_tesseract(image_bytes: bytes) -> str:
    """Tesseract OCR fallback — English first approach."""
    if not TESSERACT_AVAILABLE:
        raise ValueError("Tesseract not available")

    img = Image.open(io.BytesIO(image_bytes))
    proc = _preprocess(img)

    text = pytesseract.image_to_string(proc, lang="eng", config='--psm 6 --oem 3')

    # If English weak, try multilingual
    if not GSTIN_RE.search(text) and not re.search(r'\d{3,}', text):
        logger.info("English weak, trying eng+hin+mar")
        text_multi = pytesseract.image_to_string(proc, lang="eng+hin+mar", config='--psm 6 --oem 3')
        if len(text_multi) > len(text):
            text = text_multi

    logger.info(f"Tesseract: {len(text)} chars extracted")
    return text


# ═══════════════════════════════════════════════════════════════
#  MAIN TEXT EXTRACTOR
# ═══════════════════════════════════════════════════════════════

def extract_text_from_image(image_bytes: bytes) -> str:
    """
    Google Vision first (95% accuracy), Tesseract fallback.
    """
    if GOOGLE_VISION_API_KEY:
        try:
            text = extract_text_google_vision(image_bytes)
            if text and len(text) > 20:
                return text
        except Exception as e:
            logger.warning(f"Google Vision failed → Tesseract fallback: {e}")

    if TESSERACT_AVAILABLE:
        return extract_text_tesseract(image_bytes)

    raise ValueError("No OCR engine available. Set GOOGLE_VISION_API_KEY or install Tesseract.")


# ═══════════════════════════════════════════════════════════════
#  PARSE INVOICE FROM TEXT
# ═══════════════════════════════════════════════════════════════

def _parse_invoice_from_text(text: str, source: str = "image_ocr") -> Dict:
    invoice = {
        "invoice_number": None,
        "date": None,
        "party_name": None,
        "party_gstin": None,
        "taxable_value": 0.0,
        "igst": 0.0,
        "cgst": 0.0,
        "sgst": 0.0,
        "total_amount": 0.0,
        "hsn_code": None,
        "ocr_text": text[:1500],
        "ocr_confidence": "low",
        "source": source,
    }

    # GSTIN
    gstins = [g.upper() for g in GSTIN_RE.findall(text)]
    if gstins:
        invoice["party_gstin"] = gstins[0]
        logger.info(f"GSTINs detected: {gstins}")

    # Invoice Number
    m = INVOICE_RE.search(text)
    invoice["invoice_number"] = m.group(1).strip() if m else (
        INV_RE2.search(text).group(0).upper() if INV_RE2.search(text) else None
    )

    # Date
    m = DATE_RE2.search(text) or DATE_RE.search(text)
    if m:
        invoice["date"] = m.group(1)

    # Subtotal
    m = SUBTOTAL_RE.search(text)
    if m:
        invoice["taxable_value"] = _clean_amount(m.group(1))

    # Total
    m = TOTAL_RE.search(text)
    if m:
        invoice["total_amount"] = _clean_amount(m.group(1))

    taxable = invoice["taxable_value"]

    # CGST
    m = CGST_RE.search(text)
    if m:
        v = _clean_amount(m.group(1))
        if taxable == 0 or v < taxable:
            invoice["cgst"] = v

    # SGST
    m = SGST_RE.search(text)
    if m:
        v = _clean_amount(m.group(1))
        if taxable == 0 or v < taxable:
            invoice["sgst"] = v

    # IGST
    m = IGST_RE.search(text)
    if m:
        v = _clean_amount(m.group(1))
        if taxable == 0 or v < taxable:
            invoice["igst"] = v

    # Calculate total if missing
    if invoice["total_amount"] == 0 and invoice["taxable_value"] > 0:
        invoice["total_amount"] = (
            invoice["taxable_value"] + invoice["igst"]
            + invoice["cgst"] + invoice["sgst"]
        )

    # HSN Code
    lines = text.split('\n')
    for i, line in enumerate(lines):
        if HSN_RE.search(line):
            area = '\n'.join(lines[max(0, i):i + 5])
            hsn8 = re.findall(r'\b(\d{8})\b', area)
            if hsn8:
                invoice["hsn_code"] = hsn8[0]
                break
            hsn4 = re.findall(r'\b(\d{4})\b', area)
            if hsn4:
                invoice["hsn_code"] = hsn4[0]
                break

    # Party Name
    m = PARTY_RE.search(text)
    if m:
        name = m.group(1).strip().split('\n')[0].strip()
        if 3 < len(name) < 100:
            invoice["party_name"] = name

    # Confidence score
    fields_ok = sum(1 for v in [
        invoice["invoice_number"],
        invoice["party_gstin"],
        invoice["taxable_value"] > 0,
        invoice["date"],
        (invoice["cgst"] > 0 or invoice["igst"] > 0 or invoice["sgst"] > 0),
    ] if v)

    invoice["ocr_confidence"] = (
        "high"   if fields_ok >= 4 else
        "medium" if fields_ok >= 2 else
        "low"
    )

    logger.info(
        f"OCR parsed: inv={invoice['invoice_number']}, "
        f"gstin={invoice['party_gstin']}, "
        f"taxable={invoice['taxable_value']}, "
        f"confidence={invoice['ocr_confidence']}"
    )
    return invoice


# ═══════════════════════════════════════════════════════════════
#  PUBLIC API
# ═══════════════════════════════════════════════════════════════

def extract_invoice_from_image(image_bytes: bytes, languages: str = "eng") -> Dict:
    """Main function — extract invoice data from image bytes."""
    text = extract_text_from_image(image_bytes)
    return _parse_invoice_from_text(text, source="image_ocr")


def scan_multiple_images(image_files: List[tuple], languages: str = "eng") -> List[Dict]:
    """Scan multiple invoice images."""
    results = []
    for filename, file_bytes in image_files:
        try:
            invoice = extract_invoice_from_image(file_bytes, languages)
            invoice["source_file"] = filename
            results.append(invoice)
        except Exception as e:
            logger.warning(f"Failed to scan {filename}: {e}")
            results.append({
                "source_file": filename,
                "error": str(e),
                "ocr_confidence": "failed"
            })
    return results


def scan_image_to_invoices(
    image_bytes: bytes,
    filename: str,
    invoice_type: str = "purchase",
    our_gstin: str = "",
    period: str = "",
) -> list:
    """Scan image and return Invoice model objects."""
    from app.models.invoice import Invoice, InvoiceType

    inv_type = InvoiceType.SALE if invoice_type in ("sale", "sales") else InvoiceType.PURCHASE
    raw = extract_invoice_from_image(image_bytes)

    if raw.get("ocr_confidence") == "failed":
        return []

    try:
        invoice = Invoice(
            invoice_type=inv_type,
            invoice_number=raw.get("invoice_number") or f"OCR-{filename[:10]}",
            our_gstin=our_gstin,
            period=period,
            party_name=raw.get("party_name"),
            party_gstin=raw.get("party_gstin"),
            taxable_value=raw.get("taxable_value", 0),
            igst=raw.get("igst", 0),
            cgst=raw.get("cgst", 0),
            sgst=raw.get("sgst", 0),
            invoice_date=None,
            hsn_code=raw.get("hsn_code"),
        )
        return [invoice]
    except Exception as e:
        logger.warning(f"Skip OCR invoice: {e}")
        return []