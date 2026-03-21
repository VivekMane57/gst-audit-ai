"""
ocr_scanner.py — Extract invoice data from images (photos, scans)
===================================================================
Location: app/services/ocr_scanner.py

Handles:
  - Phone photos of invoices
  - Scanned bills
  - WhatsApp images
  - Handwritten bills (partial — depends on handwriting quality)
  - Hindi/Marathi text bills

Dependencies:
  pip install pytesseract Pillow --break-system-packages
  Also install Tesseract OCR:
    Ubuntu: sudo apt install tesseract-ocr tesseract-ocr-hin tesseract-ocr-mar
    Windows: Download from https://github.com/UB-Mannheim/tesseract/wiki
    Railway: Add to Dockerfile or nixpacks
"""

import re
import io
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

try:
    import pytesseract
    from PIL import Image, ImageEnhance, ImageFilter
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False
    logger.warning("pytesseract/Pillow not installed. OCR disabled. Run: pip install pytesseract Pillow")


# ═══════════════════════════════════════════════════════════════
#  REGEX PATTERNS (same as pdf_parser)
# ═══════════════════════════════════════════════════════════════

GSTIN_RE = re.compile(r'\b(\d{2}[A-Z]{5}\d{4}[A-Z][A-Z\d]Z[A-Z\d])\b')
INVOICE_RE = re.compile(r'(?:Invoice\s*(?:No|Number|#)?\.?\s*[:;]?\s*)([A-Za-z0-9/\-_]+)', re.IGNORECASE)
DATE_RE = re.compile(r'\b(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})\b')
AMOUNT_RE = re.compile(r'(?:Total|Grand\s*Total|Net|Taxable|Amount)[\s:₹]*([0-9,]+\.?\d*)', re.IGNORECASE)
IGST_RE = re.compile(r'(?:IGST|Integrated)[\s:₹]*([0-9,]+\.?\d*)', re.IGNORECASE)
CGST_RE = re.compile(r'(?:CGST|Central\s*Tax)[\s:₹]*([0-9,]+\.?\d*)', re.IGNORECASE)
SGST_RE = re.compile(r'(?:SGST|State\s*Tax)[\s:₹]*([0-9,]+\.?\d*)', re.IGNORECASE)
HSN_RE = re.compile(r'(?:HSN|SAC)[\s:]*(\d{4,8})', re.IGNORECASE)

# Hindi/Marathi patterns
HINDI_INVOICE_RE = re.compile(r'(?:बिल\s*(?:नं|क्र|नंबर)?\.?\s*[:;]?\s*)([A-Za-z0-9/\-_]+)', re.IGNORECASE)
HINDI_AMOUNT_RE = re.compile(r'(?:कुल|योग|रकम|राशि|रक्कम)[\s:₹]*([0-9,]+\.?\d*)', re.IGNORECASE)


def _clean_amount(text: str) -> float:
    try:
        return float(text.replace(',', '').replace('₹', '').strip())
    except (ValueError, TypeError):
        return 0.0


# ═══════════════════════════════════════════════════════════════
#  IMAGE PREPROCESSING (improve OCR accuracy)
# ═══════════════════════════════════════════════════════════════

def preprocess_image(image: Image.Image) -> Image.Image:
    """
    Preprocess image for better OCR accuracy.
    Handles: poor lighting, blur, rotation, noise.
    """
    # Convert to grayscale
    img = image.convert('L')

    # Increase contrast
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(2.0)

    # Increase sharpness
    enhancer = ImageEnhance.Sharpness(img)
    img = enhancer.enhance(2.0)

    # Remove noise
    img = img.filter(ImageFilter.MedianFilter(size=3))

    # Binarize (black and white)
    threshold = 140
    img = img.point(lambda x: 255 if x > threshold else 0)

    # Resize if too small (OCR works better on larger images)
    width, height = img.size
    if width < 1000:
        scale = 1000 / width
        img = img.resize((int(width * scale), int(height * scale)), Image.LANCZOS)

    return img


# ═══════════════════════════════════════════════════════════════
#  OCR TEXT EXTRACTION
# ═══════════════════════════════════════════════════════════════

def extract_text_from_image(
    image_bytes: bytes,
    languages: str = "eng+hin+mar",
) -> str:
    """
    Extract text from image using Tesseract OCR.

    Args:
        image_bytes: Raw image bytes
        languages: Tesseract language codes (eng, hin, mar)

    Returns:
        Extracted text string
    """
    if not OCR_AVAILABLE:
        raise ValueError("OCR not available. Install pytesseract and Pillow.")

    try:
        image = Image.open(io.BytesIO(image_bytes))

        # Preprocess for better accuracy
        processed = preprocess_image(image)

        # Run OCR with multiple languages
        text = pytesseract.image_to_string(
            processed,
            lang=languages,
            config='--psm 6 --oem 3',
        )

        logger.info(f"OCR extracted {len(text)} characters")
        return text

    except Exception as e:
        logger.error(f"OCR extraction failed: {e}")
        raise ValueError(f"Cannot extract text from image: {e}")


