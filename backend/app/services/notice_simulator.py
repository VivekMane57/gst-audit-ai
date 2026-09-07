# """
# services/notice_simulator.py  (Enhanced)
# -----------------------------------------
# Changes from previous version:
#   1. run_notice_simulation() now returns:
#      - top_risk_reasons (top 3 human-readable)
#      - estimated_penalty_exposure (total rupees at risk)
#      - issue_summary by severity
#   2. _build_top_risk_reasons() — new helper
#   3. _calc_penalty_exposure() — new helper
#   4. All existing output preserved — backward compatible

# Everything else unchanged.
# """

# import logging
# from typing import Dict, List, Optional, Any
# from datetime import datetime

# logger = logging.getLogger(__name__)


# # ═══════════════════════════════════════════════════════════════
# #  WEIGHTS + CATEGORIES (unchanged)
# # ═══════════════════════════════════════════════════════════════

# ISSUE_WEIGHTS = {
#     "gstin_invalid":     {"weight": 8,  "max": 15, "category": "registration"},
#     "invalid_gstin":     {"weight": 8,  "max": 15, "category": "registration"},   # alias
#     "tax_type_mismatch": {"weight": 12, "max": 20, "category": "tax_computation"},
#     "gstr1_missing":     {"weight": 10, "max": 18, "category": "filing"},
#     "gstr2b_missing":    {"weight": 6,  "max": 12, "category": "itc"},
#     "amount_mismatch":   {"weight": 8,  "max": 15, "category": "reconciliation"},
#     "duplicate_invoice": {"weight": 15, "max": 25, "category": "fraud"},
#     "circular_trade":    {"weight": 25, "max": 35, "category": "fraud"},
#     "circular_transaction": {"weight": 25, "max": 35, "category": "fraud"},       # alias
#     "filing_delay":      {"weight": 5,  "max": 10, "category": "filing"},
#     "rate_mismatch":     {"weight": 7,  "max": 12, "category": "tax_computation"},
#     "hsn_mismatch":      {"weight": 4,  "max": 8,  "category": "classification"},
#     "rcm_not_paid":      {"weight": 10, "max": 18, "category": "tax_computation"},
#     "itc_overclaimed":   {"weight": 18, "max": 30, "category": "itc"},
#     "r1_vs_3b_mismatch": {"weight": 14, "max": 22, "category": "reconciliation"},
#     "gstr1_vs_3b_mismatch": {"weight": 14, "max": 22, "category": "reconciliation"},  # alias
#     "gstr9_not_filed":   {"weight": 8,  "max": 15, "category": "filing"},
#     "eway_bill_missing": {"weight": 6,  "max": 10, "category": "logistics"},
#     "payment_180_days":  {"weight": 8,  "max": 14, "category": "itc"},
#     "einvoice_missing":  {"weight": 5,  "max": 10, "category": "invoicing"},
#     "export_validation": {"weight": 7,  "max": 12, "category": "invoicing"},
#     "sector_specific":   {"weight": 5,  "max": 10, "category": "filing"},
# }

# RISK_CATEGORIES = {
#     "fraud":            {"label": "Fraud Detection",        "label_hi": "धोखाधड़ी",            "label_mr": "फसवणूक",             "dept_priority": "VERY HIGH"},
#     "itc":              {"label": "ITC Irregularities",     "label_hi": "ITC अनियमितताएं",     "label_mr": "ITC अनियमितता",      "dept_priority": "VERY HIGH"},
#     "reconciliation":   {"label": "Return Mismatch",        "label_hi": "रिटर्न बेमेल",        "label_mr": "रिटर्न जुळत नाही",   "dept_priority": "HIGH"},
#     "tax_computation":  {"label": "Tax Computation Error",  "label_hi": "कर गणना त्रुटि",     "label_mr": "कर गणना त्रुटी",     "dept_priority": "HIGH"},
#     "filing":           {"label": "Filing Non-Compliance",  "label_hi": "फाइलिंग गैर-अनुपालन","label_mr": "दाखल अपूर्णता",      "dept_priority": "MEDIUM"},
#     "registration":     {"label": "Registration Issues",    "label_hi": "पंजीकरण समस्या",     "label_mr": "नोंदणी समस्या",      "dept_priority": "MEDIUM"},
#     "classification":   {"label": "HSN/SAC Classification", "label_hi": "HSN वर्गीकरण",       "label_mr": "HSN वर्गीकरण",       "dept_priority": "LOW"},
#     "logistics":        {"label": "E-Way Bill Issues",      "label_hi": "ई-वे बिल समस्या",    "label_mr": "ई-वे बिल समस्या",    "dept_priority": "LOW"},
#     "invoicing":        {"label": "Invoice Compliance",     "label_hi": "इनवॉइस अनुपालन",    "label_mr": "बीजक अनुपालन",       "dept_priority": "MEDIUM"},
# }

# DEPT_ACTIVE_MONTHS = {
#     1: 1.2, 2: 1.1, 3: 1.3, 4: 1.0, 5: 1.0, 6: 1.1,
#     7: 1.0, 8: 1.0, 9: 1.2, 10: 1.1, 11: 1.0, 12: 1.3,
# }

# NOTICE_LANG = {
#     "risk_very_high": {
#         "en": "VERY HIGH RISK — Notice almost certain within 3-6 months",
#         "hi": "बहुत अधिक जोखिम — 3-6 महीने में नोटिस लगभग निश्चित",
#         "mr": "अत्यंत उच्च धोका — 3-6 महिन्यांत नोटिस जवळजवळ निश्चित",
#     },
#     "risk_high": {
#         "en": "HIGH RISK — Strong chance of scrutiny in next 6-12 months",
#         "hi": "उच्च जोखिम — अगले 6-12 महीने में जांच की प्रबल संभावना",
#         "mr": "उच्च धोका — पुढील 6-12 महिन्यांत तपासणीची मजबूत शक्यता",
#     },
#     "risk_medium": {
#         "en": "MEDIUM RISK — Possible scrutiny, fix issues proactively",
#         "hi": "मध्यम जोखिम — जांच संभव, समस्याएं पहले से ठीक करें",
#         "mr": "मध्यम धोका — तपासणी शक्य, समस्या आधीच दुरुस्त करा",
#     },
#     "risk_low": {
#         "en": "LOW RISK — Unlikely to receive notice, good compliance",
#         "hi": "कम जोखिम — नोटिस आने की संभावना कम, अच्छा अनुपालन",
#         "mr": "कमी धोका — नोटिस येण्याची शक्यता कमी, चांगले अनुपालन",
#     },
# }

