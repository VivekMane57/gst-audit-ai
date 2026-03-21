"""
pdf_parser.py — Extract invoice data from PDF files
=====================================================
Location: app/services/pdf_parser.py

Handles:
  - Text-based PDFs (digital invoices)
  - Table-based PDFs (Tally/Busy PDF exports)
  - Multi-page PDFs
  - Extracts: GSTIN, Invoice No, Date, Amount, Tax

Dependencies:
  pip install pdfplumber --break-system-packages
"""

import re
import io
import logging
from typing import List, Dict, Optional
from datetime import date

logger = logging.getLogger(__name__)

try:
    import pdfplumber
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False
    logger.warning("pdfplumber not installed. PDF parsing disabled. Run: pip install pdfplumber")


# ═══════════════════════════════════════════════════════════════
#  REGEX PATTERNS for data extraction
# ═══════════════════════════════════════════════════════════════

GSTIN_RE = re.compile(r'\b(\d{2}[A-Z]{5}\d{4}[A-Z][A-Z\d]Z[A-Z\d])\b')
INVOICE_RE = re.compile(r'(?:Invoice\s*(?:No|Number|#)?\.?\s*[:;]?\s*)([A-Za-z0-9/\-_]+)', re.IGNORECASE)
DATE_RE = re.compile(r'\b(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})\b')
AMOUNT_RE = re.compile(r'(?:Total|Grand\s*Total|Net\s*Amount|Taxable\s*Value|Amount)[\s:₹]*([0-9,]+\.?\d*)', re.IGNORECASE)
IGST_RE = re.compile(r'(?:IGST|Integrated\s*Tax)[\s:₹]*([0-9,]+\.?\d*)', re.IGNORECASE)
CGST_RE = re.compile(r'(?:CGST|Central\s*Tax)[\s:₹]*([0-9,]+\.?\d*)', re.IGNORECASE)
SGST_RE = re.compile(r'(?:SGST|State\s*Tax|UTGST)[\s:₹]*([0-9,]+\.?\d*)', re.IGNORECASE)
HSN_RE = re.compile(r'(?:HSN|SAC)[\s:]*(\d{4,8})', re.IGNORECASE)
PARTY_RE = re.compile(r'(?:Bill\s*To|Sold\s*To|Buyer|Customer|Party|Recipient)[\s:]*(.+)', re.IGNORECASE)


def _clean_amount(text: str) -> float:
    """Clean amount string to float."""
    try:
        return float(text.replace(',', '').replace('₹', '').strip())
    except (ValueError, TypeError):
        return 0.0


def _find_first(pattern: re.Pattern, text: str) -> Optional[str]:
    """Find first match of pattern in text."""
    match = pattern.search(text)
    return match.group(1).strip() if match else None


def _find_all(pattern: re.Pattern, text: str) -> List[str]:
    """Find all matches of pattern in text."""
    return [m.strip() for m in pattern.findall(text)]


# ═══════════════════════════════════════════════════════════════
#  EXTRACT FROM TEXT
# ═══════════════════════════════════════════════════════════════

def extract_invoice_from_text(text: str) -> Dict:
    """Extract invoice data from raw text."""
    invoice = {
        "invoice_number": None,
        "date": None,
        "party_name": None,
        "party_gstin": None,
        "our_gstin": None,
        "taxable_value": 0.0,
        "igst": 0.0,
        "cgst": 0.0,
        "sgst": 0.0,
        "total_amount": 0.0,
        "hsn_code": None,
        "raw_text": text[:500],
    }

    # Extract GSTINs — first is usually seller, second is buyer
    gstins = _find_all(GSTIN_RE, text)
    if len(gstins) >= 2:
        invoice["our_gstin"] = gstins[0]
        invoice["party_gstin"] = gstins[1]
    elif len(gstins) == 1:
        invoice["party_gstin"] = gstins[0]

    # Invoice number
    invoice["invoice_number"] = _find_first(INVOICE_RE, text)

    # Date
    date_str = _find_first(DATE_RE, text)
    if date_str:
        invoice["date"] = date_str

    # Amounts
    amount_str = _find_first(AMOUNT_RE, text)
    if amount_str:
        invoice["taxable_value"] = _clean_amount(amount_str)

    igst_str = _find_first(IGST_RE, text)
    if igst_str:
        invoice["igst"] = _clean_amount(igst_str)

    cgst_str = _find_first(CGST_RE, text)
    if cgst_str:
        invoice["cgst"] = _clean_amount(cgst_str)

    sgst_str = _find_first(SGST_RE, text)
    if sgst_str:
        invoice["sgst"] = _clean_amount(sgst_str)

    # Total
    total = invoice["taxable_value"] + invoice["igst"] + invoice["cgst"] + invoice["sgst"]
    invoice["total_amount"] = total if total > 0 else invoice["taxable_value"]

    # HSN
    invoice["hsn_code"] = _find_first(HSN_RE, text)

    # Party name
    invoice["party_name"] = _find_first(PARTY_RE, text)

    return invoice


