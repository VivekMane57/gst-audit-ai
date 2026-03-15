"""
services/sector_checks.py
--------------------------
Sector-specific GST audit checks.

Sectors:
  healthcare    — Pharma / Hospital
  retail        — Trading / Shop
  manufacturing — Factory / Production
  it_services   — Software / Consulting
  real_estate   — Builder / Property
  restaurant    — Food / Hotel
  export_import — Exporter / Importer
"""
from typing import Optional
from app.models.invoice import Invoice, InvoiceType
from app.models.issue import Issue, IssueType, Severity
import logging

logger = logging.getLogger(__name__)

# ── HSN codes by sector ───────────────────────────────────────
HEALTHCARE_HSN  = {"3004", "3006", "3002", "3003", "3001", "9018", "9019", "9021"}
RESTAURANT_HSN  = {"9963", "9964", "0801", "0901", "1001"}
IT_SAC          = {"9983", "9984", "9985", "9986", "9997"}
MANUFACTURING_CAPITAL_HSN = {"8471", "8479", "8481", "8482", "8483", "8484"}

# ── Nil-rated HSN for healthcare ─────────────────────────────
NIL_RATED_HSN = {
    "3004": "Medicines — GST exempt/nil-rated check required",
    "3006": "Pharmaceutical preparations",
    "9018": "Medical instruments — verify exemption",
}


def run_sector_checks(
    invoices: list[Invoice],
    sector: str,
    our_gstin: str,
) -> list[Issue]:
    """
    Sector ke hisaab se specific checks run karo.
    Returns list of Issues.
    """
    sector = sector.lower().strip()
    issues: list[Issue] = []

    sector_map = {
        "healthcare":    _check_healthcare,
        "retail":        _check_retail,
        "manufacturing": _check_manufacturing,
        "it_services":   _check_it_services,
        "real_estate":   _check_real_estate,
        "restaurant":    _check_restaurant,
        "export_import": _check_export_import,
    }

    fn = sector_map.get(sector)
    if fn:
        issues.extend(fn(invoices, our_gstin))
    else:
        logger.warning(f"Unknown sector: {sector}")

    return issues


# ═══════════════════════════════════════════════════════════════
# HEALTHCARE / PHARMA
# ═══════════════════════════════════════════════════════════════
def _check_healthcare(invoices: list[Invoice], our_gstin: str) -> list[Issue]:
    issues = []

    for inv in invoices:
        if not inv.hsn_code:
            continue

        hsn = inv.hsn_code[:4]

        # Check 1: Nil-rated medicine pe tax charge kiya?
        if hsn in NIL_RATED_HSN and inv.total_tax > 0:
            issues.append(Issue(
                issue_type=IssueType.SECTOR_SPECIFIC,
                severity=Severity.CRITICAL,
                invoice_number=inv.invoice_number,
                party_name=inv.party_name,
                party_gstin=inv.party_gstin,
                amount=inv.total_tax,
                problem_en=(
                    f"HSN {hsn} ({NIL_RATED_HSN[hsn]}) is nil-rated/exempt. "
                    f"Tax of Rs.{inv.total_tax:.2f} should NOT be charged."
                ),
                problem_hi=(
                    f"HSN {hsn} nil-rated है। "
                    f"Rs.{inv.total_tax:.2f} का टैक्स गलत है।"
                ),
                problem_mr=(
                    f"HSN {hsn} nil-rated आहे. "
                    f"Rs.{inv.total_tax:.2f} कर चुकीचा आहे."
                ),
                legal_ref="GST Notification 02/2017 — Nil-rated medicines list",
                penalty_risk="Full tax amount refundable + ITC reversal for buyer",
                fix_steps=[
                    f"HSN {hsn} ki exemption list GST portal pe verify karo",
                    "Credit note issue karo — tax waapas karo buyer ko",
                    "GSTR-1 mein amend karo",
                    "Nil-rated supply report karo GSTR-1 Table 8 mein",
                ],
                itc_at_risk=inv.total_tax,
            ))

        # Check 2: ITC reversal — exempt drugs pe ITC nahi milti
        if (hsn in HEALTHCARE_HSN
                and inv.invoice_type == InvoiceType.PURCHASE
                and inv.total_tax > 0
                and inv.is_in_gstr2b):
            issues.append(Issue(
                issue_type=IssueType.SECTOR_SPECIFIC,
                severity=Severity.HIGH,
                invoice_number=inv.invoice_number,
                party_name=inv.party_name,
                party_gstin=inv.party_gstin,
                amount=inv.total_tax,
                problem_en=(
                    f"HSN {hsn} purchase — verify ITC eligibility. "
                    "Hospitals with exempt supply must reverse proportionate ITC."
                ),
                problem_hi=(
                    f"HSN {hsn} खरीद — ITC eligibility verify करें। "
                    "Exempt supply पर proportionate ITC reverse करना होगा।"
                ),
                problem_mr=(
                    f"HSN {hsn} खरेदी — ITC पात्रता तपासा. "
                    "Exempt पुरवठ्यावर proportionate ITC परत करावे लागेल."
                ),
                legal_ref="CGST Act Section 17(2) — Proportionate ITC reversal",
                penalty_risk="ITC reversal + 18% interest if not reversed",
                fix_steps=[
                    "Taxable vs exempt supply ka ratio calculate karo",
                    "Rule 42/43 ke hisaab se ITC reverse karo",
                    "GSTR-3B Table 4(B)(2) mein reversal show karo",
                ],
                itc_at_risk=inv.total_tax * 0.5,
            ))

    return issues


