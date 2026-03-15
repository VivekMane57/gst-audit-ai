"""
notice_simulator.py — GST Notice Prediction Engine
=====================================================
Location: app/services/notice_simulator.py

Predicts the probability of receiving a GST notice based on:
  - Current audit issues (from audit_engine)
  - Filing pattern history
  - Revenue seasonality patterns
  - Supplier risk factors
  - Historical department behavior patterns

Also provides:
  - "What-if" simulation (fix X → probability drops by Y%)
  - Risk area breakdown
  - Recommended actions to reduce notice probability
  - Auto-generated notice reply draft
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
#  NOTICE RISK WEIGHTS (Based on real GST department patterns)
# ═══════════════════════════════════════════════════════════════

# Each issue type contributes to notice probability
ISSUE_WEIGHTS = {
    # Issue Type               → Base %, Max contribution
    "gstin_invalid":            {"weight": 8,  "max": 15, "category": "registration"},
    "tax_type_mismatch":        {"weight": 12, "max": 20, "category": "tax_computation"},
    "gstr1_missing":            {"weight": 10, "max": 18, "category": "filing"},
    "gstr2b_missing":           {"weight": 6,  "max": 12, "category": "itc"},
    "amount_mismatch":          {"weight": 8,  "max": 15, "category": "reconciliation"},
    "duplicate_invoice":        {"weight": 15, "max": 25, "category": "fraud"},
    "circular_trade":           {"weight": 25, "max": 35, "category": "fraud"},
    "filing_delay":             {"weight": 5,  "max": 10, "category": "filing"},
    "rate_mismatch":            {"weight": 7,  "max": 12, "category": "tax_computation"},
    "hsn_mismatch":             {"weight": 4,  "max": 8,  "category": "classification"},
    "rcm_not_paid":             {"weight": 10, "max": 18, "category": "tax_computation"},
    "itc_overclaimed":          {"weight": 18, "max": 30, "category": "itc"},
    "r1_vs_3b_mismatch":        {"weight": 14, "max": 22, "category": "reconciliation"},
    "gstr9_not_filed":          {"weight": 8,  "max": 15, "category": "filing"},
    "eway_bill_missing":        {"weight": 6,  "max": 10, "category": "logistics"},
}

# Risk categories that GST department focuses on
RISK_CATEGORIES = {
    "fraud":            {"label": "Fraud Detection",         "label_hi": "धोखाधड़ी",           "label_mr": "फसवणूक",              "dept_priority": "VERY HIGH"},
    "itc":              {"label": "ITC Irregularities",      "label_hi": "ITC अनियमितताएं",    "label_mr": "ITC अनियमितता",       "dept_priority": "VERY HIGH"},
    "reconciliation":   {"label": "Return Mismatch",        "label_hi": "रिटर्न बेमेल",       "label_mr": "रिटर्न जुळत नाही",    "dept_priority": "HIGH"},
    "tax_computation":  {"label": "Tax Computation Error",   "label_hi": "कर गणना त्रुटि",    "label_mr": "कर गणना त्रुटी",      "dept_priority": "HIGH"},
    "filing":           {"label": "Filing Non-Compliance",   "label_hi": "फाइलिंग गैर-अनुपालन","label_mr": "दाखल अपूर्णता",       "dept_priority": "MEDIUM"},
    "registration":     {"label": "Registration Issues",     "label_hi": "पंजीकरण समस्या",    "label_mr": "नोंदणी समस्या",       "dept_priority": "MEDIUM"},
    "classification":   {"label": "HSN/SAC Classification",  "label_hi": "HSN वर्गीकरण",      "label_mr": "HSN वर्गीकरण",        "dept_priority": "LOW"},
    "logistics":        {"label": "E-Way Bill Issues",       "label_hi": "ई-वे बिल समस्या",   "label_mr": "ई-वे बिल समस्या",     "dept_priority": "LOW"},
}

# Seasonality factors — department sends more notices in certain months
DEPT_ACTIVE_MONTHS = {
    1: 1.2,   # January — post annual return deadline
    2: 1.1,
    3: 1.3,   # March — financial year end rush
    4: 1.0,
    5: 1.0,
    6: 1.1,   # June — GSTR-9 deadline period
    7: 1.0,
    8: 1.0,
    9: 1.2,   # September — half-year review
    10: 1.1,
    11: 1.0,
    12: 1.3,  # December — GSTR-9 filing deadline
}


# ═══════════════════════════════════════════════════════════════
#  MULTI-LANGUAGE TRANSLATIONS
# ═══════════════════════════════════════════════════════════════

NOTICE_LANG = {
    "notice_probability": {
        "en": "GST Notice Probability",
        "hi": "GST नोटिस की संभावना",
        "mr": "GST नोटिसची शक्यता",
    },
    "risk_areas": {
        "en": "Main Risk Areas",
        "hi": "मुख्य जोखिम क्षेत्र",
        "mr": "मुख्य धोका क्षेत्रे",
    },
    "what_if": {
        "en": "If You Fix These Issues",
        "hi": "अगर ये समस्याएं ठीक करें तो",
        "mr": "या समस्या दुरुस्त केल्यास",
    },
    "current": {
        "en": "Current",
        "hi": "वर्तमान",
        "mr": "सध्या",
    },
    "after_fix": {
        "en": "After Fixing",
        "hi": "सुधार के बाद",
        "mr": "दुरुस्तीनंतर",
    },
    "reduction": {
        "en": "Risk Reduction",
        "hi": "जोखिम में कमी",
        "mr": "धोका कमी",
    },
    "notice_types": {
        "en": "Possible Notice Types",
        "hi": "संभावित नोटिस प्रकार",
        "mr": "संभाव्य नोटिस प्रकार",
    },
    "action_needed": {
        "en": "Immediate Actions Needed",
        "hi": "तुरंत कार्रवाई आवश्यक",
        "mr": "तातडीने कारवाई आवश्यक",
    },
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

# Notice types that GST department sends
NOTICE_TYPES = {
    "ASMT-10": {
        "en": "Scrutiny Notice — Department wants to verify your returns",
        "hi": "जांच नोटिस — विभाग आपके रिटर्न सत्यापित करना चाहता है",
        "mr": "तपासणी नोटीस — विभाग तुमचे रिटर्न सत्यापित करू इच्छितो",
        "triggers": ["r1_vs_3b_mismatch", "amount_mismatch", "tax_type_mismatch"],
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
        "triggers": ["circular_trade", "itc_overclaimed", "r1_vs_3b_mismatch"],
    },
    "CMP-05": {
        "en": "Composition Scheme Violation — Show cause for removal",
        "hi": "कंपोजिशन स्कीम उल्लंघन — हटाने के लिए कारण बताओ",
        "mr": "कंपोझिशन स्कीम उल्लंघन — काढून टाकण्यासाठी कारणे दाखवा",
        "triggers": ["tax_type_mismatch", "rate_mismatch"],
    },
}


def _t(key: str, lang: str = "en") -> str:
    """Get translation."""
    return NOTICE_LANG.get(key, {}).get(lang, NOTICE_LANG.get(key, {}).get("en", key))


# ═══════════════════════════════════════════════════════════════
#  CORE: NOTICE PROBABILITY CALCULATOR
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
    """
    Calculate the probability of receiving a GST notice.
    
    Args:
        issues: List of audit issues from audit_engine
        compliance_score: Current compliance score (0-100)
        filing_delays: Number of times GSTR filed late in last 12 months
        revenue_data: Optional monthly revenue dict for seasonality
        months_since_registration: How old is the GST registration
        previous_notices: Number of notices received before
        turnover_cr: Annual turnover in crores
    
    Returns:
        Complete notice prediction with probability, risk areas,
        what-if analysis, and recommended actions.
    """
    
    # ── Step 1: Base probability from issues ──
    base_probability = 5  # Every business has a 5% base risk
    
    category_scores: Dict[str, float] = {}
    issue_contributions: List[Dict] = []
    
    for issue in issues:
        issue_type = issue.get("type", "unknown")
        severity = issue.get("severity", "medium")
        
        weight_info = ISSUE_WEIGHTS.get(issue_type, {"weight": 5, "max": 10, "category": "filing"})
        
        # Severity multiplier
        sev_mult = {"critical": 1.5, "high": 1.0, "medium": 0.6, "low": 0.3}.get(severity, 0.5)
        
        contribution = min(weight_info["weight"] * sev_mult, weight_info["max"])
        category = weight_info["category"]
        
        # Track per-category
        category_scores[category] = category_scores.get(category, 0) + contribution
        
        issue_contributions.append({
            "issue_type": issue_type,
            "invoice": issue.get("invoice", "N/A"),
            "severity": severity,
            "contribution": round(contribution, 1),
            "category": category,
            "fix_reduction": round(contribution * 0.85, 1),  # Fixing removes ~85% of risk
        })
    
    # Sum all issue contributions
    issues_probability = sum(ic["contribution"] for ic in issue_contributions)
    
    # ── Step 2: Filing behavior factor ──
    filing_factor = min(filing_delays * 3, 15)  # Max 15% from late filing
    
    # ── Step 3: Compliance score factor ──
    # Low compliance = higher notice chance
    if compliance_score < 30:
        compliance_factor = 15
    elif compliance_score < 50:
        compliance_factor = 10
    elif compliance_score < 70:
        compliance_factor = 5
    else:
        compliance_factor = 0
    
    # ── Step 4: Turnover factor (higher turnover = more scrutiny) ──
    if turnover_cr > 10:
        turnover_factor = 10
    elif turnover_cr > 5:
        turnover_factor = 7
    elif turnover_cr > 2:
        turnover_factor = 4
    else:
        turnover_factor = 0
    
    # ── Step 5: Previous notice history ──
    history_factor = min(previous_notices * 8, 20)  # Past notices = more scrutiny
    
    # ── Step 6: Seasonality (current month) ──
    current_month = datetime.now().month
    seasonal_multiplier = DEPT_ACTIVE_MONTHS.get(current_month, 1.0)
    
    # ── Step 7: Revenue seasonality check ──
    revenue_factor = 0
    revenue_anomaly = None
    if revenue_data and len(revenue_data) >= 3:
        values = list(revenue_data.values())
        avg_revenue = sum(values) / len(values)
        if avg_revenue > 0:
            for month, rev in revenue_data.items():
                drop_pct = ((avg_revenue - rev) / avg_revenue) * 100
                if drop_pct > 50:  # More than 50% drop
                    revenue_factor = 8
                    revenue_anomaly = {
                        "month": month,
                        "revenue": rev,
                        "average": round(avg_revenue, 0),
                        "drop_percent": round(drop_pct, 1),
                    }
                    break
    
    # ── Calculate total probability ──
    raw_probability = (
        base_probability +
        issues_probability +
        filing_factor +
        compliance_factor +
        turnover_factor +
        history_factor +
        revenue_factor
    )
    
    # Apply seasonal multiplier
    adjusted_probability = raw_probability * seasonal_multiplier
    
    # Cap between 2% and 95%
    final_probability = max(2, min(95, round(adjusted_probability)))
    
    # ── Determine risk level ──
    if final_probability >= 70:
        risk_level = "VERY_HIGH"
    elif final_probability >= 45:
        risk_level = "HIGH"
    elif final_probability >= 25:
        risk_level = "MEDIUM"
    else:
        risk_level = "LOW"
    
    # ── Build category breakdown ──
    risk_areas = []
    for cat, score in sorted(category_scores.items(), key=lambda x: x[1], reverse=True):
        cat_info = RISK_CATEGORIES.get(cat, {})
        risk_areas.append({
            "category": cat,
            "label": cat_info.get("label", cat),
            "label_hi": cat_info.get("label_hi", cat),
            "label_mr": cat_info.get("label_mr", cat),
            "score": round(score, 1),
            "dept_priority": cat_info.get("dept_priority", "MEDIUM"),
        })
    
    # ── Possible notice types ──
    possible_notices = []
    issue_types_found = set(ic["issue_type"] for ic in issue_contributions)
    for notice_id, notice_info in NOTICE_TYPES.items():
        triggers = set(notice_info["triggers"])
        if triggers & issue_types_found:  # If any trigger matches
            overlap = len(triggers & issue_types_found)
            possible_notices.append({
                "notice_type": notice_id,
                "description_en": notice_info["en"],
                "description_hi": notice_info["hi"],
                "description_mr": notice_info["mr"],
                "likelihood": "HIGH" if overlap >= 2 else "MEDIUM",
            })
    
    # ── Probability breakdown ──
    breakdown = {
        "base_risk": base_probability,
        "issues_risk": round(issues_probability, 1),
        "filing_risk": filing_factor,
        "compliance_risk": compliance_factor,
        "turnover_risk": turnover_factor,
        "history_risk": history_factor,
        "revenue_risk": revenue_factor,
        "seasonal_multiplier": seasonal_multiplier,
    }
    
    return {
        "probability": final_probability,
        "risk_level": risk_level,
        "risk_areas": risk_areas,
        "possible_notices": possible_notices,
        "breakdown": breakdown,
        "issue_contributions": issue_contributions,
        "revenue_anomaly": revenue_anomaly,
        "calculated_at": datetime.now().isoformat(),
    }


# ═══════════════════════════════════════════════════════════════
#  WHAT-IF SIMULATOR
# ═══════════════════════════════════════════════════════════════

def simulate_what_if(
    current_prediction: Dict,
    issues_to_fix: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Simulate: "If I fix these issues, what happens to notice probability?"
    
    Args:
        current_prediction: Output from calculate_notice_probability
        issues_to_fix: List of issue types to simulate fixing.
                       If None, simulates fixing ALL issues.
    
    Returns:
        What-if analysis with new probability and reduction details.
    """
    current_prob = current_prediction["probability"]
    contributions = current_prediction["issue_contributions"]
    
    if issues_to_fix is None:
        # Fix everything
        issues_to_fix_set = set(ic["issue_type"] for ic in contributions)
    else:
        issues_to_fix_set = set(issues_to_fix)
    
    # Calculate reduction
    total_reduction = 0
    fixes = []
    
    for ic in contributions:
        if ic["issue_type"] in issues_to_fix_set:
            reduction = ic["fix_reduction"]
            total_reduction += reduction
            fixes.append({
                "issue_type": ic["issue_type"],
                "invoice": ic["invoice"],
                "probability_reduction": round(reduction, 1),
            })
    
    new_probability = max(2, round(current_prob - total_reduction))
    
    # New risk level
    if new_probability >= 70:
        new_risk_level = "VERY_HIGH"
    elif new_probability >= 45:
        new_risk_level = "HIGH"
    elif new_probability >= 25:
        new_risk_level = "MEDIUM"
    else:
        new_risk_level = "LOW"
    
    return {
        "current_probability": current_prob,
        "new_probability": new_probability,
        "reduction": round(current_prob - new_probability, 1),
        "reduction_percent": round(((current_prob - new_probability) / max(current_prob, 1)) * 100, 1),
        "current_risk_level": current_prediction["risk_level"],
        "new_risk_level": new_risk_level,
        "fixes_applied": fixes,
        "fixes_count": len(fixes),
    }


