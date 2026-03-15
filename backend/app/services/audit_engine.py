"""
audit_engine.py
---------------
GST Audit Engine — 6 checks (L1 + L2).

Check list:
L1.1 — GSTIN Validation
L1.2 — Tax Type Check (IGST vs CGST+SGST)
L1.3 — Duplicate Invoice Detection
L2.1 — GSTR-2B Missing Invoice
L2.2 — Amount Mismatch (books vs GSTR-2B)
L2.3 — GSTR-1 Missing Invoice
"""
from typing import Optional
import logging

from app.models.invoice import Invoice, InvoiceType
from app.models.issue import Issue, IssueType, Severity
from app.utils.gstin_validator import validate_gstin
from app.utils.state_codes import is_interstate

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
# L1.1 — GSTIN Validation
# ═══════════════════════════════════════════════════════════════
def check_gstin_validation(invoices: list[Invoice]) -> list[Issue]:
    issues: list[Issue] = []
    seen: dict[str, bool] = {}

    for inv in invoices:
        if not inv.party_gstin:
            continue
        gstin = inv.party_gstin
        if gstin in seen:
            if not seen[gstin]:
                issues.append(_make_gstin_issue(inv, gstin))
            continue
        result = validate_gstin(gstin)
        seen[gstin] = result.is_valid
        if not result.is_valid:
            issues.append(_make_gstin_issue(inv, gstin, result.error))

    return issues


def _make_gstin_issue(
    inv: Invoice,
    gstin: str,
    error: Optional[str] = None,
) -> Issue:
    detail = f" ({error})" if error else ""
    return Issue(
        issue_type=IssueType.INVALID_GSTIN,
        severity=Severity.HIGH,
        invoice_number=inv.invoice_number,
        party_name=inv.party_name,
        party_gstin=gstin,
        amount=inv.total_tax,
        problem_en=(
            f"Invalid GSTIN: {gstin}{detail}. "
            "ITC claim will be rejected."
        ),
        problem_hi=(
            f"अमान्य GSTIN: {gstin}{detail}। "
            "ITC दावा अस्वीकृत होगा।"
        ),
        problem_mr=(
            f"अवैध GSTIN: {gstin}{detail}. "
            "ITC दावा नाकारला जाईल."
        ),
        legal_ref="CGST Act 2017, Section 25 — GST Registration",
        penalty_risk="Rs.10,000 per invoice penalty",
        fix_steps_en=[
            f"Verify correct GSTIN with the party.",
            "Search GSTIN on GST portal: search.gst.gov.in",
            "Amend the invoice once correct GSTIN is confirmed.",
            "If supplier's GSTIN is cancelled — reverse the ITC claim.",
        ],
        fix_steps_hi=[
            "पार्टी से सही GSTIN verify करें।",
            "GST पोर्टल पर GSTIN खोजें: search.gst.gov.in",
            "सही GSTIN मिलने पर invoice amend करें।",
            "अगर सप्लायर का GSTIN cancel है — ITC reverse करें।",
        ],
        fix_steps_mr=[
            "पार्टीकडून योग्य GSTIN तपासा.",
            "GST पोर्टलवर GSTIN शोधा: search.gst.gov.in",
            "योग्य GSTIN मिळाल्यावर बीजक दुरुस्त करा.",
            "पुरवठादाराचे GSTIN रद्द असल्यास — ITC परत करा.",
        ],
        itc_at_risk=inv.total_tax,
    )