# ═══════════════════════════════════════════════════════════════
# RETAIL / TRADING
# ═══════════════════════════════════════════════════════════════
def _check_retail(invoices: list[Invoice], our_gstin: str) -> list[Issue]:
    issues = []

    # Check: B2C invoice > Rs.2.5L — separately reportable in GSTR-1
    for inv in invoices:
        if (inv.invoice_type == InvoiceType.SALE
                and not inv.party_gstin
                and inv.taxable_value > 250000):
            issues.append(Issue(
                issue_type=IssueType.SECTOR_SPECIFIC,
                severity=Severity.MEDIUM,
                invoice_number=inv.invoice_number,
                party_name=inv.party_name or "B2C Customer",
                party_gstin=None,
                amount=inv.total_tax,
                problem_en=(
                    f"B2C invoice Rs.{inv.taxable_value:.2f} exceeds Rs.2.5L. "
                    "Must be reported separately in GSTR-1 Table 5 (B2CL)."
                ),
                problem_hi=(
                    f"B2C invoice Rs.{inv.taxable_value:.2f} — Rs.2.5L से अधिक। "
                    "GSTR-1 Table 5 में अलग से report करें।"
                ),
                problem_mr=(
                    f"B2C बीजक Rs.{inv.taxable_value:.2f} — Rs.2.5L पेक्षा जास्त. "
                    "GSTR-1 Table 5 मध्ये स्वतंत्रपणे नोंदवा."
                ),
                legal_ref="CGST Rule 59 — GSTR-1 Table 5 B2CL reporting",
                penalty_risk="Rs.200/day late fee if not reported",
                fix_steps=[
                    "GSTR-1 Table 5 (B2CL) mein ye invoice add karo",
                    "State-wise breakup dena hoga",
                    "Invoice number aur date correctly enter karo",
                ],
                itc_at_risk=0,
            ))

    # Check: Composition scheme — turnover limit
    total_sales = sum(
        inv.taxable_value for inv in invoices
        if inv.invoice_type == InvoiceType.SALE
    )
    if total_sales > 1500000:  # Rs.15L per month = Rs.1.5Cr annually
        issues.append(Issue(
            issue_type=IssueType.SECTOR_SPECIFIC,
            severity=Severity.HIGH,
            invoice_number="TURNOVER-CHECK",
            party_name=None,
            party_gstin=None,
            amount=total_sales,
            problem_en=(
                f"Monthly sales Rs.{total_sales:.2f} seems high. "
                "Verify annual turnover for composition scheme eligibility (Rs.1.5Cr limit)."
            ),
            problem_hi=(
                f"मासिक बिक्री Rs.{total_sales:.2f} — "
                "Composition scheme limit (₹1.5Cr) verify करें।"
            ),
            problem_mr=(
                f"मासिक विक्री Rs.{total_sales:.2f} — "
                "Composition scheme मर्यादा (₹1.5Cr) तपासा."
            ),
            legal_ref="CGST Act Section 10 — Composition Scheme Rs.1.5Cr limit",
            penalty_risk="Composition scheme cancellation + back tax + penalty",
            fix_steps=[
                "Annual turnover calculate karo",
                "Rs.1.5Cr se upar gaye — regular scheme pe shift karo",
                "GST officer ko inform karo — voluntary cancellation",
            ],
            itc_at_risk=0,
        ))

    return issues