# NOTICE_TYPES = {
#     "ASMT-10": {
#         "en": "Scrutiny Notice — Department wants to verify your returns",
#         "hi": "जांच नोटिस — विभाग आपके रिटर्न सत्यापित करना चाहता है",
#         "mr": "तपासणी नोटीस — विभाग तुमचे रिटर्न सत्यापित करू इच्छितो",
#         "triggers": ["r1_vs_3b_mismatch", "gstr1_vs_3b_mismatch", "amount_mismatch", "tax_type_mismatch"],
#     },
#     "DRC-01": {
#         "en": "Show Cause Notice — Demand for unpaid tax / wrong ITC",
#         "hi": "कारण बताओ नोटिस — अदत्त कर / गलत ITC की मांग",
#         "mr": "कारणे दाखवा नोटीस — न भरलेला कर / चुकीच्या ITC ची मागणी",
#         "triggers": ["itc_overclaimed", "gstr2b_missing", "duplicate_invoice"],
#     },
#     "DRC-01A": {
#         "en": "Intimation before SCN — Opportunity to pay before formal notice",
#         "hi": "SCN से पहले सूचना — औपचारिक नोटिस से पहले भुगतान का अवसर",
#         "mr": "SCN पूर्वी सूचना — औपचारिक नोटिसापूर्वी भरणा करण्याची संधी",
#         "triggers": ["r1_vs_3b_mismatch", "gstr1_missing", "filing_delay"],
#     },
#     "ADT-01": {
#         "en": "Audit Notice — Department will audit your books",
#         "hi": "ऑडिट नोटिस — विभाग आपकी बुक्स ऑडिट करेगा",
#         "mr": "ऑडिट नोटीस — विभाग तुमच्या पुस्तकांचे ऑडिट करेल",
#         "triggers": ["circular_trade", "circular_transaction", "itc_overclaimed", "r1_vs_3b_mismatch"],
#     },
#     "CMP-05": {
#         "en": "Composition Scheme Violation — Show cause for removal",
#         "hi": "कंपोजिशन स्कीम उल्लंघन — हटाने के लिए कारण बताओ",
#         "mr": "कंपोझिशन स्कीम उल्लंघन — काढून टाकण्यासाठी कारणे दाखवा",
#         "triggers": ["tax_type_mismatch", "rate_mismatch"],
#     },
# }

# # Penalty multipliers per issue type (% of tax at risk)
# PENALTY_MULTIPLIERS: dict[str, float] = {
#     "duplicate_invoice":  1.0,    # 100% of ITC
#     "circular_trade":     2.0,    # 200% — fraud penalty
#     "circular_transaction": 2.0,
#     "itc_overclaimed":    1.0,
#     "tax_type_mismatch":  0.28,   # 10% tax + 18% interest
#     "gstr2b_missing":     0.18,   # 18% interest on reversal
#     "amount_mismatch":    0.18,
#     "invalid_gstin":      0.1,    # Rs.10k per invoice (approx)
#     "gstin_invalid":      0.1,
#     "gstr1_missing":      0.05,   # Late fee
#     "payment_180_days":   0.18,
# }

# # Top risk reason templates
# RISK_REASON_TEMPLATES: dict[str, str] = {
#     "fraud":           "Circular/duplicate transactions detected — highest scrutiny risk",
#     "itc":             "ITC irregularities — invoices missing from GSTR-2B",
#     "reconciliation":  "Return mismatches — GSTR-1 vs GSTR-3B differences",
#     "tax_computation": "Wrong tax type applied (IGST/CGST/SGST errors)",
#     "filing":          "Filing non-compliance — missing/late returns",
#     "registration":    "Invalid GSTIN(s) — ITC claims at risk",
#     "classification":  "HSN code mismatches flagged",
#     "invoicing":       "Invoice compliance issues",
#     "logistics":       "E-Way Bill non-compliance",
# }


# def _t(key: str, lang: str = "en") -> str:
#     return NOTICE_LANG.get(key, {}).get(lang, NOTICE_LANG.get(key, {}).get("en", key))


# # ═══════════════════════════════════════════════════════════════
# #  NEW HELPERS
# # ═══════════════════════════════════════════════════════════════

# def _build_top_risk_reasons(
#     category_scores: Dict[str, float],
#     issue_contributions: List[Dict],
#     lang: str = "en",
# ) -> List[str]:
#     """
#     Build top 3 human-readable risk reasons.
#     Used in email subject, PDF summary, dashboard queue.
#     """
#     # Sort categories by score
#     sorted_cats = sorted(category_scores.items(), key=lambda x: x[1], reverse=True)
#     reasons = []
#     for cat, score in sorted_cats[:3]:
#         # Find most impactful issue in this category
#         cat_issues = [ic for ic in issue_contributions if ic["category"] == cat]
#         if cat_issues:
#             top_issue = sorted(cat_issues, key=lambda x: x["contribution"], reverse=True)[0]
#             issue_ref = top_issue.get("invoice", "")
#             base_reason = RISK_REASON_TEMPLATES.get(cat, f"{cat} compliance issue")
#             if issue_ref and issue_ref != "N/A":
#                 reasons.append(f"{base_reason} (e.g. {issue_ref})")
#             else:
#                 reasons.append(base_reason)
#     return reasons[:3]


# def _calc_penalty_exposure(issues: List[Dict]) -> float:
#     """
#     Estimate total financial penalty exposure in rupees.
#     Conservative estimate — uses tax_impact + penalty multiplier.
#     """
#     total = 0.0
#     for issue in issues:
#         issue_type  = issue.get("type", "")
#         tax_impact  = float(issue.get("tax_impact", 0) or 0)
#         amount      = float(issue.get("amount", 0) or 0)
#         base_amount = tax_impact if tax_impact > 0 else amount
#         multiplier  = PENALTY_MULTIPLIERS.get(issue_type, 0.1)
#         total += base_amount * multiplier
#     return round(total, 2)


# def _calc_issue_summary_from_list(issues: List[Dict]) -> Dict[str, int]:
#     """Summary counts from raw issue dicts (notice sim input format)."""
#     summary = {"total": 0, "critical": 0, "high": 0, "medium": 0, "low": 0}
#     for i in issues:
#         sev = (i.get("severity") or "low").lower()
#         summary["total"] += 1
#         if sev in summary:
#             summary[sev] += 1
#     return summary


# # ═══════════════════════════════════════════════════════════════
# #  CORE CALCULATOR (unchanged logic, same signature)
# # ═══════════════════════════════════════════════════════════════

# def calculate_notice_probability(
#     issues: List[Dict],
#     compliance_score: int = 100,
#     filing_delays: int = 0,
#     revenue_data: Optional[Dict] = None,
#     months_since_registration: int = 24,
#     previous_notices: int = 0,
#     turnover_cr: float = 1.0,
# ) -> Dict[str, Any]:
#     base_probability = 5
#     category_scores: Dict[str, float] = {}
#     issue_contributions: List[Dict] = []

#     for issue in issues:
#         issue_type = issue.get("type", "unknown")
#         severity   = issue.get("severity", "medium")
#         weight_info = ISSUE_WEIGHTS.get(issue_type, {"weight": 5, "max": 10, "category": "filing"})
#         sev_mult    = {"critical": 1.5, "high": 1.0, "medium": 0.6, "low": 0.3}.get(severity, 0.5)
#         contribution = min(weight_info["weight"] * sev_mult, weight_info["max"])
#         category     = weight_info["category"]
#         category_scores[category] = category_scores.get(category, 0) + contribution
#         issue_contributions.append({
#             "issue_type":    issue_type,
#             "invoice":       issue.get("invoice", "N/A"),
#             "severity":      severity,
#             "contribution":  round(contribution, 1),
#             "category":      category,
#             "fix_reduction": round(contribution * 0.85, 1),
#         })

#     issues_probability = sum(ic["contribution"] for ic in issue_contributions)
#     filing_factor      = min(filing_delays * 3, 15)
#     compliance_factor  = 15 if compliance_score < 30 else 10 if compliance_score < 50 else 5 if compliance_score < 70 else 0
#     turnover_factor    = 10 if turnover_cr > 10 else 7 if turnover_cr > 5 else 4 if turnover_cr > 2 else 0
#     history_factor     = min(previous_notices * 8, 20)
#     current_month      = datetime.now().month
#     seasonal_multiplier = DEPT_ACTIVE_MONTHS.get(current_month, 1.0)
#     revenue_factor     = 0
#     revenue_anomaly    = None

