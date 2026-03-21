"""
tally_parser.py — Parse Tally Prime / ERP9 XML daybook exports
================================================================
Location: app/services/tally_parser.py

Handles:
  - Tally Prime XML daybook export
  - Tally ERP9 XML export
  - Extracts: Vouchers → Sales/Purchase invoices
  - Maps: Party name, GSTIN, amounts, tax breakup

Usage:
  from app.services.tally_parser import parse_tally_xml
  invoices = parse_tally_xml(xml_bytes, our_gstin="27XXXXX", period="2025-01")
"""

import re
import io
import logging
from typing import List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

try:
    from lxml import etree
    XML_AVAILABLE = True
except ImportError:
    XML_AVAILABLE = False
    logger.warning("lxml not installed. Tally XML parsing disabled.")


def _get_text(element, tag: str, default: str = "") -> str:
    """Safely get text from XML element."""
    el = element.find(tag)
    if el is not None and el.text:
        return el.text.strip()
    # Try case-insensitive
    for child in element:
        if child.tag and child.tag.upper() == tag.upper():
            return (child.text or "").strip()
    return default


def _get_float(element, tag: str, default: float = 0.0) -> float:
    """Safely get float from XML element."""
    text = _get_text(element, tag)
    if not text:
        return default
    try:
        # Tally sometimes uses negative for credit entries
        val = float(text.replace(",", "").strip())
        return abs(val)
    except (ValueError, TypeError):
        return default


def _parse_tally_date(date_str: str) -> Optional[str]:
    """Parse Tally date format (YYYYMMDD) to ISO date."""
    if not date_str or len(date_str) < 8:
        return None
    try:
        dt = datetime.strptime(date_str[:8], "%Y%m%d")
        return dt.strftime("%Y-%m-%d")
    except ValueError:
        return None


def _extract_gstin_from_text(text: str) -> Optional[str]:
    """Extract GSTIN from any text string."""
    match = re.search(r'\b(\d{2}[A-Z]{5}\d{4}[A-Z][A-Z\d]Z[A-Z\d])\b', text)
    return match.group(1) if match else None