# ═══════════════════════════════════════════════════════════════
# MANUFACTURING
# ═══════════════════════════════════════════════════════════════
def _check_manufacturing(invoices: list[Invoice], our_gstin: str) -> list[Issue]:
    issues = []

    for inv in invoices:
        # Check 1: Job work — 45 day rule (purchase side)
        if (inv.invoice_type == InvoiceType.PURCHASE
                and inv.invoice_date
                and not inv.payment_date
                and inv.hsn_code
                and inv.hsn_code[:4] in {"9988", "9987"}):  # Job work SAC
            from datetime import date
            days = (date.today() - inv.invoice_date).days
            if days > 45:
                issues.append(Issue(
                    issue_type=IssueType.SECTOR_SPECIFIC,
                    severity=Severity.HIGH,
                    invoice_number=inv.invoice_number,
                    party_name=inv.party_name,
                    party_gstin=inv.party_gstin,
                    amount=inv.taxable_value,
                    problem_en=(
                        f"Job work goods sent {days} days ago. "
                        "Goods must return within 1 year (inputs) or 3 years (capital goods). "
                        "Challan mandatory."
                    ),
                    problem_hi=(
                        f"Job work {days} दिन पहले भेजा। "
                        "1 साल (inputs) या 3 साल (capital goods) में वापस आना चाहिए।"
                    ),
                    problem_mr=(
                        f"Job work {days} दिवसांपूर्वी पाठवले. "
                        "1 वर्ष (inputs) किंवा 3 वर्षांत परत येणे आवश्यक."
                    ),
                    legal_ref="CGST Act Section 143 — Job Work provisions",
                    penalty_risk="Deemed supply — GST + 18% interest payable",
                    fix_steps=[
                        "Job work challan check karo — ITC-04 file karo",
                        "Goods wapas mangao within deadline",
                        "Agar deadline gayi — GST pay karo + interest",
                    ],
                    itc_at_risk=inv.total_tax,
                ))

        # Check 2: Capital goods ITC — only 1/5th per year
        if (inv.invoice_type == InvoiceType.PURCHASE
                and inv.hsn_code
                and inv.hsn_code[:4] in MANUFACTURING_CAPITAL_HSN
                and inv.total_tax > 50000):
            issues.append(Issue(
                issue_type=IssueType.SECTOR_SPECIFIC,
                severity=Severity.MEDIUM,
                invoice_number=inv.invoice_number,
                party_name=inv.party_name,
                party_gstin=inv.party_gstin,
                amount=inv.total_tax,
                problem_en=(
                    f"Capital goods HSN {inv.hsn_code[:4]} — "
                    f"ITC of Rs.{inv.total_tax:.2f}. "
                    "Verify: ITC on capital goods spread over useful life if used for exempt supply."
                ),
                problem_hi=(
                    f"Capital goods HSN {inv.hsn_code[:4]} — "
                    "ITC useful life pe spread करें अगर exempt supply के लिए उपयोग।"
                ),
                problem_mr=(
                    f"Capital goods HSN {inv.hsn_code[:4]} — "
                    "Exempt पुरवठ्यासाठी वापरल्यास ITC useful life वर पसरवा."
                ),
                legal_ref="CGST Rule 43 — ITC on capital goods proportionate reversal",
                penalty_risk="ITC reversal proportionate to exempt use",
                fix_steps=[
                    "Capital goods register maintain karo",
                    "Taxable vs exempt use ka ratio calculate karo",
                    "Rule 43 ke hisaab se monthly reversal karo",
                ],
                itc_at_risk=inv.total_tax * 0.3,
            ))

    return issues