#     if revenue_data and len(revenue_data) >= 3:
#         values     = list(revenue_data.values())
#         avg_revenue = sum(values) / len(values)
#         if avg_revenue > 0:
#             for month, rev in revenue_data.items():
#                 drop_pct = ((avg_revenue - rev) / avg_revenue) * 100
#                 if drop_pct > 50:
#                     revenue_factor  = 8
#                     revenue_anomaly = {"month": month, "revenue": rev, "average": round(avg_revenue, 0), "drop_percent": round(drop_pct, 1)}
#                     break

#     raw_probability      = base_probability + issues_probability + filing_factor + compliance_factor + turnover_factor + history_factor + revenue_factor
#     adjusted_probability = raw_probability * seasonal_multiplier
#     final_probability    = max(2, min(95, round(adjusted_probability)))

#     if   final_probability >= 70: risk_level = "VERY_HIGH"
#     elif final_probability >= 45: risk_level = "HIGH"
#     elif final_probability >= 25: risk_level = "MEDIUM"
#     else:                          risk_level = "LOW"

#     risk_areas = []
#     for cat, score in sorted(category_scores.items(), key=lambda x: x[1], reverse=True):
#         cat_info = RISK_CATEGORIES.get(cat, {})
#         risk_areas.append({
#             "category":      cat,
#             "label":         cat_info.get("label", cat),
#             "label_hi":      cat_info.get("label_hi", cat),
#             "label_mr":      cat_info.get("label_mr", cat),
#             "score":         round(score, 1),
#             "dept_priority": cat_info.get("dept_priority", "MEDIUM"),
#         })

#     possible_notices = []
#     issue_types_found = set(ic["issue_type"] for ic in issue_contributions)
#     for notice_id, notice_info in NOTICE_TYPES.items():
#         triggers = set(notice_info["triggers"])
#         if triggers & issue_types_found:
#             overlap = len(triggers & issue_types_found)
#             possible_notices.append({
#                 "notice_type":     notice_id,
#                 "description_en":  notice_info["en"],
#                 "description_hi":  notice_info["hi"],
#                 "description_mr":  notice_info["mr"],
#                 "likelihood":      "HIGH" if overlap >= 2 else "MEDIUM",
#             })

#     breakdown = {
#         "base_risk":          base_probability,
#         "issues_risk":        round(issues_probability, 1),
#         "filing_risk":        filing_factor,
#         "compliance_risk":    compliance_factor,
#         "turnover_risk":      turnover_factor,
#         "history_risk":       history_factor,
#         "revenue_risk":       revenue_factor,
#         "seasonal_multiplier": seasonal_multiplier,
#     }

#     return {
#         "probability":          final_probability,
#         "risk_level":           risk_level,
#         "risk_areas":           risk_areas,
#         "possible_notices":     possible_notices,
#         "breakdown":            breakdown,
#         "issue_contributions":  issue_contributions,
#         "category_scores":      category_scores,   # NEW — needed for top_risk_reasons
#         "revenue_anomaly":      revenue_anomaly,
#         "calculated_at":        datetime.now().isoformat(),
#     }


# # ═══════════════════════════════════════════════════════════════
# #  WHAT-IF (unchanged)
# # ═══════════════════════════════════════════════════════════════

# def simulate_what_if(
#     current_prediction: Dict,
#     issues_to_fix: Optional[List[str]] = None,
# ) -> Dict[str, Any]:
#     current_prob  = current_prediction["probability"]
#     contributions = current_prediction["issue_contributions"]
#     issues_to_fix_set = set(ic["issue_type"] for ic in contributions) if issues_to_fix is None else set(issues_to_fix)

#     total_reduction = 0
#     fixes = []
#     for ic in contributions:
#         if ic["issue_type"] in issues_to_fix_set:
#             reduction = ic["fix_reduction"]
#             total_reduction += reduction
#             fixes.append({"issue_type": ic["issue_type"], "invoice": ic["invoice"], "probability_reduction": round(reduction, 1)})

#     new_probability = max(2, round(current_prob - total_reduction))
#     if   new_probability >= 70: new_risk_level = "VERY_HIGH"
#     elif new_probability >= 45: new_risk_level = "HIGH"
#     elif new_probability >= 25: new_risk_level = "MEDIUM"
#     else:                        new_risk_level = "LOW"

#     return {
#         "current_probability": current_prob,
#         "new_probability":     new_probability,
#         "reduction":           round(current_prob - new_probability, 1),
#         "reduction_percent":   round(((current_prob - new_probability) / max(current_prob, 1)) * 100, 1),
#         "current_risk_level":  current_prediction["risk_level"],
#         "new_risk_level":      new_risk_level,
#         "fixes_applied":       fixes,
#         "fixes_count":         len(fixes),
#     }


# # ═══════════════════════════════════════════════════════════════
# #  RECOMMENDATIONS (unchanged)
# # ═══════════════════════════════════════════════════════════════

# def generate_recommendations(prediction: Dict, lang: str = "en") -> List[Dict]:
#     recommendations = []
#     contributions   = prediction.get("issue_contributions", [])
#     sorted_issues   = sorted(contributions, key=lambda x: x["contribution"], reverse=True)

#     actions = {
#         "duplicate_invoice":  {"en": "Remove duplicate invoice {inv}. Claim ITC only once.", "hi": "डुप्लीकेट इनवॉइस {inv} हटाएं।", "mr": "डुप्लिकेट बीजक {inv} काढा."},
#         "tax_type_mismatch":  {"en": "Credit note for {inv}, re-invoice with correct tax type.", "hi": "{inv} क्रेडिट नोट जारी करें, सही कर प्रकार से पुनः इनवॉइस।", "mr": "{inv} साठी क्रेडिट नोट, योग्य कर प्रकारासह पुन्हा बीजक."},
#         "gstr1_missing":      {"en": "Add invoice {inv} to GSTR-1 immediately.", "hi": "इनवॉइस {inv} तुरंत GSTR-1 में जोड़ें।", "mr": "बीजक {inv} तातडीने GSTR-1 मध्ये जोडा."},
#         "gstr2b_missing":     {"en": "Contact supplier for {inv} to file GSTR-1. Don't claim ITC yet.", "hi": "{inv} के सप्लायर से GSTR-1 फाइल करवाएं।", "mr": "{inv} च्या पुरवठादाराला GSTR-1 दाखल करण्यास सांगा."},
#         "amount_mismatch":    {"en": "Claim only GSTR-2B amount for {inv}. Contact supplier to correct.", "hi": "{inv} के लिए केवल GSTR-2B राशि claim करें।", "mr": "{inv} साठी फक्त GSTR-2B रक्कम दावा करा."},
#         "invalid_gstin":      {"en": "Verify GSTIN for {inv} at search.gst.gov.in.", "hi": "{inv} का GSTIN जांचें: search.gst.gov.in।", "mr": "{inv} चा GSTIN तपासा: search.gst.gov.in."},
#         "gstin_invalid":      {"en": "Verify GSTIN for {inv} at search.gst.gov.in.", "hi": "{inv} का GSTIN जांचें: search.gst.gov.in।", "mr": "{inv} चा GSTIN तपासा: search.gst.gov.in."},
#         "circular_transaction": {"en": "URGENT: Investigate circular chain for {inv}. Keep all documentation.", "hi": "तुरंत: {inv} की चक्रीय श्रृंखला जांचें।", "mr": "तातडी: {inv} ची चक्रीय साखळी तपासा."},
#     }

