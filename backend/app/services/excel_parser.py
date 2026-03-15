# """
# excel_parser.py
# ---------------
# Excel ya CSV file ko parse karke Invoice objects banao.

# Supported formats:
# - Sales register (.xlsx, .csv)
# - Purchase register (.xlsx, .csv)
# - GSTR-2B data (.xlsx, .csv)

# Column names flexible hain — common variations handle karta hai.
# """
# import pandas as pd
# from datetime import date
# from typing import Optional, Union
# import logging
# import io

# from app.models.invoice import Invoice, InvoiceType

# logger = logging.getLogger(__name__)

# # ── Column name mappings ───────────────────────────────────────
# COLUMN_ALIASES = {
#     "invoice_number": [
#         "invoice_number", "invoice no", "invoice_no", "bill no",
#         "bill_no", "voucher no", "voucher_no", "inv no", "inv_no",
#         "document no", "document_no"
#     ],
#     "party_name": [
#         "party_name", "party name", "supplier name", "supplier_name",
#         "customer name", "customer_name", "buyer name", "buyer_name",
#         "vendor name", "vendor_name", "name"
#     ],
#     "party_gstin": [
#         "party_gstin", "party gstin", "gstin", "supplier gstin",
#         "supplier_gstin", "customer gstin", "customer_gstin",
#         "buyer gstin", "buyer_gstin", "gstin no", "gst no"
#     ],
#     "taxable_value": [
#         "taxable_value", "taxable value", "taxable amount",
#         "taxable_amount", "base amount", "base_amount",
#         "assessable value", "assessable_value", "value"
#     ],
#     "igst": [
#         "igst", "igst amount", "igst_amount", "integrated tax",
#         "integrated_tax", "igst tax"
#     ],
#     "cgst": [
#         "cgst", "cgst amount", "cgst_amount", "central tax",
#         "central_tax", "cgst tax"
#     ],
#     "sgst": [
#         "sgst", "sgst amount", "sgst_amount", "state tax",
#         "state_tax", "sgst tax", "utgst", "utgst amount"
#     ],
#     "invoice_date": [
#         "invoice_date", "invoice date", "bill date", "bill_date",
#         "date", "voucher date", "voucher_date", "doc date"
#     ],
#     "hsn_code": [
#         "hsn_code", "hsn code", "hsn", "sac", "sac code",
#         "hsn/sac", "hsn sac"
#     ],
#     "irn": [
#         "irn", "irn no", "irn_no", "e-invoice irn",
#         "invoice reference number"
#     ],
#     "payment_date": [
#         "payment_date", "payment date", "paid date", "paid_date",
#         "date of payment"
#     ],
#     "is_in_gstr2b": [
#         "is_in_gstr2b", "in gstr2b", "gstr2b", "2b status",
#         "available in 2b"
#     ],
#     "gstr2b_amount": [
#         "gstr2b_amount", "gstr2b amount", "2b amount",
#         "amount in 2b", "itc available"
#     ],
#     "is_in_gstr1": [
#         "is_in_gstr1", "in gstr1", "gstr1", "1 status",
#         "filed in gstr1"
#     ],
# }


# def _normalize_columns(df: pd.DataFrame) -> dict[str, str]:
#     df_cols_lower = {col.lower().strip(): col for col in df.columns}
#     mapping = {}
#     for standard_name, aliases in COLUMN_ALIASES.items():
#         for alias in aliases:
#             if alias.lower() in df_cols_lower:
#                 mapping[standard_name] = df_cols_lower[alias.lower()]
#                 break
#     return mapping


# def _safe_float(val) -> float:
#     try:
#         if pd.isna(val):
#             return 0.0
#         return float(val)
#     except (TypeError, ValueError):
#         return 0.0


# def _safe_str(val) -> Optional[str]:
#     try:
#         if pd.isna(val):
#             return None
#         s = str(val).strip()
#         return s if s else None
#     except (TypeError, ValueError):
#         return None


# def _safe_date(val) -> Optional[date]:
#     if val is None:
#         return None
#     try:
#         if pd.isna(val):
#             return None
#     except (TypeError, ValueError):
#         pass
#     try:
#         if isinstance(val, date):
#             return val
#         parsed = pd.to_datetime(val, dayfirst=True)
#         return parsed.date()
#     except Exception:
#         return None


# def _safe_bool(val) -> Optional[bool]:
#     if val is None:
#         return None
#     try:
#         if pd.isna(val):
#             return None
#     except (TypeError, ValueError):
#         pass
#     s = str(val).strip().lower()
#     if s in ("yes", "true", "1", "y", "available", "matched"):
#         return True
#     if s in ("no", "false", "0", "n", "not available", "missing"):
#         return False
#     return None


# def _resolve_invoice_type(invoice_type: Union[str, InvoiceType]) -> InvoiceType:
#     """
#     FIX: String ya InvoiceType enum dono accept karo.
#     audit.py string bhejta hai ('sale'/'purchase') — handle karo.
#     """
#     if isinstance(invoice_type, InvoiceType):
#         return invoice_type
#     # String → enum
#     val = str(invoice_type).lower().strip()
#     if val in ("sale", "sales"):
#         return InvoiceType.SALE
#     if val in ("purchase", "purchases"):
#         return InvoiceType.PURCHASE
#     raise ValueError(f"Invalid invoice_type: '{invoice_type}'. Use 'sale' or 'purchase'.")