# ═══════════════════════════════════════════════════════════════
# IT / SERVICES
# ═══════════════════════════════════════════════════════════════
def _check_it_services(invoices: list[Invoice], our_gstin: str) -> list[Issue]:
    issues = []

    for inv in invoices:
        if inv.invoice_type != InvoiceType.SALE:
            continue

        # Check 1: Export invoice — LUT check
        if (inv.party_gstin is None and inv.igst == 0 and inv.total_tax == 0
                and inv.taxable_value > 0):
            issues.append(Issue(
                issue_type=IssueType.SECTOR_SPECIFIC,
                severity=Severity.HIGH,
                invoice_number=inv.invoice_number,
                party_name=inv.party_name or "Foreign Client",
                party_gstin=None,
                amount=inv.taxable_value,
                problem_en=(
                    f"Zero-tax invoice {inv.invoice_number} — "
                    "likely export. Verify LUT (Letter of Undertaking) is filed. "
                    "Without LUT, IGST must be paid."
                ),
                problem_hi=(
                    f"Zero-tax invoice — Export है तो LUT filed होना चाहिए। "
                    "LUT के बिना IGST pay करना होगा।"
                ),
                problem_mr=(
                    f"Zero-tax बीजक — Export असल्यास LUT दाखल असणे आवश्यक. "
                    "LUT शिवाय IGST भरावा लागेल."
                ),
                legal_ref="CGST Rule 96A — Export without payment of tax (LUT)",
                penalty_risk="IGST payable on full export value + 18% interest",
                fix_steps=[
                    "GST portal pe LUT filing status check karo",
                    "Agar LUT nahi — turant file karo (Form RFD-11)",
                    "Foreign payment FIRC/BRC collect karo",
                    "GSTR-1 Table 6A mein export report karo",
                ],
                itc_at_risk=inv.taxable_value * 0.18,
            ))

        # Check 2: RCM on import of services
        if (inv.party_gstin and inv.party_gstin[:2] not in [our_gstin[:2]]
                and inv.hsn_code and inv.hsn_code[:4] in IT_SAC
                and inv.igst == 0):
            issues.append(Issue(
                issue_type=IssueType.SECTOR_SPECIFIC,
                severity=Severity.MEDIUM,
                invoice_number=inv.invoice_number,
                party_name=inv.party_name,
                party_gstin=inv.party_gstin,
                amount=inv.taxable_value * 0.18,
                problem_en=(
                    f"IT service purchase from {inv.party_gstin[:2]} state "
                    "with no IGST — verify if RCM (Reverse Charge) applies."
                ),
                problem_hi=(
                    "IT service purchase — RCM applicability verify करें।"
                ),
                problem_mr=(
                    "IT सेवा खरेदी — RCM लागू आहे का तपासा."
                ),
                legal_ref="CGST Act Section 9(3) — RCM on specified services",
                penalty_risk="RCM GST + 18% interest if not paid",
                fix_steps=[
                    "Supplier ka registration status check karo",
                    "Agar unregistered supplier — RCM pay karo",
                    "GSTR-3B Table 3.1(d) mein RCM report karo",
                ],
                itc_at_risk=0,
            ))

    return issues


# ═══════════════════════════════════════════════════════════════
# REAL ESTATE
# ═══════════════════════════════════════════════════════════════
def _check_real_estate(invoices: list[Invoice], our_gstin: str) -> list[Issue]:
    issues = []

    for inv in invoices:
        if not inv.hsn_code:
            continue

        hsn4 = inv.hsn_code[:4]

        # Check 1: Works contract — 12% or 18%?
        if hsn4 in {"9954"}:
            expected_rate = inv.taxable_value * 0.12
            if abs(inv.total_tax - expected_rate) > 100:
                issues.append(Issue(
                    issue_type=IssueType.SECTOR_SPECIFIC,
                    severity=Severity.HIGH,
                    invoice_number=inv.invoice_number,
                    party_name=inv.party_name,
                    party_gstin=inv.party_gstin,
                    amount=abs(inv.total_tax - expected_rate),
                    problem_en=(
                        f"Works contract HSN 9954 — tax Rs.{inv.total_tax:.2f}. "
                        "Residential = 12%, Commercial = 18%. Verify correct rate applied."
                    ),
                    problem_hi=(
                        "Works contract — Residential 12%, Commercial 18%। "
                        "Correct rate verify करें।"
                    ),
                    problem_mr=(
                        "Works contract — Residential 12%, Commercial 18%. "
                        "योग्य दर तपासा."
                    ),
                    legal_ref="GST Notification 11/2017 — Works Contract rate",
                    penalty_risk="Differential tax + 18% interest",
                    fix_steps=[
                        "Project type confirm karo — residential ya commercial",
                        "Agar residential affordable housing — 1% rate applicable",
                        "Rate mismatch hai toh credit note + revised invoice",
                    ],
                    itc_at_risk=abs(inv.total_tax - expected_rate),
                ))

        # Check 2: ITC reversal on unsold flats
        if (hsn4 in {"9954", "9972"}
                and inv.invoice_type == InvoiceType.PURCHASE
                and inv.total_tax > 10000):
            issues.append(Issue(
                issue_type=IssueType.SECTOR_SPECIFIC,
                severity=Severity.MEDIUM,
                invoice_number=inv.invoice_number,
                party_name=inv.party_name,
                party_gstin=inv.party_gstin,
                amount=inv.total_tax,
                problem_en=(
                    "Real estate purchase — ITC must be reversed proportionately "
                    "for unsold flats / exempt supply (land sale)."
                ),
                problem_hi=(
                    "Real estate purchase — unsold flats aur land sale "
                    "ke liye proportionate ITC reversal required."
                ),
                problem_mr=(
                    "Real estate खरेदी — न विकलेल्या सदनिका व जमीन विक्रीसाठी "
                    "ITC परत करणे आवश्यक."
                ),
                legal_ref="CGST Rule 42 — ITC reversal proportionate to exempt supply",
                penalty_risk="ITC reversal with 18% interest",
                fix_steps=[
                    "Sold vs unsold flats ka ratio maintain karo",
                    "Rule 42 formula: T2 = (T1 × E/F)",
                    "Annual adjustment GSTR-9 mein karo",
                ],
                itc_at_risk=inv.total_tax * 0.4,
            ))

    return issues