#     for idx, ic in enumerate(sorted_issues[:10], 1):
#         issue_type = ic["issue_type"]
#         inv        = ic.get("invoice", "N/A")
#         tmpl       = actions.get(issue_type, {"en": "Fix issue {inv} ({type}).", "hi": "समस्या {inv} ठीक करें।", "mr": "समस्या {inv} दुरुस्त करा."})
#         action_text = tmpl.get(lang, tmpl.get("en", "")).format(inv=inv, type=issue_type)
#         recommendations.append({
#             "priority":       idx,
#             "issue_type":     issue_type,
#             "invoice":        inv,
#             "action":         action_text,
#             "risk_reduction": f"{ic['fix_reduction']}%",
#             "severity":       ic["severity"],
#             "category":       ic["category"],
#         })
#     return recommendations


# # ═══════════════════════════════════════════════════════════════
# #  NOTICE REPLY DRAFT (unchanged)
# # ═══════════════════════════════════════════════════════════════

# def generate_notice_reply(
#     notice_type: str = "ASMT-10",
#     client_name: str = "",
#     client_gstin: str = "",
#     issues: List[Dict] = None,
#     lang: str = "en",
# ) -> str:
#     issues = issues or []
#     now    = datetime.now().strftime("%d/%m/%Y")
#     if lang == "mr":
#         lines = ["प्रति,", "सहाय्यक आयुक्त, GST", "वॉर्ड ____, विभाग ____", "",
#                  f"विषय: नोटीस क्र. [______] ला उत्तर | Form {notice_type}",
#                  f"GSTIN: {client_gstin}", f"करदाता: {client_name}", "", "मा. महोदय/महोदया,", ""]
#         for idx, issue in enumerate(issues[:5], 1):
#             lines += [f"{idx}. बीजक {issue.get('invoice','N/A')}: योग्य दुरुस्ती केली आहे. कागदपत्रे जोडली.", ""]
#         lines += ["जोडलेली कागदपत्रे: GSTR प्रती, Credit/Debit Notes, Bank Statements", "",
#                   "धन्यवाद,", f"[{client_name}]", f"दिनांक: {now}"]
#     elif lang == "hi":
#         lines = ["सेवा में,", "सहायक आयुक्त, GST", "वार्ड ____, डिवीजन ____", "",
#                  f"विषय: नोटिस नं. [______] का जवाब | Form {notice_type}",
#                  f"GSTIN: {client_gstin}", f"करदाता: {client_name}", "", "माननीय महोदय,", ""]
#         for idx, issue in enumerate(issues[:5], 1):
#             lines += [f"{idx}. इनवॉइस {issue.get('invoice','N/A')}: उचित सुधार किया गया। दस्तावेज संलग्न।", ""]
#         lines += ["संलग्न: GSTR प्रतियां, Credit/Debit Notes, Bank Statements", "",
#                   "धन्यवाद,", f"[{client_name}]", f"दिनांक: {now}"]
#     else:
#         lines = ["To,", "The Assistant Commissioner of GST", "Ward ____, Division ____", "",
#                  f"Subject: Reply to Notice No. [______] — Form {notice_type}",
#                  f"GSTIN: {client_gstin}", f"Taxpayer: {client_name}", "", "Respected Sir/Madam,", ""]
#         for idx, issue in enumerate(issues[:5], 1):
#             lines += [f"{idx}. Invoice {issue.get('invoice','N/A')}: Matter examined. Correction made. Documents enclosed.", ""]
#         lines += ["Enclosed: GSTR filed copies, Credit/Debit Note register, Bank Statements", "",
#                   "Yours faithfully,", f"[{client_name}]", f"Date: {now}"]
#     return "\n".join(lines)


# # ═══════════════════════════════════════════════════════════════
# #  MAIN: run_notice_simulation (ENHANCED)
# # ═══════════════════════════════════════════════════════════════

# def run_notice_simulation(
#     issues: List[Dict],
#     compliance_score: int = 100,
#     client_name: str = "",
#     client_gstin: str = "",
#     lang: str = "en",
#     filing_delays: int = 0,
#     turnover_cr: float = 1.0,
#     previous_notices: int = 0,
#     revenue_data: Optional[Dict] = None,
# ) -> Dict[str, Any]:
#     """
#     MAIN FUNCTION — Run complete notice simulation.

#     Enhanced output now includes:
#       - top_risk_reasons: List[str]  — top 3 human-readable
#       - estimated_penalty_exposure: float  — total rupees
#       - issue_summary: Dict  — severity counts
#       - if_fixed_risk_drop: Dict  — what-if fix all
#     All existing keys preserved — backward compatible.
#     """
#     logger.info(f"Notice simulation | Issues: {len(issues)} | Score: {compliance_score}")

#     # Core calculation
#     prediction = calculate_notice_probability(
#         issues=issues,
#         compliance_score=compliance_score,
#         filing_delays=filing_delays,
#         revenue_data=revenue_data,
#         previous_notices=previous_notices,
#         turnover_cr=turnover_cr,
#     )

#     # What-if
#     what_if_all      = simulate_what_if(prediction)
#     critical_types   = [ic["issue_type"] for ic in prediction["issue_contributions"] if ic["severity"] == "critical"]
#     what_if_critical = simulate_what_if(prediction, critical_types) if critical_types else None

#     # Recommendations
#     recommendations = generate_recommendations(prediction, lang)

#     # Risk message
#     risk_key     = f"risk_{prediction['risk_level'].lower()}"
#     risk_message = _t(risk_key, lang)

#     # Notice reply draft
#     reply_draft = None
#     if prediction["possible_notices"]:
#         top_notice = prediction["possible_notices"][0]["notice_type"]
#         reply_draft = generate_notice_reply(
#             notice_type=top_notice,
#             client_name=client_name,
#             client_gstin=client_gstin,
#             issues=issues,
#             lang=lang,
#         )

#     # ── NEW: Enhanced fields ──────────────────────────────────
#     top_risk_reasons = _build_top_risk_reasons(
#         category_scores     = prediction.get("category_scores", {}),
#         issue_contributions = prediction["issue_contributions"],
#         lang                = lang,
#     )

#     estimated_penalty_exposure = _calc_penalty_exposure(issues)

#     issue_summary = _calc_issue_summary_from_list(issues)

#     # ── Build final result ────────────────────────────────────
#     result = {
#         # ── Existing keys (unchanged) ──
#         "probability":          prediction["probability"],
#         "risk_level":           prediction["risk_level"],
#         "risk_message":         risk_message,
#         "risk_areas":           prediction["risk_areas"],
#         "possible_notices":     prediction["possible_notices"],
#         "breakdown":            prediction["breakdown"],
#         "revenue_anomaly":      prediction["revenue_anomaly"],
#         "what_if_fix_all":      what_if_all,
#         "what_if_fix_critical": what_if_critical,
#         "recommendations":      recommendations,
#         "notice_reply_draft":   reply_draft,
#         "labels": {
#             "probability": "GST Notice Probability",
#             "risk_areas":  "Main Risk Areas",
#             "what_if":     "If You Fix These Issues",
#             "current":     "Current",
#             "after_fix":   "After Fixing",
#             "actions":     "Immediate Actions Needed",
#             "notices":     "Possible Notice Types",
#         },
#         # ── NEW keys ──
#         "top_risk_reasons":           top_risk_reasons,
#         "estimated_penalty_exposure": estimated_penalty_exposure,
#         "issue_summary":              issue_summary,
#         "if_fixed_risk_drop":         what_if_all,   # alias for frontend
#     }