# def parse_excel(
#     file_path: str,
#     invoice_type: Union[str, InvoiceType],   # FIX: both accepted
#     our_gstin: str,
#     period: Optional[str] = None,
#     sheet_name: int = 0,
# ) -> list[Invoice]:
#     """
#     Excel/CSV file parse karke Invoice list return karo.
#     """
#     # FIX: string → enum convert
#     inv_type = _resolve_invoice_type(invoice_type)

#     logger.info(f"Parsing {inv_type.value} file: {file_path}")

#     try:
#         if file_path.endswith(".csv"):
#             df = pd.read_csv(file_path, dtype=str)
#         else:
#             df = pd.read_excel(
#                 file_path,
#                 sheet_name=sheet_name,
#                 dtype=str,
#                 engine="openpyxl",
#             )
#     except Exception as e:
#         logger.error(f"File read failed: {e}")
#         raise ValueError(f"File read nahi hua: {e}") from e

#     if df.empty:
#         logger.warning("File empty hai")
#         return []

#     col_map = _normalize_columns(df)
#     logger.info(f"Columns found: {list(col_map.keys())}")

#     if "invoice_number" not in col_map:
#         raise ValueError(
#             "Invoice Number column nahi mila. "
#             "Column ka naam hona chahiye: "
#             "'Invoice No', 'Bill No', ya 'Voucher No'"
#         )

#     invoices: list[Invoice] = []
#     errors = 0

#     for idx, row in df.iterrows():
#         try:
#             inv_no = _safe_str(row.get(col_map.get("invoice_number", ""), None))
#             if not inv_no:
#                 continue

#             invoice = Invoice(
#                 invoice_type=inv_type,
#                 invoice_number=inv_no,
#                 our_gstin=our_gstin,
#                 period=period,
#                 party_name=_safe_str(row.get(col_map.get("party_name", ""), None)),
#                 party_gstin=_safe_str(row.get(col_map.get("party_gstin", ""), None)),
#                 taxable_value=_safe_float(row.get(col_map.get("taxable_value", ""), 0)),
#                 igst=_safe_float(row.get(col_map.get("igst", ""), 0)),
#                 cgst=_safe_float(row.get(col_map.get("cgst", ""), 0)),
#                 sgst=_safe_float(row.get(col_map.get("sgst", ""), 0)),
#                 invoice_date=_safe_date(row.get(col_map.get("invoice_date", ""), None)),
#                 hsn_code=_safe_str(row.get(col_map.get("hsn_code", ""), None)),
#                 irn=_safe_str(row.get(col_map.get("irn", ""), None)),
#                 payment_date=_safe_date(row.get(col_map.get("payment_date", ""), None)),
#                 is_in_gstr1=_safe_bool(row.get(col_map.get("is_in_gstr1", ""), None)),
#                 is_in_gstr2b=_safe_bool(row.get(col_map.get("is_in_gstr2b", ""), None)),
#                 gstr2b_amount=_safe_float(row.get(col_map.get("gstr2b_amount", ""), 0)) or None,
#             )
#             invoices.append(invoice)

#         except Exception as e:
#             errors += 1
#             logger.warning(f"Row {idx + 2} skip: {e}")
#             if errors > 50:
#                 raise ValueError("Bahut zyada rows mein error. File format check karo.")

#     logger.info(f"Parsed {len(invoices)} invoices ({errors} rows skipped)")
#     return invoices


# def parse_from_bytes(
#     file_bytes: bytes,
#     filename: str,
#     invoice_type: Union[str, InvoiceType],   # FIX: both accepted
#     our_gstin: str,
#     period: Optional[str] = None,
# ) -> list[Invoice]:
#     """
#     File bytes se directly parse karo — disk pe save kiye bina.
#     FastAPI UploadFile ke saath use karo.
#     """
#     # FIX: string → enum convert
#     inv_type = _resolve_invoice_type(invoice_type)

#     logger.info(f"Parsing from bytes: {filename} ({inv_type.value})")

#     try:
#         if filename.lower().endswith(".csv"):
#             df = pd.read_csv(io.BytesIO(file_bytes), dtype=str)
#         else:
#             df = pd.read_excel(
#                 io.BytesIO(file_bytes),
#                 dtype=str,
#                 engine="openpyxl",
#             )
#     except Exception as e:
#         raise ValueError(f"File parse nahi hua: {e}") from e

#     if df.empty:
#         return []

#     col_map = _normalize_columns(df)

#     if "invoice_number" not in col_map:
#         raise ValueError(
#             "Invoice Number column nahi mila. "
#             "Supported names: 'Invoice No', 'Bill No', 'Voucher No'"
#         )

#     invoices: list[Invoice] = []
#     errors = 0

#     for idx, row in df.iterrows():
#         try:
#             inv_no = _safe_str(row.get(col_map.get("invoice_number", ""), None))
#             if not inv_no:
#                 continue

