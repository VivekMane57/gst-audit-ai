"""
services/reconciliation_service.py
------------------------------------
GSTR-2B vs Purchase Register Reconciliation Engine.

Logic:
  1. Normalize invoice numbers (remove symbols, uppercase)
  2. Exact match first: GSTIN + normalized invoice number
  3. Fuzzy match fallback (RapidFuzz, threshold=85)
  4. Categorize: Matched / Missing in 2B / Amount Mismatch
  5. Calculate total ITC loss
  6. Return structured JSON for React frontend

Install dependency:
  pip install rapidfuzz
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Optional

from rapidfuzz import fuzz

from app.models.invoice import Invoice, InvoiceType

logger = logging.getLogger(__name__)

# Fuzzy match threshold — 85 handles INV/001 vs INV-001 vs INV001
FUZZY_THRESHOLD = 85


# ═══════════════════════════════════════════════════════════════
# Output Models (dataclasses — lightweight, JSON serializable)
# ═══════════════════════════════════════════════════════════════

@dataclass
class MatchedInvoice:
    """Invoice found in both Purchase Register and GSTR-2B."""
    invoice_number:    str
    party_name:        Optional[str]
    party_gstin:       Optional[str]
    books_tax:         float
    gstr2b_tax:        float
    diff:              float              # abs(books_tax - gstr2b_tax)
    match_type:        str               # "exact" or "fuzzy"
    matched_inv_no:    str               # actual invoice number in GSTR-2B
    status:            str = "matched"


@dataclass
class MissingInvoice:
    """Invoice in Purchase Register but NOT in GSTR-2B — ITC at risk."""
    invoice_number: str
    party_name:     Optional[str]
    party_gstin:    Optional[str]
    invoice_date:   Optional[str]
    taxable_value:  float
    itc_at_risk:    float               # total_tax
    status:         str = "missing_in_2b"


@dataclass
class MismatchedInvoice:
    """Invoice found in both but amounts differ beyond tolerance."""
    invoice_number: str
    party_name:     Optional[str]
    party_gstin:    Optional[str]
    books_tax:      float
    gstr2b_tax:     float
    diff:           float
    excess_itc:     float               # how much CA over-claimed
    status:         str = "amount_mismatch"


@dataclass
class ReconciliationResult:
    """Full reconciliation output — structured for React frontend."""
    period:             str
    our_gstin:          str

    # Counts
    total_purchase_invoices: int
    total_gstr2b_invoices:   int
    matched_count:           int
    missing_count:           int
    mismatch_count:          int

    # ITC Impact
    total_itc_books:         float     # total ITC claimed in books
    total_itc_gstr2b:        float     # total ITC available in GSTR-2B
    itc_at_risk:             float     # from missing invoices
    itc_excess_claimed:      float     # from mismatched invoices
    total_tax_loss:          float     # itc_at_risk + itc_excess_claimed

    # Detail lists
    matched:    list[MatchedInvoice]    = field(default_factory=list)
    missing:    list[MissingInvoice]    = field(default_factory=list)
    mismatched: list[MismatchedInvoice] = field(default_factory=list)

    # Summary for frontend banner
    risk_level: str = "LOW"           # LOW / MEDIUM / HIGH / CRITICAL
    summary_en: str = ""
    summary_hi: str = ""
    summary_mr: str = ""


# ═══════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════

def _normalize_inv_no(inv_no: str) -> str:
    """
    Strip symbols for fuzzy comparison.
    'INV/2024/001' → 'INV2024001'
    'INV-24-001'   → 'INV24001'
    """
    return re.sub(r"[^A-Z0-9]", "", inv_no.upper())


def _fuzzy_match(
    target: str,
    candidates: list[str],
    threshold: int = FUZZY_THRESHOLD,
) -> Optional[str]:
    """
    Return best fuzzy match from candidates, or None if below threshold.
    Uses token_sort_ratio to handle word-order differences.
    """
    best_score = 0
    best_match = None
    for c in candidates:
        score = fuzz.token_sort_ratio(target, c)
        if score > best_score:
            best_score = score
            best_match = c
    if best_score >= threshold:
        return best_match
    return None


def _risk_level(tax_loss: float, total_itc: float) -> str:
    if total_itc == 0:
        return "LOW"
    pct = (tax_loss / total_itc) * 100
    if pct >= 30:
        return "CRITICAL"
    if pct >= 15:
        return "HIGH"
    if pct >= 5:
        return "MEDIUM"
    return "LOW"


def _build_summary(result: ReconciliationResult) -> tuple[str, str, str]:
    loss = result.total_tax_loss
    missing = result.missing_count
    mismatch = result.mismatch_count

    en = (
        f"{missing} invoices missing from GSTR-2B (ITC at risk: ₹{result.itc_at_risk:,.2f}). "
        f"{mismatch} invoices with amount mismatch (excess claimed: ₹{result.itc_excess_claimed:,.2f}). "
        f"Total tax loss: ₹{loss:,.2f}."
    )
    hi = (
        f"{missing} invoices GSTR-2B में नहीं (ITC खतरे में: ₹{result.itc_at_risk:,.2f}). "
        f"{mismatch} invoices में amount mismatch (अधिक claim: ₹{result.itc_excess_claimed:,.2f}). "
        f"कुल tax loss: ₹{loss:,.2f}."
    )
    mr = (
        f"{missing} invoices GSTR-2B मध्ये नाहीत (ITC धोक्यात: ₹{result.itc_at_risk:,.2f}). "
        f"{mismatch} invoices मध्ये रक्कम जुळत नाही (जास्त दावा: ₹{result.itc_excess_claimed:,.2f}). "
        f"एकूण कर नुकसान: ₹{loss:,.2f}."
    )
    return en, hi, mr


# ═══════════════════════════════════════════════════════════════
# Core Reconciliation Engine
# ═══════════════════════════════════════════════════════════════

def reconcile(
    all_invoices: list[Invoice],
    our_gstin: str,
    period: str,
    amount_tolerance: float = 1.0,
) -> ReconciliationResult:
    """
    Reconcile Purchase Register vs GSTR-2B.

    Args:
        all_invoices:     Combined list from file_router (purchase + gstr2b invoices)
        our_gstin:        Buyer's GSTIN
        period:           Audit period e.g. "2025-01"
        amount_tolerance: Rs difference below which amounts are considered equal

    Returns:
        ReconciliationResult with matched/missing/mismatched lists + ITC summary
    """
    # Split invoices
    purchase_invoices = [
        i for i in all_invoices
        if i.invoice_type == InvoiceType.PURCHASE
    ]
    # GSTR-2B invoices: purchase invoices flagged as is_in_gstr2b=True
    # OR any invoice that came from GSTR-2B file (is_in_gstr2b explicitly set)
    gstr2b_invoices = [
        i for i in purchase_invoices
        if i.is_in_gstr2b is True
    ]
    # Purchase register invoices (from books — may or may not be in GSTR-2B)
    books_invoices = [
        i for i in purchase_invoices
        if i.is_in_gstr2b is None or i.is_in_gstr2b is False or i.gstr2b_amount is not None
    ]

    logger.info(
        f"Reconciliation started | Period: {period} | "
        f"Books: {len(books_invoices)} | GSTR-2B: {len(gstr2b_invoices)}"
    )

    # ── Build GSTR-2B lookup ──────────────────────────────────
    # Key: (gstin, normalized_inv_no) → Invoice
    gstr2b_lookup: dict[tuple[str, str], Invoice] = {}
    gstr2b_norm_map: dict[str, list[tuple[str, str]]] = {}  # gstin → list of norm keys

    for inv in gstr2b_invoices:
        gstin = inv.party_gstin or "UNKNOWN"
        norm  = _normalize_inv_no(inv.invoice_number)
        key   = (gstin, norm)
        gstr2b_lookup[key] = inv
        gstr2b_norm_map.setdefault(gstin, []).append((norm, inv.invoice_number))

    # ── Track matched GSTR-2B keys (to find extras later) ────
    matched_gstr2b_keys: set[tuple[str, str]] = set()

    matched:    list[MatchedInvoice]    = []
    missing:    list[MissingInvoice]    = []
    mismatched: list[MismatchedInvoice] = []

    total_itc_books  = 0.0
    total_itc_gstr2b = 0.0

    # ── Process each books invoice ────────────────────────────
    for inv in books_invoices:
        books_tax = inv.total_tax
        total_itc_books += books_tax

        gstin     = inv.party_gstin or "UNKNOWN"
        norm      = _normalize_inv_no(inv.invoice_number)
        exact_key = (gstin, norm)

        # ── Case 1: Exact match ───────────────────────────────
        if exact_key in gstr2b_lookup:
            gstr2b_inv  = gstr2b_lookup[exact_key]
            gstr2b_tax  = gstr2b_inv.gstr2b_amount or gstr2b_inv.total_tax
            diff        = abs(books_tax - gstr2b_tax)
            total_itc_gstr2b += gstr2b_tax
            matched_gstr2b_keys.add(exact_key)

            if diff > amount_tolerance:
                mismatched.append(MismatchedInvoice(
                    invoice_number=inv.invoice_number,
                    party_name=inv.party_name,
                    party_gstin=inv.party_gstin,
                    books_tax=round(books_tax, 2),
                    gstr2b_tax=round(gstr2b_tax, 2),
                    diff=round(diff, 2),
                    excess_itc=round(max(books_tax - gstr2b_tax, 0), 2),
                ))
            else:
                matched.append(MatchedInvoice(
                    invoice_number=inv.invoice_number,
                    party_name=inv.party_name,
                    party_gstin=inv.party_gstin,
                    books_tax=round(books_tax, 2),
                    gstr2b_tax=round(gstr2b_tax, 2),
                    diff=round(diff, 2),
                    match_type="exact",
                    matched_inv_no=gstr2b_inv.invoice_number,
                ))
            continue

        # ── Case 2: Fuzzy match (same GSTIN, similar inv no) ─
        candidates = [
            norm_key
            for norm_key, _ in gstr2b_norm_map.get(gstin, [])
            if (gstin, norm_key) not in matched_gstr2b_keys
        ]
        fuzzy_norm = _fuzzy_match(norm, candidates)

        if fuzzy_norm:
            fuzzy_key   = (gstin, fuzzy_norm)
            gstr2b_inv  = gstr2b_lookup[fuzzy_key]
            gstr2b_tax  = gstr2b_inv.gstr2b_amount or gstr2b_inv.total_tax
            diff        = abs(books_tax - gstr2b_tax)
            total_itc_gstr2b += gstr2b_tax
            matched_gstr2b_keys.add(fuzzy_key)

            if diff > amount_tolerance:
                mismatched.append(MismatchedInvoice(
                    invoice_number=inv.invoice_number,
                    party_name=inv.party_name,
                    party_gstin=inv.party_gstin,
                    books_tax=round(books_tax, 2),
                    gstr2b_tax=round(gstr2b_tax, 2),
                    diff=round(diff, 2),
                    excess_itc=round(max(books_tax - gstr2b_tax, 0), 2),
                ))
            else:
                matched.append(MatchedInvoice(
                    invoice_number=inv.invoice_number,
                    party_name=inv.party_name,
                    party_gstin=inv.party_gstin,
                    books_tax=round(books_tax, 2),
                    gstr2b_tax=round(gstr2b_tax, 2),
                    diff=round(diff, 2),
                    match_type="fuzzy",
                    matched_inv_no=gstr2b_inv.invoice_number,
                ))
            continue

        # ── Case 3: Not found in GSTR-2B — ITC at risk ───────
        # Skip if invoice explicitly marked as in GSTR-2B
        if inv.is_in_gstr2b is True:
            continue

        missing.append(MissingInvoice(
            invoice_number=inv.invoice_number,
            party_name=inv.party_name,
            party_gstin=inv.party_gstin,
            invoice_date=str(inv.invoice_date) if inv.invoice_date else None,
            taxable_value=round(inv.taxable_value, 2),
            itc_at_risk=round(books_tax, 2),
        ))

    # ── Final calculations ────────────────────────────────────
    itc_at_risk       = sum(m.itc_at_risk for m in missing)
    itc_excess        = sum(m.excess_itc for m in mismatched)
    total_tax_loss    = round(itc_at_risk + itc_excess, 2)

    result = ReconciliationResult(
        period=period,
        our_gstin=our_gstin,
        total_purchase_invoices=len(books_invoices),
        total_gstr2b_invoices=len(gstr2b_invoices),
        matched_count=len(matched),
        missing_count=len(missing),
        mismatch_count=len(mismatched),
        total_itc_books=round(total_itc_books, 2),
        total_itc_gstr2b=round(total_itc_gstr2b, 2),
        itc_at_risk=round(itc_at_risk, 2),
        itc_excess_claimed=round(itc_excess, 2),
        total_tax_loss=total_tax_loss,
        matched=matched,
        missing=missing,
        mismatched=mismatched,
    )

    result.risk_level = _risk_level(total_tax_loss, total_itc_books)
    result.summary_en, result.summary_hi, result.summary_mr = _build_summary(result)

    logger.info(
        f"Reconciliation done | Matched={len(matched)} | "
        f"Missing={len(missing)} | Mismatch={len(mismatched)} | "
        f"Tax Loss=₹{total_tax_loss:,.2f} | Risk={result.risk_level}"
    )

    return result


# ═══════════════════════════════════════════════════════════════
# Serializer — React frontend ke liye clean JSON
# ═══════════════════════════════════════════════════════════════

def result_to_json(result: ReconciliationResult) -> dict:
    """Convert ReconciliationResult to JSON-serializable dict for API response."""
    return {
        "period":    result.period,
        "our_gstin": result.our_gstin,
        "summary": {
            "total_purchase_invoices": result.total_purchase_invoices,
            "total_gstr2b_invoices":   result.total_gstr2b_invoices,
            "matched_count":           result.matched_count,
            "missing_count":           result.missing_count,
            "mismatch_count":          result.mismatch_count,
            "risk_level":              result.risk_level,
            "summary_en":              result.summary_en,
            "summary_hi":              result.summary_hi,
            "summary_mr":              result.summary_mr,
        },
        "itc_impact": {
            "total_itc_books":     result.total_itc_books,
            "total_itc_gstr2b":    result.total_itc_gstr2b,
            "itc_at_risk":         result.itc_at_risk,
            "itc_excess_claimed":  result.itc_excess_claimed,
            "total_tax_loss":      result.total_tax_loss,
        },
        # React table data
        "matched": [
            {
                "invoice_number": m.invoice_number,
                "party_name":     m.party_name,
                "party_gstin":    m.party_gstin,
                "books_tax":      m.books_tax,
                "gstr2b_tax":     m.gstr2b_tax,
                "diff":           m.diff,
                "match_type":     m.match_type,
                "matched_inv_no": m.matched_inv_no,
                "status":         m.status,
            }
            for m in result.matched
        ],
        "missing": [
            {
                "invoice_number": m.invoice_number,
                "party_name":     m.party_name,
                "party_gstin":    m.party_gstin,
                "invoice_date":   m.invoice_date,
                "taxable_value":  m.taxable_value,
                "itc_at_risk":    m.itc_at_risk,
                "status":         m.status,
            }
            for m in result.missing
        ],
        "mismatched": [
            {
                "invoice_number": m.invoice_number,
                "party_name":     m.party_name,
                "party_gstin":    m.party_gstin,
                "books_tax":      m.books_tax,
                "gstr2b_tax":     m.gstr2b_tax,
                "diff":           m.diff,
                "excess_itc":     m.excess_itc,
                "status":         m.status,
            }
            for m in result.mismatched
        ],
    }