def parse_tally_xml(
    xml_bytes: bytes,
    our_gstin: str = "",
    period: str = "",
    filename: str = "tally_export.xml",
) -> list:
    """
    Parse Tally XML daybook export and return Invoice objects.

    Args:
        xml_bytes: Raw XML file bytes
        our_gstin: Company GSTIN
        period: Audit period (e.g. "2025-01")
        filename: Original filename

    Returns:
        List of Invoice objects
    """
    if not XML_AVAILABLE:
        raise ValueError("XML parsing not available. Install lxml: pip install lxml")

    from app.models.invoice import Invoice, InvoiceType

    logger.info(f"Parsing Tally XML: {filename}")

    try:
        # Parse XML — handle encoding issues
        parser = etree.XMLParser(recover=True, encoding='utf-8')
        try:
            tree = etree.parse(io.BytesIO(xml_bytes), parser)
        except Exception:
            # Try with latin-1 encoding
            text = xml_bytes.decode('latin-1', errors='ignore')
            tree = etree.fromstring(text.encode('utf-8'), parser)

        root = tree.getroot() if hasattr(tree, 'getroot') else tree

        invoices = []
        voucher_count = 0

        # Find all vouchers — Tally uses VOUCHER or TALLYMESSAGE/VOUCHER
        voucher_paths = [
            ".//VOUCHER",
            ".//TALLYMESSAGE/VOUCHER",
            ".//BODY/DATA/TALLYMESSAGE/VOUCHER",
            ".//ENVELOPE/BODY/DATA/TALLYMESSAGE/VOUCHER",
        ]

        vouchers = []
        for path in voucher_paths:
            found = root.findall(path)
            if found:
                vouchers = found
                break

        # Also try case variations
        if not vouchers:
            for el in root.iter():
                if el.tag and el.tag.upper() == "VOUCHER":
                    vouchers.append(el)

        logger.info(f"Found {len(vouchers)} vouchers in XML")

        for voucher in vouchers:
            voucher_count += 1

            # Get voucher type
            vtype = (
                voucher.get("VCHTYPE", "") or
                _get_text(voucher, "VOUCHERTYPENAME") or
                _get_text(voucher, "VCHTYPE") or
                ""
            ).upper()

            # Determine if sale or purchase
            is_sale = any(k in vtype for k in ["SALES", "SALE", "TAX INVOICE", "DEBIT NOTE"])
            is_purchase = any(k in vtype for k in ["PURCHASE", "PURCH", "CREDIT NOTE"])

            if not is_sale and not is_purchase:
                continue

            inv_type = InvoiceType.SALE if is_sale else InvoiceType.PURCHASE

            # Invoice number
            inv_no = (
                _get_text(voucher, "VOUCHERNUMBER") or
                _get_text(voucher, "REFERENCE") or
                _get_text(voucher, "INVOICENUMBER") or
                f"TALLY-{voucher_count}"
            )

            # Date
            date_str = (
                _get_text(voucher, "DATE") or
                voucher.get("DATE", "") or
                _get_text(voucher, "VOUCHERDATE")
            )
            inv_date = _parse_tally_date(date_str)

            # Party name
            party_name = (
                _get_text(voucher, "PARTYLEDGERNAME") or
                _get_text(voucher, "PARTYNAME") or
                _get_text(voucher, "BASICBUYERNAME") or
                None
            )

            # Party GSTIN
            party_gstin = (
                _get_text(voucher, "PARTYGSTIN") or
                _get_text(voucher, "GSTREGISTRATION") or
                _get_text(voucher, "PARTYMAILINGNAME") or  # sometimes GSTIN is here
                None
            )
            # Try to extract GSTIN from party_gstin text
            if party_gstin and len(party_gstin) != 15:
                extracted = _extract_gstin_from_text(party_gstin)
                party_gstin = extracted

            # Amounts — try multiple Tally fields
            taxable_value = 0.0
            igst = 0.0
            cgst = 0.0
            sgst = 0.0

            # Method 1: Direct fields
            taxable_value = _get_float(voucher, "BASICBILLVALUE") or _get_float(voucher, "AMOUNT")

            # Method 2: From ledger entries (ALLLEDGERENTRIES / LEDGERENTRIES)
            for entry_tag in ["ALLLEDGERENTRIES.LIST", "LEDGERENTRIES.LIST", "ALLLEDGERENTRIES", "LEDGERENTRIES"]:
                for entry in voucher.findall(f".//{entry_tag}") or voucher.findall(f".//{entry_tag.lower()}"):
                    ledger_name = _get_text(entry, "LEDGERNAME").upper()
                    amount = _get_float(entry, "AMOUNT")

                    if any(k in ledger_name for k in ["IGST", "INTEGRATED"]):
                        igst += amount
                    elif any(k in ledger_name for k in ["CGST", "CENTRAL"]):
                        cgst += amount
                    elif any(k in ledger_name for k in ["SGST", "STATE", "UTGST"]):
                        sgst += amount
                    elif any(k in ledger_name for k in ["SALES", "PURCHASE", "TRADE"]):
                        if amount > taxable_value:
                            taxable_value = amount

            # Method 3: From inventory entries
            if taxable_value == 0:
                for inv_entry in voucher.findall(".//ALLINVENTORYENTRIES.LIST") or []:
                    taxable_value += _get_float(inv_entry, "AMOUNT")

            # HSN code
            hsn_code = None
            for inv_entry in voucher.findall(".//ALLINVENTORYENTRIES.LIST") or []:
                hsn = _get_text(inv_entry, "HSNCODE") or _get_text(inv_entry, "HSNDESCRIPTION")
                if hsn:
                    hsn_code = re.sub(r'[^0-9]', '', hsn)[:8] or None
                    break

            # Skip zero-value vouchers
            if taxable_value == 0 and igst == 0 and cgst == 0 and sgst == 0:
                continue

            try:
                invoice = Invoice(
                    invoice_type=inv_type,
                    invoice_number=inv_no,
                    our_gstin=our_gstin,
                    period=period,
                    party_name=party_name,
                    party_gstin=party_gstin,
                    taxable_value=taxable_value,
                    igst=igst,
                    cgst=cgst,
                    sgst=sgst,
                    invoice_date=inv_date if inv_date else None,
                    hsn_code=hsn_code,
                )
                invoices.append(invoice)
            except Exception as e:
                logger.warning(f"Skip Tally voucher {inv_no}: {e}")

        sales_count = sum(1 for i in invoices if i.invoice_type == InvoiceType.SALE)
        purchase_count = sum(1 for i in invoices if i.invoice_type == InvoiceType.PURCHASE)
        logger.info(f"Tally XML parsed: {sales_count} sales + {purchase_count} purchases from {voucher_count} vouchers")

        return invoices

    except Exception as e:
        logger.error(f"Tally XML parse error: {e}")
        raise ValueError(f"Cannot parse Tally XML: {e}")