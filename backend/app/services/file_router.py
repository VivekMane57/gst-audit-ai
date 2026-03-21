"""
file_router.py — Smart file type detection + routing to correct parser
========================================================================
Location: app/services/file_router.py

Detects file type from extension + content and routes to:
  - Excel parser (.xlsx, .xls, .csv)
  - PDF parser (.pdf)
  - Image OCR (.jpg, .jpeg, .png, .webp)
  - Tally XML parser (.xml)

Usage:
  from app.services.file_router import parse_any_file
  invoices = parse_any_file(file_bytes, filename, invoice_type, our_gstin, period)
"""

import logging
from typing import List

logger = logging.getLogger(__name__)

# File type detection
EXCEL_EXTENSIONS = {".xlsx", ".xls", ".csv", ".tsv"}
PDF_EXTENSIONS = {".pdf"}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff", ".tif"}
XML_EXTENSIONS = {".xml"}

# Magic bytes for content detection
MAGIC_BYTES = {
    b"%PDF": "pdf",
    b"\xff\xd8\xff": "jpeg",
    b"\x89PNG": "png",
    b"PK": "xlsx",  # ZIP-based (xlsx is a ZIP)
    b"<?xml": "xml",
    b"<ENVELOPE": "tally_xml",
    b"<TALLYMESSAGE": "tally_xml",
}


def _detect_file_type(filename: str, file_bytes: bytes) -> str:
    """
    Detect file type from extension and content.
    Returns: "excel", "pdf", "image", "tally_xml", "xml", "unknown"
    """
    ext = ""
    if filename and "." in filename:
        ext = "." + filename.rsplit(".", 1)[-1].lower()

    # Extension-based detection
    if ext in EXCEL_EXTENSIONS:
        return "excel"
    if ext in PDF_EXTENSIONS:
        return "pdf"
    if ext in IMAGE_EXTENSIONS:
        return "image"
    if ext in XML_EXTENSIONS:
        # Check if it's Tally XML
        header = file_bytes[:500].decode("utf-8", errors="ignore").upper()
        if any(k in header for k in ["ENVELOPE", "TALLYMESSAGE", "VOUCHER", "VCHTYPE"]):
            return "tally_xml"
        return "xml"

    # Content-based detection (magic bytes)
    for magic, ftype in MAGIC_BYTES.items():
        if file_bytes[:len(magic)] == magic:
            if ftype in ("xlsx",):
                return "excel"
            if ftype == "pdf":
                return "pdf"
            if ftype in ("jpeg", "png"):
                return "image"
            if ftype in ("tally_xml", "xml"):
                header = file_bytes[:500].decode("utf-8", errors="ignore").upper()
                if any(k in header for k in ["ENVELOPE", "TALLYMESSAGE", "VOUCHER"]):
                    return "tally_xml"
                return "xml"

    logger.warning(f"Unknown file type: {filename} (ext={ext})")
    return "unknown"


def parse_any_file(
    file_bytes: bytes,
    filename: str,
    invoice_type: str = "purchase",
    our_gstin: str = "",
    period: str = "",
) -> list:
    """
    Smart parser — detects file type and routes to correct parser.

    Args:
        file_bytes: Raw file bytes
        filename: Original filename
        invoice_type: "sale" or "purchase"
        our_gstin: Company GSTIN
        period: Audit period

    Returns:
        List of Invoice objects
    """
    file_type = _detect_file_type(filename, file_bytes)
    logger.info(f"File: {filename} → Detected type: {file_type}")

    if file_type == "excel":
        from app.services.excel_parser import parse_from_bytes
        return parse_from_bytes(
            file_bytes,
            filename=filename,
            invoice_type=invoice_type,
            our_gstin=our_gstin,
            period=period,
        )

    elif file_type == "pdf":
        from app.services.pdf_parser import parse_pdf_to_invoices
        return parse_pdf_to_invoices(
            file_bytes,
            filename=filename,
            invoice_type=invoice_type,
            our_gstin=our_gstin,
            period=period,
        )

    elif file_type == "image":
        from app.services.ocr_scanner import scan_image_to_invoices
        return scan_image_to_invoices(
            file_bytes,
            filename=filename,
            invoice_type=invoice_type,
            our_gstin=our_gstin,
            period=period,
        )

    elif file_type == "tally_xml":
        from app.services.tally_parser import parse_tally_xml
        return parse_tally_xml(
            file_bytes,
            our_gstin=our_gstin,
            period=period,
            filename=filename,
        )

    else:
        # Try Excel as fallback
        logger.warning(f"Unknown type for {filename}, trying Excel parser")
        try:
            from app.services.excel_parser import parse_from_bytes
            return parse_from_bytes(
                file_bytes,
                filename=filename,
                invoice_type=invoice_type,
                our_gstin=our_gstin,
                period=period,
            )
        except Exception as e:
            logger.error(f"Fallback Excel parse failed: {e}")
            raise ValueError(
                f"Unsupported file format: {filename}. "
                f"Supported: Excel (.xlsx/.csv), PDF, Images (.jpg/.png), Tally XML"
            )


def get_supported_formats() -> dict:
    """Return supported file formats and their status."""
    pdf_ok = False
    ocr_ok = False
    xml_ok = False

    try:
        import pdfplumber
        pdf_ok = True
    except ImportError:
        pass

    try:
        import pytesseract
        from PIL import Image
        ocr_ok = True
    except ImportError:
        pass

    try:
        from lxml import etree
        xml_ok = True
    except ImportError:
        pass

    return {
        "excel": {"supported": True, "extensions": [".xlsx", ".xls", ".csv"]},
        "pdf": {"supported": pdf_ok, "extensions": [".pdf"]},
        "image": {"supported": ocr_ok, "extensions": [".jpg", ".jpeg", ".png", ".webp"]},
        "tally_xml": {"supported": xml_ok, "extensions": [".xml"]},
    }