#             invoice = Invoice(
#                 invoice_type=inv_type,
#                 invoice_number=inv_no,
#                 our_gstin=our_gstin,
#                 period=period,
#                 party_name=_safe_str(row.get(col_map.get("party_name", ""), None)),
#                 party_gstin=_safe_str(row.get(col_map.get("party_gstin", ""), None)),
#                 taxable_value=_safe_float(row.get(col_map.get("taxable_value", ""), 0)),
#                 igst=_safe_float(row.get(col_map.get("igst", ""), 0)),
#                 cgst=_safe_float(row.get(col_map.get("cgst", ""), 0)),
#                 sgst=_safe_float(row.get(col_map.get("sgst", ""), 0)),
#                 invoice_date=_safe_date(row.get(col_map.get("invoice_date", ""), None)),
#                 hsn_code=_safe_str(row.get(col_map.get("hsn_code", ""), None)),
#                 irn=_safe_str(row.get(col_map.get("irn", ""), None)),
#                 payment_date=_safe_date(row.get(col_map.get("payment_date", ""), None)),
#                 is_in_gstr1=_safe_bool(row.get(col_map.get("is_in_gstr1", ""), None)),
#                 is_in_gstr2b=_safe_bool(row.get(col_map.get("is_in_gstr2b", ""), None)),
#                 gstr2b_amount=_safe_float(row.get(col_map.get("gstr2b_amount", ""), 0)) or None,
#             )
#             invoices.append(invoice)

#         except Exception as e:
#             errors += 1
#             logger.warning(f"Row {idx + 2} skip: {e}")
#             if errors > 50:
#                 raise ValueError("Bahut zyada rows mein error. File format check karo.")

#     logger.info(f"Parsed {len(invoices)} invoices ({errors} rows skipped)")
#     return invoices



"""
excel_parser.py  —  Smart Multi-Format GST Invoice Parser
==========================================================
Location: app/services/excel_parser.py  (REPLACE existing file)

Features:
  - Auto-detects column names from ANY accounting software
  - Supports: Tally, Busy, Zoho, Marg ERP, SAP, QuickBooks,
    GSTN Portal downloads, Manual Excel/CSV
  - 3-Layer detection: Keyword → Pattern → Fallback
  - Auto-finds header row (skips company title/blank rows)
  - Detects source software automatically
  - Hindi/Marathi column names supported
  - Returns mapping confidence score
"""

import re
import io
import logging
from datetime import date
from typing import Optional, Union, Dict, List, Tuple

import pandas as pd

from app.models.invoice import Invoice, InvoiceType

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
#  COLUMN ALIASES  —  200+ variations from real-world exports
# ═══════════════════════════════════════════════════════════════