# ═══════════════════════════════════════════════════════════════
# L1.2 — Tax Type Check (IGST vs CGST+SGST)
# ═══════════════════════════════════════════════════════════════
def check_tax_type(invoices: list[Invoice]) -> list[Issue]:
    issues: list[Issue] = []

    for inv in invoices:
        if not inv.party_gstin or not inv.our_gstin:
            continue
        if inv.total_tax == 0:
            continue

        interstate = is_interstate(inv.our_gstin, inv.party_gstin)

        # Inter-state but CGST+SGST charged
        if interstate and inv.cgst > 0 and inv.igst == 0:
            issues.append(Issue(
                issue_type=IssueType.TAX_TYPE_MISMATCH,
                severity=Severity.CRITICAL,
                invoice_number=inv.invoice_number,
                party_name=inv.party_name,
                party_gstin=inv.party_gstin,
                amount=inv.total_tax,
                problem_en=(
                    f"Inter-state supply to {inv.party_gstin[:2]} "
                    f"but CGST+SGST charged (Rs.{inv.cgst + inv.sgst:.2f}). "
                    "IGST must be applied."
                ),
                problem_hi=(
                    f"अंतर-राज्य आपूर्ति ({inv.party_gstin[:2]}) पर "
                    f"CGST+SGST (Rs.{inv.cgst + inv.sgst:.2f}) लगाया। "
                    "IGST लगना चाहिए था।"
                ),
                problem_mr=(
                    f"आंतरराज्य पुरवठा ({inv.party_gstin[:2]}) वर "
                    f"CGST+SGST (Rs.{inv.cgst + inv.sgst:.2f}) आकारला. "
                    "IGST आकारणे आवश्यक."
                ),
                legal_ref="IGST Act 2017, Section 8(2) — Inter-state supply",
                penalty_risk=f"10% of tax + 18% interest = Rs.{inv.total_tax * 0.28:.2f}",
                fix_steps_en=[
                    "Issue a credit note against the original invoice.",
                    "Raise a new invoice with IGST only.",
                    "Amend GSTR-1 in the next period.",
                    "Inform the buyer — their ITC is also affected.",
                ],
                fix_steps_hi=[
                    "Original invoice के against credit note जारी करें।",
                    "केवल IGST के साथ नई invoice बनाएं।",
                    "अगले period में GSTR-1 amend करें।",
                    "Buyer को inform करें — उनका ITC भी affected है।",
                ],
                fix_steps_mr=[
                    "मूळ बीजकाविरुद्ध credit note जारी करा.",
                    "फक्त IGST सह नवीन बीजक तयार करा.",
                    "पुढील कालावधीत GSTR-1 दुरुस्त करा.",
                    "Buyer ला कळवा — त्यांचे ITC देखील प्रभावित आहे.",
                ],
                itc_at_risk=inv.total_tax,
            ))

        # Intra-state but IGST charged
        elif not interstate and inv.igst > 0 and inv.cgst == 0:
            issues.append(Issue(
                issue_type=IssueType.TAX_TYPE_MISMATCH,
                severity=Severity.CRITICAL,
                invoice_number=inv.invoice_number,
                party_name=inv.party_name,
                party_gstin=inv.party_gstin,
                amount=inv.total_tax,
                problem_en=(
                    f"Intra-state supply but IGST charged "
                    f"(Rs.{inv.igst:.2f}). CGST+SGST must be applied."
                ),
                problem_hi=(
                    f"राज्य के अंदर आपूर्ति पर IGST "
                    f"(Rs.{inv.igst:.2f}) लगाया। "
                    "CGST+SGST लगना चाहिए था।"
                ),
                problem_mr=(
                    f"राज्यांतर्गत पुरवठ्यावर IGST "
                    f"(Rs.{inv.igst:.2f}) आकारला. "
                    "CGST+SGST आकारणे आवश्यक."
                ),
                legal_ref="CGST Act 2017, Section 9 — Intra-state supply",
                penalty_risk=f"10% of tax + 18% interest = Rs.{inv.total_tax * 0.28:.2f}",
                fix_steps_en=[
                    "Issue a credit note against the original invoice.",
                    "Raise a new invoice with CGST + SGST only.",
                    "Amend GSTR-1 in the next period.",
                ],
                fix_steps_hi=[
                    "Original invoice के against credit note जारी करें।",
                    "केवल CGST + SGST के साथ नई invoice बनाएं।",
                    "अगले period में GSTR-1 amend करें।",
                ],
                fix_steps_mr=[
                    "मूळ बीजकाविरुद्ध credit note जारी करा.",
                    "फक्त CGST + SGST सह नवीन बीजक तयार करा.",
                    "पुढील कालावधीत GSTR-1 दुरुस्त करा.",
                ],
                itc_at_risk=inv.total_tax,
            ))

    return issues


