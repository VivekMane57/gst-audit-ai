"""
translations.py
---------------
EN / HI / MR text strings.
Claude API se nahi — hardcoded templates use karo audit issues ke liye.
Accurate legal language ke liye hardcoded better hai.
Claude sirf notice reply aur complex explanations ke liye use hoga.
"""
from typing import Literal

Language = Literal["en", "hi", "mr"]

TRANSLATIONS: dict[str, dict[Language, str]] = {
    # ── Audit Issues ──────────────────────────────────────────────────────────
    "tax_type_mismatch_interstate": {
        "en": (
            "Inter-state supply (different states) but CGST+SGST charged. "
            "IGST should have been applied."
        ),
        "hi": (
            "अंतर-राज्य आपूर्ति पर IGST की जगह CGST+SGST लगाया। "
            "IGST लगना चाहिए था।"
        ),
        "mr": (
            "आंतरराज्य पुरवठ्यावर IGST ऐवजी CGST+SGST आकारला. "
            "IGST आकारणे आवश्यक होते."
        ),
    },
    "tax_type_mismatch_intrastate": {
        "en": (
            "Intra-state supply (same state) but IGST charged. "
            "CGST+SGST should have been applied."
        ),
        "hi": (
            "राज्य के अंदर आपूर्ति पर CGST+SGST की जगह IGST लगाया। "
            "CGST+SGST लगना चाहिए था।"
        ),
        "mr": (
            "राज्यांतर्गत पुरवठ्यावर CGST+SGST ऐवजी IGST आकारला. "
            "CGST+SGST आकारणे आवश्यक होते."
        ),
    },
    "gstr2b_missing": {
        "en": (
            "Supplier has not filed GSTR-1 for this invoice. "
            "ITC cannot be claimed until supplier files."
        ),
        "hi": (
            "सप्लायर ने इस इनवॉइस के लिए GSTR-1 फाइल नहीं की। "
            "जब तक सप्लायर फाइल न करे, ITC क्लेम नहीं कर सकते।"
        ),
        "mr": (
            "पुरवठादाराने या बीजकासाठी GSTR-1 दाखल केली नाही. "
            "पुरवठादाराने दाखल केल्याशिवाय ITC दावा करता येणार नाही."
        ),
    },
    "amount_mismatch": {
        "en": (
            "Invoice amount in books differs from GSTR-2B. "
            "ITC on the difference amount may be disallowed."
        ),
        "hi": (
            "बुक्स और GSTR-2B में राशि अलग है। "
            "अंतर की राशि पर ITC अस्वीकृत हो सकता है।"
        ),
        "mr": (
            "पुस्तके आणि GSTR-2B मधील बीजक रक्कम वेगळी आहे. "
            "फरकाच्या रकमेवर ITC नाकारला जाऊ शकतो."
        ),
    },
    "gstr1_missing": {
        "en": (
            "Invoice recorded in books but not reported in GSTR-1. "
            "Buyer cannot claim ITC. Late fee applicable under Section 47."
        ),
        "hi": (
            "इनवॉइस बुक्स में है लेकिन GSTR-1 में रिपोर्ट नहीं हुई। "
            "खरीदार ITC क्लेम नहीं कर सकता। धारा 47 के तहत विलंब शुल्क लागू।"
        ),
        "mr": (
            "बीजक पुस्तकांमध्ये नोंदवले पण GSTR-1 मध्ये नाही. "
            "खरेदीदार ITC दावा करू शकत नाही. कलम 47 अंतर्गत विलंब शुल्क लागू."
        ),
    },
    "duplicate_invoice": {
        "en": (
            "Duplicate invoice number detected. "
            "Risk of double ITC claim — may attract Section 122 penalty."
        ),
        "hi": (
            "डुप्लीकेट इनवॉइस नंबर मिला। "
            "दोहरे ITC क्लेम का खतरा — धारा 122 के तहत जुर्माना हो सकता है।"
        ),
        "mr": (
            "डुप्लिकेट बीजक क्रमांक आढळला. "
            "दुहेरी ITC दाव्याचा धोका — कलम 122 अंतर्गत दंड होऊ शकतो."
        ),
    },
    "invalid_gstin": {
        "en": "GSTIN format is invalid. Verify with supplier before filing.",
        "hi": "GSTIN फॉर्मेट अमान्य है। फाइलिंग से पहले सप्लायर से जांचें।",
        "mr": "GSTIN स्वरूप अवैध आहे. दाखल करण्यापूर्वी पुरवठादाराकडून तपासा.",
    },
    "gstr1_vs_3b_mismatch": {
        "en": (
            "GSTR-1 total tax differs from GSTR-3B. "
            "Auto-generated notice expected under Section 61."
        ),
        "hi": (
            "GSTR-1 और GSTR-3B का कुल टैक्स अलग है। "
            "धारा 61 के तहत स्वचालित नोटिस की संभावना।"
        ),
        "mr": (
            "GSTR-1 आणि GSTR-3B चा एकूण कर वेगळा आहे. "
            "कलम 61 अंतर्गत स्वयंचलित नोटीस अपेक्षित."
        ),
    },

    # ── Risk Levels ───────────────────────────────────────────────────────────
    "risk_low":      {"en": "LOW RISK",      "hi": "कम जोखिम",    "mr": "कमी धोका"},
    "risk_medium":   {"en": "MEDIUM RISK",   "hi": "मध्यम जोखिम", "mr": "मध्यम धोका"},
    "risk_high":     {"en": "HIGH RISK",     "hi": "उच्च जोखिम",  "mr": "उच्च धोका"},
    "risk_critical": {"en": "CRITICAL RISK", "hi": "गंभीर जोखिम", "mr": "गंभीर धोका"},

    # ── Fix Steps ─────────────────────────────────────────────────────────────
    "fix_credit_note": {
        "en": "Issue a credit note against this invoice",
        "hi": "इस इनवॉइस के विरुद्ध क्रेडिट नोट जारी करें",
        "mr": "या बीजकाविरुद्ध क्रेडिट नोट जारी करा",
    },
    "fix_amend_gstr1": {
        "en": "Amend GSTR-1 in next filing period",
        "hi": "अगले फाइलिंग पीरियड में GSTR-1 संशोधित करें",
        "mr": "पुढील दाखल कालावधीत GSTR-1 दुरुस्त करा",
    },
    "fix_contact_supplier": {
        "en": "Contact supplier immediately and request GSTR-1 filing",
        "hi": "तुरंत सप्लायर से संपर्क करें और GSTR-1 फाइल करने का अनुरोध करें",
        "mr": "तातडीने पुरवठादाराशी संपर्क साधा आणि GSTR-1 दाखल करण्याची विनंती करा",
    },
    "fix_do_not_claim_itc": {
        "en": "Do NOT claim ITC until invoice appears in GSTR-2B",
        "hi": "जब तक इनवॉइस GSTR-2B में न आए, ITC क्लेम न करें",
        "mr": "बीजक GSTR-2B मध्ये येईपर्यंत ITC दावा करू नका",
    },
}


def get_text(key: str, lang: Language = "en") -> str:
    """
    Ek translation string fetch karo.
    Key nahi mili toh English fallback.
    Language nahi mili toh English fallback.
    """
    entry = TRANSLATIONS.get(key)
    if entry is None:
        return key                              # key hi return karo fallback
    return entry.get(lang) or entry.get("en") or key