# ═══════════════════════════════════════════════════════════════
#  RECOMMENDED ACTIONS GENERATOR
# ═══════════════════════════════════════════════════════════════

def generate_recommendations(
    prediction: Dict,
    lang: str = "en",
) -> List[Dict]:
    """
    Generate prioritized action items to reduce notice probability.
    """
    recommendations = []
    contributions = prediction.get("issue_contributions", [])
    
    # Sort by contribution (highest risk first)
    sorted_issues = sorted(contributions, key=lambda x: x["contribution"], reverse=True)
    
    for idx, ic in enumerate(sorted_issues[:10], 1):  # Top 10 actions
        issue_type = ic["issue_type"]
        
        # Action templates per issue type
        actions = {
            "duplicate_invoice": {
                "en": f"Remove duplicate invoice {ic['invoice']}. Check purchase register for other duplicates.",
                "hi": f"डुप्लीकेट इनवॉइस {ic['invoice']} हटाएं। अन्य डुप्लीकेट के लिए खरीद रजिस्टर जांचें।",
                "mr": f"डुप्लिकेट बीजक {ic['invoice']} काढा. इतर डुप्लिकेटसाठी खरेदी रजिस्टर तपासा.",
            },
            "tax_type_mismatch": {
                "en": f"Issue credit note for {ic['invoice']} and re-invoice with correct tax type (IGST vs CGST+SGST).",
                "hi": f"{ic['invoice']} के लिए क्रेडिट नोट जारी करें और सही कर प्रकार से पुनः इनवॉइस बनाएं।",
                "mr": f"{ic['invoice']} साठी क्रेडिट नोट जारी करा आणि योग्य कर प्रकारासह पुन्हा बीजक बनवा.",
            },
            "gstr1_missing": {
                "en": f"Add invoice {ic['invoice']} to GSTR-1 immediately. Inform buyer about delay.",
                "hi": f"इनवॉइस {ic['invoice']} तुरंत GSTR-1 में जोड़ें। खरीदार को देरी की सूचना दें।",
                "mr": f"बीजक {ic['invoice']} तातडीने GSTR-1 मध्ये जोडा. खरेदीदाराला उशीराची माहिती द्या.",
            },
            "gstr2b_missing": {
                "en": f"Contact supplier for {ic['invoice']} to file their GSTR-1. Do NOT claim ITC until resolved.",
                "hi": f"{ic['invoice']} के सप्लायर से संपर्क करें GSTR-1 फाइल करवाने के लिए। हल होने तक ITC क्लेम न करें।",
                "mr": f"{ic['invoice']} च्या पुरवठादाराशी संपर्क साधा GSTR-1 दाखल करण्यासाठी. निराकरण होईपर्यंत ITC दावा करू नका.",
            },
            "amount_mismatch": {
                "en": f"Verify correct amount for {ic['invoice']} with supplier. Issue debit/credit note if needed.",
                "hi": f"{ic['invoice']} की सही राशि सप्लायर से कन्फर्म करें। जरूरत हो तो डेबिट/क्रेडिट नोट बनाएं।",
                "mr": f"{ic['invoice']} ची योग्य रक्कम पुरवठादाराकडून निश्चित करा. आवश्यक असल्यास डेबिट/क्रेडिट नोट बनवा.",
            },
            "gstin_invalid": {
                "en": f"Verify correct GSTIN for {ic['invoice']}. Search on GST portal: search.gst.gov.in.",
                "hi": f"{ic['invoice']} के लिए सही GSTIN जांचें। GST पोर्टल पर खोजें: search.gst.gov.in।",
                "mr": f"{ic['invoice']} साठी योग्य GSTIN तपासा. GST पोर्टलवर शोधा: search.gst.gov.in.",
            },
            "circular_trade": {
                "en": f"URGENT: Investigate circular transaction chain. Verify all parties are genuine. Keep documentation.",
                "hi": f"तुरंत: चक्रीय लेनदेन श्रृंखला की जांच करें। सभी पक्ष वास्तविक हैं सत्यापित करें।",
                "mr": f"तातडी: चक्रीय व्यवहार साखळीची तपासणी करा. सर्व पक्ष खरे आहेत याची पडताळणी करा.",
            },
        }
        
        action_text = actions.get(issue_type, {}).get(lang, f"Fix issue {ic['invoice']} ({issue_type})")
        
        recommendations.append({
            "priority": idx,
            "issue_type": issue_type,
            "invoice": ic["invoice"],
            "action": action_text,
            "risk_reduction": f"{ic['fix_reduction']}%",
            "severity": ic["severity"],
            "category": ic["category"],
        })
    
    return recommendations