COLUMN_ALIASES: Dict[str, List[str]] = {

    # ── Invoice Number ────────────────────────────────────────
    "invoice_number": [
        # English common
        "invoice number", "invoice no", "invoice no.", "inv no",
        "inv no.", "invoice#", "inv#",
        # Bill variants
        "bill no", "bill no.", "bill number", "bill#",
        # Voucher variants (Tally)
        "voucher no", "voucher no.", "voucher number", "vch no",
        "vch no.", "voucher ref",
        # Document variants
        "document no", "document no.", "document number", "doc no",
        "doc no.", "doc number",
        # Reference
        "ref no", "ref no.", "reference no", "reference number",
        # Credit/Debit note
        "credit note no", "debit note no", "cn no", "dn no",
        # Others
        "memo no", "receipt no", "challan no", "sr no",
        # GSTN portal
        "invoice/advance receipt number", "original invoice number",
        # SAP
        "billing document",
        # Short forms
        "inv", "bill", "vch",
        # Hindi / Marathi
        "बिल नंबर", "बीजक क्रमांक", "चालान नंबर",
        "इनवॉइस नंबर", "बीजक क्र.",
    ],

    # ── Invoice Date ──────────────────────────────────────────
    "invoice_date": [
        "invoice date", "inv date", "bill date", "voucher date",
        "vch date", "date", "doc date", "document date",
        "transaction date", "txn date", "billing date",
        "supply date", "date of invoice", "date of supply",
        # GSTN portal
        "invoice/advance receipt date",
        # Hindi / Marathi
        "दिनांक", "तारीख", "इनवॉइस दिनांक",
    ],

    # ── Party / Customer / Supplier Name ──────────────────────
    "party_name": [
        # Party
        "party name", "party", "party's name",
        # Customer
        "customer name", "customer", "cust name",
        # Supplier
        "supplier name", "supplier", "supp name",
        # Vendor
        "vendor name", "vendor",
        # Buyer / Seller
        "buyer name", "buyer", "seller name", "seller",
        # Account (Tally / Busy)
        "account name", "account", "ledger name", "ledger",
        "particulars",
        # Descriptive
        "name of party", "name of customer", "name of supplier",
        "bill to", "ship to", "sold to", "purchased from",
        "consignee", "receiver", "recipient", "name",
        # GSTN portal
        "trade/legal name", "trade name of supplier",
        "legal name of supplier", "trade name",
        # Hindi / Marathi
        "पार्टी का नाम", "पक्षाचे नाव", "ग्राहक",
        "पुरवठादार", "सप्लायर का नाम",
    ],

    # ── GSTIN ─────────────────────────────────────────────────
    "party_gstin": [
        # Standard
        "gstin", "gstin/uin", "gst no", "gst no.", "gst number",
        "gstin no", "gstin no.", "gstin number",
        # With party prefix
        "party gstin", "customer gstin", "supplier gstin",
        "vendor gstin", "buyer gstin", "seller gstin",
        # Descriptive
        "gstin of supplier", "gstin of buyer",
        "gstin of recipient", "gstin/uin of recipient",
        "gstin/uin of supplier",
        "gst identification number", "gst id",
        # Tally specific
        "party gstin/uin",
        # GSTN portal
        "gstin of supplier",
        # Hindi / Marathi
        "जीएसटीआईएन", "जीएसटी नंबर", "जीएसटी क्रमांक",
        # Short
        "gst",
    ],

    # ── Taxable Value / Amount ────────────────────────────────
    "taxable_value": [
        # Standard
        "taxable value", "taxable amount", "taxable amt",
        # Base
        "base amount", "base value", "net amount", "net value",
        # Assessable
        "assessable value", "assessable amount",
        # Sub total
        "sub total", "subtotal", "sub-total",
        # Value of goods/services
        "value of goods", "value of services",
        # Gross (Tally)
        "gross total", "gross amount", "gross value",
        # Invoice value
        "invoice value", "total value",
        # Pre-tax
        "amount before tax", "pre-tax amount",
        # Busy
        "net taxable",
        # GSTN portal (with ₹ symbol)
        "taxable value (₹)", "taxable value(₹)",
        # Generic
        "amount", "amt", "value",
        # Hindi / Marathi
        "करपात्र रक्कम", "कर योग्य मूल्य", "करपात्र मूल्य",
    ],

    # ── IGST ──────────────────────────────────────────────────
    "igst": [
        "igst", "igst amount", "igst amt", "igst value",
        "integrated tax", "integrated gst", "igst tax",
        "igst total",
        # With rate suffix
        "igst@5%", "igst@12%", "igst@18%", "igst@28%",
        # GSTN portal
        "igst (₹)", "igst amount(₹)", "integrated tax(₹)",
        # Busy
        "integrated tax amount",
        # Hindi / Marathi
        "आईजीएसटी", "एकात्मिक कर",
    ],

    # ── CGST ──────────────────────────────────────────────────
    "cgst": [
        "cgst", "cgst amount", "cgst amt", "cgst value",
        "central tax", "central gst", "cgst tax", "cgst total",
        # With rate suffix
        "cgst@2.5%", "cgst@6%", "cgst@9%", "cgst@14%",
        # GSTN portal
        "cgst (₹)", "cgst amount(₹)", "central tax(₹)",
        # Busy
        "central tax amount",
        # Hindi / Marathi
        "सीजीएसटी", "केंद्रीय कर",
    ],

    # ── SGST / UTGST ──────────────────────────────────────────
    "sgst": [
        "sgst", "sgst amount", "sgst amt", "sgst value",
        "state tax", "state gst", "sgst tax", "sgst total",
        # UTGST
        "utgst", "utgst amount", "utgst amt",
        # With rate suffix
        "sgst@2.5%", "sgst@6%", "sgst@9%", "sgst@14%",
        # GSTN portal
        "sgst (₹)", "sgst amount(₹)", "state tax(₹)",
        # Busy
        "state tax amount",
        # Hindi / Marathi
        "एसजीएसटी", "राज्य कर",
    ],

    # ── HSN / SAC Code ────────────────────────────────────────
    "hsn_code": [
        "hsn code", "hsn", "hsn/sac", "hsn/sac code",
        "sac code", "sac", "hsn number", "sac number",
        "product code", "item code", "tariff code",
        "hsn/sac of supply", "chapter code",
        # Hindi / Marathi
        "एचएसएन कोड", "एचएसएन",
    ],

    # ── CESS ──────────────────────────────────────────────────
    "cess": [
        "cess", "cess amount", "cess amt", "cess value",
        "compensation cess", "gst cess", "additional cess",
        "cess (₹)", "cess amount(₹)",
    ],

    # ── GST Rate ──────────────────────────────────────────────
    "gst_rate": [
        "rate", "tax rate", "gst rate", "gst %", "rate (%)",
        "rate of tax", "applicable rate", "tax %", "gst rate (%)",
    ],

    # ── IRN (E-Invoice Reference) ─────────────────────────────
    "irn": [
        "irn", "irn no", "irn no.", "e-invoice irn",
        "invoice reference number", "irn number",
    ],

    # ── Payment Date ──────────────────────────────────────────
    "payment_date": [
        "payment date", "paid date", "date of payment",
        "received date", "receipt date",
    ],

    # ── Place of Supply ───────────────────────────────────────
    "place_of_supply": [
        "place of supply", "pos", "supply state", "state",
        "destination state", "recipient state", "buyer state",
        "state of supply", "state code",
    ],

    # ── Total Amount (with tax) ───────────────────────────────
    "total_amount": [
        "total amount", "total", "invoice total", "grand total",
        "total invoice value", "final amount", "bill total",
        "total with tax", "amount with tax",
        "total including tax", "total inc tax",
    ],

    # ── Reverse Charge ────────────────────────────────────────
    "reverse_charge": [
        "reverse charge", "rcm", "reverse charge mechanism",
        "is reverse charge", "rcm applicable",
    ],

    # ── Invoice Type (B2B / B2C / Export) ─────────────────────
    "invoice_type_tag": [
        "invoice type", "inv type", "type", "supply type",
        "transaction type", "nature of supply", "category",
    ],

    # ── GSTR-1 Status ─────────────────────────────────────────
    "is_in_gstr1": [
        "in gstr1", "gstr1 status", "filed in gstr1", "gstr-1",
        "reported in gstr1", "gstr1 reported", "is in gstr1",
        "gstr1", "1 status",
    ],

    # ── GSTR-2B Status ────────────────────────────────────────
    "is_in_gstr2b": [
        "in gstr2b", "gstr2b status", "gstr-2b", "gstr2b match",
        "available in gstr2b", "2b status", "itc available",
        "is in gstr2b", "gstr2b",
    ],

    # ── GSTR-2B Amount ────────────────────────────────────────
    "gstr2b_amount": [
        "gstr2b amount", "2b amount", "gstr2b taxable",
        "portal amount", "gstr-2b value", "2b taxable value",
        "amount in 2b", "itc available amount",
    ],
}