# ═══════════════════════════════════════════════════════════════
#  INVOICE DATA EXTRACTION FROM OCR TEXT
# ═══════════════════════════════════════════════════════════════

def extract_invoice_from_image(
    image_bytes: bytes,
    languages: str = "eng+hin+mar",
) -> Dict:
    """
    Extract invoice data from image.

    Returns dict with: invoice_number, party_gstin, taxable_value,
    igst, cgst, sgst, date, hsn_code, party_name
    """
    text = extract_text_from_image(image_bytes, languages)

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
        "ocr_text": text[:1000],
        "ocr_confidence": "medium",
        "source": "image_ocr",
    }

    # GSTIN
    gstins = GSTIN_RE.findall(text)
    if gstins:
        invoice["party_gstin"] = gstins[0]

    # Invoice number — try English then Hindi
    inv_match = INVOICE_RE.search(text)
    if not inv_match:
        inv_match = HINDI_INVOICE_RE.search(text)
    if inv_match:
        invoice["invoice_number"] = inv_match.group(1).strip()

    # Date
    date_match = DATE_RE.search(text)
    if date_match:
        invoice["date"] = date_match.group(1)

    # Amounts — English
    amount_match = AMOUNT_RE.search(text)
    if amount_match:
        invoice["taxable_value"] = _clean_amount(amount_match.group(1))

    # Amounts — Hindi/Marathi fallback
    if invoice["taxable_value"] == 0:
        hindi_amount = HINDI_AMOUNT_RE.search(text)
        if hindi_amount:
            invoice["taxable_value"] = _clean_amount(hindi_amount.group(1))

    # Tax amounts
    igst_match = IGST_RE.search(text)
    if igst_match:
        invoice["igst"] = _clean_amount(igst_match.group(1))

    cgst_match = CGST_RE.search(text)
    if cgst_match:
        invoice["cgst"] = _clean_amount(cgst_match.group(1))

    sgst_match = SGST_RE.search(text)
    if sgst_match:
        invoice["sgst"] = _clean_amount(sgst_match.group(1))

    # HSN
    hsn_match = HSN_RE.search(text)
    if hsn_match:
        invoice["hsn_code"] = hsn_match.group(1)

    # Total
    total = invoice["taxable_value"] + invoice["igst"] + invoice["cgst"] + invoice["sgst"]
    invoice["total_amount"] = total if total > 0 else invoice["taxable_value"]

    # Confidence based on fields found
    fields_found = sum(1 for v in [
        invoice["invoice_number"], invoice["party_gstin"],
        invoice["taxable_value"], invoice["date"]
    ] if v)
    invoice["ocr_confidence"] = (
        "high" if fields_found >= 3 else
        "medium" if fields_found >= 2 else
        "low"
    )

    return invoice


# ═══════════════════════════════════════════════════════════════
#  BATCH: MULTIPLE IMAGES
# ═══════════════════════════════════════════════════════════════

def scan_multiple_images(
    image_files: List[tuple],
    languages: str = "eng+hin+mar",
) -> List[Dict]:
    """
    Scan multiple invoice images.

    Args:
        image_files: List of (filename, bytes) tuples

    Returns:
        List of extracted invoice dicts
    """
    results = []
    for filename, file_bytes in image_files:
        try:
            invoice = extract_invoice_from_image(file_bytes, languages)
            invoice["source_file"] = filename
            results.append(invoice)
            logger.info(f"Scanned {filename}: GSTIN={invoice.get('party_gstin')}, Amount={invoice.get('taxable_value')}")
        except Exception as e:
            logger.warning(f"Failed to scan {filename}: {e}")
            results.append({
                "source_file": filename,
                "error": str(e),
                "ocr_confidence": "failed",
            })

    return results


# ═══════════════════════════════════════════════════════════════
#  CONVERT TO INVOICE OBJECTS
# ═══════════════════════════════════════════════════════════════

def scan_image_to_invoices(
    image_bytes: bytes,
    filename: str,
    invoice_type: str = "purchase",
    our_gstin: str = "",
    period: str = "",
) -> list:
    """
    Scan image and convert to Invoice objects.
    Can be used directly in audit router.
    """
    from app.models.invoice import Invoice, InvoiceType

    inv_type = InvoiceType.SALE if invoice_type in ("sale", "sales") else InvoiceType.PURCHASE

    raw = extract_invoice_from_image(image_bytes)

    if raw.get("ocr_confidence") == "failed":
        return []

    try:
        inv_no = raw.get("invoice_number") or f"OCR-{filename[:10]}"

        invoice = Invoice(
            invoice_type=inv_type,
            invoice_number=inv_no,
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