# ═══════════════════════════════════════════════════════════════
# RESTAURANT / FOOD
# ═══════════════════════════════════════════════════════════════
def _check_restaurant(invoices: list[Invoice], our_gstin: str) -> list[Issue]:
    issues = []

    for inv in invoices:
        if not inv.hsn_code:
            continue

        hsn4 = inv.hsn_code[:4]

        # Check 1: Restaurant — 5% rate, NO ITC claim allowed
        if hsn4 in {"9963"} and inv.invoice_type == InvoiceType.PURCHASE:
            if inv.is_in_gstr2b and inv.total_tax > 0:
                issues.append(Issue(
                    issue_type=IssueType.SECTOR_SPECIFIC,
                    severity=Severity.CRITICAL,
                    invoice_number=inv.invoice_number,
                    party_name=inv.party_name,
                    party_gstin=inv.party_gstin,
                    amount=inv.total_tax,
                    problem_en=(
                        "Restaurant under 5% scheme CANNOT claim ITC on inputs. "
                        f"ITC of Rs.{inv.total_tax:.2f} must be reversed immediately."
                    ),
                    problem_hi=(
                        "5% scheme restaurant — input pe ITC नहीं मिलती। "
                        f"Rs.{inv.total_tax:.2f} का ITC reverse करें।"
                    ),
                    problem_mr=(
                        "5% scheme restaurant — input वर ITC मिळत नाही. "
                        f"Rs.{inv.total_tax:.2f} ITC परत करा."
                    ),
                    legal_ref="GST Notification 11/2017 — Restaurant 5% no ITC",
                    penalty_risk="100% ITC reversal + 18% interest",
                    fix_steps=[
                        "Restaurant 5% scheme mein hai — ITC claim BILKUL mat karo",
                        "Claimed ITC GSTR-3B Table 4(B) mein reverse karo",
                        "Agar 18% scheme prefer karo toh GST officer ko inform karo",
                    ],
                    itc_at_risk=inv.total_tax,
                ))

        # Check 2: AC restaurant — 5% correct rate?
        if (hsn4 in {"9963"}
                and inv.invoice_type == InvoiceType.SALE
                and inv.total_tax > 0):
            effective_rate = (inv.total_tax / inv.taxable_value * 100) if inv.taxable_value else 0
            if abs(effective_rate - 5.0) > 0.5 and abs(effective_rate - 18.0) > 0.5:
                issues.append(Issue(
                    issue_type=IssueType.SECTOR_SPECIFIC,
                    severity=Severity.HIGH,
                    invoice_number=inv.invoice_number,
                    party_name=inv.party_name,
                    party_gstin=inv.party_gstin,
                    amount=inv.total_tax,
                    problem_en=(
                        f"Restaurant sale — tax rate {effective_rate:.1f}%. "
                        "Should be 5% (no ITC) or 18% (with ITC). Wrong rate applied."
                    ),
                    problem_hi=(
                        f"Restaurant sale — rate {effective_rate:.1f}% है। "
                        "5% (no ITC) ya 18% (with ITC) hona chahiye।"
                    ),
                    problem_mr=(
                        f"Restaurant विक्री — दर {effective_rate:.1f}% आहे. "
                        "5% (ITC नाही) किंवा 18% (ITC सह) असणे आवश्यक."
                    ),
                    legal_ref="GST Notification 11/2017 — Restaurant rates",
                    penalty_risk="Differential tax + penalty",
                    fix_steps=[
                        "Standalone restaurant = 5% (no ITC)",
                        "Hotel premises restaurant (room tariff >Rs.7500) = 18%",
                        "Correct rate apply karo — invoice amend karo",
                    ],
                    itc_at_risk=0,
                ))

    return issues