# ═══════════════════════════════════════════════════════════════
#  EXTRACT FROM TABLES
# ═══════════════════════════════════════════════════════════════

def extract_invoices_from_table(table: list) -> List[Dict]:
    """Extract invoice rows from a PDF table."""
    if not table or len(table) < 2:
        return []

    # First row = headers
    headers = [str(h).lower().strip() if h else "" for h in table[0]]

    # Find column indices
    col_map = {}
    for idx, h in enumerate(headers):
        if any(k in h for k in ["invoice", "bill", "voucher", "inv"]):
            col_map["invoice_number"] = idx
        elif any(k in h for k in ["gstin", "gst"]):
            col_map["party_gstin"] = idx
        elif any(k in h for k in ["taxable", "amount", "value", "total"]):
            col_map["taxable_value"] = idx
        elif any(k in h for k in ["igst", "integrated"]):
            col_map["igst"] = idx
        elif any(k in h for k in ["cgst", "central"]):
            col_map["cgst"] = idx
        elif any(k in h for k in ["sgst", "state", "utgst"]):
            col_map["sgst"] = idx
        elif any(k in h for k in ["date"]):
            col_map["date"] = idx
        elif any(k in h for k in ["party", "name", "customer", "supplier"]):
            col_map["party_name"] = idx
        elif any(k in h for k in ["hsn", "sac"]):
            col_map["hsn_code"] = idx

    invoices = []
    for row in table[1:]:
        if not row or all(not cell for cell in row):
            continue

        inv = {}
        for field, idx in col_map.items():
            if idx < len(row) and row[idx]:
                val = str(row[idx]).strip()
                if field in ("taxable_value", "igst", "cgst", "sgst"):
                    inv[field] = _clean_amount(val)
                else:
                    inv[field] = val

        if inv.get("invoice_number") or inv.get("taxable_value"):
            invoices.append(inv)

    return invoices


# ═══════════════════════════════════════════════════════════════
#  MAIN: PARSE PDF
# ═══════════════════════════════════════════════════════════════

def parse_pdf(file_bytes: bytes, filename: str = "invoice.pdf") -> List[Dict]:
    """
    Parse PDF file and extract invoice data.

    Args:
        file_bytes: Raw PDF bytes
        filename: Original filename

    Returns:
        List of invoice dicts with extracted data
    """
    if not PDF_AVAILABLE:
        raise ValueError("PDF parsing not available. Install pdfplumber: pip install pdfplumber")

    logger.info(f"Parsing PDF: {filename}")

    all_invoices = []
    full_text = ""

    try:
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for page_num, page in enumerate(pdf.pages, 1):
                # Extract text
                page_text = page.extract_text() or ""
                full_text += page_text + "\n"

                # Extract tables
                tables = page.extract_tables() or []
                for table in tables:
                    table_invoices = extract_invoices_from_table(table)
                    if table_invoices:
                        all_invoices.extend(table_invoices)
                        logger.info(f"Page {page_num}: Found {len(table_invoices)} invoices in table")

        # If no tables found, try text extraction
        if not all_invoices and full_text.strip():
            text_invoice = extract_invoice_from_text(full_text)
            if text_invoice.get("invoice_number") or text_invoice.get("party_gstin"):
                all_invoices.append(text_invoice)
                logger.info(f"Extracted 1 invoice from text")

        logger.info(f"PDF parsed: {len(all_invoices)} invoices from {filename}")
        return all_invoices

    except Exception as e:
        logger.error(f"PDF parse error: {e}")
        raise ValueError(f"Cannot parse PDF: {e}")


def parse_pdf_to_invoices(
    file_bytes: bytes,
    filename: str,
    invoice_type: str = "purchase",
    our_gstin: str = "",
    period: str = "",
) -> list:
    """
    Parse PDF and convert to Invoice objects (same as excel_parser output).
    Can be used directly in audit router.
    """
    from app.models.invoice import Invoice, InvoiceType

    inv_type = InvoiceType.SALE if invoice_type in ("sale", "sales") else InvoiceType.PURCHASE

    raw_invoices = parse_pdf(file_bytes, filename)

    invoices = []
    for raw in raw_invoices:
        try:
            inv_no = raw.get("invoice_number") or f"PDF-{len(invoices)+1}"

            invoice = Invoice(
                invoice_type=inv_type,
                invoice_number=inv_no,
                our_gstin=our_gstin or raw.get("our_gstin", ""),
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
            invoices.append(invoice)
        except Exception as e:
            logger.warning(f"Skip PDF invoice: {e}")

    logger.info(f"PDF → {len(invoices)} Invoice objects")
    return invoices