# ═══════════════════════════════════════════════════════════════
#  SOFTWARE SIGNATURES  —  Auto-detect source software
# ═══════════════════════════════════════════════════════════════

SOFTWARE_SIGNATURES = {
    "tally": [
        "vch no", "voucher no", "particulars", "gstin/uin",
        "vch date", "voucher ref", "party's name",
    ],
    "busy": [
        "account name", "integrated tax", "central tax",
        "state tax", "integrated tax amount",
    ],
    "zoho": [
        "invoice number", "customer name", "sub total",
        "tax amount", "balance due",
    ],
    "marg": [
        "bill no", "bill date", "party name", "net amount",
        "bill amount",
    ],
    "sap": [
        "billing document", "company code", "document number",
        "fiscal year",
    ],
    "gstn_portal": [
        "gstin of supplier", "trade/legal name",
        "invoice/advance receipt number",
        "taxable value(₹)", "taxable value (₹)",
    ],
    "quickbooks": [
        "transaction type", "num", "memo",
    ],
}


# ═══════════════════════════════════════════════════════════════
#  REGEX PATTERNS  —  For data-level detection (Layer 2)
# ═══════════════════════════════════════════════════════════════

GSTIN_RE  = re.compile(r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][A-Z0-9]Z[A-Z0-9]$')
DATE_RES  = [
    re.compile(r'^\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4}$'),   # DD/MM/YYYY or DD-MM-YY
    re.compile(r'^\d{4}[/\-]\d{1,2}[/\-]\d{1,2}$'),      # YYYY-MM-DD
    re.compile(r'^\d{1,2}\-[A-Za-z]{3}\-\d{2,4}$'),      # DD-Mon-YYYY
]
AMOUNT_RE = re.compile(r'^-?[\d,]+\.?\d*$')
HSN_RE    = re.compile(r'^\d{2,8}$')
INV_RE    = re.compile(r'^[A-Za-z0-9/\-_\.]{2,40}$')


# ═══════════════════════════════════════════════════════════════
#  HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════