# ═══════════════════════════════════════════════════════════════
# EXPORT / IMPORT
# ═══════════════════════════════════════════════════════════════
def _check_export_import(invoices: list[Invoice], our_gstin: str) -> list[Issue]:
    issues = []

    for inv in invoices:
        # Check 1: Export sale — IRN mandatory (e-invoice)
        if (inv.invoice_type == InvoiceType.SALE
                and inv.total_tax == 0
                and inv.taxable_value > 50000
                and not inv.irn):
            issues.append(Issue(
                issue_type=IssueType.SECTOR_SPECIFIC,
                severity=Severity.HIGH,
                invoice_number=inv.invoice_number,
                party_name=inv.party_name or "Foreign Buyer",
                party_gstin=inv.party_gstin,
                amount=inv.taxable_value,
                problem_en=(
                    f"Export invoice {inv.invoice_number} (Rs.{inv.taxable_value:.2f}) "
                    "has no IRN. E-invoice mandatory for turnover >Rs.5Cr."
                ),
                problem_hi=(
                    f"Export invoice — IRN missing। "
                    "Rs.5Cr+ turnover pe e-invoice mandatory है।"
                ),
                problem_mr=(
                    f"Export बीजक — IRN नाही. "
                    "Rs.5Cr+ उलाढालीसाठी e-invoice अनिवार्य."
                ),
                legal_ref="CGST Rule 48(4) — E-invoice for eligible taxpayers",
                penalty_risk="Rs.10,000 penalty per invoice",
                fix_steps=[
                    "IRP portal pe e-invoice generate karo",
                    "IRN aur QR code invoice pe print karo",
                    "Shipping bill ke saath IRN attach karo",
                ],
                itc_at_risk=0,
            ))

        # Check 2: Import purchase — IGST paid at customs = ITC eligible
        if (inv.invoice_type == InvoiceType.PURCHASE
                and inv.igst > 0
                and inv.party_gstin is None):
            if not inv.is_in_gstr2b:
                issues.append(Issue(
                    issue_type=IssueType.SECTOR_SPECIFIC,
                    severity=Severity.HIGH,
                    invoice_number=inv.invoice_number,
                    party_name=inv.party_name or "Foreign Supplier",
                    party_gstin=None,
                    amount=inv.igst,
                    problem_en=(
                        f"Import invoice {inv.invoice_number} — "
                        f"IGST Rs.{inv.igst:.2f} paid at customs. "
                        "Claim ITC using Bill of Entry, not GSTR-2B."
                    ),
                    problem_hi=(
                        "Import invoice — IGST customs pe paid है। "
                        "Bill of Entry se ITC claim karo, GSTR-2B se nahi।"
                    ),
                    problem_mr=(
                        "Import बीजक — IGST customs वर भरला. "
                        "Bill of Entry वरून ITC दावा करा, GSTR-2B वरून नाही."
                    ),
                    legal_ref="CGST Act Section 3 of Customs — Import IGST ITC",
                    penalty_risk="ITC wrongly claimed if Bill of Entry not matched",
                    fix_steps=[
                        "Bill of Entry number note karo",
                        "ICEGATE portal pe Bill of Entry status check karo",
                        "GSTR-3B Table 4(A)(1) mein import ITC claim karo",
                        "Bill of Entry copy records mein rakhna mandatory",
                    ],
                    itc_at_risk=inv.igst,
                ))

    return issues