# ═══════════════════════════════════════════════════════════════
#  NOTICE REPLY DRAFT GENERATOR
# ═══════════════════════════════════════════════════════════════

def generate_notice_reply(
    notice_type: str = "ASMT-10",
    client_name: str = "",
    client_gstin: str = "",
    issues: List[Dict] = None,
    lang: str = "en",
) -> str:
    """
    Generate a professional notice reply draft.
    """
    issues = issues or []
    now = datetime.now().strftime("%d/%m/%Y")
    
    if lang == "mr":
        lines = [
            "प्रति,",
            "सहाय्यक आयुक्त, GST",
            "वॉर्ड ____, विभाग ____",
            "",
            f"विषय: नोटीस क्र. [______] दिनांक [______] ला उत्तर",
            f"संदर्भ: Form {notice_type}",
            f"GSTIN: {client_gstin}",
            f"करदाता: {client_name}",
            "",
            "मा. महोदय/महोदया,",
            "",
            "वरील संदर्भातील नोटिसीच्या अनुषंगाने आमचे उत्तर खालीलप्रमाणे सादर करत आहोत:",
            "",
        ]
    elif lang == "hi":
        lines = [
            "सेवा में,",
            "सहायक आयुक्त, GST",
            "वार्ड ____, डिवीजन ____",
            "",
            f"विषय: नोटिस नं. [______] दिनांक [______] का जवाब",
            f"संदर्भ: Form {notice_type}",
            f"GSTIN: {client_gstin}",
            f"करदाता: {client_name}",
            "",
            "माननीय महोदय/महोदया,",
            "",
            "उपरोक्त संदर्भ में प्राप्त नोटिस के संबंध में हमारा जवाब निम्नानुसार प्रस्तुत है:",
            "",
        ]
    else:
        lines = [
            "To,",
            "The Assistant Commissioner of GST",
            "Ward ____, Division ____",
            "",
            f"Subject: Reply to Notice No. [______] dated [______]",
            f"Reference: Form {notice_type}",
            f"GSTIN: {client_gstin}",
            f"Taxpayer: {client_name}",
            "",
            "Respected Sir/Madam,",
            "",
            "With reference to the above-mentioned notice, we hereby submit our reply as under:",
            "",
        ]
    
    # Add issue-wise responses
    for idx, issue in enumerate(issues[:7], 1):
        inv = issue.get("invoice", "N/A")
        issue_type = issue.get("type", "unknown")
        
        if lang == "mr":
            lines.append(f"{idx}. बीजक {inv} ({issue_type}) बद्दल:")
            lines.append(f"   - ही बाब तपासली असून योग्य दुरुस्ती केली आहे.")
            lines.append(f"   - सहाय्यक कागदपत्रे जोडली आहेत.")
            lines.append("")
        elif lang == "hi":
            lines.append(f"{idx}. इनवॉइस {inv} ({issue_type}) के बारे में:")
            lines.append(f"   - इस मामले की जांच की गई है और उचित सुधार किया गया है।")
            lines.append(f"   - सहायक दस्तावेज संलग्न हैं।")
            lines.append("")
        else:
            lines.append(f"{idx}. Regarding Invoice {inv} ({issue_type}):")
            lines.append(f"   - This matter has been examined and appropriate correction has been made.")
            lines.append(f"   - Supporting documents are enclosed herewith.")
            lines.append("")
    
    # Closing
    if lang == "mr":
        lines.extend([
            "जोडलेली कागदपत्रे:",
            "  - GSTR-1 आणि GSTR-3B दाखल प्रती",
            "  - क्रेडिट/डेबिट नोट रजिस्टर",
            "  - पुरवठादार संवाद पुरावा",
            "  - बँक स्टेटमेंट (लागू असल्यास)",
            "",
            "आम्ही विनम्रपणे विनंती करतो की वरील स्पष्टीकरण स्वीकारावे.",
            "",
            "धन्यवाद,",
            "आपला विश्वासू,",
            f"[{client_name}]",
            f"[{client_gstin}]",
            f"दिनांक: {now}",
        ])
    elif lang == "hi":
        lines.extend([
            "संलग्न दस्तावेज:",
            "  - GSTR-1 और GSTR-3B फाइल कॉपी",
            "  - क्रेडिट/डेबिट नोट रजिस्टर",
            "  - सप्लायर संवाद प्रमाण",
            "  - बैंक स्टेटमेंट (यदि लागू हो)",
            "",
            "हम विनम्रतापूर्वक अनुरोध करते हैं कि उपरोक्त स्पष्टीकरण स्वीकार किया जाए।",
            "",
            "धन्यवाद,",
            "भवदीय,",
            f"[{client_name}]",
            f"[{client_gstin}]",
            f"दिनांक: {now}",
        ])
    else:
        lines.extend([
            "Supporting Documents Enclosed:",
            "  - GSTR-1 & GSTR-3B filed copies",
            "  - Credit/Debit Note register",
            "  - Supplier communication proof",
            "  - Bank statements (if applicable)",
            "",
            "We humbly request that the above clarification be accepted.",
            "",
            "Thanking you,",
            "Yours faithfully,",
            f"[{client_name}]",
            f"[{client_gstin}]",
            f"Date: {now}",
        ])
    
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════
#  MAIN: FULL NOTICE SIMULATION
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
    MAIN FUNCTION: Run complete notice simulation.
    
    Call this from your audit router after running audit_engine.
    
    Returns complete simulation with:
      - Notice probability %
      - Risk level + message
      - Risk area breakdown
      - Possible notice types
      - What-if analysis (fix all)
      - Top recommendations
      - Notice reply draft
    """
    logger.info(f"Running notice simulation | Issues: {len(issues)} | Score: {compliance_score}")
    
    # Calculate probability
    prediction = calculate_notice_probability(
        issues=issues,
        compliance_score=compliance_score,
        filing_delays=filing_delays,
        revenue_data=revenue_data,
        previous_notices=previous_notices,
        turnover_cr=turnover_cr,
    )
    
    # What-if: fix everything
    what_if_all = simulate_what_if(prediction)
    
    # What-if: fix only critical issues
    critical_types = [ic["issue_type"] for ic in prediction["issue_contributions"] if ic["severity"] == "critical"]
    what_if_critical = simulate_what_if(prediction, critical_types) if critical_types else None
    
    # Recommendations
    recommendations = generate_recommendations(prediction, lang)
    
    # Risk message
    risk_key = f"risk_{prediction['risk_level'].lower()}"
    risk_message = _t(risk_key, lang)
    
    # Notice reply draft (for most likely notice type)
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
    
    result = {
        "probability": prediction["probability"],
        "risk_level": prediction["risk_level"],
        "risk_message": risk_message,
        "risk_areas": prediction["risk_areas"],
        "possible_notices": prediction["possible_notices"],
        "breakdown": prediction["breakdown"],
        "revenue_anomaly": prediction["revenue_anomaly"],
        "what_if_fix_all": what_if_all,
        "what_if_fix_critical": what_if_critical,
        "recommendations": recommendations,
        "notice_reply_draft": reply_draft,
        "labels": {
            "probability": _t("notice_probability", lang),
            "risk_areas": _t("risk_areas", lang),
            "what_if": _t("what_if", lang),
            "current": _t("current", lang),
            "after_fix": _t("after_fix", lang),
            "actions": _t("action_needed", lang),
            "notices": _t("notice_types", lang),
        },
    }
    
    logger.info(f"Notice simulation complete | Probability: {prediction['probability']}% | Risk: {prediction['risk_level']}")
    
    return result