#     logger.info(f"Notice sim complete | {prediction['probability']}% | {prediction['risk_level']} | penalty=₹{estimated_penalty_exposure:,.0f}")
#     return result




"""
services/notice_simulator.py  (Enhanced + FIXED)
-----------------------------------------
Changes from previous version:
  1. run_notice_simulation() now returns:
     - top_risk_reasons (top 3 human-readable)
     - estimated_penalty_exposure (total rupees at risk)
     - issue_summary by severity
  2. _build_top_risk_reasons() — new helper
  3. _calc_penalty_exposure() — new helper
  4. All existing output preserved — backward compatible

  FIX (this version): risk_areas "score" is a SUM of per-issue
  contributions across every issue in that category. With enough
  issues in one category, that sum can exceed 100 even though
  each individual contribution is capped at its own issue's max.
  The frontend displays this score as a "%", so an uncapped sum
  above 100 renders as a mathematically impossible percentage
  (e.g. "126%"). Fix: cap the aggregated category score at 100
  at the point risk_areas is built (see calculate_notice_probability).

Everything else unchanged.
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
#  WEIGHTS + CATEGORIES (unchanged)
# ═══════════════════════════════════════════════════════════════

ISSUE_WEIGHTS = {
    "gstin_invalid":     {"weight": 8,  "max": 15, "category": "registration"},
    "invalid_gstin":     {"weight": 8,  "max": 15, "category": "registration"},   # alias
    "tax_type_mismatch": {"weight": 12, "max": 20, "category": "tax_computation"},
    "gstr1_missing":     {"weight": 10, "max": 18, "category": "filing"},
    "gstr2b_missing":    {"weight": 6,  "max": 12, "category": "itc"},
    "amount_mismatch":   {"weight": 8,  "max": 15, "category": "reconciliation"},
    "duplicate_invoice": {"weight": 15, "max": 25, "category": "fraud"},
    "circular_trade":    {"weight": 25, "max": 35, "category": "fraud"},
    "circular_transaction": {"weight": 25, "max": 35, "category": "fraud"},       # alias
    "filing_delay":      {"weight": 5,  "max": 10, "category": "filing"},
    "rate_mismatch":     {"weight": 7,  "max": 12, "category": "tax_computation"},
    "hsn_mismatch":      {"weight": 4,  "max": 8,  "category": "classification"},
    "rcm_not_paid":      {"weight": 10, "max": 18, "category": "tax_computation"},
    "itc_overclaimed":   {"weight": 18, "max": 30, "category": "itc"},
    "r1_vs_3b_mismatch": {"weight": 14, "max": 22, "category": "reconciliation"},
    "gstr1_vs_3b_mismatch": {"weight": 14, "max": 22, "category": "reconciliation"},  # alias
    "gstr9_not_filed":   {"weight": 8,  "max": 15, "category": "filing"},
    "eway_bill_missing": {"weight": 6,  "max": 10, "category": "logistics"},
    "payment_180_days":  {"weight": 8,  "max": 14, "category": "itc"},
    "einvoice_missing":  {"weight": 5,  "max": 10, "category": "invoicing"},
    "export_validation": {"weight": 7,  "max": 12, "category": "invoicing"},
    "sector_specific":   {"weight": 5,  "max": 10, "category": "filing"},
}

RISK_CATEGORIES = {
    "fraud":            {"label": "Fraud Detection",        "label_hi": "धोखाधड़ी",            "label_mr": "फसवणूक",             "dept_priority": "VERY HIGH"},
    "itc":              {"label": "ITC Irregularities",     "label_hi": "ITC अनियमितताएं",     "label_mr": "ITC अनियमितता",      "dept_priority": "VERY HIGH"},
    "reconciliation":   {"label": "Return Mismatch",        "label_hi": "रिटर्न बेमेल",        "label_mr": "रिटर्न जुळत नाही",   "dept_priority": "HIGH"},
    "tax_computation":  {"label": "Tax Computation Error",  "label_hi": "कर गणना त्रुटि",     "label_mr": "कर गणना त्रुटी",     "dept_priority": "HIGH"},
    "filing":           {"label": "Filing Non-Compliance",  "label_hi": "फाइलिंग गैर-अनुपालन","label_mr": "दाखल अपूर्णता",      "dept_priority": "MEDIUM"},
    "registration":     {"label": "Registration Issues",    "label_hi": "पंजीकरण समस्या",     "label_mr": "नोंदणी समस्या",      "dept_priority": "MEDIUM"},
    "classification":   {"label": "HSN/SAC Classification", "label_hi": "HSN वर्गीकरण",       "label_mr": "HSN वर्गीकरण",       "dept_priority": "LOW"},
    "logistics":        {"label": "E-Way Bill Issues",      "label_hi": "ई-वे बिल समस्या",    "label_mr": "ई-वे बिल समस्या",    "dept_priority": "LOW"},
    "invoicing":        {"label": "Invoice Compliance",     "label_hi": "इनवॉइस अनुपालन",    "label_mr": "बीजक अनुपालन",       "dept_priority": "MEDIUM"},
}

DEPT_ACTIVE_MONTHS = {
    1: 1.2, 2: 1.1, 3: 1.3, 4: 1.0, 5: 1.0, 6: 1.1,
    7: 1.0, 8: 1.0, 9: 1.2, 10: 1.1, 11: 1.0, 12: 1.3,
}

NOTICE_LANG = {
    "risk_very_high": {
        "en": "VERY HIGH RISK — Notice almost certain within 3-6 months",
        "hi": "बहुत अधिक जोखिम — 3-6 महीने में नोटिस लगभग निश्चित",
        "mr": "अत्यंत उच्च धोका — 3-6 महिन्यांत नोटिस जवळजवळ निश्चित",
    },
    "risk_high": {
        "en": "HIGH RISK — Strong chance of scrutiny in next 6-12 months",
        "hi": "उच्च जोखिम — अगले 6-12 महीने में जांच की प्रबल संभावना",
        "mr": "उच्च धोका — पुढील 6-12 महिन्यांत तपासणीची मजबूत शक्यता",
    },
    "risk_medium": {
        "en": "MEDIUM RISK — Possible scrutiny, fix issues proactively",
        "hi": "मध्यम जोखिम — जांच संभव, समस्याएं पहले से ठीक करें",
        "mr": "मध्यम धोका — तपासणी शक्य, समस्या आधीच दुरुस्त करा",
    },
    "risk_low": {
        "en": "LOW RISK — Unlikely to receive notice, good compliance",
        "hi": "कम जोखिम — नोटिस आने की संभावना कम, अच्छा अनुपालन",
        "mr": "कमी धोका — नोटिस येण्याची शक्यता कमी, चांगले अनुपालन",
    },
}

NOTICE_TYPES = {
    "ASMT-10": {
        "en": "Scrutiny Notice — Department wants to verify your returns",
        "hi": "जांच नोटिस — विभाग आपके रिटर्न सत्यापित करना चाहता है",
        "mr": "तपासणी नोटीस — विभाग तुमचे रिटर्न सत्यापित करू इच्छितो",
        "triggers": ["r1_vs_3b_mismatch", "gstr1_vs_3b_mismatch", "amount_mismatch", "tax_type_mismatch"],
    },
    "DRC-01": {
        "en": "Show Cause Notice — Demand for unpaid tax / wrong ITC",
        "hi": "कारण बताओ नोटिस — अदत्त कर / गलत ITC की मांग",
        "mr": "कारणे दाखवा नोटीस — न भरलेला कर / चुकीच्या ITC ची मागणी",
        "triggers": ["itc_overclaimed", "gstr2b_missing", "duplicate_invoice"],
    },
    "DRC-01A": {
        "en": "Intimation before SCN — Opportunity to pay before formal notice",
        "hi": "SCN से पहले सूचना — औपचारिक नोटिस से पहले भुगतान का अवसर",
        "mr": "SCN पूर्वी सूचना — औपचारिक नोटिसापूर्वी भरणा करण्याची संधी",
        "triggers": ["r1_vs_3b_mismatch", "gstr1_missing", "filing_delay"],
    },
    "ADT-01": {
        "en": "Audit Notice — Department will audit your books",
        "hi": "ऑडिट नोटिस — विभाग आपकी बुक्स ऑडिट करेगा",
        "mr": "ऑडिट नोटीस — विभाग तुमच्या पुस्तकांचे ऑडिट करेल",
        "triggers": ["circular_trade", "circular_transaction", "itc_overclaimed", "r1_vs_3b_mismatch"],
    },
    "CMP-05": {
        "en": "Composition Scheme Violation — Show cause for removal",
        "hi": "कंपोजिशन स्कीम उल्लंघन — हटाने के लिए कारण बताओ",
        "mr": "कंपोझिशन स्कीम उल्लंघन — काढून टाकण्यासाठी कारणे दाखवा",
        "triggers": ["tax_type_mismatch", "rate_mismatch"],
    },
}

# Penalty multipliers per issue type (% of tax at risk)
PENALTY_MULTIPLIERS: dict[str, float] = {
    "duplicate_invoice":  1.0,    # 100% of ITC
    "circular_trade":     2.0,    # 200% — fraud penalty
    "circular_transaction": 2.0,
    "itc_overclaimed":    1.0,
    "tax_type_mismatch":  0.28,   # 10% tax + 18% interest
    "gstr2b_missing":     0.18,   # 18% interest on reversal
    "amount_mismatch":    0.18,
    "invalid_gstin":      0.1,    # Rs.10k per invoice (approx)
    "gstin_invalid":      0.1,
    "gstr1_missing":      0.05,   # Late fee
    "payment_180_days":   0.18,
}

# Top risk reason templates
RISK_REASON_TEMPLATES: dict[str, str] = {
    "fraud":           "Circular/duplicate transactions detected — highest scrutiny risk",
    "itc":             "ITC irregularities — invoices missing from GSTR-2B",
    "reconciliation":  "Return mismatches — GSTR-1 vs GSTR-3B differences",
    "tax_computation": "Wrong tax type applied (IGST/CGST/SGST errors)",
    "filing":          "Filing non-compliance — missing/late returns",
    "registration":    "Invalid GSTIN(s) — ITC claims at risk",
    "classification":  "HSN code mismatches flagged",
    "invoicing":       "Invoice compliance issues",
    "logistics":       "E-Way Bill non-compliance",
}


def _t(key: str, lang: str = "en") -> str:
    return NOTICE_LANG.get(key, {}).get(lang, NOTICE_LANG.get(key, {}).get("en", key))


# ═══════════════════════════════════════════════════════════════
#  NEW HELPERS
# ═══════════════════════════════════════════════════════════════

def _build_top_risk_reasons(
    category_scores: Dict[str, float],
    issue_contributions: List[Dict],
    lang: str = "en",
) -> List[str]:
    """
    Build top 3 human-readable risk reasons.
    Used in email subject, PDF summary, dashboard queue.
    """
    # Sort categories by score
    sorted_cats = sorted(category_scores.items(), key=lambda x: x[1], reverse=True)
    reasons = []
    for cat, score in sorted_cats[:3]:
        # Find most impactful issue in this category
        cat_issues = [ic for ic in issue_contributions if ic["category"] == cat]
        if cat_issues:
            top_issue = sorted(cat_issues, key=lambda x: x["contribution"], reverse=True)[0]
            issue_ref = top_issue.get("invoice", "")
            base_reason = RISK_REASON_TEMPLATES.get(cat, f"{cat} compliance issue")
            if issue_ref and issue_ref != "N/A":
                reasons.append(f"{base_reason} (e.g. {issue_ref})")
            else:
                reasons.append(base_reason)
    return reasons[:3]


def _calc_penalty_exposure(issues: List[Dict]) -> float:
    """
    Estimate total financial penalty exposure in rupees.
    Conservative estimate — uses tax_impact + penalty multiplier.
    """
    total = 0.0
    for issue in issues:
        issue_type  = issue.get("type", "")
        tax_impact  = float(issue.get("tax_impact", 0) or 0)
        amount      = float(issue.get("amount", 0) or 0)
        base_amount = tax_impact if tax_impact > 0 else amount
        multiplier  = PENALTY_MULTIPLIERS.get(issue_type, 0.1)
        total += base_amount * multiplier
    return round(total, 2)


def _calc_issue_summary_from_list(issues: List[Dict]) -> Dict[str, int]:
    """Summary counts from raw issue dicts (notice sim input format)."""
    summary = {"total": 0, "critical": 0, "high": 0, "medium": 0, "low": 0}
    for i in issues:
        sev = (i.get("severity") or "low").lower()
        summary["total"] += 1
        if sev in summary:
            summary[sev] += 1
    return summary


# ═══════════════════════════════════════════════════════════════
#  CORE CALCULATOR (FIXED: risk_areas score now capped at 100)
# ═══════════════════════════════════════════════════════════════

def calculate_notice_probability(
    issues: List[Dict],
    compliance_score: int = 100,
    filing_delays: int = 0,
    revenue_data: Optional[Dict] = None,
    months_since_registration: int = 24,
    previous_notices: int = 0,
    turnover_cr: float = 1.0,
) -> Dict[str, Any]:
    base_probability = 5
    category_scores: Dict[str, float] = {}
    issue_contributions: List[Dict] = []

    for issue in issues:
        issue_type = issue.get("type", "unknown")
        severity   = issue.get("severity", "medium")
        weight_info = ISSUE_WEIGHTS.get(issue_type, {"weight": 5, "max": 10, "category": "filing"})
        sev_mult    = {"critical": 1.5, "high": 1.0, "medium": 0.6, "low": 0.3}.get(severity, 0.5)
        contribution = min(weight_info["weight"] * sev_mult, weight_info["max"])
        category     = weight_info["category"]
        category_scores[category] = category_scores.get(category, 0) + contribution
        issue_contributions.append({
            "issue_type":    issue_type,
            "invoice":       issue.get("invoice", "N/A"),
            "severity":      severity,
            "contribution":  round(contribution, 1),
            "category":      category,
            "fix_reduction": round(contribution * 0.85, 1),
        })

    issues_probability = sum(ic["contribution"] for ic in issue_contributions)
    filing_factor      = min(filing_delays * 3, 15)
    compliance_factor  = 15 if compliance_score < 30 else 10 if compliance_score < 50 else 5 if compliance_score < 70 else 0
    turnover_factor    = 10 if turnover_cr > 10 else 7 if turnover_cr > 5 else 4 if turnover_cr > 2 else 0
    history_factor     = min(previous_notices * 8, 20)
    current_month      = datetime.now().month
    seasonal_multiplier = DEPT_ACTIVE_MONTHS.get(current_month, 1.0)
    revenue_factor     = 0
    revenue_anomaly    = None

    if revenue_data and len(revenue_data) >= 3:
        values     = list(revenue_data.values())
        avg_revenue = sum(values) / len(values)
        if avg_revenue > 0:
            for month, rev in revenue_data.items():
                drop_pct = ((avg_revenue - rev) / avg_revenue) * 100
                if drop_pct > 50:
                    revenue_factor  = 8
                    revenue_anomaly = {"month": month, "revenue": rev, "average": round(avg_revenue, 0), "drop_percent": round(drop_pct, 1)}
                    break

    raw_probability      = base_probability + issues_probability + filing_factor + compliance_factor + turnover_factor + history_factor + revenue_factor
    adjusted_probability = raw_probability * seasonal_multiplier
    final_probability    = max(2, min(95, round(adjusted_probability)))

    if   final_probability >= 70: risk_level = "VERY_HIGH"
    elif final_probability >= 45: risk_level = "HIGH"
    elif final_probability >= 25: risk_level = "MEDIUM"
    else:                          risk_level = "LOW"

    # ── FIX: category_scores is a SUM of per-issue contributions,
    # not a percentage of any total — with several issues in one
    # category this can legitimately sum past 100. The frontend
    # renders this value with a literal "%" suffix, so it must be
    # clamped to a valid 0-100 range here at the source, not just
    # cosmetically in the UI.
    risk_areas = []
    for cat, score in sorted(category_scores.items(), key=lambda x: x[1], reverse=True):
        cat_info = RISK_CATEGORIES.get(cat, {})
        capped_score = min(100.0, max(0.0, score))
        risk_areas.append({
            "category":      cat,
            "label":         cat_info.get("label", cat),
            "label_hi":      cat_info.get("label_hi", cat),
            "label_mr":      cat_info.get("label_mr", cat),
            "score":         round(capped_score, 1),
            "raw_score":     round(score, 1),  # kept for debugging/analytics — not rendered with a "%" anywhere
            "dept_priority": cat_info.get("dept_priority", "MEDIUM"),
        })

    possible_notices = []
    issue_types_found = set(ic["issue_type"] for ic in issue_contributions)
    for notice_id, notice_info in NOTICE_TYPES.items():
        triggers = set(notice_info["triggers"])
        if triggers & issue_types_found:
            overlap = len(triggers & issue_types_found)
            possible_notices.append({
                "notice_type":     notice_id,
                "description_en":  notice_info["en"],
                "description_hi":  notice_info["hi"],
                "description_mr":  notice_info["mr"],
                "likelihood":      "HIGH" if overlap >= 2 else "MEDIUM",
            })

    breakdown = {
        "base_risk":          base_probability,
        "issues_risk":        round(issues_probability, 1),
        "filing_risk":        filing_factor,
        "compliance_risk":    compliance_factor,
        "turnover_risk":      turnover_factor,
        "history_risk":       history_factor,
        "revenue_risk":       revenue_factor,
        "seasonal_multiplier": seasonal_multiplier,
    }

    return {
        "probability":          final_probability,
        "risk_level":           risk_level,
        "risk_areas":           risk_areas,
        "possible_notices":     possible_notices,
        "breakdown":            breakdown,
        "issue_contributions":  issue_contributions,
        "category_scores":      category_scores,   # NEW — needed for top_risk_reasons
        "revenue_anomaly":      revenue_anomaly,
        "calculated_at":        datetime.now().isoformat(),
    }


# ═══════════════════════════════════════════════════════════════
#  WHAT-IF (unchanged)
# ═══════════════════════════════════════════════════════════════

def simulate_what_if(
    current_prediction: Dict,
    issues_to_fix: Optional[List[str]] = None,
) -> Dict[str, Any]:
    current_prob  = current_prediction["probability"]
    contributions = current_prediction["issue_contributions"]
    issues_to_fix_set = set(ic["issue_type"] for ic in contributions) if issues_to_fix is None else set(issues_to_fix)

    total_reduction = 0
    fixes = []
    for ic in contributions:
        if ic["issue_type"] in issues_to_fix_set:
            reduction = ic["fix_reduction"]
            total_reduction += reduction
            fixes.append({"issue_type": ic["issue_type"], "invoice": ic["invoice"], "probability_reduction": round(reduction, 1)})

    new_probability = max(2, round(current_prob - total_reduction))
    if   new_probability >= 70: new_risk_level = "VERY_HIGH"
    elif new_probability >= 45: new_risk_level = "HIGH"
    elif new_probability >= 25: new_risk_level = "MEDIUM"
    else:                        new_risk_level = "LOW"

    return {
        "current_probability": current_prob,
        "new_probability":     new_probability,
        "reduction":           round(current_prob - new_probability, 1),
        "reduction_percent":   round(((current_prob - new_probability) / max(current_prob, 1)) * 100, 1),
        "current_risk_level":  current_prediction["risk_level"],
        "new_risk_level":      new_risk_level,
        "fixes_applied":       fixes,
        "fixes_count":         len(fixes),
    }


# ═══════════════════════════════════════════════════════════════
#  RECOMMENDATIONS (unchanged)
# ═══════════════════════════════════════════════════════════════

def generate_recommendations(prediction: Dict, lang: str = "en") -> List[Dict]:
    recommendations = []
    contributions   = prediction.get("issue_contributions", [])
    sorted_issues   = sorted(contributions, key=lambda x: x["contribution"], reverse=True)

    actions = {
        "duplicate_invoice":  {"en": "Remove duplicate invoice {inv}. Claim ITC only once.", "hi": "डुप्लीकेट इनवॉइस {inv} हटाएं।", "mr": "डुप्लिकेट बीजक {inv} काढा."},
        "tax_type_mismatch":  {"en": "Credit note for {inv}, re-invoice with correct tax type.", "hi": "{inv} क्रेडिट नोट जारी करें, सही कर प्रकार से पुनः इनवॉइस।", "mr": "{inv} साठी क्रेडिट नोट, योग्य कर प्रकारासह पुन्हा बीजक."},
        "gstr1_missing":      {"en": "Add invoice {inv} to GSTR-1 immediately.", "hi": "इनवॉइस {inv} तुरंत GSTR-1 में जोड़ें।", "mr": "बीजक {inv} तातडीने GSTR-1 मध्ये जोडा."},
        "gstr2b_missing":     {"en": "Contact supplier for {inv} to file GSTR-1. Don't claim ITC yet.", "hi": "{inv} के सप्लायर से GSTR-1 फाइल करवाएं।", "mr": "{inv} च्या पुरवठादाराला GSTR-1 दाखल करण्यास सांगा."},
        "amount_mismatch":    {"en": "Claim only GSTR-2B amount for {inv}. Contact supplier to correct.", "hi": "{inv} के लिए केवल GSTR-2B राशि claim करें।", "mr": "{inv} साठी फक्त GSTR-2B रक्कम दावा करा."},
        "invalid_gstin":      {"en": "Verify GSTIN for {inv} at search.gst.gov.in.", "hi": "{inv} का GSTIN जांचें: search.gst.gov.in।", "mr": "{inv} चा GSTIN तपासा: search.gst.gov.in."},
        "gstin_invalid":      {"en": "Verify GSTIN for {inv} at search.gst.gov.in.", "hi": "{inv} का GSTIN जांचें: search.gst.gov.in।", "mr": "{inv} चा GSTIN तपासा: search.gst.gov.in."},
        "circular_transaction": {"en": "URGENT: Investigate circular chain for {inv}. Keep all documentation.", "hi": "तुरंत: {inv} की चक्रीय श्रृंखला जांचें।", "mr": "तातडी: {inv} ची चक्रीय साखळी तपासा."},
    }

    for idx, ic in enumerate(sorted_issues[:10], 1):
        issue_type = ic["issue_type"]
        inv        = ic.get("invoice", "N/A")
        tmpl       = actions.get(issue_type, {"en": "Fix issue {inv} ({type}).", "hi": "समस्या {inv} ठीक करें।", "mr": "समस्या {inv} दुरुस्त करा."})
        action_text = tmpl.get(lang, tmpl.get("en", "")).format(inv=inv, type=issue_type)
        recommendations.append({
            "priority":       idx,
            "issue_type":     issue_type,
            "invoice":        inv,
            "action":         action_text,
            "risk_reduction": f"{ic['fix_reduction']}%",
            "severity":       ic["severity"],
            "category":       ic["category"],
        })
    return recommendations


# ═══════════════════════════════════════════════════════════════
#  NOTICE REPLY DRAFT (unchanged)
# ═══════════════════════════════════════════════════════════════

def generate_notice_reply(
    notice_type: str = "ASMT-10",
    client_name: str = "",
    client_gstin: str = "",
    issues: List[Dict] = None,
    lang: str = "en",
) -> str:
    issues = issues or []
    now    = datetime.now().strftime("%d/%m/%Y")
    if lang == "mr":
        lines = ["प्रति,", "सहाय्यक आयुक्त, GST", "वॉर्ड ____, विभाग ____", "",
                 f"विषय: नोटीस क्र. [______] ला उत्तर | Form {notice_type}",
                 f"GSTIN: {client_gstin}", f"करदाता: {client_name}", "", "मा. महोदय/महोदया,", ""]
        for idx, issue in enumerate(issues[:5], 1):
            lines += [f"{idx}. बीजक {issue.get('invoice','N/A')}: योग्य दुरुस्ती केली आहे. कागदपत्रे जोडली.", ""]
        lines += ["जोडलेली कागदपत्रे: GSTR प्रती, Credit/Debit Notes, Bank Statements", "",
                  "धन्यवाद,", f"[{client_name}]", f"दिनांक: {now}"]
    elif lang == "hi":
        lines = ["सेवा में,", "सहायक आयुक्त, GST", "वार्ड ____, डिवीजन ____", "",
                 f"विषय: नोटिस नं. [______] का जवाब | Form {notice_type}",
                 f"GSTIN: {client_gstin}", f"करदाता: {client_name}", "", "माननीय महोदय,", ""]
        for idx, issue in enumerate(issues[:5], 1):
            lines += [f"{idx}. इनवॉइस {issue.get('invoice','N/A')}: उचित सुधार किया गया। दस्तावेज संलग्न।", ""]
        lines += ["संलग्न: GSTR प्रतियां, Credit/Debit Notes, Bank Statements", "",
                  "धन्यवाद,", f"[{client_name}]", f"दिनांक: {now}"]
    else:
        lines = ["To,", "The Assistant Commissioner of GST", "Ward ____, Division ____", "",
                 f"Subject: Reply to Notice No. [______] — Form {notice_type}",
                 f"GSTIN: {client_gstin}", f"Taxpayer: {client_name}", "", "Respected Sir/Madam,", ""]
        for idx, issue in enumerate(issues[:5], 1):
            lines += [f"{idx}. Invoice {issue.get('invoice','N/A')}: Matter examined. Correction made. Documents enclosed.", ""]
        lines += ["Enclosed: GSTR filed copies, Credit/Debit Note register, Bank Statements", "",
                  "Yours faithfully,", f"[{client_name}]", f"Date: {now}"]
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════
#  MAIN: run_notice_simulation (ENHANCED)
# ═══════════════════════════════════════════════════════════════

def run_notice_simulation(
    issues: List[Dict],
    compliance_score: int = 100,
    client_name: str = "",
    client_gstin: str = "",
    lang: str = "en",
    filing_delays: int = 0,
    turnover_cr: float = 1.0,
    previous_notices: int = 0,
    revenue_data: Optional[Dict] = None,
) -> Dict[str, Any]:
    """
    MAIN FUNCTION — Run complete notice simulation.

    Enhanced output now includes:
      - top_risk_reasons: List[str]  — top 3 human-readable
      - estimated_penalty_exposure: float  — total rupees
      - issue_summary: Dict  — severity counts
      - if_fixed_risk_drop: Dict  — what-if fix all
    All existing keys preserved — backward compatible.
    """
    logger.info(f"Notice simulation | Issues: {len(issues)} | Score: {compliance_score}")

    # Core calculation
    prediction = calculate_notice_probability(
        issues=issues,
        compliance_score=compliance_score,
        filing_delays=filing_delays,
        revenue_data=revenue_data,
        previous_notices=previous_notices,
        turnover_cr=turnover_cr,
    )

    # What-if
    what_if_all      = simulate_what_if(prediction)
    critical_types   = [ic["issue_type"] for ic in prediction["issue_contributions"] if ic["severity"] == "critical"]
    what_if_critical = simulate_what_if(prediction, critical_types) if critical_types else None

    # Recommendations
    recommendations = generate_recommendations(prediction, lang)

    # Risk message
    risk_key     = f"risk_{prediction['risk_level'].lower()}"
    risk_message = _t(risk_key, lang)

    # Notice reply draft
    reply_draft = None
    if prediction["possible_notices"]:
        top_notice = prediction["possible_notices"][0]["notice_type"]
        reply_draft = generate_notice_reply(
            notice_type=top_notice,
            client_name=client_name,
            client_gstin=client_gstin,
            issues=issues,
            lang=lang,
        )

    # ── NEW: Enhanced fields ──────────────────────────────────
    top_risk_reasons = _build_top_risk_reasons(
        category_scores     = prediction.get("category_scores", {}),
        issue_contributions = prediction["issue_contributions"],
        lang                = lang,
    )

    estimated_penalty_exposure = _calc_penalty_exposure(issues)

    issue_summary = _calc_issue_summary_from_list(issues)

    # ── Build final result ────────────────────────────────────
    result = {
        # ── Existing keys (unchanged) ──
        "probability":          prediction["probability"],
        "risk_level":           prediction["risk_level"],
        "risk_message":         risk_message,
        "risk_areas":           prediction["risk_areas"],
        "possible_notices":     prediction["possible_notices"],
        "breakdown":            prediction["breakdown"],
        "revenue_anomaly":      prediction["revenue_anomaly"],
        "what_if_fix_all":      what_if_all,
        "what_if_fix_critical": what_if_critical,
        "recommendations":      recommendations,
        "notice_reply_draft":   reply_draft,
        "labels": {
            "probability": "GST Notice Probability",
            "risk_areas":  "Main Risk Areas",
            "what_if":     "If You Fix These Issues",
            "current":     "Current",
            "after_fix":   "After Fixing",
            "actions":     "Immediate Actions Needed",
            "notices":     "Possible Notice Types",
        },
        # ── NEW keys ──
        "top_risk_reasons":           top_risk_reasons,
        "estimated_penalty_exposure": estimated_penalty_exposure,
        "issue_summary":              issue_summary,
        "if_fixed_risk_drop":         what_if_all,   # alias for frontend
    }

    logger.info(f"Notice sim complete | {prediction['probability']}% | {prediction['risk_level']} | penalty=₹{estimated_penalty_exposure:,.0f}")
    return result