# ═══════════════════════════════════════════════════════════════
# L1.3 — Duplicate Invoice Detection
# ═══════════════════════════════════════════════════════════════
def check_duplicate_invoices(invoices: list[Invoice]) -> list[Issue]:
    issues: list[Issue] = []
    seen: dict[tuple, Invoice] = {}

    for inv in invoices:
        key = (
            inv.party_gstin or "UNKNOWN",
            inv.invoice_number,
            str(inv.invoice_date or ""),
        )
        if key in seen:
            issues.append(Issue(
                issue_type=IssueType.DUPLICATE_INVOICE,
                severity=Severity.HIGH,
                invoice_number=inv.invoice_number,
                party_name=inv.party_name,
                party_gstin=inv.party_gstin,
                amount=inv.total_tax,
                problem_en=(
                    f"Invoice {inv.invoice_number} from "
                    f"{inv.party_name or inv.party_gstin} appears twice. "
                    "Double ITC claim will be rejected."
                ),
                problem_hi=(
                    f"Invoice {inv.invoice_number} "
                    f"({inv.party_name or inv.party_gstin}) दो बार है। "
                    "Double ITC claim अस्वीकृत होगा।"
                ),
                problem_mr=(
                    f"Invoice {inv.invoice_number} "
                    f"({inv.party_name or inv.party_gstin}) दोनदा आहे. "
                    "Double ITC दावा नाकारला जाईल."
                ),
                legal_ref="CGST Act 2017, Section 16(2) — ITC conditions, Section 122 — Penalty",
                penalty_risk="100% of duplicate ITC amount as penalty",
                fix_steps_en=[
                    f"Remove the duplicate entry of invoice {inv.invoice_number}.",
                    "Keep only one entry per invoice number per supplier.",
                    "Check your purchase register for other duplicates.",
                    "Claim ITC only once in GSTR-3B.",
                ],
                fix_steps_hi=[
                    f"Invoice {inv.invoice_number} की duplicate entry हटाएं।",
                    "प्रत्येक सप्लायर का invoice एक बार ही रखें।",
                    "Purchase register में अन्य duplicates भी check करें।",
                    "GSTR-3B में ITC सिर्फ एक बार claim करें।",
                ],
                fix_steps_mr=[
                    f"Invoice {inv.invoice_number} ची duplicate नोंद काढा.",
                    "प्रत्येक पुरवठादाराचे बीजक फक्त एकदाच ठेवा.",
                    "Purchase register मध्ये इतर duplicates तपासा.",
                    "GSTR-3B मध्ये ITC फक्त एकदाच दावा करा.",
                ],
                itc_at_risk=inv.total_tax,
            ))
        else:
            seen[key] = inv

    return issues


# ═══════════════════════════════════════════════════════════════
# L2.1 — GSTR-2B Missing Invoice
# ═══════════════════════════════════════════════════════════════
def check_gstr2b_missing(invoices: list[Invoice]) -> list[Issue]:
    issues: list[Issue] = []

    for inv in invoices:
        if inv.invoice_type != InvoiceType.PURCHASE:
            continue
        if inv.is_in_gstr2b is False and inv.total_tax > 0:
            issues.append(Issue(
                issue_type=IssueType.GSTR2B_MISSING,
                severity=Severity.HIGH,
                invoice_number=inv.invoice_number,
                party_name=inv.party_name,
                party_gstin=inv.party_gstin,
                amount=inv.total_tax,
                problem_en=(
                    f"Invoice {inv.invoice_number} from "
                    f"{inv.party_name or inv.party_gstin} "
                    f"not in GSTR-2B. ITC of Rs.{inv.total_tax:.2f} "
                    "cannot be claimed."
                ),
                problem_hi=(
                    f"Invoice {inv.invoice_number} "
                    f"({inv.party_name or inv.party_gstin}) "
                    f"GSTR-2B में नहीं है। "
                    f"Rs.{inv.total_tax:.2f} का ITC claim नहीं कर सकते।"
                ),
                problem_mr=(
                    f"Invoice {inv.invoice_number} "
                    f"({inv.party_name or inv.party_gstin}) "
                    f"GSTR-2B मध्ये नाही. "
                    f"Rs.{inv.total_tax:.2f} चा ITC दावा करता येणार नाही."
                ),
                legal_ref=(
                    "CGST Act 2017, Section 16(2)(aa) — "
                    "ITC only if invoice in GSTR-2B (Finance Act 2021)"
                ),
                penalty_risk=f"ITC reversal + 18% interest = Rs.{inv.total_tax * 1.18:.2f}",
                fix_steps_en=[
                    f"Contact supplier ({inv.party_name or inv.party_gstin}) to file their pending GSTR-1.",
                    "Do NOT claim ITC until the invoice appears in GSTR-2B.",
                    "Check GSTR-2B again next month after supplier files.",
                    "If supplier repeatedly fails to file — consider switching supplier.",
                ],
                fix_steps_hi=[
                    f"Supplier ({inv.party_name or inv.party_gstin}) से pending GSTR-1 file करवाएं।",
                    "GSTR-2B में आने तक ITC claim बिल्कुल न करें।",
                    "Supplier के file करने के बाद अगले महीने GSTR-2B check करें।",
                    "अगर supplier बार-बार file नहीं करता — supplier बदलने पर विचार करें।",
                ],
                fix_steps_mr=[
                    f"पुरवठादार ({inv.party_name or inv.party_gstin}) ला प्रलंबित GSTR-1 दाखल करण्यास सांगा.",
                    "GSTR-2B मध्ये येईपर्यंत ITC दावा करू नका.",
                    "पुरवठादाराने दाखल केल्यानंतर पुढील महिन्यात GSTR-2B तपासा.",
                    "पुरवठादार वारंवार दाखल करत नसल्यास — पुरवठादार बदलण्याचा विचार करा.",
                ],
                itc_at_risk=inv.total_tax,
            ))

    return issues