def _norm(text) -> str:
    """Normalize any value for comparison."""
    s = str(text).lower().strip()
    s = re.sub(r'[₹%()#\./\-_]', ' ', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s


def _safe_float(val) -> float:
    try:
        if pd.isna(val):
            return 0.0
        return float(str(val).replace(',', '').replace('₹', '').strip())
    except (TypeError, ValueError):
        return 0.0


def _safe_str(val) -> Optional[str]:
    try:
        if pd.isna(val):
            return None
        s = str(val).strip()
        return s if s and s.lower() not in ('nan', 'none', 'nat') else None
    except (TypeError, ValueError):
        return None


def _safe_date(val) -> Optional[date]:
    if val is None:
        return None
    try:
        if pd.isna(val):
            return None
    except (TypeError, ValueError):
        pass
    try:
        if isinstance(val, date):
            return val
        parsed = pd.to_datetime(val, dayfirst=True)
        return parsed.date()
    except Exception:
        return None


def _safe_bool(val) -> Optional[bool]:
    if val is None:
        return None
    try:
        if pd.isna(val):
            return None
    except (TypeError, ValueError):
        pass
    s = str(val).strip().lower()
    if s in ("yes", "true", "1", "y", "available", "matched", "filed"):
        return True
    if s in ("no", "false", "0", "n", "not available", "missing", "not filed"):
        return False
    return None


def _resolve_invoice_type(invoice_type: Union[str, InvoiceType]) -> InvoiceType:
    """Accept both string and enum for invoice_type."""
    if isinstance(invoice_type, InvoiceType):
        return invoice_type
    val = str(invoice_type).lower().strip()
    if val in ("sale", "sales"):
        return InvoiceType.SALE
    if val in ("purchase", "purchases"):
        return InvoiceType.PURCHASE
    raise ValueError(f"Invalid invoice_type: '{invoice_type}'. Use 'sale' or 'purchase'.")


# ═══════════════════════════════════════════════════════════════
#  LAYER 1:  KEYWORD MATCHING
# ═══════════════════════════════════════════════════════════════

def _keyword_match(df_columns: List[str]) -> Dict[str, str]:
    """
    Match DataFrame column names to standard fields using aliases.
    Returns {standard_field: actual_column_name}
    """
    # Build lowercase → actual column map
    col_lower_map = {}
    for col in df_columns:
        col_lower_map[_norm(col)] = col

    mapping: Dict[str, str] = {}
    used_cols: set = set()

    for field, aliases in COLUMN_ALIASES.items():
        best_col = None
        best_score = 0

        for norm_col, actual_col in col_lower_map.items():
            if actual_col in used_cols:
                continue

            for alias in aliases:
                alias_n = _norm(alias)

                # Exact match
                if norm_col == alias_n:
                    score = 100
                # Contains
                elif alias_n in norm_col or norm_col in alias_n:
                    score = 80
                # Word overlap
                else:
                    a_words = set(alias_n.split())
                    c_words = set(norm_col.split())
                    overlap = a_words & c_words
                    score = 60 if overlap and len(overlap) >= len(a_words) * 0.5 else 0

                if score > best_score:
                    best_score = score
                    best_col = actual_col

        if best_col and best_score >= 60:
            mapping[field] = best_col
            used_cols.add(best_col)

    return mapping


# ═══════════════════════════════════════════════════════════════
#  LAYER 2:  PATTERN DETECTION  (analyze actual data)
# ═══════════════════════════════════════════════════════════════

def _sample_values(df: pd.DataFrame, col: str, n: int = 20) -> List[str]:
    """Get non-empty string samples from a column."""
    vals = []
    for v in df[col].head(n):
        s = str(v).strip()
        if s and s.lower() not in ('nan', 'none', '', '-', 'nat'):
            vals.append(s)
    return vals


def _pattern_detect(df: pd.DataFrame, existing_map: Dict[str, str]) -> Dict[str, str]:
    """
    Detect unmapped columns by analyzing the actual data values.
    Fills gaps left by keyword matching.
    """
    mapped_cols = set(existing_map.values())
    unmapped = [c for c in df.columns if c not in mapped_cols]
    new_map: Dict[str, str] = {}

    for col in unmapped:
        samples = _sample_values(df, col)
        if not samples:
            continue

        # ── GSTIN ──
        if "party_gstin" not in existing_map and "party_gstin" not in new_map:
            hits = sum(1 for v in samples if GSTIN_RE.match(v.upper()))
            if hits >= len(samples) * 0.4:
                new_map["party_gstin"] = col
                continue

        # ── Date ──
        if "invoice_date" not in existing_map and "invoice_date" not in new_map:
            hits = sum(1 for v in samples if any(r.match(v) for r in DATE_RES))
            if hits >= len(samples) * 0.4:
                new_map["invoice_date"] = col
                continue

        # ── HSN code ──
        if "hsn_code" not in existing_map and "hsn_code" not in new_map:
            stripped = [v.replace(' ', '') for v in samples]
            hits = sum(1 for v in stripped if HSN_RE.match(v))
            if hits >= len(samples) * 0.4:
                try:
                    avg = sum(int(v) for v in stripped if HSN_RE.match(v)) / max(hits, 1)
                    if avg < 1_0000_0000:  # HSN codes max 8 digits
                        new_map["hsn_code"] = col
                        continue
                except ValueError:
                    pass

        # ── Amount columns (detect by numeric pattern + magnitude) ──
        amt_hits = sum(
            1 for v in samples
            if AMOUNT_RE.match(v.replace(',', '').replace(' ', ''))
        )
        if amt_hits >= len(samples) * 0.6:
            try:
                nums = [
                    float(v.replace(',', '').replace(' ', ''))
                    for v in samples
                    if AMOUNT_RE.match(v.replace(',', '').replace(' ', ''))
                ]
                avg = sum(nums) / max(len(nums), 1)

                # Largest unmapped number column → taxable value
                if "taxable_value" not in existing_map and "taxable_value" not in new_map and avg > 500:
                    new_map["taxable_value"] = col
                elif "igst" not in existing_map and "igst" not in new_map:
                    new_map["igst"] = col
                elif "cgst" not in existing_map and "cgst" not in new_map:
                    new_map["cgst"] = col
                elif "sgst" not in existing_map and "sgst" not in new_map:
                    new_map["sgst"] = col
            except (ValueError, ZeroDivisionError):
                pass
            continue

        # ── Invoice number ──
        if "invoice_number" not in existing_map and "invoice_number" not in new_map:
            hits = sum(1 for v in samples if INV_RE.match(v))
            if hits >= len(samples) * 0.5:
                new_map["invoice_number"] = col
                continue

    return {**existing_map, **new_map}


# ═══════════════════════════════════════════════════════════════
#  SOFTWARE DETECTION
# ═══════════════════════════════════════════════════════════════

def detect_software(columns: List[str], sheet_name: str = "") -> str:
    """Detect which accounting software generated the file."""
    norm_cols = [_norm(c) for c in columns]
    norm_sheet = sheet_name.lower().strip()

    best = "unknown"
    best_score = 0

    for sw, keywords in SOFTWARE_SIGNATURES.items():
        score = sum(
            2 for kw in keywords
            if any(kw in nc for nc in norm_cols)
        )
        if score > best_score:
            best_score = score
            best = sw

    return best if best_score >= 2 else "manual_excel"


# ═══════════════════════════════════════════════════════════════
#  HEADER ROW DETECTION  (skip title / blank rows)
# ═══════════════════════════════════════════════════════════════

def find_header_row(df_raw: pd.DataFrame, max_search: int = 15) -> int:
    """
    Find which row contains column headers.
    Many Excel files have company name, address, blank rows
    before the actual data headers.
    """
    all_kw = set()
    for aliases in COLUMN_ALIASES.values():
        for a in aliases:
            all_kw.add(_norm(a))

    best_row = 0
    best_score = 0

    for i in range(min(max_search, len(df_raw))):
        row_vals = df_raw.iloc[i].tolist()
        score = 0
        non_empty = 0

        for cell in row_vals:
            cn = _norm(cell)
            if cn and cn not in ('nan', 'none', ''):
                non_empty += 1
                if any(kw in cn or cn in kw for kw in all_kw):
                    score += 1

        total = score * 10 + non_empty
        if non_empty >= 3 and score >= 2 and total > best_score:
            best_score = total
            best_row = i

    return best_row


# ═══════════════════════════════════════════════════════════════
#  SMART COLUMN MAPPING  (main orchestrator)
# ═══════════════════════════════════════════════════════════════

class ColumnMappingResult:
    """Holds mapping metadata for logging / frontend display."""
    def __init__(self):
        self.mapping: Dict[str, str] = {}   # standard_field → actual_col
        self.software: str = "unknown"
        self.confidence: float = 0.0
        self.unmapped: List[str] = []
        self.warnings: List[str] = []

    def to_dict(self) -> dict:
        return {
            "mapping": self.mapping,
            "software": self.software,
            "confidence": self.confidence,
            "unmapped_critical": self.unmapped,
            "warnings": self.warnings,
        }


CRITICAL_FIELDS = ["invoice_number", "taxable_value"]
IMPORTANT_FIELDS = [
    "party_gstin", "party_name", "invoice_date",
    "igst", "cgst", "sgst",
]


def smart_map(df: pd.DataFrame, sheet_name: str = "") -> ColumnMappingResult:
    """
    Run Layer 1 (keyword) + Layer 2 (pattern) and return mapping.
    """
    result = ColumnMappingResult()

    # Software detection
    result.software = detect_software(list(df.columns), sheet_name)
    if result.software != "manual_excel":
        logger.info(f"Detected software: {result.software.upper()}")

    # Layer 1: keyword
    result.mapping = _keyword_match(list(df.columns))
    logger.info(f"Layer 1 (keyword): mapped {len(result.mapping)} fields → {list(result.mapping.keys())}")

    # Layer 2: pattern (if we have data)
    if len(df) > 0:
        result.mapping = _pattern_detect(df, result.mapping)
        logger.info(f"Layer 2 (pattern): total {len(result.mapping)} fields → {list(result.mapping.keys())}")

    # Check coverage
    for f in CRITICAL_FIELDS:
        if f not in result.mapping:
            result.unmapped.append(f)

    total = len(CRITICAL_FIELDS) + len(IMPORTANT_FIELDS)
    found = sum(1 for f in CRITICAL_FIELDS + IMPORTANT_FIELDS if f in result.mapping)
    result.confidence = round(found / total * 100, 1)

    if result.unmapped:
        result.warnings.append(
            f"Could not detect: {', '.join(result.unmapped)}. "
            f"Rename column to 'Invoice No' or 'Taxable Value'."
        )

    return result


# ═══════════════════════════════════════════════════════════════
#  CORE PARSE FUNCTIONS  (used by audit.py)
# ═══════════════════════════════════════════════════════════════

def parse_excel(
    file_path: str,
    invoice_type: Union[str, InvoiceType],
    our_gstin: str,
    period: Optional[str] = None,
    sheet_name: int = 0,
) -> list[Invoice]:
    """Parse Excel/CSV file from disk path."""
    inv_type = _resolve_invoice_type(invoice_type)
    logger.info(f"Parsing {inv_type.value} file: {file_path}")

    try:
        if file_path.endswith(".csv"):
            df = pd.read_csv(file_path, dtype=str)
        else:
            df = pd.read_excel(file_path, sheet_name=sheet_name, dtype=str, engine="openpyxl")
    except Exception as e:
        logger.error(f"File read failed: {e}")
        raise ValueError(f"Cannot read file: {e}") from e

    return _parse_dataframe(df, inv_type, our_gstin, period)


def parse_from_bytes(
    file_bytes: bytes,
    filename: str,
    invoice_type: Union[str, InvoiceType],
    our_gstin: str,
    period: Optional[str] = None,
) -> list[Invoice]:
    """Parse from file bytes (FastAPI UploadFile)."""
    inv_type = _resolve_invoice_type(invoice_type)
    logger.info(f"Parsing from bytes: {filename} ({inv_type.value})")

    try:
        if filename.lower().endswith(".csv"):
            df = pd.read_csv(io.BytesIO(file_bytes), dtype=str)
        else:
            df = pd.read_excel(io.BytesIO(file_bytes), dtype=str, engine="openpyxl")
    except Exception as e:
        raise ValueError(f"Cannot parse file: {e}") from e

    return _parse_dataframe(df, inv_type, our_gstin, period, filename)


def _parse_dataframe(
    df: pd.DataFrame,
    inv_type: InvoiceType,
    our_gstin: str,
    period: Optional[str],
    source: str = "",
) -> list[Invoice]:
    """
    Internal: Parse a DataFrame into Invoice objects.
    Uses smart column mapping (Layer 1 + Layer 2).
    """
    if df.empty:
        logger.warning("File is empty")
        return []

    # ── Auto-detect header row ──
    # Some files have company name / blank rows at the top
    # Check if current first row looks like headers
    first_row_norm = [_norm(str(c)) for c in df.columns]
    all_kw = set()
    for aliases in COLUMN_ALIASES.values():
        for a in aliases:
            all_kw.add(_norm(a))

    header_match = sum(1 for c in first_row_norm if any(kw in c or c in kw for kw in all_kw))

    if header_match < 2:
        # Current header row is probably not real headers
        # Read file as raw (no header) and find real header row
        logger.info("Header row may not be row 0 — searching...")
        df_raw = df.copy()
        # Reset: make all rows into data, no header
        df_raw.columns = range(len(df_raw.columns))

        hdr_idx = find_header_row(df_raw)
        if hdr_idx > 0:
            logger.info(f"Found header at row {hdr_idx}")
            # Re-read: skip rows before header
            new_headers = df_raw.iloc[hdr_idx].tolist()
            df = df_raw.iloc[hdr_idx + 1:].reset_index(drop=True)
            df.columns = [str(h).strip() for h in new_headers]

    # ── Smart column mapping ──
    mapping_result = smart_map(df)
    col_map = mapping_result.mapping

    if "invoice_number" not in col_map:
        # Last resort: try first column that has alphanumeric data
        for c in df.columns:
            samples = _sample_values(df, c)
            inv_hits = sum(1 for v in samples if INV_RE.match(v))
            if inv_hits >= len(samples) * 0.3 and len(samples) >= 2:
                col_map["invoice_number"] = c
                logger.info(f"Fallback: using column '{c}' as invoice_number")
                break

    if "invoice_number" not in col_map:
        raise ValueError(
            "Invoice Number column not found. "
            "Please name it: 'Invoice No', 'Bill No', or 'Voucher No'. "
            f"Found columns: {list(df.columns)}"
        )

    # ── Parse rows into Invoice objects ──
    invoices: list[Invoice] = []
    errors = 0

    for idx, row in df.iterrows():
        try:
            inv_no = _safe_str(row.get(col_map.get("invoice_number", ""), None))
            if not inv_no:
                continue

            invoice = Invoice(
                invoice_type=inv_type,
                invoice_number=inv_no,
                our_gstin=our_gstin,
                period=period,
                party_name=_safe_str(row.get(col_map.get("party_name", ""), None)),
                party_gstin=_safe_str(row.get(col_map.get("party_gstin", ""), None)),
                taxable_value=_safe_float(row.get(col_map.get("taxable_value", ""), 0)),
                igst=_safe_float(row.get(col_map.get("igst", ""), 0)),
                cgst=_safe_float(row.get(col_map.get("cgst", ""), 0)),
                sgst=_safe_float(row.get(col_map.get("sgst", ""), 0)),
                invoice_date=_safe_date(row.get(col_map.get("invoice_date", ""), None)),
                hsn_code=_safe_str(row.get(col_map.get("hsn_code", ""), None)),
                irn=_safe_str(row.get(col_map.get("irn", ""), None)),
                payment_date=_safe_date(row.get(col_map.get("payment_date", ""), None)),
                is_in_gstr1=_safe_bool(row.get(col_map.get("is_in_gstr1", ""), None)),
                is_in_gstr2b=_safe_bool(row.get(col_map.get("is_in_gstr2b", ""), None)),
                gstr2b_amount=_safe_float(row.get(col_map.get("gstr2b_amount", ""), 0)) or None,
            )
            invoices.append(invoice)

        except Exception as e:
            errors += 1
            logger.warning(f"Row {idx + 2} skipped: {e}")
            if errors > 100:
                raise ValueError(
                    "Too many row errors (>100). Check file format. "
                    f"Mapped columns: {col_map}"
                )

    logger.info(f"Parsed {len(invoices)} invoices ({errors} rows skipped)")

    if mapping_result.software != "manual_excel":
        logger.info(f"Source software: {mapping_result.software.upper()} | Confidence: {mapping_result.confidence}%")

    return invoices