# ═══════════════════════════════════════════════════════════════
# L2.2 — Amount Mismatch (Books vs GSTR-2B)
# ═══════════════════════════════════════════════════════════════
def check_amount_mismatch(
    invoices: list[Invoice],
    tolerance: float = 1.0,
) -> list[Issue]:
    issues: list[Issue] = []

    for inv in invoices:
        if inv.invoice_type != InvoiceType.PURCHASE:
            continue
        if inv.gstr2b_amount is None:
            continue
        if inv.is_in_gstr2b is False:
            continue

        books_tax  = inv.total_tax
        gstr2b_tax = inv.gstr2b_amount
        diff       = abs(books_tax - gstr2b_tax)

        if diff > tolerance:
            issues.append(Issue(
                issue_type=IssueType.AMOUNT_MISMATCH,
                severity=Severity.MEDIUM,
                invoice_number=inv.invoice_number,
                party_name=inv.party_name,
                party_gstin=inv.party_gstin,
                amount=diff,
                problem_en=(
                    f"Invoice {inv.invoice_number}: Books tax "
                    f"Rs.{books_tax:.2f} vs GSTR-2B Rs.{gstr2b_tax:.2f}. "
                    f"Difference Rs.{diff:.2f} — ITC on excess not allowed."
                ),
                problem_hi=(
                    f"Invoice {inv.invoice_number}: Books में tax "
                    f"Rs.{books_tax:.2f} vs GSTR-2B Rs.{gstr2b_tax:.2f}। "
                    f"अंतर Rs.{diff:.2f} — excess पर ITC नहीं मिलेगा।"
                ),
                problem_mr=(
                    f"Invoice {inv.invoice_number}: Books मध्ये कर "
                    f"Rs.{books_tax:.2f} vs GSTR-2B Rs.{gstr2b_tax:.2f}. "
                    f"फरक Rs.{diff:.2f} — जास्तीवर ITC मिळणार नाही."
                ),
                legal_ref="CGST Rule 36(4) — ITC limited to GSTR-2B amount",
                penalty_risk=f"Excess ITC Rs.{diff:.2f} disallowed + 18% interest",
                fix_steps_en=[
                    f"Claim ITC of Rs.{gstr2b_tax:.2f} only (GSTR-2B amount).",
                    f"Do not claim the excess Rs.{diff:.2f}.",
                    "Contact supplier to correct the amount in their GSTR-1.",
                    "Update your books to match the GSTR-2B figure.",
                ],
                fix_steps_hi=[
                    f"केवल Rs.{gstr2b_tax:.2f} का ITC claim करें (GSTR-2B amount)।",
                    f"Excess Rs.{diff:.2f} का ITC claim न करें।",
                    "Supplier से GSTR-1 में amount correct करवाएं।",
                    "अपनी books को GSTR-2B amount से match करें।",
                ],
                fix_steps_mr=[
                    f"फक्त Rs.{gstr2b_tax:.2f} चा ITC दावा करा (GSTR-2B रक्कम).",
                    f"जास्तीचा Rs.{diff:.2f} ITC दावा करू नका.",
                    "पुरवठादाराला GSTR-1 मध्ये रक्कम दुरुस्त करण्यास सांगा.",
                    "तुमच्या books GSTR-2B रकमेशी जुळवा.",
                ],
                itc_at_risk=diff,
            ))

    return issues


# ═══════════════════════════════════════════════════════════════
# L2.3 — GSTR-1 Missing Invoice (Sales)
# ═══════════════════════════════════════════════════════════════
def check_gstr1_missing(invoices: list[Invoice]) -> list[Issue]:
    issues: list[Issue] = []

    for inv in invoices:
        if inv.invoice_type != InvoiceType.SALE:
            continue
        if inv.is_in_gstr1 is False and inv.total_tax > 0:
            issues.append(Issue(
                issue_type=IssueType.GSTR1_MISSING,
                severity=Severity.HIGH,
                invoice_number=inv.invoice_number,
                party_name=inv.party_name,
                party_gstin=inv.party_gstin,
                amount=inv.total_tax,
                problem_en=(
                    f"Sale invoice {inv.invoice_number} "
                    f"(Rs.{inv.taxable_value:.2f}) not reported in GSTR-1. "
                    "Buyer cannot claim ITC. Late fee applicable."
                ),
                problem_hi=(
                    f"Sales invoice {inv.invoice_number} "
                    f"(Rs.{inv.taxable_value:.2f}) GSTR-1 में report नहीं। "
                    "Buyer ITC claim नहीं कर सकता। Late fee लागू।"
                ),
                problem_mr=(
                    f"विक्री बीजक {inv.invoice_number} "
                    f"(Rs.{inv.taxable_value:.2f}) GSTR-1 मध्ये नाही. "
                    "Buyer ITC घेऊ शकत नाही. विलंब शुल्क लागू."
                ),
                legal_ref=(
                    "CGST Act 2017, Section 37 — GSTR-1 mandatory. "
                    "Section 47 — Late fee Rs.50/day (max Rs.10,000)"
                ),
                penalty_risk="Rs.50/day late fee + buyer's ITC loss",
                fix_steps_en=[
                    f"Add invoice {inv.invoice_number} to GSTR-1 immediately.",
                    "If deadline has passed — report it in the next month's GSTR-1.",
                    "Inform the buyer — they must wait for ITC until GSTR-2B is updated.",
                    "Calculate the late fee and pay before filing.",
                ],
                fix_steps_hi=[
                    f"Invoice {inv.invoice_number} को तुरंत GSTR-1 में add करें।",
                    "Deadline निकल गई है — अगले महीने की GSTR-1 में report करें।",
                    "Buyer को inform करें — GSTR-2B update होने तक ITC नहीं मिलेगा।",
                    "Late fee calculate करें और file करने से पहले pay करें।",
                ],
                fix_steps_mr=[
                    f"Invoice {inv.invoice_number} लगेच GSTR-1 मध्ये जोडा.",
                    "Deadline गेली असल्यास — पुढील महिन्याच्या GSTR-1 मध्ये नोंदवा.",
                    "Buyer ला कळवा — GSTR-2B अपडेट होईपर्यंत ITC मिळणार नाही.",
                    "Late fee calculate करा आणि दाखल करण्यापूर्वी भरा.",
                ],
                itc_at_risk=0.0,
            ))

    return issues


# ═══════════════════════════════════════════════════════════════
# MAIN — Run All Checks
# ═══════════════════════════════════════════════════════════════
def run_all_checks(
    invoices: list[Invoice],
    our_gstin: str,
    period: Optional[str] = None,
) -> list[Issue]:
    """Run all 6 checks and return combined issues sorted by severity."""
    logger.info(
        f"Running audit on {len(invoices)} invoices "
        f"| GSTIN: {our_gstin[:2]}*** | Period: {period}"
    )

    all_issues: list[Issue] = []

    # L1 Checks
    all_issues.extend(check_gstin_validation(invoices))
    all_issues.extend(check_tax_type(invoices))
    all_issues.extend(check_duplicate_invoices(invoices))

    # L2 Checks
    all_issues.extend(check_gstr2b_missing(invoices))
    all_issues.extend(check_amount_mismatch(invoices))
    all_issues.extend(check_gstr1_missing(invoices))

    # Sort by severity: CRITICAL → HIGH → MEDIUM → LOW
    severity_order = {
        Severity.CRITICAL: 0,
        Severity.HIGH:     1,
        Severity.MEDIUM:   2,
        Severity.LOW:      3,
    }
    all_issues.sort(key=lambda x: severity_order.get(x.severity, 99))

    logger.info(
        f"Audit complete — {len(all_issues)} issues | "
        f"CRITICAL={sum(1 for i in all_issues if i.severity == Severity.CRITICAL)}, "
        f"HIGH={sum(1 for i in all_issues if i.severity == Severity.HIGH)}, "
        f"MEDIUM={sum(1 for i in all_issues if i.severity == Severity.MEDIUM)}"
    )

    return all_issues